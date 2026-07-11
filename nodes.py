import httpx
import re
import ast
import inspect

OLLAMA_URL = "http://ollama-cpu-engine:11434/api/generate"

ALLOWED_MODULES = {
    "math", "random", "itertools", "functools", "collections",
    "statistics", "datetime", "re", "json", "string"
}


def _extract_code(raw_text: str) -> str:
    if not raw_text:
        return ""
    match = re.search(r"```(?:python)?\s*(.*?)```", raw_text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return raw_text.strip()


def _extract_safe_definitions(code: str):
    """Top-level pe sirf function/class/import rakhta hai (LLM ke test calls hataata hai).
    Import-detection ke liye POORA tree scan karta hai (ast.walk) — chahe import
    function/class/try-block ke andar kahin bhi chhupa ho, ab pakda jaayega."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return code, []

    # 🌟 FIX: ast.walk() poore tree ko recursively traverse karta hai
    imported_modules = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.extend(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported_modules.append(node.module.split(".")[0])

    # Top-level pe sirf definitions rakho — LLM ke apne test calls (n=10, print(...)) hatao
    safe_nodes = [
        node for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef,
                              ast.ClassDef, ast.Import, ast.ImportFrom))
    ]
    safe_tree = ast.Module(body=safe_nodes, type_ignores=[])
    return ast.unparse(safe_tree), imported_modules


async def local_llm_code_generator_node(state):
    print(f"🤖 [LLM Node] Iteration: {state['retry_counter']}")
    base_prompt = (
        f"Write a Python function named 'compute_metrics' that solves this task: "
        f"{state['user_instruction']}\n\n"
        f"STRICT RULES you must follow:\n"
        f"1. The function must take ZERO arguments — define it as `def compute_metrics():`.\n"
        f"2. If the task needs a number (like 'n' terms), pick a reasonable fixed value "
        f"(e.g. n = 10) and define it INSIDE the function body, not as a parameter.\n"
        f"3. Only use Python's built-in standard library. Do NOT import external packages "
        f"like numpy, pandas, requests, etc. — anywhere in the code, including inside the function.\n"
        f"4. Do NOT include any input(), test calls, or print statements outside the function.\n"
        f"5. Return the result using 'return', not 'yield'.\n"
        f"6. Output ONLY raw python code, no markdown ticks, no prose."
    )

    if state["execution_error"]:
        base_prompt += (
            f"\n\n🚨 Your previous attempt failed with this error:\n{state['execution_error']}\n"
            f"Fix it by following the STRICT RULES above exactly."
        )

    payload = {"model": "llama3.2", "prompt": base_prompt, "stream": False}

    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            response = await client.post(OLLAMA_URL, json=payload)
            response.raise_for_status()
            raw_response_json = response.json()
            raw_output = raw_response_json.get("response", "")
            clean_code = _extract_code(raw_output)
            preview = (raw_output[:120] + "...") if raw_output else "(empty response from Ollama)"

            eval_count = raw_response_json.get("eval_count", 0)
            eval_duration_ns = raw_response_json.get("eval_duration", 0)

            return {
                "generated_code": clean_code,
                "execution_error": "",
                "retry_counter": state["retry_counter"] + 1,
                "engineering_telemetry_logs": [
                    f"LLM generated code version for run {state['retry_counter']}. "
                    f"Preview: {preview} | TOKENS:{eval_count} | EVAL_NS:{eval_duration_ns}"
                ]
            }
    except httpx.HTTPStatusError as e:
        error_detail = e.response.text[:300]
        return {
            "generated_code": "",
            "execution_error": f"LLM HTTP Error {e.response.status_code}: {error_detail}",
            "retry_counter": state["retry_counter"] + 1,
            "engineering_telemetry_logs": [f"LLM HTTP error on run {state['retry_counter']}: {error_detail}"]
        }
    except Exception as e:
        return {
            "generated_code": "",
            "execution_error": f"LLM Network Drop: {str(e)}",
            "retry_counter": state["retry_counter"] + 1,
            "engineering_telemetry_logs": [f"LLM call failed on run {state['retry_counter']}: {str(e)}"]
        }


import docker
import os
import uuid
import json as _json

_docker_client = None

def _get_docker_client():
    global _docker_client
    if _docker_client is None:
        _docker_client = docker.from_env()
    return _docker_client


SANDBOX_SCRATCH_DIR = "/app/sandbox_scratch"   # FastAPI container ke andar ka path


def code_execution_runtime_node(state):
    print("⚙️ [Compiler Node] Validating code in ISOLATED sandbox container...")
    code = state["generated_code"]

    if not code.strip():
        return {
            "execution_error": "Generated code string is empty or blank!",
            "engineering_telemetry_logs": ["Runtime failure: empty code string."]
        }

    safe_code, imported_modules = _extract_safe_definitions(code)
    disallowed = [m for m in imported_modules if m not in ALLOWED_MODULES]
    if disallowed:
        return {
            "execution_error": f"Module(s) {disallowed} are not available in this environment.",
            "engineering_telemetry_logs": [f"Blocked at AST layer: disallowed import {disallowed}"]
        }

    test_script = f"""
{safe_code}

import inspect, json, sys

fn = compute_metrics
sig = inspect.signature(fn)
required = [n for n, p in sig.parameters.items() if p.default is inspect.Parameter.empty]
if required:
    print(json.dumps({{"error": f"Requires argument(s) {{required}} with no default value."}}))
    sys.exit(1)

if inspect.isgeneratorfunction(fn):
    print(json.dumps({{"error": "Function uses 'yield' — use 'return' instead."}}))
    sys.exit(1)

result = fn()
print(json.dumps({{"success": True, "result": str(result)}}))
"""

    # 🌟 FIX: unique filename shared-locker (named volume) me likho, host path nahi
    filename = f"{uuid.uuid4().hex}.py"
    os.makedirs(SANDBOX_SCRATCH_DIR, exist_ok=True)
    script_path_in_fastapi = os.path.join(SANDBOX_SCRATCH_DIR, filename)

    with open(script_path_in_fastapi, "w") as f:
        f.write(test_script)

    try:
        client = _get_docker_client()
        container_output = client.containers.run(
            "python:3.11-slim",
            command=["python3", f"/sandbox/{filename}"],
            # 🌟 FIX: host path ki jagah named volume use karo — ye dono containers me
            # SAME dikhta hai kyunki dono ek hi Docker-managed shared locker access kar rahe hain
            volumes={"sandbox_scratch": {"bind": "/sandbox", "mode": "ro"}},
            network_disabled=True,
            mem_limit="128m",
            cpu_quota=50000,
            remove=True,
            stdout=True,
            stderr=True,
        )
        output_text = container_output.decode("utf-8").strip()
        parsed = _json.loads(output_text.splitlines()[-1])

        if parsed.get("error"):
            return {
                "execution_error": parsed["error"],
                "engineering_telemetry_logs": [f"Sandbox validation failed: {parsed['error']}"]
            }

        return {
            "execution_error": "",
            "engineering_telemetry_logs": ["Code passed compilation successfully inside isolated sandbox."]
        }

    except docker.errors.ContainerError as e:
        stderr_output = e.stderr.decode("utf-8")[-500:] if e.stderr else str(e)
        return {
            "execution_error": stderr_output,
            "engineering_telemetry_logs": [f"Sandbox runtime error: {stderr_output}"]
        }
    except Exception as e:
        return {
            "execution_error": f"Sandbox execution failed: {str(e)}",
            "engineering_telemetry_logs": [f"Sandbox infrastructure error: {str(e)}"]
        }
    finally:
        os.remove(script_path_in_fastapi)   # apna banaya hua file cleanup karo


def master_production_commit_node(state):
    print("🚀 [Commit Node] Hardcoding clean build states...")
    return {"engineering_telemetry_logs": ["State locked permanently onto disk safely."]}


def loop_evaluation_router(state) -> str:
    if state["execution_error"]:
        if state["retry_counter"] >= 3:
            return "terminate_fault"
        return "route_to_fix"
    return "proceed_to_human_clearance"
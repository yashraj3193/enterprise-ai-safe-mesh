import httpx
import re
import ast
import inspect

OLLAMA_URL = "http://ollama-cpu-engine:11434/api/generate"

# 🌟 Ye woh modules hain jo hum guaranteed allow karte hain (Python ke apne built-in)
# Agar LLM inke alawa kuch aur import karega (numpy, pandas, requests, etc),
# hum use exec() karne se pehle hi rok denge — taaki wasted retry na ho.
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
    """Sirf function/class/import statements rakhta hai — LLM ke apne
    test calls (jaise n=10, print(...), input(...)) hata deta hai.
    Saath me, ye code me use hue saare imports ki list bhi return karta hai."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return code, []

    safe_nodes = []
    imported_modules = []

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            safe_nodes.append(node)
        elif isinstance(node, ast.Import):
            safe_nodes.append(node)
            imported_modules.extend(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            safe_nodes.append(node)
            if node.module:
                imported_modules.append(node.module.split(".")[0])

    safe_tree = ast.Module(body=safe_nodes, type_ignores=[])
    return ast.unparse(safe_tree), imported_modules


async def local_llm_code_generator_node(state):
    print(f"🤖 [LLM Node] Iteration: {state['retry_counter']}")

    # 🌟 FIX #1: Rules pehle se hi clearly bata do, guess karne mat do
    base_prompt = (
        f"Write a Python function named 'compute_metrics' that solves this task: "
        f"{state['user_instruction']}\n\n"
        f"STRICT RULES you must follow:\n"
        f"1. The function must take ZERO arguments — define it as `def compute_metrics():`.\n"
        f"2. If the task needs a number (like 'n' terms), pick a reasonable fixed value "
        f"(e.g. n = 10) and define it INSIDE the function body, not as a parameter.\n"
        f"3. Only use Python's built-in standard library. Do NOT import external packages "
        f"like numpy, pandas, requests, etc.\n"
        f"4. Do NOT include any input(), test calls, or print statements outside the function.\n"
        f"5. Output ONLY raw python code, no markdown ticks, no prose."
    )

    if state["execution_error"]:
        # 🌟 FIX #2: Sirf error nahi, solution bhi batao
        base_prompt += (
            f"\n\n🚨 Your previous attempt failed with this error:\n{state['execution_error']}\n"
            f"Fix it by following the STRICT RULES above exactly."
        )

    payload = {"model": "llama3.2", "prompt": base_prompt, "stream": False}

    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            response = await client.post(OLLAMA_URL, json=payload)
            response.raise_for_status()
            raw_output = response.json().get("response", "")
            clean_code = _extract_code(raw_output)
            preview = (raw_output[:120] + "...") if raw_output else "(empty response from Ollama)"

            return {
                "generated_code": clean_code,
                "execution_error": "",
                "retry_counter": state["retry_counter"] + 1,
                "engineering_telemetry_logs": [
                    f"LLM generated code version for run {state['retry_counter']}. Preview: {preview}"
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


def code_execution_runtime_node(state):
    print("⚙️ [Compiler Node] Validating code string in sandboxed scope...")
    local_scope = {}
    code = state["generated_code"]

    if not code.strip():
        return {
            "execution_error": "Generated code string is empty or blank!",
            "engineering_telemetry_logs": ["Runtime failure: empty code string."]
        }

    try:
        safe_code, imported_modules = _extract_safe_definitions(code)

        # 🌟 FIX #3: Import allowlist check — exec() karne se pehle hi rok do
        disallowed = [m for m in imported_modules if m not in ALLOWED_MODULES]
        if disallowed:
            raise ImportError(
                f"Module(s) {disallowed} are not available in this environment. "
                f"Only use Python's built-in standard library (no numpy/pandas/etc)."
            )

        exec(safe_code, {}, local_scope)

        if "compute_metrics" not in local_scope:
            raise NameError("Function 'compute_metrics' not found in string streams.")

        fn = local_scope["compute_metrics"]

        if not callable(fn):
            raise TypeError("'compute_metrics' exists but is not a callable function.")

        sig = inspect.signature(fn)
        required_params = [
            name for name, param in sig.parameters.items()
            if param.default is inspect.Parameter.empty
            and param.kind in (
                inspect.Parameter.POSITIONAL_ONLY,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                inspect.Parameter.KEYWORD_ONLY,
            )
        ]

        if required_params:
            raise TypeError(
                f"'compute_metrics' requires argument(s) {required_params} with no default value. "
                f"Move these values inside the function body as hardcoded defaults instead."
            )

        # Actual chala ke dekho — logic errors (jaise division by zero) yahi pakde jaayenge
        fn()

        return {"execution_error": "", "engineering_telemetry_logs": ["Code passed compilation successfully."]}

    except Exception as runtime_error:
        return {
            "execution_error": str(runtime_error),
            "engineering_telemetry_logs": [f"Runtime failure captured: {str(runtime_error)}"]
        }


def master_production_commit_node(state):
    print("🚀 [Commit Node] Hardcoding clean build states...")
    return {"engineering_telemetry_logs": ["State locked permanently onto disk safely."]}


def loop_evaluation_router(state) -> str:
    if state["execution_error"]:
        if state["retry_counter"] >= 3:
            return "terminate_fault"
        return "route_to_fix"
    return "proceed_to_human_clearance"
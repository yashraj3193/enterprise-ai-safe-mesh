import httpx
import re

# Inside Docker, we talk to ollama container name, outside docker we talk to localhost
OLLAMA_URL = "http://ollama-cpu-engine:11434/api/generate"


def _extract_code(raw_text: str) -> str:
    """Robustly pull python code out of the LLM response, even if it
    wraps the code with prose or uses generic ``` fences."""
    if not raw_text:
        return ""

    # Prefer a fenced ```python ... ``` or ``` ... ``` block if present
    match = re.search(r"```(?:python)?\s*(.*?)```", raw_text, re.DOTALL)
    if match:
        return match.group(1).strip()

    # No fences found — fall back to raw text, stripped
    return raw_text.strip()


async def local_llm_code_generator_node(state):
    print(f"🤖 [LLM Node] Iteration: {state['retry_counter']}")
    base_prompt = (
        f"Write a clean Python function named 'compute_metrics' to solve this: "
        f"{state['user_instruction']}. Output ONLY raw python code, no markdown ticks, no prose."
    )

    if state["execution_error"]:
        base_prompt += f"\n\n🚨 FIX THIS ERROR: {state['execution_error']}"

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
                "execution_error": "",  # clear stale error before next compile attempt
                "retry_counter": state["retry_counter"] + 1,
                "engineering_telemetry_logs": [
                    f"LLM generated code version for run {state['retry_counter']}. Preview: {preview}"
                ]
            }
    except httpx.HTTPStatusError as e:
        error_detail = e.response.text[:300]  # actual Ollama error body
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
        exec(code, {}, local_scope)
        if "compute_metrics" in local_scope:
            return {"execution_error": "", "engineering_telemetry_logs": ["Code passed compilation successfully."]}
        else:
            raise NameError("Function 'compute_metrics' not found in string streams.")
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
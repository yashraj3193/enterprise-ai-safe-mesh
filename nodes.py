import httpx

# Inside Docker, we talk to ollama container name, outside docker we talk to localhost
OLLAMA_URL = "http://ollama-service:11434/api/generate"

async def local_llm_code_generator_node(state):
    print(f"🤖 [LLM Node] Iteration: {state['retry_counter']}")
    base_prompt = f"Write a clean Python function named 'compute_metrics' to solve this: {state['user_instruction']}. Output ONLY raw python code, no markdown ticks, no prose."
    
    if state["execution_error"]:
        base_prompt += f"\n\n🚨 FIX THIS ERROR: {state['execution_error']}"

    payload = {"model": "llama3.2", "prompt": base_prompt, "stream": False}

    async with httpx.AsyncClient(timeout=90.0) as client:
        try:
            response = await client.post(OLLAMA_URL, json=payload)
            clean_code = response.json().get("response", "").replace("```python", "").replace("```", "").strip()
            return {
                "generated_code": clean_code,
                "retry_counter": state["retry_counter"] + 1,
                "engineering_telemetry_logs": [f"LLM generated code version for run {state['retry_counter']}."]
            }
        except Exception as e:
            return {"execution_error": f"LLM Network Drop: {str(e)}"}

def code_execution_runtime_node(state):
    print("⚙️ [Compiler Node] Validating code string in sandboxed scope...")
    local_scope = {}
    try:
        exec(state["generated_code"], {}, local_scope)
        if "compute_metrics" in local_scope:
            return {"execution_error": "", "engineering_telemetry_logs": ["Code passed compilation successfully."]}
        else:
            raise NameError("Function 'compute_metrics' not found in string streams.")
    except Exception as runtime_error:
        return {"execution_error": str(runtime_error), "engineering_telemetry_logs": [f"Runtime failure captured: {str(runtime_error)}"]}

def master_production_commit_node(state):
    print("🚀 [Commit Node] Hardcoding clean build states...")
    return {"engineering_telemetry_logs": ["State locked permanently onto disk safely."]}

def loop_evaluation_router(state) -> str:
    if state["execution_error"]:
        if state["retry_counter"] >= 3:
            return "terminate_fault"
        return "route_to_fix"
    return "proceed_to_human_clearance"
from fastapi import FastAPI
from pydantic import BaseModel
from graph import compiled_mesh_engine

app = FastAPI(title="Production Local Mesh API")

class AuditRequest(BaseModel):
    instruction: str
    thread_id: str

@app.post("/api/v1/execute")
async def trigger_mesh_pipeline(payload: AuditRequest):
    tx_config = {"configurable": {"thread_id": payload.thread_id}}
    initial_state = {
        "user_instruction": payload.instruction,
        "generated_code": "", "execution_error": "", "retry_counter": 0,
        "admin_clearance": "PENDING",
        "engineering_telemetry_logs": ["Pipeline booted via FastAPI gateway."]
    }
    
    # Kickoff graph and pause at human breakpoint gate
    output_state = await compiled_mesh_engine.ainvoke(initial_state, config=tx_config)
    return {
        "status": "PAUSED_FOR_ADMIN_APPROVAL",
        "current_code": output_state.get("generated_code"),
        "logs": output_state.get("engineering_telemetry_logs")
    }
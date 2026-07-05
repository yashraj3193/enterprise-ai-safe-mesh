from contextlib import asynccontextmanager
from fastapi import FastAPI
from pydantic import BaseModel
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from graph import mesh_builder

# State storage for our runtime engine instance
compiled_mesh_engine = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global compiled_mesh_engine
    # Setup connection safely inside FastAPI's running async event loop
    async with AsyncSqliteSaver.from_conn_string("/app/data/audit_state.db") as checkpointer:
        compiled_mesh_engine = mesh_builder.compile(
            checkpointer=checkpointer,
            interrupt_before=["production_commit"]
        )
        print("💥 Elite AI Safe-Mesh Engine compiled with Async State Persistence successfully!")
        yield
    # Connection cleanly teardown here when app closes

app = FastAPI(title="Production Local Mesh API", lifespan=lifespan)

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
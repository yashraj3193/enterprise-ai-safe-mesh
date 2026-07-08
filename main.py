from contextlib import asynccontextmanager
from fastapi import FastAPI
from pydantic import BaseModel
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver 
from graph import mesh_builder

# Global state store for our runtime engine instance
compiled_mesh_engine = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global compiled_mesh_engine
    # Setup connection safely inside FastAPI's running async event loop
    async with AsyncSqliteSaver.from_conn_string("/app/data/audit_state.db") as checkpointer:
        compiled_mesh_engine = mesh_builder.compile(
            checkpointer=checkpointer,
            interrupt_before=["production_commit"]  # Breaks exactly before production commit
        )
        print("💥 Elite AI Safe-Mesh Engine compiled with Async State Persistence successfully!")
        yield
    # Connection cleanly teardown here when app closes

app = FastAPI(title="Production Local Mesh API", lifespan=lifespan)

# --- REQUEST SCHEMAS ---

class AuditRequest(BaseModel):
    instruction: str
    thread_id: str

# 🌟 NEW MODEL: Admin decision structure
class ApproveRequest(BaseModel):
    thread_id: str
    decision: str  # Must pass "APPROVED" or "REJECTED"


# --- ENDPOINTS ---

@app.post("/api/v1/execute")
async def trigger_mesh_pipeline(payload: AuditRequest):
    tx_config = {"configurable": {"thread_id": payload.thread_id}}
    initial_state = {
        "user_instruction": payload.instruction,
        "generated_code": "", 
        "execution_error": "", 
        "retry_counter": 0,
        "admin_clearance": "PENDING",
        "engineering_telemetry_logs": ["Pipeline booted via FastAPI gateway."]
    }
    
    # Kickoff graph run execution
    output_state = await compiled_mesh_engine.ainvoke(initial_state, config=tx_config)
    
    # 🌟 CRITICAL FIX: Check if graph is actually halted at an interrupt boundary
    current_graph_state = await compiled_mesh_engine.aget_state(tx_config)
    
    if current_graph_state.next:  # If next node exists, it means we are paused safely at 'production_commit'
        return {
            "status": "PAUSED_FOR_ADMIN_APPROVAL",
            "current_code": output_state.get("generated_code"),
            "logs": output_state.get("engineering_telemetry_logs")
        }
    else:  # If next is empty [], graph bypassed the gate and hit END (Max Retries Crashed)
        return {
            "status": "PIPELINE_CRASHED_MAX_RETRIES_REACHED",
            "current_code": output_state.get("generated_code"),
            "logs": output_state.get("engineering_telemetry_logs")
        }

# 🌟 NEW ENDPOINT: Human-In-The-Loop Approval Mechanism
@app.post("/api/v1/approve")
async def approve_mesh_pipeline(payload: ApproveRequest):
    global compiled_mesh_engine
    tx_config = {"configurable": {"thread_id": payload.thread_id}}
    
    if payload.decision.upper() == "APPROVED":
        # 1. Manually write approval stamp to disk database state
        await compiled_mesh_engine.aupdate_state(
            tx_config, 
            {
                "admin_clearance": "APPROVED",
                "engineering_telemetry_logs": ["Admin clearance granted. Resuming pipeline execution."]
            }, 
            as_node="production_commit"
        )
        
        # 2. Resume graph from where it was frozen by passing None
        output_state = await compiled_mesh_engine.ainvoke(None, config=tx_config)
        
        return {
            "status": "SUCCESSFULLY_COMMITTED_TO_PRODUCTION",
            "final_code": output_state.get("generated_code"),
            "logs": output_state.get("engineering_telemetry_logs")
        }
        
    else:
        # If admin rejects, update state and do not trigger ainvoke(None) to let it terminate
        await compiled_mesh_engine.aupdate_state(
            tx_config, 
            {
                "admin_clearance": "REJECTED",
                "engineering_telemetry_logs": ["Admin clearance DENIED. Aborting state generation."]
            }, 
            as_node="production_commit"
        )
        return {
            "status": "PIPELINE_TERMINATED_BY_ADMIN",
            "message": "The generated code was rejected by the supervisor."
        }
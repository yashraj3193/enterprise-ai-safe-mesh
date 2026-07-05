from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from state import MeshSystemState
from nodes import (
    local_llm_code_generator_node,
    code_execution_runtime_node,
    master_production_commit_node,
    loop_evaluation_router
)

mesh_builder = StateGraph(MeshSystemState)
mesh_builder.add_node("llm_generator", local_llm_code_generator_node)
mesh_builder.add_node("runtime_compiler", code_execution_runtime_node)
mesh_builder.add_node("production_commit", master_production_commit_node)

mesh_builder.add_edge(START, "llm_generator")
mesh_builder.add_edge("llm_generator", "runtime_compiler")
mesh_builder.add_conditional_edges(
    "runtime_compiler",
    loop_evaluation_router,
    {
        "route_to_fix": "llm_generator",
        "terminate_fault": END,
        "proceed_to_human_clearance": "production_commit"
    }
)
mesh_builder.add_edge("production_commit", END)

# We initialize checkpointer inside the runtime lifespan loop in main.py to handle async loops cleanly.
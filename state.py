from typing import Annotated, TypedDict
import operator

class MeshSystemState(TypedDict):
    user_instruction: str
    generated_code: str
    execution_error: str
    retry_counter: int
    admin_clearance: str
    engineering_telemetry_logs: Annotated[list[str], operator.add]
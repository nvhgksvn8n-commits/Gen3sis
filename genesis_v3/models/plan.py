from pydantic import BaseModel
from typing import List, Dict, Any

class ExecutionPlan(BaseModel):
    task_id: str
    goal: str
    steps: List[Dict[str, Any]]
    selected_capabilities: List[str]
    expected_output: Any | None = None

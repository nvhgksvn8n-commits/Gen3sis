from typing import List
from genesis_v3.models.plan import ExecutionPlan

class Planner:
    def __init__(self, registry):
        self.registry = registry

    def create_plan(self, task_id: str, goal: str) -> ExecutionPlan:
        # Very small planner: if goal mentions 'median' plan to find sorter then median
        steps = []
        if 'median' in goal.lower():
            # request sorter capability
            steps.append({"capability_query":"sort", "input_from":"user"})
            steps.append({"capability_query":"median", "input_from":"step_1"})
        else:
            steps.append({"capability_query":goal, "input_from":"user"})
        return ExecutionPlan(task_id=task_id, goal=goal, steps=steps, selected_capabilities=[])

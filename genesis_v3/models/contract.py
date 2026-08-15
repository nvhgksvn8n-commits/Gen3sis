from pydantic import BaseModel
from typing import Any

class CapabilityContract(BaseModel):
    input_schema: Any | None = None
    output_schema: Any | None = None
    preconditions: Any | None = None
    postconditions: Any | None = None
    deterministic: bool = True
    resource_limits: Any | None = None

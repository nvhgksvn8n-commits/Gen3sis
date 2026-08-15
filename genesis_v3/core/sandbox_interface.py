from typing import Protocol, Optional
from pydantic import BaseModel
from typing import Any, Dict

class SandboxResult(BaseModel):
    success: bool
    output: Any | None = None
    error: str | None = None
    execution_time: float | None = None
    resources: Dict[str, Any] | None = None

class Sandbox(Protocol):
    def execute(
        self,
        artifact_hash: str,
        entrypoint: str,
        inputs: Dict[str, Any],
        limits: Dict[str, Any] | None = None,
    ) -> SandboxResult:
        ...

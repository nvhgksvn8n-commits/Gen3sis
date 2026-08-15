from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class CognitiveSnapshot(BaseModel):
    snapshot_id: str
    parent_id: Optional[str]
    timestamp: datetime
    schema_version: str = '1.0'
    capability_registry_hash: str | None
    dependency_graph_hash: str | None
    active_capability_ids: List[str] = []

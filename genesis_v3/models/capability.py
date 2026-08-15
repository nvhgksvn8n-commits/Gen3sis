from datetime import datetime
from pydantic import BaseModel
from typing import List, Optional

class CapabilityArtifact(BaseModel):
    capability_id: str
    name: str
    description: Optional[str]
    version: str
    status: str
    bundle_hash: str
    manifest_hash: str
    contract_hash: str
    implementation_hash: str
    test_hash: str | None = None
    dependencies: List[str] = []
    created_at: datetime

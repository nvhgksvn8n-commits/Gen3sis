from genesis_v3.core.planner import Planner
from genesis_v3.core.composer import Composer
from genesis_v3.registry.database import CapabilityRegistry
from genesis_v3.storage.cas import ContentAddressableStore
from genesis_v3.core.snapshot import SnapshotManager
from genesis_v3.core.sandbox import MockSandbox
from genesis_v3.core.verifier import Verifier

class GenesisAgent:
    def __init__(self, db_path=':memory:'):
        self.cas = ContentAddressableStore('content_store')
        self.registry = CapabilityRegistry(db_path)
        self.planner = Planner(self.registry)
        self.composer = Composer(self.registry)
        self.sandbox = MockSandbox(self.cas)
        self.snapshot_mgr = SnapshotManager(self.registry, self.cas)
        self.verifier = Verifier()

    def run_task(self, task_id: str, goal: str):
        plan = self.planner.create_plan(task_id, goal)
        # Try to execute plan; pass verifier to enforce activation gating
        result = self.composer.execute_plan(plan, self.sandbox, self.registry, self.cas, self.snapshot_mgr, self.verifier)
        return result

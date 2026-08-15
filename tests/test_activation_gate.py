import os
import json
from genesis_v3.core.verifier import VerificationResult


def test_activation_gate(tmp_path):
    from genesis_v3.storage.cas import ContentAddressableStore
    from genesis_v3.registry.database import CapabilityRegistry
    from genesis_v3.core.snapshot import SnapshotManager
    from genesis_v3.core.composer import Composer
    from genesis_v3.core.sandbox import MockSandbox

    cas = ContentAddressableStore(str(tmp_path / 'cas'))
    db = CapabilityRegistry(':memory:')
    sm = SnapshotManager(db, cas, base_dir=str(tmp_path / 'snapshots'))
    composer = Composer(db)
    sandbox = MockSandbox(cas)

    # seed registry with sorter implementation
    impl = 'def sort_list(lst):\n    return sorted(lst)\n'
    h = cas.store_bytes(impl.encode())
    db.register('skill_002_sort','sort','0.1','ACTIVE',h)

    # create initial snapshot
    sm.prepare_snapshot('initial')
    sm.commit_snapshot('initial')
    active_path = os.path.join(str(tmp_path / 'snapshots'), 'ACTIVE')
    with open(active_path, 'r') as f:
        assert f.read().strip() == 'initial'

    # Mock verifier that returns FAIL
    class MockVerifierFail:
        def verify_capability(self, capability_id, cas_, registry_, sandbox_, tests=None):
            return VerificationResult(status='FAIL', capability_id=capability_id, artifact_hash='h', tests_run=1, tests_passed=0, tests_failed=1, errors=['failed'], duration=0.0, provenance={})

    # Attempt to execute plan with failing verifier; activation should NOT change ACTIVE
    plan = type('P', (), {'goal':'median: [3,1,2]'})()
    res = composer.execute_plan(plan, sandbox, db, cas, sm, MockVerifierFail())
    assert res['action'] == 'rejected'
    with open(active_path, 'r') as f:
        assert f.read().strip() == 'initial'

    # Mock verifier that returns INCONCLUSIVE
    class MockVerifierInconclusive:
        def verify_capability(self, capability_id, cas_, registry_, sandbox_, tests=None):
            return VerificationResult(status='INCONCLUSIVE', capability_id=capability_id, artifact_hash='h', tests_run=0, tests_passed=0, tests_failed=0, errors=[], duration=0.0, provenance={})

    res2 = composer.execute_plan(plan, sandbox, db, cas, sm, MockVerifierInconclusive())
    assert res2['action'] == 'rejected'
    with open(active_path, 'r') as f:
        assert f.read().strip() == 'initial'

    # Mock verifier that returns INFRASTRUCTURE_ERROR
    class MockVerifierInfra:
        def verify_capability(self, capability_id, cas_, registry_, sandbox_, tests=None):
            return VerificationResult(status='INFRASTRUCTURE_ERROR', capability_id=capability_id, artifact_hash='h', tests_run=0, tests_passed=0, tests_failed=0, errors=['err'], duration=0.0, provenance={})

    res3 = composer.execute_plan(plan, sandbox, db, cas, sm, MockVerifierInfra())
    assert res3['action'] == 'rejected'
    with open(active_path, 'r') as f:
        assert f.read().strip() == 'initial'

    # Mock verifier that returns PASS -> activation should occur
    class MockVerifierPass:
        def verify_capability(self, capability_id, cas_, registry_, sandbox_, tests=None):
            return VerificationResult(status='PASS', capability_id=capability_id, artifact_hash='h', tests_run=1, tests_passed=1, tests_failed=0, errors=[], duration=0.0, provenance={})

    res4 = composer.execute_plan(plan, sandbox, db, cas, sm, MockVerifierPass())
    assert res4['action'] == 'created_capability'
    with open(active_path, 'r') as f:
        assert f.read().strip() == 'median_created'

import os

def test_verifier_success(tmp_path):
    from genesis_v3.storage.cas import ContentAddressableStore
    from genesis_v3.registry.database import CapabilityRegistry
    from genesis_v3.core.sandbox import MockSandbox
    from genesis_v3.core.verifier import Verifier

    cas = ContentAddressableStore(str(tmp_path / 'cas'))
    db = CapabilityRegistry(':memory:')
    # prepare a sort implementation
    impl = 'def sort_list(lst):\n    return sorted(lst)\n'
    h = cas.store_bytes(impl.encode())
    db.register('skill_sort_test','sort','0.1','ACTIVE',h)

    sandbox = MockSandbox(cas)
    verifier = Verifier()
    res = verifier.verify_capability('skill_sort_test', cas, db, sandbox, tests=[{'entrypoint':'sort_list','inputs':{'lst':[3,1,2]},'expected':[1,2,3]}])
    assert res.status == 'PASS'
    assert res.tests_run == 1
    assert res.tests_passed == 1


def test_verifier_incorrect_candidate_fail(tmp_path):
    from genesis_v3.storage.cas import ContentAddressableStore
    from genesis_v3.registry.database import CapabilityRegistry
    from genesis_v3.core.sandbox import MockSandbox
    from genesis_v3.core.verifier import Verifier

    cas = ContentAddressableStore(str(tmp_path / 'cas'))
    db = CapabilityRegistry(':memory:')
    impl = 'def sort_list(lst):\n    return list(reversed(lst))\n'
    h = cas.store_bytes(impl.encode())
    db.register('skill_bad_sort','sort','0.1','ACTIVE',h)
    sandbox = MockSandbox(cas)
    verifier = Verifier()
    res = verifier.verify_capability('skill_bad_sort', cas, db, sandbox, tests=[{'entrypoint':'sort_list','inputs':{'lst':[3,1,2]},'expected':[1,2,3]}])
    assert res.status == 'FAIL'
    assert res.tests_failed == 1


def test_missing_artifact_infrastructure_error(tmp_path):
    from genesis_v3.storage.cas import ContentAddressableStore
    from genesis_v3.registry.database import CapabilityRegistry
    from genesis_v3.core.sandbox import MockSandbox
    from genesis_v3.core.verifier import Verifier

    cas = ContentAddressableStore(str(tmp_path / 'cas'))
    db = CapabilityRegistry(':memory:')
    db.register('skill_missing','missing','0.1','ACTIVE','deadbeef')
    sandbox = MockSandbox(cas)
    verifier = Verifier()
    res = verifier.verify_capability('skill_missing', cas, db, sandbox, tests=[{'entrypoint':'foo','inputs':{},'expected':None}])
    assert res.status == 'INFRASTRUCTURE_ERROR'


def test_invalid_contract_missing_entrypoint(tmp_path):
    from genesis_v3.storage.cas import ContentAddressableStore
    from genesis_v3.registry.database import CapabilityRegistry
    from genesis_v3.core.sandbox import MockSandbox
    from genesis_v3.core.verifier import Verifier

    cas = ContentAddressableStore(str(tmp_path / 'cas'))
    db = CapabilityRegistry(':memory:')
    impl = 'def something_else(x):\n    return x\n'
    h = cas.store_bytes(impl.encode())
    db.register('skill_no_entry','noentry','0.1','ACTIVE',h)
    sandbox = MockSandbox(cas)
    verifier = Verifier()
    res = verifier.verify_capability('skill_no_entry', cas, db, sandbox, tests=[{'entrypoint':'sort_list','inputs':{'lst':[1]},'expected':[1]}])
    assert res.status == 'FAIL'


def test_sandbox_failure_infrastructure(tmp_path):
    from genesis_v3.storage.cas import ContentAddressableStore
    from genesis_v3.registry.database import CapabilityRegistry
    from genesis_v3.core.sandbox import MockSandbox
    from genesis_v3.core.verifier import Verifier
    from genesis_v3.core.sandbox_interface import SandboxResult

    cas = ContentAddressableStore(str(tmp_path / 'cas'))
    db = CapabilityRegistry(':memory:')
    impl = 'def sort_list(lst):\n    return sorted(lst)\n'
    h = cas.store_bytes(impl.encode())
    db.register('skill_sort_fail','sort','0.1','ACTIVE',h)

    # Create a failing sandbox wrapper
    class FailingSandbox(MockSandbox):
        def execute(self, artifact_hash, entrypoint, inputs, limits=None):
            return SandboxResult(success=False, error='simulated sandbox crash')

    sandbox = FailingSandbox(cas)
    verifier = Verifier()
    res = verifier.verify_capability('skill_sort_fail', cas, db, sandbox, tests=[{'entrypoint':'sort_list','inputs':{'lst':[3,1,2]},'expected':[1,2,3]}])
    assert res.status == 'INFRASTRUCTURE_ERROR'

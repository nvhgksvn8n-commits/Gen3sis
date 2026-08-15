import os

def test_no_eval_usage_in_composer():
    path = os.path.join('genesis_v3', 'core', 'composer.py')
    with open(path, 'r') as f:
        src = f.read()
    assert 'eval(' not in src, "composer.py must not use eval()"


def test_snapshot_immutability_and_commit(tmp_path):
    # create a SnapshotManager pointing at tmp snapshots dir
    from genesis_v3.registry.database import CapabilityRegistry
    from genesis_v3.storage.cas import ContentAddressableStore
    from genesis_v3.core.snapshot import SnapshotManager
    db = CapabilityRegistry(':memory:')
    cas = ContentAddressableStore(str(tmp_path / 'cas'))
    sm = SnapshotManager(db, cas, base_dir=str(tmp_path / 'snapshots'))

    # seed registry with a capability entry so manifest has bundle_hash
    os.makedirs('skills/skill_001_add', exist_ok=True)
    db.register('skill_001_add','add','0.1','ACTIVE','deadbeef')

    sm.prepare_snapshot('s1')
    sm.commit_snapshot('s1')
    snap_file = tmp_path / 'snapshots' / 's1.json'
    assert snap_file.exists(), 'Snapshot file must remain in snapshots directory after commit'
    active = tmp_path / 'snapshots' / 'ACTIVE'
    assert active.exists()
    with open(active, 'r') as f:
        content = f.read().strip()
    assert content == 's1'


def test_rollback(tmp_path):
    from genesis_v3.registry.database import CapabilityRegistry
    from genesis_v3.storage.cas import ContentAddressableStore
    from genesis_v3.core.snapshot import SnapshotManager
    db = CapabilityRegistry(':memory:')
    cas = ContentAddressableStore(str(tmp_path / 'cas'))
    sm = SnapshotManager(db, cas, base_dir=str(tmp_path / 'snapshots'))

    db.register('skill_001_add','add','0.1','ACTIVE','hash1')
    sm.prepare_snapshot('s1')
    db.register('skill_002_sort','sort','0.1','ACTIVE','hash2')
    sm.prepare_snapshot('s2')

    sm.commit_snapshot('s1')
    sm.commit_snapshot('s2')
    # ensure ACTIVE points to s2
    with open(os.path.join(str(tmp_path / 'snapshots'), 'ACTIVE'),'r') as f:
        assert f.read().strip() == 's2'

    # rollback to s1
    sm.rollback('s1')
    with open(os.path.join(str(tmp_path / 'snapshots'), 'ACTIVE'),'r') as f:
        assert f.read().strip() == 's1'

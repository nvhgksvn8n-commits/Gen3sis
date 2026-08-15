import os
import json
from datetime import datetime
import hashlib

class SnapshotManager:
    def __init__(self, registry, cas, base_dir='snapshots'):
        self.registry = registry
        self.cas = cas
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)
        self.active_pointer = os.path.join(self.base_dir, 'ACTIVE')

    def prepare_snapshot(self, name: str):
        # create minimal snapshot manifest
        manifest = {
            'snapshot_id': name,
            'timestamp': datetime.utcnow().isoformat(),
            'capabilities': self.registry.list_all()
        }
        path = os.path.join(self.base_dir, f'{name}.json')
        with open(path, 'w') as f:
            json.dump(manifest, f, indent=2)
        return path

    def validate_snapshot(self, name: str) -> bool:
        path = os.path.join(self.base_dir, f'{name}.json')
        if not os.path.exists(path):
            return False
        try:
            with open(path, 'r') as f:
                manifest = json.load(f)
            if manifest.get('snapshot_id') != name:
                return False
            caps = manifest.get('capabilities', [])
            # basic validation: each capability entry should have a bundle_hash
            for c in caps:
                if 'bundle_hash' not in c:
                    return False
            return True
        except Exception:
            return False

    def seal_snapshot(self, name: str):
        # In this minimal implementation sealing is a noop (manifest file persists)
        # Real implementation would store sealed snapshot in CAS and record hash
        path = os.path.join(self.base_dir, f'{name}.json')
        if not os.path.exists(path):
            raise FileNotFoundError('snapshot not found')
        # compute content hash for informational purposes
        with open(path, 'rb') as f:
            data = f.read()
        h = hashlib.sha256(data).hexdigest()
        return h

    def commit_snapshot(self, name: str):
        path = os.path.join(self.base_dir, f'{name}.json')
        if not os.path.exists(path):
            raise FileNotFoundError('snapshot not found')
        # do not move the snapshot file; keep immutable manifest in snapshots/
        # ACTIVE should contain only the pointer (snapshot filename)
        tmp = self.active_pointer + '.tmp'
        # write the pointer atomically: content is the snapshot filename
        with open(tmp, 'w') as f:
            f.write(f"{name}\n")
        os.replace(tmp, self.active_pointer)
        return True

    def rollback(self, name: str):
        # validate target snapshot, then atomically switch ACTIVE pointer
        path = os.path.join(self.base_dir, f'{name}.json')
        if not os.path.exists(path):
            raise FileNotFoundError('snapshot not found')
        if not self.validate_snapshot(name):
            raise RuntimeError('snapshot validation failed')
        tmp = self.active_pointer + '.tmp'
        with open(tmp, 'w') as f:
            f.write(f"{name}\n")
        os.replace(tmp, self.active_pointer)
        return True

    def recover(self):
        # On startup, validate ACTIVE pointer and referenced snapshot.
        if not os.path.exists(self.active_pointer):
            return False
        try:
            with open(self.active_pointer, 'r') as f:
                name = f.read().strip()
            return self.validate_snapshot(name)
        except Exception:
            return False

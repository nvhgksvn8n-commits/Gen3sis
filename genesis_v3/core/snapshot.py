import os
import json
from datetime import datetime

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

    def commit_snapshot(self, name: str):
        path = os.path.join(self.base_dir, f'{name}.json')
        if not os.path.exists(path):
            raise FileNotFoundError('snapshot not found')
        # atomic replace
        tmp = self.active_pointer + '.tmp'
        os.replace(path, tmp)
        os.replace(tmp, self.active_pointer)
        return True

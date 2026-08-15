import sqlite3
import json
from datetime import datetime
import os

class CapabilityRegistry:
    def __init__(self, db_path=':memory:'):
        self.db_path = db_path
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._init_schema()

    def _init_schema(self):
        cur = self._conn.cursor()
        cur.execute('''CREATE TABLE IF NOT EXISTS capabilities(
            capability_id TEXT PRIMARY KEY,
            name TEXT,
            version TEXT,
            status TEXT,
            bundle_hash TEXT,
            created_at TEXT,
            metadata TEXT
        )''')
        self._conn.commit()

    def register(self, capability_id, name, version, status, bundle_hash, metadata=None):
        cur = self._conn.cursor()
        cur.execute('INSERT INTO capabilities(capability_id,name,version,status,bundle_hash,created_at,metadata) VALUES(?,?,?,?,?,?,?)',
                    (capability_id,name,version,status,bundle_hash,datetime.utcnow().isoformat(), json.dumps(metadata or {})))
        self._conn.commit()

    def find_by_name(self, name):
        cur = self._conn.cursor()
        cur.execute('SELECT capability_id,name,version,status,bundle_hash,metadata FROM capabilities WHERE name=?', (name,))
        row = cur.fetchone()
        if not row:
            return None
        return {'capability_id':row[0],'name':row[1],'version':row[2],'status':row[3],'bundle_hash':row[4],'metadata':json.loads(row[5])}

    def list_all(self):
        cur = self._conn.cursor()
        cur.execute('SELECT capability_id,name,version,status,bundle_hash,created_at FROM capabilities')
        rows = cur.fetchall()
        return [{'capability_id':r[0],'name':r[1],'version':r[2],'status':r[3],'bundle_hash':r[4],'created_at':r[5]} for r in rows]

    def load_implementation(self, capability_id):
        # look for file in skills/<capability_id>/implementation.py
        path = os.path.join('skills', capability_id, 'implementation.py')
        if not os.path.exists(path):
            raise FileNotFoundError(path)
        with open(path, 'r') as f:
            return f.read()

    def create_generated_median_capability(self, median_logic_source, cas: 'ContentAddressableStore'):
        # Generate a simple median implementation and register
        capability_id = 'skill_004_median'
        impl = '''def median(lst):\n    s = sorted(lst)\n    n = len(s)\n    if n%2==1:\n        return s[n//2]\n    return (s[n//2-1]+s[n//2])/2\n'''
        os.makedirs(os.path.join('skills', capability_id), exist_ok=True)
        with open(os.path.join('skills', capability_id, 'implementation.py'), 'w') as f:
            f.write(impl)
        bundle_hash = cas.store_bytes(impl.encode())
        self.register(capability_id, 'median', '0.1', 'EXPERIMENTAL', bundle_hash, metadata={'generated':True})
        return {'capability_id':capability_id,'bundle_hash':bundle_hash}

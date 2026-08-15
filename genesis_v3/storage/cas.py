import os
import hashlib

class ContentAddressableStore:
    def __init__(self, root='content_store'):
        self.root = root
        os.makedirs(self.root, exist_ok=True)

    def store_bytes(self, data: bytes) -> str:
        h = hashlib.sha256(data).hexdigest()
        sub = os.path.join(self.root, 'sha256', h[:2])
        os.makedirs(sub, exist_ok=True)
        path = os.path.join(sub, h)
        if not os.path.exists(path):
            with open(path, 'wb') as f:
                f.write(data)
        return h

    def retrieve_bytes(self, h: str) -> bytes:
        path = os.path.join(self.root, 'sha256', h[:2], h)
        with open(path, 'rb') as f:
            return f.read()

    def retrieve_verified(self, expected_hash: str) -> bytes:
        path = os.path.join(self.root, 'sha256', expected_hash[:2], expected_hash)
        if not os.path.exists(path):
            raise FileNotFoundError(path)
        with open(path, 'rb') as f:
            data = f.read()
        h = hashlib.sha256(data).hexdigest()
        if h != expected_hash:
            raise ValueError('CAS integrity check failed: hash mismatch')
        return data

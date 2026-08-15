import os
import json
from datetime import datetime
import hashlib
from typing import Optional

class SnapshotValidationError(Exception):
    pass

class SnapshotManager:
    def __init__(self, registry, cas, base_dir='snapshots'):
        self.registry = registry
        self.cas = cas
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)
        self.active_pointer = os.path.join(self.base_dir, 'ACTIVE')
        self.previous_pointer = os.path.join(self.base_dir, 'PREVIOUS_ACTIVE')
        self.history_file = os.path.join(self.base_dir, 'ACTIVE_HISTORY.json')

    def _manifest_path(self, name: str) -> str:
        return os.path.join(self.base_dir, f'{name}.json')

    def prepare_snapshot(self, name: str):
        # create minimal snapshot manifest (DRAFT)
        manifest = {
            'snapshot_id': name,
            'timestamp': datetime.utcnow().isoformat(),
            'capabilities': self.registry.list_all()
        }
        path = self._manifest_path(name)
        with open(path, 'w') as f:
            json.dump(manifest, f, indent=2)
        return path

    def _load_manifest_by_name(self, name: str) -> dict:
        path = self._manifest_path(name)
        if not os.path.exists(path):
            raise FileNotFoundError(path)
        with open(path, 'r') as f:
            return json.load(f)

    def _canonical_snapshot_bytes(self, manifest: dict) -> bytes:
        # Build canonical representation: include snapshot_id, capabilities, verification_provenance if present
        canonical = {
            'snapshot_id': manifest.get('snapshot_id'),
            'capabilities': manifest.get('capabilities', [])
        }
        # include verification_provenance if present
        if 'verification_provenance' in manifest:
            canonical['verification_provenance'] = manifest['verification_provenance']
        # Deterministic JSON
        return json.dumps(canonical, sort_keys=True, separators=(',',':')).encode('utf-8')

    def validate_snapshot(self, name_or_hash: str) -> bool:
        """
        Validate snapshot by name (draft) or by sealed hash.
        Checks:
          - manifest exists
          - every capability entry has bundle_hash and that artifact exists in CAS
          - if sealed (hash provided), verify provenance CAS entries exist (if referenced)
        """
        try:
            if len(name_or_hash) == 64 and os.path.exists(self._manifest_path(name_or_hash)):
                # sealed manifest file present
                manifest_path = self._manifest_path(name_or_hash)
                with open(manifest_path, 'r') as f:
                    manifest = json.load(f)
                # verify canonical hash matches filename
                canonical = self._canonical_snapshot_bytes(manifest)
                h = hashlib.sha256(canonical).hexdigest()
                if h != name_or_hash:
                    return False
                # fallthrough to deeper checks
            elif len(name_or_hash) == 64:
                # attempt to retrieve from CAS
                try:
                    data = self.cas.retrieve_verified(name_or_hash)
                except Exception:
                    return False
                manifest = json.loads(data.decode('utf-8'))
            else:
                manifest = self._load_manifest_by_name(name_or_hash)

            # check capabilities bundle_hash existence in CAS
            for c in manifest.get('capabilities', []):
                bh = c.get('bundle_hash')
                if not bh:
                    return False
                try:
                    self.cas.retrieve_verified(bh)
                except Exception:
                    return False

            # if verification_provenance present, ensure prov CAS hashes exist
            for vp in manifest.get('verification_provenance', []):
                prov_hash = vp.get('provenance_cas_hash')
                if prov_hash:
                    try:
                        self.cas.retrieve_verified(prov_hash)
                    except Exception:
                        return False

            return True
        except Exception:
            return False

    def seal_snapshot(self, name: str) -> str:
        """
        Seal a draft snapshot: compute canonical bytes, hash, store in CAS, and write sealed manifest file snapshots/<hash>.json
        Returns snapshot_hash
        """
        manifest = self._load_manifest_by_name(name)
        canonical = self._canonical_snapshot_bytes(manifest)
        h = hashlib.sha256(canonical).hexdigest()
        # store in CAS
        cas_hash = self.cas.store_bytes(canonical)
        if cas_hash != h:
            # This should not happen unless CAS store altered content
            raise RuntimeError('CAS returned mismatching hash')
        # write sealed manifest file (canonical JSON) for history
        sealed_path = self._manifest_path(h)
        if not os.path.exists(sealed_path):
            with open(sealed_path, 'wb') as f:
                f.write(canonical)
        return h

    def commit_snapshot(self, name_or_hash: str) -> bool:
        """
        Commit a snapshot to ACTIVE. Accepts either a draft name or a sealed snapshot hash.
        Ensures the snapshot is sealed and verified in CAS before activation.
        """
        # Determine sealed hash
        if len(name_or_hash) == 64:
            snapshot_hash = name_or_hash
            # ensure sealed manifest exists either as file or in CAS
            sealed_path = self._manifest_path(snapshot_hash)
            if os.path.exists(sealed_path):
                # ensure hash matches file
                with open(sealed_path, 'rb') as f:
                    data = f.read()
                if hashlib.sha256(data).hexdigest() != snapshot_hash:
                    raise SnapshotValidationError('sealed manifest content does not match hash')
            else:
                # ensure CAS has it
                try:
                    self.cas.retrieve_verified(snapshot_hash)
                except Exception as e:
                    raise SnapshotValidationError(f'snapshot not sealed in CAS: {e}')
        else:
            # treat as draft name: validate draft then seal it
            if not self.validate_snapshot(name_or_hash):
                raise SnapshotValidationError('draft manifest validation failed')
            snapshot_hash = self.seal_snapshot(name_or_hash)
            # ensure sealed manifest file exists (seal_snapshot writes it)
        # final validation: ensure CAS can retrieve snapshot
        try:
            _ = self.cas.retrieve_verified(snapshot_hash)
        except Exception as e:
            raise SnapshotValidationError(f'CAS retrieval failed for sealed snapshot: {e}')

        # preserve previous ACTIVE
        prev_hash = None
        if os.path.exists(self.active_pointer):
            with open(self.active_pointer, 'r') as f:
                prev_hash = f.read().strip()
            # record previous
            with open(self.previous_pointer, 'w') as f:
                f.write(prev_hash + '\n')
            # append to history
            hist = []
            if os.path.exists(self.history_file):
                try:
                    with open(self.history_file, 'r') as hf:
                        hist = json.load(hf)
                except Exception:
                    hist = []
            hist.append({'activated_at': datetime.utcnow().isoformat(), 'prev': prev_hash, 'new': snapshot_hash})
            with open(self.history_file, 'w') as hf:
                json.dump(hist, hf, indent=2)

        # atomically write ACTIVE as the snapshot hash
        tmp = self.active_pointer + '.tmp'
        with open(tmp, 'w') as f:
            f.write(f"{snapshot_hash}\n")
        os.replace(tmp, self.active_pointer)
        return True

    def rollback(self, snapshot_hash: str) -> bool:
        # validate target snapshot from CAS
        try:
            data = self.cas.retrieve_verified(snapshot_hash)
        except Exception as e:
            raise SnapshotValidationError(f'target snapshot not available in CAS: {e}')
        try:
            manifest = json.loads(data.decode('utf-8'))
        except Exception:
            raise SnapshotValidationError('cannot decode snapshot manifest from CAS')
        # validate referenced artifacts
        for c in manifest.get('capabilities', []):
            bh = c.get('bundle_hash')
            if not bh:
                raise SnapshotValidationError('capability missing bundle_hash')
            try:
                self.cas.retrieve_verified(bh)
            except Exception as e:
                raise SnapshotValidationError(f'capability artifact missing: {e}')
        # update ACTIVE atomically
        prev_hash = None
        if os.path.exists(self.active_pointer):
            with open(self.active_pointer, 'r') as f:
                prev_hash = f.read().strip()
            with open(self.previous_pointer, 'w') as f:
                f.write(prev_hash + '\n')
        tmp = self.active_pointer + '.tmp'
        with open(tmp, 'w') as f:
            f.write(f"{snapshot_hash}\n")
        os.replace(tmp, self.active_pointer)
        # append to history
        hist = []
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r') as hf:
                    hist = json.load(hf)
            except Exception:
                hist = []
        hist.append({'rollback_at': datetime.utcnow().isoformat(), 'prev': prev_hash, 'restored': snapshot_hash})
        with open(self.history_file, 'w') as hf:
            json.dump(hist, hf, indent=2)
        return True

    def recover(self) -> bool:
        # On startup, validate ACTIVE pointer and referenced snapshot.
        if not os.path.exists(self.active_pointer):
            return False
        try:
            with open(self.active_pointer, 'r') as f:
                name = f.read().strip()
            # name is expected to be a snapshot hash
            try:
                data = self.cas.retrieve_verified(name)
            except Exception:
                # attempt to find a recent valid snapshot among sealed files
                sealed_files = []
                for fname in os.listdir(self.base_dir):
                    if len(fname) == 64 and fname.endswith('.json'):
                        sealed_files.append(fname[:-5])
                # sort by file mtime descending
                sealed_files_sorted = sorted(sealed_files, key=lambda h: os.path.getmtime(self._manifest_path(h)), reverse=True)
                for h in sealed_files_sorted:
                    if self.validate_snapshot(h):
                        # restore this snapshot as ACTIVE
                        tmp = self.active_pointer + '.tmp'
                        with open(tmp, 'w') as ftmp:
                            ftmp.write(f"{h}\n")
                        os.replace(tmp, self.active_pointer)
                        return True
                return False
            # validate snapshot content and references
            if not self.validate_snapshot(name):
                # find most recent valid as above
                sealed_files = []
                for fname in os.listdir(self.base_dir):
                    if len(fname) == 64 and fname.endswith('.json'):
                        sealed_files.append(fname[:-5])
                sealed_files_sorted = sorted(sealed_files, key=lambda h: os.path.getmtime(self._manifest_path(h)), reverse=True)
                for h in sealed_files_sorted:
                    if self.validate_snapshot(h):
                        tmp = self.active_pointer + '.tmp'
                        with open(tmp, 'w') as ftmp:
                            ftmp.write(f"{h}\n")
                        os.replace(tmp, self.active_pointer)
                        return True
                return False
            return True
        except Exception:
            return False

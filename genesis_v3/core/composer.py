from typing import Any
import ast
import json
import hashlib
from datetime import datetime

class Composer:
    def __init__(self, registry):
        self.registry = registry

    def execute_plan(self, plan, sandbox, registry, cas, snapshot_mgr, verifier):
        # For this MVP, support median flow specifically but without eval().
        if 'median' in plan.goal.lower():
            arr = plan.goal.split(':')[-1].strip()
            # expect input like 'median: [1,2,3]'
            try:
                # safer literal eval for Python literals only
                arr_eval = ast.literal_eval(arr)
                if not isinstance(arr_eval, (list, tuple)):
                    raise ValueError('expected a list or tuple')
                arr_eval = list(arr_eval)
            except Exception:
                arr_eval = [3,1,2]
            # try to find median capability
            cap = registry.find_by_name('median')
            if cap:
                # use CAS-backed execution
                artifact_hash = cap.get('bundle_hash')
                result = sandbox.execute(artifact_hash, 'median', {'lst':arr_eval})
                if result.success:
                    return {'result': result.output, 'action':'reuse'}
                return {'error': result.error, 'action':'fail'}
            # else try to compose using sort
            sorter = registry.find_by_name('sort')
            if sorter:
                artifact_hash = sorter.get('bundle_hash')
                res = sandbox.execute(artifact_hash, 'sort_list', {'lst':arr_eval})
                if not res.success:
                    return {'error':res.error, 'action':'fail'}
                sorted_list = res.output
                # compute median locally
                n = len(sorted_list)
                if n%2==1:
                    median = sorted_list[n//2]
                else:
                    median = (sorted_list[n//2 -1] + sorted_list[n//2])/2
                # Create a new median capability (simulate creation)
                new_cap = registry.create_generated_median_capability(median_logic_source=None, cas=cas)

                # Run verifier on the new capability and enforce activation gate
                verification = verifier.verify_capability(new_cap['capability_id'], cas, registry, sandbox,
                                                           tests=[{'entrypoint':'median','inputs':{'lst':arr_eval},'expected':median}])

                # Only allow activation if verifier reports PASS
                if verification.status != 'PASS':
                    # Do not prepare or commit snapshot; reject activation
                    return {'result':None, 'action':'rejected', 'verification': verification.dict()}

                # Persist verification provenance in CAS (immutable) before snapshot activation
                prov = {
                    'capability_id': verification.capability_id,
                    'artifact_hash': verification.artifact_hash,
                    'verification_status': verification.status,
                    'verifier_version': verification.provenance.get('verifier_version', 'unknown'),
                    'verification_timestamp': verification.provenance.get('timestamp', datetime.utcnow().isoformat()),
                    'tests_run': verification.tests_run,
                    'tests_passed': verification.tests_passed,
                    'tests_failed': verification.tests_failed,
                    'errors': verification.errors,
                }
                # compute deterministic hash over canonicalized provenance (excluding the hash field)
                canonical = json.dumps(prov, sort_keys=True, separators=(',',':')).encode('utf-8')
                verification_result_hash = hashlib.sha256(canonical).hexdigest()
                prov['verification_result_hash'] = verification_result_hash
                # store the provenance JSON in CAS
                prov_bytes = json.dumps(prov, sort_keys=True, indent=2).encode('utf-8')
                prov_cas_hash = cas.store_bytes(prov_bytes)

                # Build snapshot manifest and include provenance reference
                snapshot_mgr.prepare_snapshot('median_created')
                # update the snapshot manifest to include verification provenance reference
                manifest_path = os.path.join(snapshot_mgr.base_dir, 'median_created.json')
                try:
                    with open(manifest_path, 'r') as f:
                        manifest = json.load(f)
                except Exception:
                    manifest = {'snapshot_id':'median_created','timestamp':datetime.utcnow().isoformat(),'capabilities':registry.list_all()}
                # attach provenance reference
                vp = manifest.get('verification_provenance', [])
                vp.append({
                    'capability_id': prov['capability_id'],
                    'artifact_hash': prov['artifact_hash'],
                    'verification_status': prov['verification_status'],
                    'verification_result_hash': prov['verification_result_hash'],
                    'provenance_cas_hash': prov_cas_hash,
                })
                manifest['verification_provenance'] = vp
                # write back manifest
                with open(manifest_path, 'w') as f:
                    json.dump(manifest, f, indent=2, sort_keys=True)

                # validate snapshot before commit
                if not snapshot_mgr.validate_snapshot('median_created'):
                    # If validation fails, do not activate nor claim activation provenance
                    return {'result':None, 'action':'rejected', 'reason':'snapshot_validation_failed'}

                # commit snapshot (atomic activation)
                snapshot_mgr.commit_snapshot('median_created')
                return {'result':median, 'action':'created_capability', 'new_capability':new_cap, 'verification_provenance_hash': verification_result_hash, 'provenance_cas_hash': prov_cas_hash}
            else:
                return {'error':'no sorter available', 'action':'fail'}
        else:
            return {'error':'unsupported goal', 'action':'fail'}

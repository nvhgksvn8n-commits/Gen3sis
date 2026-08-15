from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

class VerificationResult(BaseModel):
    status: str  # PASS / FAIL / INCONCLUSIVE / INFRASTRUCTURE_ERROR
    capability_id: str
    artifact_hash: Optional[str]
    tests_run: int = 0
    tests_passed: int = 0
    tests_failed: int = 0
    errors: List[str] = []
    duration: float | None = None
    provenance: Dict[str, Any] = {}


class Verifier:
    def __init__(self, version: str = 'v0.1'):
        self.version = version

    def verify_capability(self, capability_id: str, cas, registry, sandbox, tests: List[Dict[str, Any]] | None = None) -> VerificationResult:
        import time
        start = time.time()
        errors: List[str] = []
        tests = tests or []
        # Resolve bundle hash
        try:
            bundle_hash = registry.get_bundle_hash(capability_id)
        except Exception as e:
            duration = time.time() - start
            return VerificationResult(
                status='INFRASTRUCTURE_ERROR',
                capability_id=capability_id,
                artifact_hash=None,
                tests_run=0,
                tests_passed=0,
                tests_failed=0,
                errors=[f'registry error: {e}'],
                duration=duration,
                provenance={
                    'capability_id': capability_id,
                    'artifact_hash': None,
                    'verifier_version': self.version,
                    'timestamp': datetime.utcnow().isoformat(),
                    'tests_executed': [],
                    'result': 'INFRASTRUCTURE_ERROR'
                }
            )

        # Retrieve artifact from CAS
        try:
            artifact_bytes = cas.retrieve_verified(bundle_hash)
        except FileNotFoundError as e:
            duration = time.time() - start
            return VerificationResult(
                status='INFRASTRUCTURE_ERROR',
                capability_id=capability_id,
                artifact_hash=bundle_hash,
                errors=[f'CAS missing artifact: {e}'],
                duration=duration,
                provenance={
                    'capability_id': capability_id,
                    'artifact_hash': bundle_hash,
                    'verifier_version': self.version,
                    'timestamp': datetime.utcnow().isoformat(),
                    'tests_executed': [],
                    'result': 'INFRASTRUCTURE_ERROR'
                }
            )
        except Exception as e:
            duration = time.time() - start
            return VerificationResult(
                status='INFRASTRUCTURE_ERROR',
                capability_id=capability_id,
                artifact_hash=bundle_hash,
                errors=[f'CAS retrieval error: {e}'],
                duration=duration,
                provenance={
                    'capability_id': capability_id,
                    'artifact_hash': bundle_hash,
                    'verifier_version': self.version,
                    'timestamp': datetime.utcnow().isoformat(),
                    'tests_executed': [],
                    'result': 'INFRASTRUCTURE_ERROR'
                }
            )

        try:
            src = artifact_bytes.decode('utf-8')
        except Exception as e:
            duration = time.time() - start
            return VerificationResult(
                status='INFRASTRUCTURE_ERROR',
                capability_id=capability_id,
                artifact_hash=bundle_hash,
                errors=[f'decode error: {e}'],
                duration=duration,
                provenance={
                    'capability_id': capability_id,
                    'artifact_hash': bundle_hash,
                    'verifier_version': self.version,
                    'timestamp': datetime.utcnow().isoformat(),
                    'tests_executed': [],
                    'result': 'INFRASTRUCTURE_ERROR'
                }
            )

        # Basic contract validation: ensure tests reference entrypoints that exist in source
        tests_executed = []
        tests_run = 0
        tests_passed = 0
        tests_failed = 0
        infra_error = False

        for t in tests:
            tests_run += 1
            entrypoint = t.get('entrypoint')
            inputs = t.get('inputs', {})
            expected = t.get('expected', None)
            tests_executed.append({'entrypoint': entrypoint, 'inputs': inputs, 'expected': expected})

            # Check entrypoint presence
            if not entrypoint or f'def {entrypoint}' not in src:
                tests_failed += 1
                errors.append(f'missing entrypoint {entrypoint}')
                continue

            # Execute via sandbox
            try:
                result = sandbox.execute(bundle_hash, entrypoint, inputs)
            except Exception as e:
                infra_error = True
                errors.append(f'sandbox execution raised: {e}')
                break

            if not result.success:
                # Treat sandbox failures as infrastructure errors
                infra_error = True
                errors.append(f'sandbox execution failed: {result.error}')
                break

            # Compare output
            out = result.output
            if out == expected:
                tests_passed += 1
            else:
                tests_failed += 1
                errors.append(f'output mismatch for {entrypoint}: expected={expected}, got={out}')

        duration = time.time() - start

        if infra_error:
            status = 'INFRASTRUCTURE_ERROR'
        elif tests_run == 0:
            status = 'INCONCLUSIVE'
        elif tests_failed > 0:
            status = 'FAIL'
        else:
            status = 'PASS'

        provenance = {
            'capability_id': capability_id,
            'artifact_hash': bundle_hash,
            'verifier_version': self.version,
            'timestamp': datetime.utcnow().isoformat(),
            'tests_executed': tests_executed,
            'result': status,
        }

        return VerificationResult(
            status=status,
            capability_id=capability_id,
            artifact_hash=bundle_hash,
            tests_run=tests_run,
            tests_passed=tests_passed,
            tests_failed=tests_failed,
            errors=errors,
            duration=duration,
            provenance=provenance,
        )

import hashlib
import json
from typing import Any, Dict
from genesis_v3.core.sandbox_interface import Sandbox, SandboxResult

class MockSandbox:
    def __init__(self, cas):
        self.cas = cas

    def execute(self, artifact_hash: str, entrypoint: str, inputs: Dict[str, Any], limits: Dict[str, Any] | None = None) -> SandboxResult:
        # Retrieve artifact via CAS and verify
        try:
            artifact_bytes = self.cas.retrieve_verified(artifact_hash)
        except Exception as e:
            return SandboxResult(success=False, error=f'CAS retrieval failed: {e}')
        try:
            src = artifact_bytes.decode('utf-8')
        except Exception as e:
            return SandboxResult(success=False, error=f'decode error: {e}')

        # Deterministic, pattern-matching execution for test purposes only.
        try:
            if entrypoint == 'sort_list' and 'def sort_list' in src:
                lst = inputs.get('lst', [])
                return SandboxResult(success=True, output=sorted(lst))
            if entrypoint == 'median' and 'def median' in src:
                lst = inputs.get('lst', [])
                s = sorted(lst)
                n = len(s)
                if n % 2 == 1:
                    return SandboxResult(success=True, output=s[n//2])
                return SandboxResult(success=True, output=(s[n//2 -1] + s[n//2]) / 2)
            if entrypoint == 'add' and 'def add' in src:
                a = inputs.get('a'); b = inputs.get('b')
                return SandboxResult(success=True, output=a+b)
            return SandboxResult(success=False, error='Unknown entrypoint or implementation')
        except Exception as e:
            return SandboxResult(success=False, error=str(e))

    # Backwards-compat helper
    def run_python_function(self, implementation_source: str, func_name: str, inputs: dict) -> Any:
        # Keep previous behavior for internal calls that might use run_python_function
        if 'def sort_list' in implementation_source and func_name == 'sort_list':
            lst = inputs.get('lst', [])
            return sorted(lst)
        if 'def median' in implementation_source and func_name == 'median':
            lst = inputs.get('lst', [])
            n = len(lst)
            s = sorted(lst)
            if n%2==1:
                return s[n//2]
            return (s[n//2 -1] + s[n//2])/2
        if 'def add' in implementation_source and func_name == 'add':
            a = inputs.get('a'); b = inputs.get('b')
            return a+b
        raise RuntimeError('Sandbox cannot run unknown implementation in MockSandbox')

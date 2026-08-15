import hashlib
import json
from typing import Any

class MockSandbox:
    def __init__(self, cas):
        self.cas = cas

    def run_python_function(self, implementation_source: str, func_name: str, inputs: dict) -> Any:
        # implementation_source is expected to be python source code string
        # For safety, we do not exec arbitrary code. We detect known capability patterns.
        if 'def sort_list' in implementation_source and func_name=='sort_list':
            # naive parse: find list in inputs
            lst = inputs.get('lst', [])
            return sorted(lst)
        if 'def median' in implementation_source and func_name=='median':
            lst = inputs.get('lst', [])
            n = len(lst)
            s = sorted(lst)
            if n%2==1:
                return s[n//2]
            return (s[n//2 -1] + s[n//2])/2
        if 'def add' in implementation_source and func_name=='add':
            a = inputs.get('a'); b = inputs.get('b')
            return a+b
        # fallback
        raise RuntimeError('Sandbox cannot run unknown implementation in MockSandbox')

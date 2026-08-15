from typing import Any

class Composer:
    def __init__(self, registry):
        self.registry = registry

    def execute_plan(self, plan, sandbox, registry, cas, snapshot_mgr):
        # For this MVP, support median flow specifically.
        if 'median' in plan.goal.lower():
            arr = plan.goal.split(':')[-1].strip()
            # expect input like 'median: [1,2,3]'
            try:
                arr_eval = eval(arr)
            except Exception:
                arr_eval = [3,1,2]
            # try to find median capability
            cap = registry.find_by_name('median')
            if cap:
                impl = registry.load_implementation(cap['capability_id'])
                # execute implementation in sandbox
                res = sandbox.run_python_function(impl, 'median', {'lst':arr_eval})
                return {'result':res, 'action':'reuse'}
            # else try to compose using sort
            sorter = registry.find_by_name('sort')
            if sorter:
                sort_impl = registry.load_implementation(sorter['capability_id'])
                sorted_list = sandbox.run_python_function(sort_impl, 'sort_list', {'lst':arr_eval})
                # compute median locally
                n = len(sorted_list)
                if n%2==1:
                    median = sorted_list[n//2]
                else:
                    median = (sorted_list[n//2 -1] + sorted_list[n//2])/2
                # Create a new median capability (simulate creation)
                new_cap = registry.create_generated_median_capability(median_logic_source=None, cas=cas)
                # Build snapshot and activate
                snapshot_mgr.prepare_snapshot('median_created')
                snapshot_mgr.commit_snapshot('median_created')
                return {'result':median, 'action':'created_capability', 'new_capability':new_cap}
            else:
                return {'error':'no sorter available', 'action':'fail'}
        else:
            return {'error':'unsupported goal', 'action':'fail'}

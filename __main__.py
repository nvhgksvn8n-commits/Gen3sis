#!/usr/bin/env python3
import argparse
from genesis_v3.core.agent import GenesisAgent

if __name__=='__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--task', required=True)
    args = p.parse_args()
    agent = GenesisAgent(db_path=':memory:')
    # seed
    from genesis_v3.core import agent as ag
    # lightweight seeding
    with open('skills/skill_001_add/implementation.py') as f:
        a = f.read()
    agent.cas.store_bytes(a.encode())
    agent.registry.register('skill_001_add','add','0.1','ACTIVE',agent.cas.store_bytes(a.encode()))
    with open('skills/skill_002_sort/implementation.py') as f:
        s = f.read()
    agent.cas.store_bytes(s.encode())
    agent.registry.register('skill_002_sort','sort','0.1','ACTIVE',agent.cas.store_bytes(s.encode()))
    with open('skills/skill_003_reverse/implementation.py') as f:
        r = f.read()
    agent.cas.store_bytes(r.encode())
    agent.registry.register('skill_003_reverse','reverse','0.1','ACTIVE',agent.cas.store_bytes(r.encode()))

    res = agent.run_task('cli', args.task)
    print(res)

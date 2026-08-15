import pytest
from genesis_v3.core.agent import GenesisAgent
import os


def setup_seed_registry(registry, cas):
    # register initial three capabilities
    # skill_001_add
    with open('skills/skill_001_add/implementation.py','r') as f:
        impl = f.read()
    b1 = cas.store_bytes(impl.encode())
    registry.register('skill_001_add','add','0.1','ACTIVE',b1)
    # skill_002_sort
    with open('skills/skill_002_sort/implementation.py','r') as f:
        impl = f.read()
    b2 = cas.store_bytes(impl.encode())
    registry.register('skill_002_sort','sort','0.1','ACTIVE',b2)
    # skill_003_reverse
    with open('skills/skill_003_reverse/implementation.py','r') as f:
        impl = f.read()
    b3 = cas.store_bytes(impl.encode())
    registry.register('skill_003_reverse','reverse','0.1','ACTIVE',b3)


def test_median_evolution(tmp_path):
    agent = GenesisAgent(db_path=':memory:')
    # seed registry
    setup_seed_registry(agent.registry, agent.cas)
    # Run median task; use inline array
    res = agent.run_task('t1', 'median: [3,1,2,5]')
    assert res['action'] == 'created_capability'
    assert res['result'] == 2.5
    # run again - should reuse median capability
    res2 = agent.run_task('t2', 'median: [7,1,3]')
    assert res2['action'] == 'reuse'


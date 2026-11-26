"""Offline before/after traversal counts and durable-byte comparison."""
from contextlib import ExitStack
from copy import deepcopy
import json
from pathlib import Path
import shutil
import socket
import sys
from types import ModuleType
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT/'external/SkillAdam')]
REPORT = ROOT/'docs/methods/v27/memory_publication_20261102'


def before_module(name):
    relative = f'src/skill_evolution/v27/{name}.py'
    module = ModuleType('src.skill_evolution.v27.' + name.replace('/', '.'))
    module.__package__ = module.__name__.rsplit('.', 1)[0]
    exec(compile((REPORT/'before'/relative).read_text(), relative, 'exec'), module.__dict__)
    return module


def main():
    connections = []
    def blocked(*args, **kwargs):
        connections.append('blocked')
        raise AssertionError('Offline synthetic comparison only')
    with ExitStack() as stack:
        for attr in ('connect', 'connect_ex'):
            stack.enter_context(patch.object(socket.socket, attr, blocked))
        stack.enter_context(patch('socket.create_connection', blocked))
        stack.enter_context(patch('subprocess.Popen', blocked))
        stack.enter_context(patch('dotenv.dotenv_values', blocked))
        from tests.skill_evolution.v27.test_memory_publication import MemoryPublicationTests, CONTRACT
        from src.skill_evolution.v27 import evolution, memory_operation
        from src.skill_evolution.v27.contracts import memory
        old = before_module('contracts/memory')
        old_evolution = before_module('evolution'); old_evolution.memory = old
        fixture = MemoryPublicationTests(); fixture.setUp()
        try:
            source = fixture.root/'source'; active = memory.empty_memory()
            for i in range(1, 4):
                fixture.commit(source, f'R{i}', fixture.bundle(active))
                active = fixture.load(source)
            bundle = fixture.bundle(active)
            result = {'entries': []}
            counts, views, commits = {}, {}, {}
            for version, contract in (('before', old), ('after', memory)):
                target = fixture.root/version
                with patch.object(contract, '_archive', wraps=contract._archive) as archive:
                    if version == 'before':
                        old_evolution._prepare_memory(source, target)
                        commits[version] = contract.commit_memory(target, context_id='R4', context=bundle,
                                                                  result=result, memory_contract=CONTRACT)
                        views[version] = contract.load_memory(target, memory_contract=CONTRACT)
                        assert contract.load_memory(target, memory_contract=CONTRACT) == views[version]
                    else:
                        with memory_operation.operation(CONTRACT) as session:
                            evolution._prepare_memory(source, target, session=session)
                            commits[version] = fixture.commit(target, 'R4', bundle, result)
                            views[version] = fixture.load(target)
                            assert fixture.load(target) == views[version]
                            session.verify()
                    counts[version] = archive.call_count
                cold = fixture.root/(version+'_cold'); shutil.copytree(source, cold)
                with patch.object(contract, '_archive', wraps=contract._archive) as archive:
                    contract.commit_memory(cold, context_id='R4', context=deepcopy(bundle),
                                           result=result, memory_contract=CONTRACT)
                counts[version+'_standalone'] = archive.call_count
            assert views['before'] == views['after'] and commits['before'] == commits['after']
            for name in ('active.json', 'archive/R4.json'):
                assert (fixture.root/'before'/name).read_bytes() == (fixture.root/'after'/name).read_bytes()
            assert counts == {'before': 6, 'before_standalone': 2, 'after': 1, 'after_standalone': 1}
        finally:
            fixture.tearDown()
    report = {'status': 'passed', 'seed_commits': 3, 'history_traversals': counts,
              'views_and_commits_equal': True, 'durable_bytes_equal': True,
              'network_attempts': len(connections), 'real_model_requests': 0,
              'note': 'Synthetic publication-only counters; no wall-time speedup or API-cost estimate.'}
    (REPORT/'traversal_comparison.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()

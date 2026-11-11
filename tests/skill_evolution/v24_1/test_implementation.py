"""V24.1 integration: approved text, configuration invariants and offline execution."""
from copy import deepcopy
import json
import subprocess
import sys

import pytest
from src.skill_evolution.v24_1 import baseline, evolution as ev, config
from src.skill_evolution.v24_1.benchmark import current
from .support import migrated, CapturedHarness

STAGES = ['grouping', 'diagnosis', 'preconditioner', 'editor', 'replay']


def test_preparation_matches_exact_baseline(tmp_path):
    evidence, original = baseline.audit()
    value, changes = baseline.resolved_config()
    assert {r['path'] for r in changes} == baseline.ALLOWED_CHANGES
    assert value['method']['knowledge_review'] == 'disabled_v1'
    output = tmp_path/'prepared'
    prepared = baseline.prepare(output)
    assert prepared['model_requests'] == prepared['environment_episodes'] == 0
    assert prepared['workers'] == 10
    assert prepared['batch_sizes'] == [10, 10, 10, 10, 10, 7]
    assert not (output/'S1').exists()
    for p in (baseline.SOURCE/'data').rglob('*'):
        if p.is_file():
            assert p.read_bytes() == (output/'data'/p.relative_to(baseline.SOURCE/'data')).read_bytes()
    for name in ('budget.json', 'initial_baseline_reference.json', 'runtime.json'):
        assert baseline.read(output/'config'/name) == baseline.read(baseline.SOURCE/'config'/name)
    assert baseline.read(output/'config/source_config.json') == original
    with pytest.raises(ValueError, match='new directory'):
        baseline.prepare(output)


def test_production_imports_are_independent():
    code = """
import sys
from src.skill_evolution.v24_1 import evolution, evaluation
from src.skill_evolution.v24_1.benchmarks.alfworld.adapter import ALFWorldAdapter
assert not [n for n in sys.modules if n == 'src.skill_evolution.v24' or n.startswith(('src.skill_evolution.v24.', 'src.skill_evolution.v25', 'src.skill_evolution.v23', 'src.adapters.', 'alfworld', 'textworld'))]
"""
    subprocess.run([sys.executable, '-c', code], cwd=ev.ROOT, check=True, capture_output=True)


def test_actor_command_and_call_settings_unchanged():
    from src.skill_evolution.v24 import evolution as old
    from src.skill_evolution.v24.benchmark import using_benchmark as old_using
    from src.skill_evolution.v24.benchmarks.alfworld.adapter import ALFWorldAdapter as OldAdapter
    _, original = baseline.audit()
    value, _ = baseline.resolved_config()
    for task, final in [('train:0000', False), ('val:0000', False), ('test:0000', True)]:
        new_command = ev.actor_command(task, '/skill.md', '/output', value, final=final)
        with old_using(OldAdapter()):
            old_command = old.actor_command(task, '/skill.md', '/output', original, final=final)
        assert new_command[:2]+new_command[3:] == old_command[:2]+old_command[3:]
        assert new_command[2] == old_command[2].replace('.v24.', '.v24_1.')
    for stage in STAGES:
        assert ev.stage_call_config(value, stage) == old.stage_call_config(original, stage)


@pytest.mark.parametrize('stop', ['diagnosis_no_change', 'preconditioner_no_change'])
def test_no_change_continues_with_same_skill_and_memory(tmp_path, stop):
    h = CapturedHarness()
    h.stop = stop
    ev.run_campaign(tmp_path, config=migrated(2), generate=h.generate, actor_runner=h.actor)
    assert ev.read(tmp_path/'state.json')['next_round'] == 3
    for number in (1, 2):
        result = ev.read(tmp_path/'rounds'/f'R{number:02}'/'result.json')
        assert result['outcome'] == 'no_change'
        assert result['before']['active_memory'] == result['after']['active_memory']
        assert result['before']['parent'] == result['after']['parent']
    assert 'editor' not in h.calls and 'replay' not in h.calls
    ev.final_parent(tmp_path)


@pytest.mark.parametrize('recover', [False, True])
def test_removed_need_evidence_is_output_error_not_semantic_stop(tmp_path, recover):
    h = CapturedHarness()
    h.stop = 'diagnosis_need_evidence'
    count = 0
    def generate(messages, dest):
        nonlocal count
        if 'diagnosis' in dest.parts:
            count += 1
            if recover and count > 1:
                h.stop = 'diagnosis_no_change'
        return h.generate(messages, dest)
    if recover:
        ev.run_campaign(tmp_path, config=migrated(), generate=generate, actor_runner=h.actor)
        assert count == 2
        assert ev.read(tmp_path/'rounds/R01/result.json')['outcome'] == 'no_change'
        assert 'Unknown decision' in json.dumps(h.requests[-1])
    else:
        with pytest.raises(ev.Stopped, match='exhausted'):
            ev.run_campaign(tmp_path, config=migrated(), generate=generate, actor_runner=h.actor)
        with pytest.raises(ev.Stopped, match='exhausted'):
            ev.run_campaign(tmp_path, resume=True, generate=generate, actor_runner=h.actor)
        assert count == 6
        assert ev.read(tmp_path/'state.json')['next_round'] == 1
    assert 'editor' not in h.calls and 'replay' not in h.calls


@pytest.mark.parametrize('stage', STAGES)
def test_mixed_retries_keep_budget_and_feedback(tmp_path, stage):
    from tests.skill_evolution.v23_5.test_unified_retry import Scripted
    h = Scripted(stage, ['json', 'timeout', 'length', 'schema', 'chunked', 'valid'])
    assert ev.run_campaign(tmp_path, config=migrated(), generate=h.generate, actor_runner=h.actor)['status'] == 'complete'
    assert len(h.requests) == 6
    assert h.requests[1] == h.requests[2]
    assert h.requests[4] == h.requests[5]
    assert 'NOT_FEEDBACK_EVIDENCE' not in json.dumps(h.requests)
    ev.final_parent(tmp_path)


@pytest.mark.parametrize('stage', STAGES)
def test_interrupted_retry_budget_persists(tmp_path, stage):
    from tests.skill_evolution.v23_5.test_unified_retry import Scripted
    h = Scripted(stage, ['schema', 'timeout', 'interrupt', 'json', 'length', 'schema', 'valid'])
    with pytest.raises(KeyboardInterrupt):
        ev.run_campaign(tmp_path, config=migrated(), generate=h.generate, actor_runner=h.actor)
    assert len(h.requests) == 3
    for _ in range(2):
        with pytest.raises(ev.Stopped, match='exhausted'):
            ev.run_campaign(tmp_path, resume=True, generate=h.generate, actor_runner=h.actor)
        assert len(h.requests) == 6
    assert not (tmp_path/'rounds/R01/memory').exists()


def test_wrong_version_and_tampered_source_rejected(tmp_path):
    value = migrated()
    bad = deepcopy(value)
    bad['benchmark']['adapter_version'] = 'v24_alfworld_v1'
    with pytest.raises(ValueError):
        ev.initialize(tmp_path/'bad', bad)
    ev.initialize(tmp_path/'S1', value)
    path = tmp_path/'S1/contract.json'
    frozen = ev.read(path)
    frozen.pop(next(iter(frozen)))
    ev.save(path, frozen)
    with pytest.raises(ValueError, match='Frozen source'):
        ev.run_campaign(tmp_path/'S1', resume=True, generate=lambda *_: pytest.fail('model called'),
                        actor_runner=lambda *_: pytest.fail('actor called'))


def test_actual_module_requests_use_approved_text(tmp_path):
    h = CapturedHarness()
    ev.run_campaign(tmp_path, config=migrated(), generate=h.generate, actor_runner=h.actor)
    for stage, messages in zip(h.calls, h.requests):
        if stage in baseline.PROMPTS:
            approved = (baseline.DRAFT/'prompts'/f'{stage}.md').read_text()
            # Only the unchanged execution context and Knowledge view may be appended.
            actual = messages[0]['content']
            if stage == 'replay':
                assert actual.startswith(approved.rstrip() + '\n\n## Execution Context')
            else:
                prefix, suffix = approved.split('{{execution_context}}')
                assert actual.startswith(prefix + '## Execution Context')
                if stage == 'preconditioner':
                    view = ev.preconditioner.KNOWLEDGE_VIEW_PATH.read_text()
                    assert actual.endswith(suffix + '\n\n' + view)
                else:
                    assert actual.endswith(suffix)
    assert h.calls == STAGES


def test_no_unintended_source_or_prompt_changes():
    from pathlib import Path
    old = ev.ROOT/'src/skill_evolution/v24'
    new = Path(ev.__file__).parent
    intentional = {'README.md', 'baseline.py', 'benchmark.py', 'benchmarks/alfworld/adapter.py',
                   'benchmarks/alfworld/evaluation.py', 'cli.py', 'config.py', 'contracts/diagnosis.py',
                   'diagnosis.py', 'editor.py', 'evolution.py', 'preconditioner.py', 'replay.py'}
    intentional.update('benchmarks/alfworld/prompts/v23_5/'+stem+suffix+'.md'
                       for stem in baseline.PROMPTS.values() for suffix in ('', '_feedback'))
    changed = set()
    for path in old.rglob('*'):
        if not path.is_file() or path.suffix not in ('.py', '.md', '.json'):
            continue
        relative = str(path.relative_to(old))
        original = path.read_text().replace('src.skill_evolution.v24.', 'src.skill_evolution.v24_1.')
        original = original.replace('src.skill_evolution.v24 import', 'src.skill_evolution.v24_1 import')
        original = original.replace('src/skill_evolution/v24/', 'src/skill_evolution/v24_1/')
        if (new/relative).read_text() != original:
            changed.add(relative)
    assert changed == intentional

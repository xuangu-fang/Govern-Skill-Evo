from pathlib import Path
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'scripts/runs'))
import prepare_spreadsheetbench_fourway_test as app
import run_spreadsheetbench_fourway_test as execution


def sources(tmp_path):
    v25 = tmp_path / 'v25'; adam = tmp_path / 'adam'; shared = tmp_path / 'shared'
    for p in (v25, adam, shared): p.mkdir()
    state = {'next_round': 3, 'parent': 'retained.md'}
    app.ev.save(v25 / 'config.json', {'batches': [[], []]})
    app.ev.save(v25 / 'state.json', state)
    for n in (1, 2):
        app.ev.save(v25 / f'rounds/R{n:02d}/result.json', {'status': 'completed', 'after': state})
    (v25 / 'retained.md').write_text('retained earlier Skill')
    (v25 / 'last_candidate.md').write_text('rejected latest candidate')
    app.ev.save(adam / 'checkpoint.json', {'next_iteration': 2, 'iterations': [{}, {}],
        'pending_post_decision': None, 'terminal_stop_reason': '', 'current_skill': 'Adam final'})
    app.ev.save(adam / 'completion.json', {'status': 'complete', 'iterations': [{}, {}]})
    (adam / 'final_skill.md').write_text('Adam final')
    cfg = {'test_tasks': [f'test:{n}' for n in range(280)], 'actor_max_workers': 4}
    app.ev.save(shared / 'config.json', cfg)
    for name in ('manifest.json', 'contract.json', 'runtime.json'): app.ev.save(shared / name, {})
    (shared / 'initial_skill.md').write_text('Initial Skill')
    plan = {'tasks': cfg['test_tasks'], 'pending_tasks': []}
    return v25, adam, shared, cfg, plan


def test_four_bindings_use_retained_skills_and_identical_environment(tmp_path):
    v25, adam, shared, cfg, plan = sources(tmp_path)
    root = tmp_path / 'fourway'
    with patch.object(app.controls, 'check', return_value=(cfg, plan)):
        result = app.prepare(root, shared, v25, adam)
        assert result['execution_order'] == list(app.ARMS)
        assert result['tasks_per_arm'] == 280
        assert (root / 'skills/v25.md').read_text() == 'retained earlier Skill'
        assert app.ev.read(root / 'no_skill.json')['actor_skill'] is None
        assert not (root / 'results').exists()
        (root / 'skills/skilladam.md').write_text('changed')
        with pytest.raises(ValueError, match='Frozen file changed'): app.check(root)


def test_pending_momentum_cannot_be_bound_as_final(tmp_path):
    v25, adam, *_ = sources(tmp_path)
    checkpoint = app.ev.read(adam / 'checkpoint.json')
    checkpoint['pending_post_decision'] = {'iteration': 1}
    app.ev.save(adam / 'checkpoint.json', checkpoint)
    with pytest.raises(ValueError, match='training incomplete'): app.final_sources(v25, adam)


def test_changed_task_order_rejected_even_if_hash_refreshed(tmp_path):
    v25, adam, shared, cfg, plan = sources(tmp_path)
    root = tmp_path / 'fourway'
    with patch.object(app.controls, 'check', return_value=(cfg, plan)):
        app.prepare(root, shared, v25, adam)
        path = root / 'v25.json'; row = app.ev.read(path)
        row['tasks'] = list(reversed(row['tasks'])); app.ev.save(path, row)
        manifest = app.ev.read(root / 'manifest.json')
        manifest['files'][str(path)] = app.controls.sha(path)
        app.ev.save(root / 'manifest.json', manifest)
        with pytest.raises(ValueError, match='Task ordering differs'): app.check(root)


@pytest.mark.parametrize('arm', app.ARMS)
def test_execution_passes_bound_skill_and_shared_config(tmp_path, arm):
    v25, adam, shared, cfg, plan = sources(tmp_path)
    root = tmp_path / 'fourway'
    with patch.object(app.controls, 'check', return_value=(cfg, plan)):
        app.prepare(root, shared, v25, adam)
    row = app.ev.read(root / f'{arm}.json')
    records = [{'task': {'id': key}, 'score': {'hard': 1, 'per_cell_pass_rate': 1},
                'termination': 'valid_workbook_submitted', 'code_attempts': 1} for key in row['tasks']]
    with patch.object(app.ev, '_actors', return_value=(['/fake'] * 280, records)) as actors:
        result = execution.run_arm(root, shared, row, cfg)
    assert actors.call_args.args[0] == shared
    assert actors.call_args.args[3] == cfg['test_tasks']
    skill = actors.call_args.args[4]
    assert skill == (Path(row['actor_skill']) if row['actor_skill'] else None)
    if arm in ('v25', 'skilladam'): assert skill.read_text() != 'Initial Skill'
    assert actors.call_args.args[5] is cfg
    assert result['completed'] == 280


@pytest.mark.parametrize('fail', [False, True])
def test_fourway_execution_order_and_stop(tmp_path, fail):
    v25, adam, shared, cfg, plan = sources(tmp_path)
    root = tmp_path / 'fourway'; seen = []
    def run_arm(root, shared, row, config, **kwargs):
        seen.append(row['arm'])
        if fail: raise RuntimeError('interrupted')
        return {'completed': 280, 'hard': 1}
    with patch.object(app.controls, 'check', return_value=(cfg, plan)):
        app.prepare(root, shared, v25, adam)
        with patch.object(execution, 'run_arm', side_effect=run_arm):
            if fail:
                with pytest.raises(RuntimeError): execution.run(root, runner=object())
                assert seen == ['no_skill']
                assert app.ev.read(root / 'progress.json')['status'] == 'stopped'
            else:
                execution.run(root, runner=object())
                assert seen == list(app.ARMS)
                assert app.ev.read(root / 'progress.json')['status'] == 'completed'

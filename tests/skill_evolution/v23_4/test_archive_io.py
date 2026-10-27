"""Split archives preserve historical selection and consumed retry slots."""
import json
import importlib

import pytest

from experiments.methods.v23_4 import archive_io
from experiments.methods.v23_4.semantic_generation_001 import run as study
from .offline_cases import cases


def roots(tmp_path, monkeypatch):
    source = tmp_path / 'experiments'
    archive = tmp_path / 'artifacts'
    monkeypatch.setattr(archive_io, 'EXPERIMENTS', source)
    monkeypatch.setattr(archive_io, 'ARCHIVE', archive)
    return source, archive


def test_read_and_enumerate_both_namespaces(tmp_path, monkeypatch):
    source, archive = roots(tmp_path, monkeypatch)
    for root in (source, archive):
        (root / 'study/config').mkdir(parents=True)
    (source / 'study/config/freeze.json').write_text('{}')
    (archive / 'study/config/input.json').write_text('{"saved": true}')
    (archive / 'study/config/freeze.json').write_text('{"obsolete": true}')
    assert study.read(source / 'study/config/input.json') == {'saved': True}
    assert study.read(archive / 'study/config/freeze.json') == {}
    paths = list(archive_io.archive_glob(source / 'study/config', '*.json'))
    assert paths == [source / 'study/config/freeze.json', archive / 'study/config/input.json']
    assert list(archive_io.archive_glob(archive / 'study/config', '*.json')) == paths
    assert archive_io.runtime_root(source / 'study') == archive / 'study'
    assert archive_io.runtime_root(source / 'unmigrated') == source / 'unmigrated'


@pytest.mark.parametrize('exhausted', [False, True])
def test_migrated_study_does_not_repeat_attempts(tmp_path, monkeypatch, exhausted):
    source, archive = roots(tmp_path, monkeypatch)
    here = source / 'semantic_generation_001'
    monkeypatch.setattr(study, 'HERE', here)
    monkeypatch.setattr(study, 'verify', lambda: ('fake', {'endpoint': 'http://fixture.invalid'}))
    case = next(c for c in cases() if c['id'] == 'A3')
    monkeypatch.setattr(study, 'inputs', lambda *args: ({'payload': case['payload']}, []))
    monkeypatch.setattr(study.time, 'sleep', lambda _: None)
    calls = []

    def send(req, key, dest, config):
        calls.append(1)
        study.save(dest / 'http_status.json', {'status_code': 200})
        return {'content': json.dumps({} if exhausted else case['output']), 'finish_reason': 'stop'}

    monkeypatch.setattr(study, 'transport', lambda: send)

    def run():
        if exhausted:
            with pytest.raises(RuntimeError, match='restarts exhausted'):
                study.run('A3', 'pc')
        else:
            study.run('A3', 'pc')

    run()
    for path in list(here.rglob('*')):
        if path.is_file() and path.name not in ('selected.json', 'attempt.json', 'parsed.json', 'result.json'):
            destination = archive / path.relative_to(source)
            destination.parent.mkdir(parents=True, exist_ok=True)
            path.rename(destination)
    run()
    assert len(calls) == (4 if exhausted else 1)
    assert not (here / 'runs/A3_pc/material.json').exists()
    assert not (here / 'runs/A3_pc/attempt_001/response.json').exists()
    if not exhausted:
        assert study.load('A3', 'pc')['raw_preconditioner'] == case['output']


@pytest.mark.parametrize('label', ['r05', 'r06'])
@pytest.mark.parametrize('missing_selection', [False, True])
def test_migrated_actor_reuses_completed_episode(tmp_path, monkeypatch, label, missing_selection):
    source, archive = roots(tmp_path, monkeypatch)
    actor = importlib.import_module(f'experiments.methods.v23_4.{label}_actor_comparison_001.run')
    here = source / f'{label}_actor_comparison_001'
    monkeypatch.setattr(actor, 'HERE', here)
    monkeypatch.setattr(actor, 'verify', lambda: {})
    (here / 'config').mkdir(parents=True)
    (here / 'config/parent.md').write_text('Frozen Parent')
    task = 'val:0001'
    config = {'task_items': {task: {'id': task}}}
    calls = []

    def run(task_id, skill, destination, cfg):
        calls.append(1)
        path = destination / 'trajectory.json'
        path.write_text(json.dumps({'task': cfg['task_items'][task_id],
            'skill': {'text': skill.read_text()}, 'status': 'success', 'won': True, 'steps': []}))
        return path

    result = actor.one('parent', task, config, runner=run)
    marker = here / 'runs/parent/val_0001/selected.json'
    for path in list(here.glob('runs/**/*')):
        if path.is_file() and path.name not in ('attempt.json', 'selected.json'):
            destination = archive / path.relative_to(source)
            destination.parent.mkdir(parents=True, exist_ok=True)
            path.rename(destination)
    if missing_selection:
        marker.unlink()
    assert actor.one('parent', task, config, runner=run) == result
    assert len(calls) == 1
    assert actor.read(result['trajectory'])['status'] == 'success'
    assert not (here / 'runs/parent/val_0001/attempt_001/trajectory.json').exists()
    if missing_selection:
        assert not marker.exists()
        assert actor.read(archive_io.raw_path(marker)) == result


@pytest.mark.parametrize('interrupted', [False, True])
def test_diagnostic_archived_calls_are_never_resent(tmp_path, monkeypatch, interrupted):
    from experiments.methods.v23_4.replay_layered_diagnostic_001 import run as diagnostic
    source, archive = roots(tmp_path, monkeypatch)
    here = source / 'diagnostic'
    monkeypatch.setattr(diagnostic, 'HERE', here)
    monkeypatch.setattr(diagnostic, 'verify', lambda: 'offline-fixture')
    labels = ('R05_A', 'R05_B', 'R06_A', 'R06_B')
    (here / 'repeat_plan.json').parent.mkdir(parents=True)
    (here / 'repeat_plan.json').write_text(json.dumps({'repeat_conditions': labels}))

    def forbidden_transport():
        pytest.fail('A recorded diagnostic attempt must never be resent')

    monkeypatch.setattr(diagnostic, 'transport', forbidden_transport)
    for label in labels:
        for number in (1, 2):
            relative = f'diagnostic/runs/{label}/attempt_{number:03}'
            raw = archive / relative
            raw.mkdir(parents=True)
            (raw / 'started.json').write_text(json.dumps({'label': label, 'replicate': number}))
            if not interrupted:
                retained = source / relative
                retained.mkdir(parents=True)
                (retained / 'attempt.json').write_text('{"status":"valid"}')
                (retained / 'parsed.json').write_text('{"answers":[]}')
    for label in labels:
        for number in (1, 2):
            diagnostic.call(label, number)
    assert len(list(diagnostic.archive_glob(here / 'runs', '*/attempt_*/started.json'))) == 8
    assert not list(here.glob('runs/*/attempt_*/started.json'))


def test_diagnostic_save_reuses_archived_input(tmp_path, monkeypatch):
    from experiments.methods.v23_4.replay_layered_diagnostic_001.design import save
    source, archive = roots(tmp_path, monkeypatch)
    relative = 'diagnostic/config/R05_A/request.json'
    archived = archive / relative
    archived.parent.mkdir(parents=True)
    original = json.dumps({'body': {'messages': []}}, ensure_ascii=False, indent=2) + '\n'
    archived.write_text(original)
    save(source / relative, {'body': {'messages': []}})
    assert not (source / relative).exists()
    assert archived.read_text() == original
    with pytest.raises(AssertionError, match='Immutable artifact differs'):
        save(source / relative, {'body': {'messages': ['changed']}})
    assert archived.read_text() == original


def test_diagnostic_counts_archived_budget_before_a_new_slot(tmp_path, monkeypatch):
    from experiments.methods.v23_4.replay_layered_diagnostic_001 import run as diagnostic
    source, archive = roots(tmp_path, monkeypatch)
    here = source / 'diagnostic'
    monkeypatch.setattr(diagnostic, 'HERE', here)
    monkeypatch.setattr(diagnostic, 'verify', lambda: 'offline-fixture')

    def forbidden_transport():
        pytest.fail('Eight archived starts must exhaust the HTTP budget')

    monkeypatch.setattr(diagnostic, 'transport', forbidden_transport)
    # Even interrupted historical sends outside the requested slot consume budget.
    for number in range(1, 9):
        path = archive / f'diagnostic/runs/historical/attempt_{number:03}/started.json'
        path.parent.mkdir(parents=True)
        path.write_text('{}')
    with pytest.raises(AssertionError, match='Total HTTP budget exhausted'):
        diagnostic.call('R05_A', 1)
    assert not (archive / 'diagnostic/runs/R05_A/attempt_001').exists()

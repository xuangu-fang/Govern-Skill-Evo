"""Gate decisions start with raw recorded environment events; no network."""
from copy import deepcopy
import json
from pathlib import Path
import pytest

from src.skill_evolution.v23 import gate
from tests.skill_evolution.v23.test_grouping import record
from tests.skill_evolution.v23.test_replay_memory import records


def batch(statuses, skill=None):
    result = []
    for i, status in enumerate(statuses, 1):
        template = records(skill)[0]
        fresh = record(i, status=status, parent=skill)
        template.update(fresh)
        template['skill'] = records(skill)[0]['skill']
        if skill is not None:
            template['run_id'] = 'candidate-' + template['run_id']
        result.append(template)
    return result


def assemble(p, q):
    return gate.build_gate(p, q, [r['task']['id'] for r in p],
                           parent_skill=None, candidate_skill='Candidate\n')


@pytest.mark.parametrize('ps,qs,decision', [
    (['step_limit'], ['success'], 'ACCEPT'),
    (['success'], ['success'], 'RETAIN'),
    (['success'], ['step_limit'], 'RETAIN'),
    (['step_limit', 'environment_ended'], ['environment_ended', 'step_limit'], 'RETAIN'),
    (['success', 'success'], ['success', 'success'], 'RETAIN'),
    (['success', 'step_limit', 'environment_ended'], ['step_limit', 'success', 'success'], 'ACCEPT'),
])
def test_rule_from_environment_records(ps, qs, decision):
    p, q = batch(ps), batch(qs, 'Candidate\n')
    before = deepcopy((p, q))
    bundle = assemble(p, q[::-1])
    result = gate.decide_gate(bundle['input'], [r['task']['id'] for r in p])
    assert result == {'decision': decision, 'parent_success': ps.count('success'),
                      'candidate_success': qs.count('success'), 'compared': len(ps)}
    assert (p, q) == before


@pytest.mark.parametrize('status', ['error', 'interrupted', 'unknown', 'running', 'starting'])
def test_technical_or_unknown_cannot_count_false(status):
    with pytest.raises(ValueError, match='incomplete/technical'):
        assemble(batch(['success']), batch([status], 'Candidate\n'))


@pytest.mark.parametrize('side', ['parent', 'candidate'])
def test_pending_network_failure(side):
    p, q = batch(['success']), batch(['success'], 'Candidate\n')
    r = (p if side == 'parent' else q)[0]
    r.update(status='error', won=False, error_stage='model_request', error_type='HTTPError')
    r['steps'][-1]['phase'] = 'requesting'
    with pytest.raises(ValueError): assemble(p, q)


@pytest.mark.parametrize('kind', ['task', 'model', 'protocol', 'environment', 'reset', 'skill',
                                  'duplicate_task', 'missing', 'identity', 'feedback', 'raw_bool'])
def test_raw_source_invalid(kind):
    p, q = batch(['success', 'step_limit']), batch(['success', 'step_limit'], 'Candidate\n')
    if kind == 'task': q[0]['task']['id'] = 'other'
    elif kind == 'model': q[0]['model'] = 'other'
    elif kind == 'protocol': q[0]['protocol']['environment_seed'] = 99
    elif kind == 'environment': q[0]['environment']['game_sha256'] = 'other'
    elif kind == 'reset': q[0]['initial_observation'] += ' changed'
    elif kind == 'skill': q[0]['skill']['sha256'] = 'invalid'
    elif kind == 'duplicate_task': q[1]['task'] = deepcopy(q[0]['task'])
    elif kind == 'missing': q.pop()
    elif kind == 'identity': q[0]['run_id'] = p[0]['run_id']
    elif kind == 'feedback': q[0]['steps'][-1]['won'] = False
    elif kind == 'raw_bool': q[0]['won'] = 1
    with pytest.raises(ValueError): assemble(p, q)


@pytest.mark.parametrize('kind', ['empty', 'duplicate', 'frozen_missing', 'frozen_extra', 'frozen_duplicate',
                                  'none', 'number', 'string', 'extra', 'same_run'])
def test_normalized_contract(kind):
    b = assemble(batch(['success']), batch(['success'], 'Candidate\n'))
    v = b['input']; tasks = [v['pairs'][0]['task_id']]
    if kind == 'empty': v['pairs'] = []
    elif kind == 'duplicate': v['pairs'] *= 2
    elif kind == 'frozen_missing': tasks = []
    elif kind == 'frozen_extra': tasks += ['other']
    elif kind == 'frozen_duplicate': tasks *= 2
    elif kind in ('none', 'number', 'string'):
        v['pairs'][0]['parent']['success'] = {'none': None, 'number': 1, 'string': 'true'}[kind]
    elif kind == 'extra': v['decision'] = 'ACCEPT'
    elif kind == 'same_run': v['pairs'][0]['candidate']['run_id'] = v['pairs'][0]['parent']['run_id']
    with pytest.raises(ValueError): gate.decide_gate(v, tasks)


@pytest.fixture
def storage(tmp_path, monkeypatch):
    b = assemble(batch(['success', 'step_limit']), batch(['success', 'success'], 'Candidate\n'))
    b.update(frozen_tasks=[p['task_id'] for p in b['input']['pairs']], sources={'offline': 'hash'},
             origin={'replay_directory': 'offline', 'tasks_file': 'tasks'}, rule=gate.RULE)
    monkeypatch.setattr(gate, 'assemble_gate', lambda *a, **kw: deepcopy(b))
    return tmp_path, b


def test_save_read_reuse_without_decision(storage, monkeypatch):
    root, b = storage
    first = gate.run_gate('offline', 'tasks', root)
    assert first['result']['decision'] == 'ACCEPT' and not first['reused']
    original = (root/'gate.json').read_bytes()
    monkeypatch.setattr(gate, 'decide_gate', lambda *a: pytest.fail('Repeated Gate calculation'))
    assert gate.run_gate('offline', 'tasks', root)['reused']
    assert gate.load_gate(root)['result'] == first['result']
    assert (root/'gate.json').read_bytes() == original


@pytest.mark.parametrize('kind', ['source', 'input', 'rule', 'decision', 'count', 'type', 'extra', 'json'])
def test_corruption_or_conflict_rejected(storage, kind):
    root, b = storage
    gate.run_gate('offline', 'tasks', root)
    path = root/'gate.json'; saved = json.loads(path.read_text())
    if kind == 'source': b['sources']['offline'] = 'changed'
    elif kind == 'input': b['input']['pairs'][0]['parent']['success'] = False
    elif kind == 'rule': saved['bundle']['rule'] = 'different'
    elif kind == 'decision': saved['result']['decision'] = 'RETAIN'
    elif kind == 'count': saved['result']['parent_success'] = 0
    elif kind == 'type': saved['result']['parent_success'] = True
    elif kind == 'extra': saved['result']['reason'] = 'extra'
    path.write_text('{' if kind == 'json' else json.dumps(saved))
    original = path.read_bytes()
    with pytest.raises(ValueError): gate.run_gate('offline', 'tasks', root)
    assert (root/'failure.json').exists() and path.read_bytes() == original


def test_technical_stop_without_decision(tmp_path, monkeypatch):
    def fail(*a): raise FileNotFoundError('Missing trajectory')
    monkeypatch.setattr(gate, 'assemble_gate', fail)
    with pytest.raises(FileNotFoundError): gate.run_gate('archive', 'tasks', tmp_path)
    assert not (tmp_path/'gate.json').exists()
    assert 'decision' not in json.loads((tmp_path/'failure.json').read_text())


def test_real_archive_handoff_and_protection(tmp_path, monkeypatch):
    replay = Path('artifacts/methods/v23/v23_replay_memory_001/replay')
    tasks = Path('experiments/methods/v23/v23_replay_memory_001/config/plan.json')
    if not replay.exists(): pytest.skip('Local real archive unavailable')
    bundle = gate.assemble_gate(replay, tasks)
    protected = {p: gate._hash(p) for p in replay.parent.rglob('*') if p.is_file()}
    protected.update({Path(p): h for p, h in bundle['sources'].items()})
    first = gate.run_gate(replay, tasks, tmp_path)
    assert first['result'] == {'decision': 'RETAIN', 'parent_success': 3,
                               'candidate_success': 2, 'compared': 4}
    monkeypatch.setattr(gate, 'decide_gate', lambda *a: pytest.fail('Repeated decision'))
    assert gate.run_gate(replay, tasks, tmp_path)['reused']
    assert all(gate._hash(p) == h for p, h in protected.items())
    # A frozen task may not be dropped even when the remaining pairs are valid.
    smaller = tmp_path/'tasks.json'; smaller.write_text(json.dumps(bundle['frozen_tasks'][:-1]))
    with pytest.raises(ValueError): gate.assemble_gate(replay, smaller)
    smaller.write_text(json.dumps(bundle['frozen_tasks']))
    # Detect real source-byte changes even when JSON facts remain identical.
    monkeypatch.undo()
    gate.run_gate(replay, smaller, tmp_path/'second')
    smaller.write_text(json.dumps(bundle['frozen_tasks'], indent=2))
    with pytest.raises(ValueError, match='sources/input/rule changed'):
        gate.load_gate(tmp_path/'second')
    smaller.unlink()
    with pytest.raises(FileNotFoundError): gate.load_gate(tmp_path/'second')

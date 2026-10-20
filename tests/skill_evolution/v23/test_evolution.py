"""Offline full module chaining and crash injection; actual validators are used."""
from copy import deepcopy
import json
from pathlib import Path
import pytest
import requests
from src.skill_evolution.v23 import evolution as ev, editor, memory
from src.adapters.alfworld.skill_runtime import load_skill, execution_protocol
from tests.skill_evolution.v23.test_grouping import record
from tests.skill_evolution.v23.test_replay_memory import records


def config(rounds=2):
    return {'batches': [[f'train:{10+i*2+j:04}' for j in range(2)] for i in range(rounds)],
        'max_attempts': 3, 'actor_request_attempts': 3, 'max_steps': 50,
        'continue_no_change': True, 'max_input_chars': 300000, 'max_input_bytes': 400000,
        'actor_python': 'offline', 'actor_model': 'offline',
        'call_config': ev.grouping.call_configuration(base_url='https://offline.invalid', model='offline', max_tokens=16384, timeout=300)}


class Harness:
    def __init__(self, outcome='ACCEPT'):
        self.calls = []; self.actor_calls = []; self.outcome = outcome
        self.fail = None; self.failures = 0; self.stop = None; self.empty_memory = False
        self.memories = []

    def actor(self, task, skill, dest, cfg):
        self.actor_calls.append((task, str(dest)))
        candidate = 'candidate_runs' in str(dest)
        success = candidate if self.outcome == 'ACCEPT' else not candidate
        r = records()[0]
        n = int(task.split(':')[1]); parent = None if skill is None else Path(skill).read_text()
        fresh = record(n, parent=parent, status='success' if success else 'step_limit',
                       menus=[['help', 'look', 'look']] + [['look', 'open cabinet 1'] for _ in range(1 if success else 49)])
        r.update(fresh); r['protocol'] = execution_protocol(50); r['skill'] = load_skill(skill)
        r['run_id'] = f'{dest.parent.parent.parent.name}-{n}-{len(self.actor_calls)}'
        path = dest/'trajectory.json'; ev.save(path, r)
        return path

    def generate(self, messages, dest):
        name = messages[0]['content'].splitlines()[0][2:].lower()
        self.calls.append(name)
        ev.save(dest/'request.json', {'messages': messages})
        if self.fail == name and self.failures:
            self.failures -= 1
            if self.stop == 'timeout': raise requests.Timeout('offline timeout')
            if self.stop == '429':
                ev.save(dest/'http_status.json', {'status_code': 429})
                (dest/'http_response.txt').write_text('temporary rate limit')
                raise ValueError('HTTP 429')
            if self.stop == '401':
                ev.save(dest/'http_status.json', {'status_code': 401})
                (dest/'http_response.txt').write_text('unauthorized')
                raise ValueError('HTTP 401')
            content = {'empty': '', 'json': '{', 'fields': '{}', 'patch': '{"patch":"bad", "reason":"x"}',
                       'evidence': '{"entries":[{"revises":[],"knowledge":"x","evidence":["diff","P999:1"]}]}'}
            return {'content': content.get(self.stop, '{}'), 'finish_reason': 'length' if self.stop == 'truncated' else 'stop', 'usage': {'total_tokens': 5}}
        payload = json.loads(messages[1]['content'])
        if name == 'grouping':
            ids = [r['ref'] for r in payload['runs']]
            result = {'groups': [{'group_id': 'G1', 'members': ids, 'decision_problem': 'Whether to inspect a closed cabinet.',
                'shared_basis': ', '.join(r+':1' for r in ids), 'important_differences': []}]}
        elif name == 'diagnosis':
            result = {'decision': 'revise', 'reason': 'Observed inspection opportunity.', 'plan': {
                'goal': 'Inspect visible containers.', 'updates': [{'id': 'u1', 'text': 'Inspect a visible closed container before searching elsewhere.', 'basis': ['G1', 'P1:1']}], 'checks': []}}
            if self.stop in ('diagnosis_no_change', 'diagnosis_need_evidence'):
                result.update(decision=self.stop.removeprefix('diagnosis_'), plan=None)
        elif name == 'preconditioner':
            self.memories.append(deepcopy(payload['memory']))
            result = {'decision': 'ready', 'reason': 'Keep supported guidance.', 'adjustments': [], 'checks': None}
            if self.stop == 'preconditioner_no_change':
                result.update(decision='no_change', adjustments=[{'from': ['u1'], 'to': [], 'basis': ['P1:1'], 'reason': 'Already covered.'}], checks=[])
            elif self.stop == 'preconditioner_need_evidence': result['decision'] = 'need_evidence'
        elif name == 'editor':
            old = payload['parent']; new = (old or '') + 'Inspect visible containers.\n'
            result = {'patch': editor.actual_diff(old, new), 'reason': 'Implement instruction.'}
            if self.stop == 'editor_empty': result['patch'] = ''
            if self.stop == 'editor_null': result['patch'] = None
        elif name == 'replay':
            ids = [e['id'] for e in payload['memory']['entries']]
            result = {'entries': [] if self.empty_memory else [{'revises': ids,
                'knowledge': 'Synthetic response under observed inspection conditions; attribution remains uncertain.',
                'evidence': ['diff', 'P1:1', 'Q1:1']}]}
        else: raise AssertionError(name)
        return {'content': json.dumps(result), 'finish_reason': 'stop', 'usage': {'total_tokens': 10}}


def run(root, h, **kw):
    return ev.run_campaign(root, generate=h.generate, actor_runner=h.actor, **kw)


@pytest.mark.parametrize('decision', ['ACCEPT', 'RETAIN'])
def test_two_rounds_real_validators(tmp_path, decision):
    h = Harness(decision); result = run(tmp_path, h, config=config())
    assert result['status'] == 'complete' and result['state']['next_round'] == 3
    assert (result['state']['parent'] is not None) == (decision == 'ACCEPT')
    assert h.memories[0] == memory.empty_memory() and h.memories[1]['entries'][0]['id'] == 'M1'
    final = memory.load_memory(tmp_path/result['state']['active_memory'])
    assert [e['id'] for e in final['entries']] == ['M2']
    assert len(h.actor_calls) == 8 and len(h.calls) == 10
    before = (len(h.calls), len(h.actor_calls))
    run(tmp_path, h, resume=True)
    assert before == (len(h.calls), len(h.actor_calls))


@pytest.mark.parametrize('kind,stage', [('timeout','grouping'), ('429','grouping'), ('empty','diagnosis'),
    ('json','diagnosis'), ('fields','preconditioner'), ('truncated','grouping'), ('patch','editor'), ('evidence','replay')])
def test_two_failures_then_success(tmp_path, kind, stage):
    h = Harness(); h.stop = kind; h.fail = stage; h.failures = 2
    run(tmp_path, h, config=config(1))
    assert h.calls.count(stage) == 3
    attempts = tmp_path/'rounds/R01'/stage/'attempts'
    assert (attempts/'001/error.json').exists() and (attempts/'002/error.json').exists()
    assert (attempts/'003/validation.json').exists()


@pytest.mark.parametrize('stage', ['editor', 'replay'])
def test_exhaustion_stop_resume_and_no_early_publish(tmp_path, stage):
    h = Harness(); h.fail = stage; h.failures = 3; h.stop = 'json'
    with pytest.raises(ev.Stopped): run(tmp_path, h, config=config(1))
    state = ev.read(tmp_path/'state.json'); assert state['next_round'] == 1 and state['parent'] is None
    assert not memory.load_memory(tmp_path/state['active_memory'])['entries']
    with pytest.raises(ValueError): run(tmp_path, h)
    actor_before = len(h.actor_calls); before = h.calls.count('grouping')
    run(tmp_path, h, resume=True)
    assert h.calls.count('grouping') == before
    assert len(h.actor_calls) == actor_before + (2 if stage == 'editor' else 0)
    assert (tmp_path/f'rounds/R01/{stage}/attempts/004').exists()


@pytest.mark.parametrize('point', ['diagnosis', 'memory_prepared', 'before_publish', 'after_publish'])
def test_crash_resume_publication(tmp_path, point):
    h = Harness()
    def crash(name):
        if name == point: raise KeyboardInterrupt()
    with pytest.raises(KeyboardInterrupt): run(tmp_path, h, config=config(1), hook=crash)
    prior = len(h.calls)
    run(tmp_path, h, resume=True)
    assert h.calls.count('grouping') == 1
    if point != 'diagnosis': assert len(h.calls) == prior
    state = ev.read(tmp_path/'state.json')
    assert [e['id'] for e in memory.load_memory(tmp_path/state['active_memory'])['entries']] == ['M1']


@pytest.mark.parametrize('stop', ['diagnosis_no_change', 'diagnosis_need_evidence', 'preconditioner_no_change',
                                 'preconditioner_need_evidence', 'editor_empty', 'editor_null'])
def test_semantic_stops_no_retry(tmp_path, stop):
    h = Harness(); h.stop = stop
    if 'need_evidence' in stop or stop == 'editor_null':
        with pytest.raises(ev.Stopped): run(tmp_path, h, config=config(1))
        with pytest.raises(ValueError, match='Semantic blocker'): run(tmp_path, h, resume=True)
    else: run(tmp_path, h, config=config(1))
    assert all(h.calls.count(n) == 1 for n in h.calls)
    assert not any('candidate_runs' in p for _, p in h.actor_calls)


def test_empty_replay_and_permanent_error(tmp_path):
    h = Harness(); h.empty_memory = True
    run(tmp_path/'empty', h, config=config())
    assert h.memories == [memory.empty_memory(), memory.empty_memory()]
    h = Harness(); h.fail = 'grouping'; h.failures = 3; h.stop = '401'
    with pytest.raises(ev.Stopped): run(tmp_path/'bad', h, config=config(1))
    assert h.calls == ['grouping']


def test_frozen_content_and_readonly_status(tmp_path):
    h = Harness(); ev.initialize(tmp_path, config(1))
    before = {str(p): p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    ev.status(tmp_path)
    assert before == {str(p): p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    c = ev.read(tmp_path/'config.json'); c['call_config']['max_tokens'] = 10; ev.save(tmp_path/'config.json', c)
    with pytest.raises(ValueError): run(tmp_path, h)
    assert not h.calls


def test_partial_actor_resume_restarts_only_failed_task(tmp_path):
    h = Harness(); failed = False
    def actor(task, skill, dest, cfg):
        nonlocal failed
        path = h.actor(task, skill, dest, cfg)
        if 'candidate_runs' in str(dest) and task.endswith('0011') and not failed:
            failed = True; r = ev.read(path); r['status'] = 'error'; ev.save(path, r)
        return path
    with pytest.raises(ValueError): ev.run_campaign(tmp_path, config=config(1), generate=h.generate, actor_runner=actor)
    ev.run_campaign(tmp_path, resume=True, generate=h.generate, actor_runner=actor)
    assert len(h.actor_calls) == 5
    assert len(list((tmp_path/'rounds/R01/candidate_runs/train_0011/attempts').iterdir())) == 2


def test_saved_response_recovery_without_new_request(tmp_path, monkeypatch):
    h = Harness(); original = ev.grouping.write_record; crashed = False
    def interrupt(path, value):
        nonlocal crashed
        original(path, value)
        if path.name == 'response.json' and not crashed:
            crashed = True; raise KeyboardInterrupt()
    monkeypatch.setattr(ev.grouping, 'write_record', interrupt)
    with pytest.raises(KeyboardInterrupt): run(tmp_path, h, config=config(1))
    monkeypatch.setattr(ev.grouping, 'write_record', original)
    run(tmp_path, h, resume=True)
    assert h.calls.count('grouping') == 1
    selected = ev.read(tmp_path/'rounds/R01/grouping/result.json')
    assert selected['path'].endswith('/recovered')


def test_recorded_recovery_only_changes_failed_stage(tmp_path):
    h = Harness(); h.fail = 'editor'; h.failures = 3; h.stop = 'patch'
    with pytest.raises(ev.Stopped): run(tmp_path, h, config=config(1))
    original = (tmp_path/'config.json').read_bytes()
    cfg = config(1)['call_config']; cfg['max_tokens'] = 20000
    amendment = tmp_path/'amendment.json'
    ev.save(amendment, {'stage': 'editor', 'reason': 'Explicit offline budget recovery test.', 'call_config': cfg})
    run(tmp_path, h, resume=True, recovery_file=amendment)
    assert (tmp_path/'config.json').read_bytes() == original
    assert ev.read(tmp_path/'rounds/R01/editor/attempts/004/run.json')['call_config']['max_tokens'] == 20000
    assert h.calls.count('grouping') == 1


def test_frozen_prompt_change_is_not_silent(tmp_path, monkeypatch):
    h = Harness(); ev.initialize(tmp_path, config(1)); actual = ev.frozen_contract()
    changed = deepcopy(actual); changed['src/skill_evolution/v23/diagnosis_prompt.md'] += '\nchanged'
    monkeypatch.setattr(ev, 'frozen_contract', lambda: changed)
    with pytest.raises(ValueError, match='Frozen source'): run(tmp_path, h)
    assert not h.actor_calls and not h.calls


@pytest.mark.parametrize('kind', ['timeout', 'http429', 'empty', 'truncated', 'json', 'permanent'])
def test_actor_request_budget(kind, monkeypatch):
    from src.adapters.alfworld import run_task_upstream as actor
    monkeypatch.setattr(actor.time, 'sleep', lambda _: None)
    class Response:
        status_code = 429 if kind == 'http429' else 401 if kind == 'permanent' else 200
        ok = status_code == 200
        text = 'error'
        def json(self):
            if kind == 'json': raise ValueError('Invalid JSON')
            return {'choices': [{'message': {'content': '' if kind == 'empty' else '<action>look</action>'},
                'finish_reason': 'length' if kind == 'truncated' else 'stop'}]}
    class Session:
        calls = 0
        def post(self, *a, **k):
            self.calls += 1
            if kind == 'timeout': raise requests.Timeout()
            return Response()
    session = Session()
    with pytest.raises((requests.Timeout, ValueError, RuntimeError)):
        actor.chat(session, 'offline', 'unused', 'offline', [], max_attempts=3, strict_response=True)
    assert session.calls == (1 if kind == 'permanent' else 3)

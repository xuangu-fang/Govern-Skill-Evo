"""Bounded authentication retry and immutable mixed-source Campaign recovery."""
from copy import deepcopy
import hashlib
import json
from unittest.mock import Mock

import pytest
import requests

from src.adapters.alfworld.run_task_upstream import chat
from src.adapters.alfworld.skill_runtime import context_fingerprint, execution_fingerprint
from src.skill_evolution.v23_5 import evolution as ev, retry_401 as recovery
from .test_baseline import Harness, config


def six_config():
    cfg = config(1)
    cfg.update(max_attempts=6, actor_request_attempts=6, retry_delay_seconds=0)
    return cfg


def response(status):
    r = requests.Response(); r.status_code = status
    r._content = json.dumps({'choices': [{'finish_reason': 'stop', 'message': {
        'content': '<action>look</action>'}}]}).encode()
    return r


@pytest.mark.parametrize('statuses,expected', [([401]*5+[200], 6), ([401]*6, 6),
    ([401, 503, 401, 429, 401, 200], 6), ([403], 1), ([400], 1)])
def test_actor_401_shares_six_request_budget(monkeypatch, statuses, expected):
    monkeypatch.setattr('src.adapters.alfworld.run_task_upstream.time.sleep', lambda _: None)
    session = Mock(); session.post.side_effect = [response(s) for s in statuses]
    args = (session, 'https://offline.invalid', 'unused', 'offline', [])
    if statuses[-1] == 200:
        assert chat(*args, max_attempts=6, strict_response=True)['api_attempts'] == expected
    else:
        with pytest.raises(RuntimeError): chat(*args, max_attempts=6, strict_response=True)
    assert session.post.call_count == expected
    assert all(call == session.post.call_args_list[0] for call in session.post.call_args_list)


@pytest.mark.parametrize('stage', list(ev.MODULES))
@pytest.mark.parametrize('failures', [5, 6])
def test_module_401_budget_and_resume(tmp_path, stage, failures):
    h = Harness(); h.stop = '401'; h.fail = stage; h.failures = failures
    def run(**kw):
        return ev.run_campaign(tmp_path, generate=h.generate, actor_runner=h.actor, **kw)
    if failures == 5:
        assert run(config=six_config())['status'] == 'complete'
        run(resume=True)
    else:
        with pytest.raises(ev.Stopped): run(config=six_config())
        with pytest.raises(ev.Stopped): run(resume=True)
    assert h.calls.count(stage) == 6


def old_and_new():
    new = ev.frozen_contract(); old = deepcopy(new)
    old[recovery.ACTOR] = old[recovery.ACTOR].replace(recovery.NEW, recovery.OLD)
    old.pop('src/skill_evolution/v23_5/retry_401.py')
    return old, new


def hashes(contract):
    return {n: hashlib.sha256(contract['src/adapters/alfworld/'+n].encode()).hexdigest()
            for n in ('run_task_skill.py', 'skill_runtime.py', 'run_task_upstream.py', 'run_task.py')}


def stopped_campaign(root, monkeypatch):
    old, new = old_and_new()
    monkeypatch.setattr(ev, 'frozen_contract', lambda: old)
    ev.initialize(root, six_config())
    ev.save(root/'stop.json', {'kind': 'technical', 'round': 1, 'stage': 'candidate_runs'})
    monkeypatch.setattr(ev, 'frozen_contract', lambda: new)
    return old, new


@pytest.mark.parametrize('tamper', ['live', 'original', 'approved', 'config'])
def test_amendment_detects_changes(tmp_path, monkeypatch, tamper):
    old, new = stopped_campaign(tmp_path, monkeypatch)
    original_bytes = (tmp_path/'contract.json').read_bytes()
    recovery.enable(tmp_path, reason='Test authorization')
    ev._check_contract(tmp_path)
    assert (tmp_path/'contract.json').read_bytes() == original_bytes
    assert recovery.enable(tmp_path, reason='Test authorization')['policy'] == recovery.POLICY
    if tamper == 'live':
        new['src/skill_evolution/v23_5/editor_prompt.md'] += 'changed'
    else:
        path = {'original': tmp_path/'contract.json', 'approved': tmp_path/recovery.DIRECTORY/'contract.json',
                'config': tmp_path/'config.json'}[tamper]
        data = ev.read(path); data['tampered'] = True; ev.save(path, data)
    with pytest.raises(ValueError): ev._check_contract(tmp_path)


@pytest.mark.parametrize('file', ['src/skill_evolution/v23_5/editor_prompt.md', recovery.ACTOR])
def test_amendment_rejects_unrelated_changes(tmp_path, monkeypatch, file):
    old, new = stopped_campaign(tmp_path, monkeypatch)
    new[file] += '\n# unrelated\n'
    with pytest.raises(ValueError): recovery.enable(tmp_path, reason='Test authorization')
    assert not (tmp_path/recovery.DIRECTORY).exists()


def test_resume_reuses_completed_records_and_allows_only_reviewed_pair(tmp_path, monkeypatch):
    old, new = old_and_new(); active = [old]
    monkeypatch.setattr(ev, 'frozen_contract', lambda: active[0])
    h = Harness(); fail_once = [True]
    def actor(task, skill, dest, cfg):
        path = h.actor(task, skill, dest, cfg); record = ev.read(path)
        record.setdefault('purpose', 'learning')
        record['implementation']['files'] = hashes(active[0])
        record['context_fingerprint'] = context_fingerprint(record)
        record['execution_fingerprint'] = execution_fingerprint(record)
        if 'candidate_runs' in str(dest) and task == cfg['batches'][0][-1] and fail_once[0]:
            record['status'] = 'error'; fail_once[0] = False
        ev.save(path, record)
        return path
    with pytest.raises(ValueError):
        ev.run_campaign(tmp_path, config=six_config(), generate=h.generate, actor_runner=actor)
    immutable = {p: p.read_bytes() for p in tmp_path.rglob('trajectory.json')}
    old_calls, old_actors = len(h.calls), len(h.actor_calls)
    active[0] = new
    with pytest.raises(ValueError, match='Frozen source'): ev._check_contract(tmp_path)
    recovery.enable(tmp_path, reason='Test explicit user restart and HTTP 401 retries')
    result = ev.run_campaign(tmp_path, resume=True, generate=h.generate, actor_runner=actor)
    assert result['status'] == 'complete'
    assert len(h.actor_calls) == old_actors + 1
    assert h.calls[old_calls:] == ['replay']
    assert all(p.read_bytes() == data for p, data in immutable.items())
    pair_data = ev.read(tmp_path/'rounds/R01/pairs/input.json')
    assert pair_data['pair_audit'][1]['implementation_review']['parent_files'] == hashes(old)
    assert pair_data['pair_audit'][1]['implementation_review']['candidate_files'] == hashes(new)
    ev.final_parent(tmp_path)
    ev.run_campaign(tmp_path, resume=True, generate=h.generate, actor_runner=actor)
    assert len(h.actor_calls) == old_actors + 1
    bad = {'implementation': {'files': {'unexpected': 'hash'}}}
    with pytest.raises(ValueError, match='not covered'):
        recovery.implementation_review(tmp_path, [{'implementation': {'files': hashes(old)}}], [bad])

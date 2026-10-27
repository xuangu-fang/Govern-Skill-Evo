"""Request-local budget escalation, archive reuse and source amendment boundaries."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from src.skill_evolution.v23_4 import evolution as ev, output_budget as ob, budget_actor
from src.adapters.alfworld.run_task_skill import RecordingSession
from .test_evolution import Harness, config, run


def enable(root):
    ob.enable(root, ev.frozen_contract(), reason='Explicit synthetic test authorization')


def test_six_archived_truncations_double_only_current_stage_and_reuse(tmp_path):
    h = Harness(); h.fail = 'preconditioner'; h.stop = 'truncated'; h.failures = 6
    with pytest.raises(ev.Stopped): run(tmp_path, h, config=config(1))
    with pytest.raises(ev.Stopped): run(tmp_path, h, resume=True)
    original = (tmp_path/'contract.json').read_bytes()
    old_calls, old_actors = len(h.calls), len(h.actor_calls)
    enable(tmp_path)
    result = run(tmp_path, h, resume=True)
    assert result['status'] == 'complete'
    rd = tmp_path/'rounds/R01'
    assert ev.read(rd/'preconditioner/attempts/007/run.json')['call_config']['max_tokens'] == 32768
    assert ev.read(rd/'editor/attempts/001/run.json')['call_config']['max_tokens'] == 16384
    assert len(h.calls) == old_calls + 3 and len(h.actor_calls) == old_actors + 2
    assert (tmp_path/'contract.json').read_bytes() == original
    assert ev.read(tmp_path/'config.json') == ev.read(tmp_path/'initial_config.json')
    prior = len(h.calls)
    run(tmp_path, h, resume=True)
    assert len(h.calls) == prior
    assert ev.final_parent(tmp_path) == rd/'editor/attempts/001/candidate.md'


def test_new_module_escalates_at_six_then_six_and_resets_next_call(tmp_path):
    ev.initialize(tmp_path, config(1)); enable(tmp_path)
    h = Harness(); h.fail = 'grouping'; h.stop = 'truncated'; h.failures = 12
    run(tmp_path, h, resume=True)
    attempts = tmp_path/'rounds/R01/grouping/attempts'
    limits = [ev.read(p/'run.json')['call_config']['max_tokens'] for p in sorted(attempts.iterdir())]
    assert limits == [16384]*6 + [32768]*6 + [65536]
    assert ev.read(tmp_path/'rounds/R01/diagnosis/attempts/001/run.json')['call_config']['max_tokens'] == 16384


@pytest.mark.parametrize('kind', ['json', 'empty', '429', 'timeout'])
def test_other_module_errors_still_stop_after_three(tmp_path, kind):
    ev.initialize(tmp_path, config(1)); enable(tmp_path)
    h = Harness(); h.fail = 'grouping'; h.stop = kind; h.failures = 8
    with pytest.raises(ev.Stopped): run(tmp_path, h, resume=True)
    assert h.calls == ['grouping']*3


def test_amendment_rejects_unrelated_change_and_post_enable_drift(tmp_path, monkeypatch):
    ev.initialize(tmp_path, config(1)); contract = ev.frozen_contract()
    bad = deepcopy(contract); bad['src/skill_evolution/v23_4/diagnosis_prompt.md'] += '\nchanged'
    with pytest.raises(ValueError, match='unrelated'): ob.enable(tmp_path, bad, reason='test')
    enable(tmp_path)
    monkeypatch.setattr(ev, 'frozen_contract', lambda: bad)
    with pytest.raises(ValueError, match='Frozen source'): ev._check_contract(tmp_path)


class Response:
    def __init__(self, reason='stop', status=200, content='<action>look</action>'):
        self.status_code = status; self.ok = status == 200
        self.payload = {'choices': [{'finish_reason': reason, 'message': {'content': content}}],
                        'usage': {'completion_tokens': 10}}
        self.content = json.dumps(self.payload).encode(); self.text = self.content.decode()
    def json(self): return self.payload


class Session:
    def __init__(self, responses): self.responses = iter(responses); self.limits = []
    def post(self, endpoint, **kwargs):
        self.limits.append(kwargs['json']['max_tokens']); return next(self.responses)


def test_actor_six_then_double_same_step_archive_and_next_step_reset(tmp_path, monkeypatch):
    monkeypatch.setattr(budget_actor.time, 'sleep', lambda _: None)
    raw = Session([Response('length')]*12 + [Response(), Response()])
    record = {'model': 'offline', 'output_budget_policy': deepcopy(ob.POLICY), 'steps': [{'messages': []}]}
    path = tmp_path/'trajectory.json'
    session = RecordingSession(raw, record, path, archive_responses=True)
    result = budget_actor.chat(session, 'offline', 'unused', 'offline', [])
    assert result['api_attempts'] == 13
    assert len(record['steps']) == 1
    ob.validate_actor(path, record)
    record['steps'].append({'messages': []})
    budget_actor.chat(session, 'offline', 'unused', 'offline', [])
    assert raw.limits == [16384]*6 + [32768]*6 + [65536, 16384]
    ob.validate_actor(path, record)
    record['steps'][0]['transport_attempts'][0]['request_parameters']['max_tokens'] = 32768
    with pytest.raises(ValueError, match='generation parameters'): ob.validate_actor(path, record)


@pytest.mark.parametrize('responses,count', [([Response(content='')]*3, 3),
    ([Response(status=429)]*3, 3), ([Response(status=400)], 1),
    ([Response('length')]*3 + [Response(content='')]*3, 6)])
def test_actor_other_errors_bounded_no_escalation(responses, count, monkeypatch):
    monkeypatch.setattr(budget_actor.time, 'sleep', lambda _: None)
    session = Session(responses)
    with pytest.raises((ValueError, RuntimeError)):
        budget_actor.chat(session, 'offline', 'unused', 'offline', [])
    assert session.limits == [16384]*count


def test_partial_saved_response_recovery_uses_raised_budget(tmp_path, monkeypatch):
    ev.initialize(tmp_path, config(1)); enable(tmp_path)
    h = Harness(); h.fail = 'grouping'; h.stop = 'truncated'; h.failures = 6
    write = ev.grouping.write_record
    def crash(path, value):
        write(path, value)
        if path.name == 'response.json' and path.parent.name == '007': raise KeyboardInterrupt()
    monkeypatch.setattr(ev.grouping, 'write_record', crash)
    with pytest.raises(KeyboardInterrupt): run(tmp_path, h, resume=True)
    monkeypatch.setattr(ev.grouping, 'write_record', write)
    run(tmp_path, h, resume=True)
    assert h.calls.count('grouping') == 7
    assert ev.read(tmp_path/'rounds/R01/grouping/result.json')['path'].endswith('/recovered')


def test_real_old_parent_new_actor_source_review(tmp_path):
    import hashlib
    from src.adapters.alfworld.skill_runtime import implementation_metadata
    from src.skill_evolution.v23.gate import build_gate
    original_root = ev.ROOT/'artifacts/methods/v23_4/v23_4_alfworld_formal_001/S1'
    # Existing immutable Parent trajectories supply real identity/reset/implementation facts.
    parents = [ev.read(ev.read(p)['trajectory']) for p in sorted((original_root/'rounds/R03/parent_runs').glob('*/result.json'))]
    assert len(parents) == 10
    ev.initialize(tmp_path, config(1))
    ev.save(tmp_path/'contract.json', ev.read(original_root/'contract.json'))
    enable(tmp_path)
    candidates = deepcopy(parents)
    new = implementation_metadata()
    for name in ('budget_actor.py', 'output_budget.py'):
        new['files']['v23_4/'+name] = hashlib.sha256((ev.ROOT/'src/skill_evolution/v23_4'/name).read_bytes()).hexdigest()
    for record in candidates:
        record['implementation'] = deepcopy(new)
        record['run_id'] += '_synthetic_candidate'
    review = ob.implementation_review(tmp_path, parents, candidates)
    gate = build_gate(parents, candidates, [p['task']['id'] for p in parents],
                      parent_skill=None, candidate_skill=None, implementation_review=review)
    assert len(gate['audit']) == 10
    candidates[0]['implementation']['files']['run_task.py'] = 'tampered'
    with pytest.raises(ValueError, match='not covered'): ob.implementation_review(tmp_path, parents, candidates)


def test_future_evaluation_uses_opt_in_actor_without_starting_it(tmp_path, monkeypatch):
    from src.skill_evolution.v23_4 import benchmark as bm, evaluation
    experiment, campaign = tmp_path/'experiment', tmp_path/'campaign'
    bm.prepare(experiment, campaign); enable(campaign)
    monkeypatch.setattr(ev, 'final_parent', lambda _: None)
    bundle = evaluation.prepare(experiment/'config/evaluation.json')
    command = next(iter(bundle['commands']['S1'].values()))
    assert command[4:6] == ['-m', 'src.skill_evolution.v23_4.budget_actor']
    assert command[command.index('--budget-campaign')+1] == str(campaign)
    assert evaluation.actor_config(bundle)['_output_budget_campaign'] == str(campaign)
    assert bundle['configs']['S1']['output_budget_policy'] == ob.POLICY

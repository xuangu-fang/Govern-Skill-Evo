import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import requests

from src.adapters.alfworld import skill_runtime as rt
from src.adapters.alfworld.run_task_skill import run_episode, RecordingSession
from src.adapters.alfworld.run_task_upstream import chat
from src.adapters.alfworld.verify_skill_run import verify_record
from src.skill_evolution.v23_5 import evolution as ev, evaluation
from tests.adapters.alfworld.test_skill_episode import FakeEnvironment
from .test_baseline import Harness, config
from .test_initial_epochs import configured


def align_record(record):
    record.setdefault('purpose', 'optimization')
    record['protocol'] = rt.execution_protocol(record['protocol']['max_steps'], rt.SKILLOPT_INJECTION)
    observation, history = record['initial_observation'], []
    for event in record['steps']:
        event['messages'] = rt.build_skill_messages(observation, event['admissible_commands'], record['goal'],
                                                   history, record['skill'], rt.SKILLOPT_INJECTION)
        history.append({'observation': observation, 'action': event['action']})
        observation = event['observation']
    record['context_fingerprint'] = rt.context_fingerprint(record)
    record['execution_fingerprint'] = rt.execution_fingerprint(record)
    return record


def test_training_gate_replay_use_new_protocol_and_resume(tmp_path):
    cfg = configured(); cfg['actor_skill_injection'] = rt.SKILLOPT_INJECTION
    h = Harness()
    def actor(task, skill, dest, cfg):
        path = h.actor(task, skill, dest, cfg)
        ev.save(path, align_record(ev.read(path)))
        return path
    ev.run_campaign(tmp_path, config=cfg, actor_runner=actor, generate=h.generate)
    assert ev.final_parent(tmp_path).read_text().startswith(cfg['initial_skill']['text'])
    assert ev.read(tmp_path/'rounds/R02/result.json')['outcome'] == 'ACCEPT'
    before = len(h.actor_calls)
    ev.run_campaign(tmp_path, resume=True, actor_runner=actor, generate=h.generate)
    assert len(h.actor_calls) == before


def test_training_and_test_command_parameters_match():
    cfg = config(); cfg['actor_skill_injection'] = rt.SKILLOPT_INJECTION
    a = ev.actor_command('train:0000', Path('skill.md'), Path('train'), cfg)
    b = ev.actor_command('test:0000', Path('skill.md'), Path('test'), cfg, final=True)
    for option in ('--split', '--purpose', '--task-id', '--output-root'):
        a[a.index(option)+1] = b[b.index(option)+1] = 'IGNORED_TASK_CONTEXT'
    assert a == b
    assert a[a.index('--skill-injection')+1] == rt.SKILLOPT_INJECTION
    with pytest.raises(ValueError): ev.actor_command('test:0000', None, Path('x'), cfg)
    with pytest.raises(ValueError): ev.actor_command('train:0000', None, Path('x'), cfg, final=True)


def test_final_test_waits_for_published_campaign(tmp_path):
    cfg = configured(); exp = tmp_path/'experiment'; campaign = tmp_path/'campaign'
    ev.save(exp/'config/campaign.json', cfg); ev.initialize(campaign, cfg)
    with pytest.raises(ValueError, match='not complete'): evaluation.prepare(exp, campaign)


@pytest.mark.parametrize('attempts', [3, 6])
@pytest.mark.parametrize('transient_status', [401, 503])
@pytest.mark.parametrize('output_format', [rt.LEGACY_OUTPUT, rt.ACTION_ONLY_OUTPUT])
def test_final_evaluation_actual_messages_archive_and_resume(tmp_path, monkeypatch, attempts, transient_status, output_format):
    cfg = config(1)
    cfg['max_attempts'] = cfg['actor_request_attempts'] = attempts
    monkeypatch.setattr('src.adapters.alfworld.run_task_upstream.time.sleep', lambda _: None)
    cfg.update(actor_skill_injection=rt.SKILLOPT_INJECTION, actor_base_url='https://offline.invalid',
               environment_root=str(tmp_path), actor_max_workers=1)
    if output_format != rt.LEGACY_OUTPUT:
        cfg['actor_output_format'] = output_format
    task = {'id': 'test:0000', 'gamefile': 'game.tw-pddl', 'task_type': 'fixture'}
    cfg['task_items'] = {task['id']: task}
    game = tmp_path/'game.tw-pddl'; game.write_text('offline fixture')
    manifest = tmp_path/'items.json'; manifest.write_text(json.dumps([task]))
    bundle = {'actor_config': cfg, 'campaign': str(tmp_path/'campaign'), 'tasks': [task],
              'skill_text': 'Use the visible actions.\n', 'initial_reference': {'remeasure': False},
              'runtime': {'packages': {k: 'fixture' for k in ('alfworld', 'textworld', 'requests')}}}
    calls = []
    def actor(tid, skill, dest, conf):
        calls.append(tid)
        record = rt.make_record(item=task, split='test', purpose='final', skill=rt.load_skill(skill),
            model=cfg['actor_model'], max_steps=50, gamefile=game, manifest_path=manifest,
            versions=bundle['runtime']['packages'],
            backend_id=hashlib.sha256(cfg['call_config']['endpoint'].encode()).hexdigest(), injection=rt.SKILLOPT_INJECTION,
            output_format=output_format)
        record['request_policy'] = {'max_attempts': attempts, 'strict_response': True}
        path = dest/'trajectory.json'
        response = requests.Response(); response.status_code = 200
        response._content = json.dumps({'choices': [{'finish_reason': 'stop', 'message': {'content': '<action>look</action>'}}],
                                      'usage': {'prompt_tokens': 5, 'completion_tokens': 5, 'total_tokens': 10}}).encode()
        sent = []
        def post(*a, **kw):
            sent.append(kw['json'])
            response.status_code = transient_status if attempts == 6 and len(sent) < 6 else 200
            return response
        session = RecordingSession(SimpleNamespace(post=post), record, path, archive_responses=True)
        run_episode(FakeEnvironment(win=True), lambda msgs: chat(session, cfg['call_config']['endpoint'],
                    'offline-key', cfg['actor_model'], msgs, max_attempts=attempts, strict_response=True), record, path)
        assert len(sent) == (6 if attempts == 6 else 1)
        verify_record(record)
        return path
    root = tmp_path/'test'
    result = evaluation.run(root, bundle=bundle, runner=actor)
    assert result['success_rate'] == 1 and len(calls) == 1
    evaluation.run(root, bundle=bundle, runner=actor, resume=True)
    assert len(calls) == 1
    path = Path(result['tasks'][0]['trajectory']); raw = ev.read(path)
    raw['steps'][0]['messages'][1]['content'] = 'wrong wrapper'
    ev.save(path, raw)
    with pytest.raises(ValueError): evaluation.run(root, bundle=bundle, runner=actor, resume=True)

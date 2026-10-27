"""Ported final-evaluation contract test: real Actor code, fake HTTP/environment only."""
import json
from pathlib import Path
from types import SimpleNamespace
import pytest
import requests
from src.skill_evolution.v24.benchmarks.alfworld.actor import skill_runtime as rt
from src.skill_evolution.v24.benchmarks.alfworld.actor.run_task_skill import run_episode, RecordingSession
from src.skill_evolution.v24.benchmarks.alfworld.actor.run_task_upstream import chat
from src.skill_evolution.v24.benchmarks.alfworld.actor.actor_prompt import visible_commands
from src.skill_evolution.v24.benchmarks.alfworld.actor.verify_skill_run import verify_record
from src.skill_evolution.v24 import evolution as ev, evaluation
from src.skill_evolution.v24.config import baseline_config
from src.skill_evolution.v24.benchmark import current
from tests.adapters.alfworld.test_skill_episode import FakeEnvironment
from tests.skill_evolution.v23_5.test_knowledge_review import cfg


def config(rounds=1):
    return baseline_config(cfg(rounds), benchmark=current())


@pytest.mark.parametrize('attempts', [3, 6])
@pytest.mark.parametrize('transient_status', [401, 503])
@pytest.mark.parametrize('output_format', [rt.LEGACY_OUTPUT, rt.ACTION_ONLY_OUTPUT])
@pytest.mark.parametrize('feedback', [False, True])
def test_final_evaluation_actual_messages_archive_and_resume(tmp_path, monkeypatch, attempts, transient_status, output_format, feedback):
    cfg = config(1)
    cfg['max_attempts'] = cfg['actor_request_attempts'] = attempts
    monkeypatch.setattr('src.skill_evolution.v24.benchmarks.alfworld.actor.run_task_upstream.time.sleep', lambda _: None)
    cfg.update(actor_skill_injection=rt.SKILLOPT_INJECTION, actor_base_url='https://offline.invalid',
               environment_root=str(tmp_path), actor_max_workers=1,
               actor_retry_invalid_actions=feedback, actor_action_feedback=feedback)
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
            backend_id=cfg['call_config']['endpoint'], injection=rt.SKILLOPT_INJECTION,
            output_format=output_format, retry_invalid_actions=feedback, action_feedback=feedback)
        record['request_policy'] = {'max_attempts': attempts, 'strict_response': True}
        path = dest/'trajectory.json'
        response = requests.Response(); response.status_code = 200
        sent = []
        def post(*a, **kw):
            sent.append(kw['json'])
            response.status_code = transient_status if attempts == 6 and len(sent) < 6 else 200
            invalid = feedback and len(sent) == 1
            if invalid: response.status_code = 200
            response._content = json.dumps({'choices': [{'finish_reason': 'stop', 'message': {
                'content': '<action>not a legal command</action>' if invalid else '<action>look</action>'}}],
                'usage': {'prompt_tokens': 5, 'completion_tokens': 5, 'total_tokens': 10}}).encode()
            return response
        session = RecordingSession(SimpleNamespace(post=post), record, path, archive_responses=True)
        def options():
            return {'action_candidates': visible_commands(record['steps'][-1]['admissible_commands']),
                    'on_response_error': session.response_error} if feedback else {}
        run_episode(FakeEnvironment(win=True), lambda msgs: chat(session, cfg['call_config']['endpoint'],
                    'offline-key', cfg['actor_model'], msgs, max_attempts=attempts, strict_response=True,
                    action_feedback=feedback, **options()), record, path)
        assert len(sent) == (6 if attempts == 6 else 2 if feedback else 1)
        if feedback:
            assert len(sent[1]['messages']) == 4
            assert all(s['messages'] == sent[1]['messages'] for s in sent[1:])
            assert len(record['steps']) == 1
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


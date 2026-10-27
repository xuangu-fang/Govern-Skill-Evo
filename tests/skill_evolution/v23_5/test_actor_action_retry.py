"""Local action checks share the HTTP retry cap; no real model/environment calls."""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import requests

from src.adapters.alfworld import run_task_skill as actor, skill_runtime as rt
from src.adapters.alfworld.actor_prompt import visible_commands
from src.adapters.alfworld.run_task_upstream import chat
from src.adapters.alfworld.response_archive import verify_response_archive
from src.adapters.alfworld.verify_skill_run import verify_record
from src.skill_evolution.v23.facts import build_facts
from src.skill_evolution.v23_5 import evolution as ev
from tests.adapters.alfworld.test_skill_episode import FakeEnvironment
from .test_baseline import config


def fixture_record(tmp_path, enabled=True, feedback=False):
    (tmp_path/'game').write_text('offline')
    item = {'id': 'train:0000', 'gamefile': 'game'}
    (tmp_path/'train').mkdir()
    manifest = tmp_path/'train/items.json'
    manifest.write_text(json.dumps([item]))
    r = rt.make_record(item=item, split='train', purpose='learning', skill=rt.load_skill(),
        model='offline', max_steps=3, gamefile=tmp_path/'game', manifest_path=manifest,
        versions={}, backend_id='offline', output_format=rt.ACTION_ONLY_OUTPUT,
        retry_invalid_actions=enabled, action_feedback=feedback)
    r['request_policy'] = {'max_attempts': 6, 'strict_response': True}
    return r


def transport(actions, sent, env):
    def send(request, **kwargs):
        assert env.count == 0, 'Rejected attempts must not step the environment'
        sent.append(json.loads(request.body))
        kind = actions[len(sent)-1]
        if kind == 'timeout':
            raise requests.Timeout('offline')
        if kind == 'interrupt':
            raise KeyboardInterrupt()
        response = requests.Response()
        response.request, response.url = request, request.url
        response.status_code = int(kind) if kind in ('429', '401', '400') else 200
        body = {'choices': [{'finish_reason': 'length' if kind == 'length' else 'stop',
                            'message': {'reasoning_content': 'PRIVATE_REASONING_NOT_FOR_FEEDBACK', 'content': {
                                'missing': 'I will look.', 'unclosed': '<action>look',
                                'illegal': '<action>go to cabinet 3</action>',
                                'placeholder': '<action>...</action><action>look</action>',
                                'empty_action': '<action></action>',
                                'hidden': '<action>help</action>',
                                'valid': '<action>look</action>',
                            }.get(kind, '<action>look</action>')}}],
                'usage': {'prompt_tokens': 10, 'completion_tokens': 5, 'total_tokens': 15}}
        if kind == 'malformed': body = {}
        response._content = json.dumps(body).encode()
        return response
    return send


def execute(tmp_path, monkeypatch, actions, *, enabled=True, win=True, feedback=False):
    record = fixture_record(tmp_path, enabled, feedback)
    env = FakeEnvironment(win=win, done=True)
    env.reset = lambda: SimpleNamespace(feedback='Your task is to: test goal',
                                       admissible_commands=['help', 'look'])
    output, sent = tmp_path/'trajectory.json', []
    monkeypatch.setattr(requests.adapters.HTTPAdapter, 'send', staticmethod(transport(actions, sent, env)))
    monkeypatch.setattr('src.adapters.alfworld.run_task_upstream.time.sleep', lambda _: None)
    with requests.Session() as session:
        recorder = actor.RecordingSession(session, record, output, archive_responses=True)
        def generate(messages):
            options = ({'action_candidates': visible_commands(record['steps'][-1]['admissible_commands']),
                        'on_response_error': recorder.response_error} if enabled else {})
            return chat(recorder, 'https://offline.invalid/chat', 'unused', 'offline', messages,
                        max_attempts=6, strict_response=True, action_feedback=feedback, **options)
        actor.run_episode(env, generate, record, output)
    if not feedback:
        assert all(request == sent[0] for request in sent)
        assert all(len(request['messages']) == 2 for request in sent)
    assert all(request['max_tokens'] == 16384 and request['messages'][:2] == sent[0]['messages'] for request in sent)
    assert json.loads(output.read_text()) == record
    for attempt in record['steps'][0]['transport_attempts']:
        verify_response_archive(output, attempt)
    assert verify_record(record)['trace_valid']
    build_facts([record])
    return record, env, sent


@pytest.mark.parametrize('bad', ['missing', 'unclosed', 'illegal', 'placeholder', 'empty_action', 'hidden'])
def test_invalid_action_retries_same_request_without_environment_step(tmp_path, monkeypatch, bad):
    r, env, sent = execute(tmp_path, monkeypatch, [bad, 'valid'])
    assert len(sent) == 2 and env.count == 1 and r['status'] == 'success'
    event, = r['steps']
    assert event['action'] == 'look' and event['fallback'] is None
    error = event['transport_attempts'][0]['response_validation_error']
    assert error == ('missing_action_tag' if bad in ('missing', 'unclosed') else 'action_not_admissible')


def test_legal_response_has_no_extra_request_even_if_environment_does_not_succeed(tmp_path, monkeypatch):
    r, env, sent = execute(tmp_path, monkeypatch, ['valid'], win=False)
    assert len(sent) == 1 and env.count == 1 and r['status'] == 'environment_ended'


def test_all_failures_share_six_total_requests(tmp_path, monkeypatch):
    r, env, sent = execute(tmp_path, monkeypatch, ['missing', '429', 'length', 'illegal', 'timeout', 'valid'])
    assert len(sent) == 6 and env.count == 1 and r['status'] == 'success'


@pytest.mark.parametrize('bad', ['missing', 'illegal', 'malformed'])
def test_exhaustion_stops_without_fallback_or_environment_step(tmp_path, monkeypatch, bad):
    r, env, sent = execute(tmp_path, monkeypatch, [bad]*6)
    assert len(sent) == 6 and env.count == 0 and r['status'] == 'error'
    assert r['error_stage'] == 'model_request'
    event, = r['steps']
    assert event['phase'] == 'requesting' and 'action' not in event and 'observation' not in event


def test_permanent_http_failure_is_not_retried(tmp_path, monkeypatch):
    r, env, sent = execute(tmp_path, monkeypatch, ['400'])
    assert len(sent) == 1 and env.count == 0 and r['status'] == 'error'


@pytest.mark.parametrize('bad', ['missing', 'illegal'])
def test_legacy_protocol_preserves_existing_behavior(tmp_path, monkeypatch, bad):
    r, env, sent = execute(tmp_path, monkeypatch, [bad], enabled=False)
    assert len(sent) == 1 and env.count == 1
    event, = r['steps']
    assert event['fallback'] == ('missing_action_tag' if bad == 'missing' else None)


def test_new_policy_rejects_tampered_executed_action(tmp_path, monkeypatch):
    r, _, _ = execute(tmp_path, monkeypatch, ['valid'])
    event = r['steps'][0]
    event['model_response']['content'] = '<action>go to cabinet 3</action>'
    event.update(action='go to cabinet 3', action_in_admissible_commands=False)
    with pytest.raises(ValueError, match='retry boundary'): verify_record(r)
    with pytest.raises(ValueError, match='retry boundary'): build_facts([r])


def test_train_and_test_commands_freeze_opt_in_policy():
    cfg = config(1)
    cfg['actor_retry_invalid_actions'] = True
    ev.validate_config(cfg)
    for task, final in [('train:0000', False), ('test:0000', True)]:
        assert '--retry-invalid-actions' in ev.actor_command(task, None, Path('offline'), cfg, final=final)
    cfg.pop('actor_retry_invalid_actions')
    assert '--retry-invalid-actions' not in ev.actor_command('train:0000', None, Path('offline'), cfg)
    cfg['actor_retry_invalid_actions'] = 'true'
    with pytest.raises(ValueError, match='boolean'): ev.validate_config(cfg)


@pytest.mark.parametrize('feedback', [False, True])
def test_actual_cli_enables_action_retries(tmp_path, monkeypatch, feedback):
    fixture_record(tmp_path)
    env, sent = FakeEnvironment(win=True), []
    env.seed = lambda _: None
    env.close = lambda: None
    monkeypatch.setattr(actor, 'SPLIT_ROOT', tmp_path)
    monkeypatch.setattr(actor, 'load_dotenv', lambda *a, **k: None)
    monkeypatch.setattr(actor, 'installed_versions', lambda: {})
    monkeypatch.setattr(actor, 'environment_modules', lambda: (
        SimpleNamespace(start=lambda *a, **k: env, EnvInfos=lambda **k: None), lambda **k: None))
    monkeypatch.setenv('ALFWORLD_DATA', str(tmp_path))
    monkeypatch.setenv('OPENAI_BASE_URL', 'https://offline.invalid')
    monkeypatch.setenv('OPENAI_API_KEY', 'offline-test')
    monkeypatch.setattr(requests.adapters.HTTPAdapter, 'send', staticmethod(transport(['illegal', 'valid'], sent, env)))
    monkeypatch.setattr('src.adapters.alfworld.run_task_upstream.time.sleep', lambda _: None)
    assert actor.main(['--output-root', str(tmp_path/'runs'), '--model', 'offline', '--strict-response',
                       '--archive-responses', '--retry-invalid-actions', '--output-format', rt.ACTION_ONLY_OUTPUT]
                      + (['--action-feedback'] if feedback else [])) == 0
    path, = (tmp_path/'runs').glob('*/trajectory.json')
    r = json.loads(path.read_text())
    assert len(sent) == 2 and env.count == 1 and rt.protocol_action_retry(r['protocol'])
    assert verify_record(r)['trace_valid']
    assert rt.protocol_action_feedback(r['protocol']) == feedback
    assert len(sent[1]['messages']) == (4 if feedback else 2)

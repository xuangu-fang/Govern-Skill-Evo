"""Actor feedback preserves the frozen task and replaces only the latest error."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from src.adapters.alfworld.verify_skill_run import verify_record
from src.adapters.alfworld.response_archive import verify_response_archive
from src.adapters.alfworld import skill_runtime as rt
from src.skill_evolution.v23.facts import build_facts
from src.skill_evolution.v23_5 import evolution as ev
from .test_actor_action_retry import execute
from .test_baseline import config


@pytest.mark.parametrize('bad', ['missing', 'unclosed', 'illegal', 'placeholder', 'empty_action', 'hidden'])
def test_previous_body_and_specific_diagnostic(tmp_path, monkeypatch, bad):
    r, env, sent = execute(tmp_path, monkeypatch, [bad, 'valid'], feedback=True)
    assert env.count == 1 and len(sent) == 2 and r['status'] == 'success'
    messages = sent[1]['messages']
    assert len(messages) == 4 and messages[2]['role'] == 'assistant' and messages[3]['role'] == 'user'
    source = r['steps'][0]['transport_attempts'][0]['action_validation']
    assert messages[2]['content'] == source['content']
    assert messages[3]['content'] == source['diagnostic']
    assert '# Previous Action Validation Error' in source['diagnostic']
    assert 'environment state is unchanged' in source['diagnostic']
    assert 'PRIVATE_REASONING_NOT_FOR_FEEDBACK' not in json.dumps(sent)
    if bad in ('missing', 'unclosed'):
        assert 'No complete action element' in source['diagnostic']
    else:
        assert 'not in the current admissible action list' in source['diagnostic']
    if bad == 'illegal':
        assert '"go to cabinet 3"' in source['diagnostic']
        assert 'examine cabinet 3' not in source['diagnostic']


def test_shared_cap_preserved_feedback_and_replacement(tmp_path, monkeypatch):
    r, env, sent = execute(tmp_path, monkeypatch,
                          ['illegal', '401', 'length', 'missing', 'timeout', 'valid'], feedback=True)
    assert len(sent) == 6 and env.count == 1
    assert sent[1] == sent[2] == sent[3]
    assert sent[4] == sent[5] and sent[4] != sent[1]
    assert sent[1]['messages'][2]['content'] == '<action>go to cabinet 3</action>'
    assert sent[4]['messages'][2]['content'] == 'I will look.'
    attempts = r['steps'][0]['transport_attempts']
    assert [a['feedback_from_attempt'] for a in attempts] == [None, 1, 1, 1, 4, 4]


@pytest.mark.parametrize('bad', ['illegal', 'missing'])
def test_feedback_does_not_extend_budget(tmp_path, monkeypatch, bad):
    r, env, sent = execute(tmp_path, monkeypatch, [bad]*6, feedback=True)
    assert len(sent) == 6 and env.count == 0 and r['status'] == 'error'
    assert len(r['steps']) == 1 and 'action' not in r['steps'][0]
    assert all(len(request['messages']) == 4 for request in sent[1:])


def test_normal_response_has_no_feedback_or_extra_call(tmp_path, monkeypatch):
    r, env, sent = execute(tmp_path, monkeypatch, ['valid'], feedback=True)
    assert len(sent) == 1 and len(sent[0]['messages']) == 2 and env.count == 1


def test_interruption_preserves_actual_feedback_request(tmp_path, monkeypatch):
    r, env, sent = execute(tmp_path, monkeypatch, ['illegal', 'interrupt'], feedback=True)
    assert r['status'] == 'interrupted' and env.count == 0
    attempts = r['steps'][0]['transport_attempts']
    assert attempts[1]['messages'] == sent[1]['messages']
    assert attempts[1]['feedback_from_attempt'] == 1


@pytest.mark.parametrize('mutation', ['messages', 'diagnostic', 'source', 'hash'])
def test_reload_rejects_feedback_tampering(tmp_path, monkeypatch, mutation):
    r, _, _ = execute(tmp_path, monkeypatch, ['illegal', 'valid'], feedback=True)
    a, b = r['steps'][0]['transport_attempts']
    if mutation == 'messages': b['messages'][2]['content'] = 'changed'
    elif mutation == 'diagnostic': a['action_validation']['diagnostic'] = 'changed'
    elif mutation == 'source': b['feedback_from_attempt'] = None
    else: b['request_sha256'] = 'changed'
    with pytest.raises(ValueError): verify_record(r)
    with pytest.raises(ValueError): build_facts([r])


def test_feedback_body_must_match_raw_response(tmp_path, monkeypatch):
    r, _, _ = execute(tmp_path, monkeypatch, ['illegal', 'valid'], feedback=True)
    a = deepcopy(r['steps'][0]['transport_attempts'][0])
    a['action_validation']['content'] = '<action>go to cabinet 4</action>'
    with pytest.raises(ValueError, match='raw response'):
        verify_response_archive(tmp_path/'trajectory.json', a)


def test_train_and_final_commands_share_policy():
    cfg = config(1)
    cfg.update(actor_retry_invalid_actions=True, actor_action_feedback=True)
    ev.validate_config(cfg)
    for task, final in [('train:0000', False), ('test:0000', True)]:
        cmd = ev.actor_command(task, None, Path('offline'), cfg, final=final)
        assert '--action-feedback' in cmd and '--retry-invalid-actions' in cmd
    cfg['actor_retry_invalid_actions'] = False
    with pytest.raises(ValueError, match='requires action retries'): ev.validate_config(cfg)
    with pytest.raises(ValueError): rt.execution_protocol(50, action_feedback=True)

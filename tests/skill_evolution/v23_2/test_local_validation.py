"""Verify version isolation, real contracts, retries and stops without a model."""
from copy import deepcopy
import json
from pathlib import Path

import pytest
import requests

from src.skill_evolution.v23 import diagnosis, preconditioner as pc, editor, evolution, grouping
from src.skill_evolution.v23_2 import local_validation as local
from tests.skill_evolution.v23.test_diagnosis import make_grouping, proposal, answer


@pytest.fixture
def saved(tmp_path):
    grouped = grouping.load_grouping(make_grouping(tmp_path/'upstream'))
    return {**grouped, 'diagnosis': proposal(), 'memory': {'entries': [], 'sources': {}}}


@pytest.fixture
def config():
    return {'call_config': {'model': 'offline'}, 'max_attempts': 3, 'retry_delay_seconds': 0,
            'max_input_chars': 1000000, 'max_message_utf8_bytes': 1500000}


def keep():
    return {'decision': 'ready', 'reason': 'Keep the supported Update.', 'adjustments': [], 'checks': None}


@pytest.mark.parametrize('base,model', [
    ('http://llm-proxy.intra.xiaojukeji.com', 'deepseek-v4.1-flash'),
    ('https://api.deepseek.com', 'deepseek-flash'),
])
def test_live_stage_routes_and_archives_actual_configuration(saved, config, tmp_path, monkeypatch, base, model):
    from types import SimpleNamespace
    monkeypatch.setenv('OPENAI_BASE_URL', base)
    monkeypatch.setenv('OPENAI_API_KEY', 'synthetic')
    config['call_config'] = grouping.call_configuration(
        base_url='https://api.deepseek.com', model='deepseek-flash', max_tokens=16384, timeout=300)
    config['stage_configs'] = {'preconditioner': {**config['call_config'], 'max_tokens': 20000}}
    original = deepcopy(config)
    calls = []
    payload = {'model': model, 'choices': [{'message': {'content': json.dumps(keep())}, 'finish_reason': 'stop'}]}
    def post(session, endpoint, **kwargs):
        calls.append((endpoint, kwargs['json']))
        return SimpleNamespace(status_code=200, content=json.dumps(payload).encode(), json=lambda: payload)
    monkeypatch.setattr(requests.Session, 'post', post)
    out = tmp_path/'routed'
    result = local.run_stage('preconditioner', saved, out, config)
    meta = evolution.read(out/'attempts/001/run.json')['call_config']
    assert meta['endpoint'] == calls[0][0] == base + '/chat/completions'
    assert meta['model'] == calls[0][1]['model'] == model
    assert meta['max_tokens'] == calls[0][1]['max_tokens'] == 20000
    assert config == original and len(calls) == 1
    assert local.load_attempt(out/'attempts/001') == result
    with pytest.raises(FileExistsError):
        local.run_stage('preconditioner', saved, out, config)
    assert len(calls) == 1


def test_default_messages_inherit_v23(saved):
    for name, module in local.MODULES.items():
        assert local.PROMPTS[name] == module.PROMPT_PATH
        assert local.messages_for(name, saved) == module.messages_for(saved)


def test_archived_prompt_replacements_require_explicit_selection(saved):
    replacements = {
        'diagnosis': (
            'Its triggering conditions must be identifiable from information available to the Actor at decision time.',
            'Each Update must be executable using information and actions available to the Actor at every required decision point, including throughout multi-step procedures.'),
        'preconditioner': (
            'Examine whether each Update is appropriate relative to the Parent Skill and executable using information and actions available to the Actor at decision time.',
            'Examine whether each Update is appropriate relative to the Parent Skill. Check whether each Update is executable throughout its intended behavior. If it depends on unavailable information, adjust its strategy or scope to remove that dependency, or withdraw it. Merely acknowledging the limitation in the reason is insufficient.')}
    for name, (old, new) in replacements.items():
        original = local.MODULES[name].PROMPT_PATH.read_text()
        archived = Path(local.__file__).with_name(f'{name}_prompt.md')
        assert archived.read_text() == original.replace(old, new)
        before = local.MODULES[name].messages_for(saved)
        current = local.messages_for(name, saved, prompt_path=archived)
        assert current[0]['content'] == before[0]['content'].replace(old, new)
        assert current[1] == before[1]
        assert local.MODULES[name].messages_for(saved) == before
        assert len(current) == 2


def test_diagnosis_to_preconditioner_to_editor_input(saved, config, tmp_path):
    d = local.run_stage('diagnosis', saved, tmp_path/'d', config, generate=lambda *_: answer())
    assert d['diagnosis'] == proposal()
    p = local.run_stage('preconditioner', d, tmp_path/'p', config, generate=lambda *_: answer(keep()))
    assert p['effective_plan'] == proposal()['plan']
    # Pure handoff only; do not run Editor, produce a patch, or build a Candidate.
    assert editor.editor_input(p) == {'parent': saved['facts']['parent'], 'plan': p['effective_plan']}
    assert json.loads(editor.messages_for(p)[1]['content'])['plan'] == p['effective_plan']
    assert p['memory'] == saved['memory']
    assert local.load_attempt(tmp_path/'p/attempts/001') == p
    with pytest.raises(FileExistsError):
        local.run_stage('preconditioner', d, tmp_path/'p', config, generate=lambda *_: pytest.fail('repeat'))


@pytest.mark.parametrize('decision', ['no_change', 'need_evidence'])
def test_semantic_stops_are_not_retried(saved, config, tmp_path, decision):
    if decision == 'no_change':
        result = {'decision': decision, 'reason': 'Unsupported dependency.',
                  'adjustments': [{'from': ['u1'], 'to': [], 'basis': ['P1:1'], 'reason': 'Cannot justify it.'}], 'checks': []}
    else:
        result = {'decision': decision, 'reason': 'Missing essential evidence.', 'adjustments': [], 'checks': None}
    calls = []
    def generate(*_):
        calls.append(1)
        return answer(result)
    value = local.run_stage('preconditioner', saved, tmp_path/'p', config, generate=generate)
    assert value['effective_plan'] is None and len(calls) == 1


def test_contract_retry_preserves_output_and_identical_messages(saved, config, tmp_path):
    bad = keep(); bad['unexpected_score'] = 1
    messages = []
    def generate(msg, path):
        messages.append(deepcopy(msg))
        return answer(bad if len(messages) == 1 else keep())
    local.run_stage('preconditioner', saved, tmp_path/'p', config, generate=generate)
    assert messages[0] == messages[1]
    first = tmp_path/'p/attempts/001'
    assert evolution.read(first/'parsed.json') == bad
    assert evolution.read(first/'validation.json')['valid'] is False
    assert evolution.read(first/'error.json')['retryable'] is True
    assert not (first/'effective_plan.json').exists()


def test_timeout_attempt_budget_and_preservation(saved, config, tmp_path):
    calls = []
    def generate(*_):
        calls.append(1)
        raise requests.Timeout('offline timeout')
    with pytest.raises(evolution.Stopped):
        local.run_stage('preconditioner', saved, tmp_path/'p', config, generate=generate)
    assert len(calls) == 3
    assert len(list((tmp_path/'p/attempts').glob('*/error.json'))) == 3
    assert not list((tmp_path/'p').rglob('effective_plan.json'))


@pytest.mark.parametrize('limit', ['max_input_chars', 'max_message_utf8_bytes'])
def test_capacity_stops_before_request_without_compression(saved, config, tmp_path, limit):
    config[limit] = 1
    before = deepcopy(saved)
    with pytest.raises(evolution.Stopped):
        local.run_stage('preconditioner', saved, tmp_path/'p', config,
                        generate=lambda *_: pytest.fail('must not call'))
    assert evolution.read(tmp_path/'p/stop.json')['kind'] == 'capacity'
    assert saved == before
    assert not (tmp_path/'p/attempts').exists()


def test_remote_context_error_is_not_retried(saved, config, tmp_path):
    calls = []
    def generate(msg, path):
        calls.append(1)
        evolution.save(path/'http_status.json', {'status_code': 400})
        (path/'http_response.txt').write_text('maximum context length exceeded')
        raise ValueError('Model API returned HTTP 400')
    with pytest.raises(evolution.Stopped):
        local.run_stage('preconditioner', saved, tmp_path/'p', config, generate=generate)
    assert len(calls) == 1


def test_no_keyword_blacklist_or_semantic_resampling(saved, config, tmp_path):
    value = keep()
    value['adjustments'] = [{'from': ['u1'], 'to': [{'id': 'u1', 'text': 'Choose an unvisited location.'}],
                            'basis': ['P1:1'], 'reason': 'Proposed strategy.'}]
    calls = []
    def generate(*_):
        calls.append(1)
        return answer(value)
    result = local.run_stage('preconditioner', saved, tmp_path/'p', config, generate=generate)
    assert result['effective_plan']['updates'][0]['text'] == 'Choose an unvisited location.'
    assert len(calls) == 1  # Semantic assessment belongs in the report, not retry selection.
    changed = evolution.read(tmp_path/'p/attempts/001/effective_plan.json')
    changed['updates'][0]['text'] = 'tampered'
    evolution.save(tmp_path/'p/attempts/001/effective_plan.json', changed)
    with pytest.raises(ValueError, match='Compiled Plan differs'):
        local.load_attempt(tmp_path/'p/attempts/001')

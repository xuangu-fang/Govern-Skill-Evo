import json
import sys
from types import SimpleNamespace

import pytest

from src.skill_evolution.diagnosis_v17 import run_group_diagnosis, MODEL
from tests.skill_evolution.test_group_diagnosis_input_v17 import case, build
from tests.skill_evolution.test_diagnosis_validation_v17 import valid


def test_one_call_exact_raw_and_settings(case, tmp_path):
    request = build(case)[0]
    raw = ' \n' + json.dumps(valid(request), indent=2) + '\n '
    calls = []
    def transport(prepared):
        calls.append(prepared)
        assert prepared['model'] == MODEL and prepared['temperature'] == 0
        assert prepared['max_completion_tokens'] == 24_000
        assert prepared['max_retries'] == 0
        assert (tmp_path / 'run/request.json').exists()
        return {'raw_response': raw, 'finish_reason': 'stop', 'usage': {'total_tokens': 10}}
    result = run_group_diagnosis(request, artifact_dir=tmp_path / 'run', transport=transport)
    assert result['status'] == 'VALID' and len(calls) == 1
    saved = json.loads((tmp_path / 'run/validated_diagnosis.json').read_text())
    assert saved['raw_response'] == raw
    assert saved['semantic'] == valid(request)
    with pytest.raises(FileExistsError):
        run_group_diagnosis(request, artifact_dir=tmp_path / 'run', transport=transport)
    assert len(calls) == 1


@pytest.mark.parametrize('stage,raw,finish', [
    ('PARSE', 'bad JSON', 'stop'), ('STRUCTURE', '{}', 'stop'),
    ('PARSE', None, 'stop'), ('COMPLETION', '{}', 'length'),
])
def test_rejection_without_retry_or_fallback(case, tmp_path, stage, raw, finish):
    calls = []
    def transport(prepared):
        calls.append(1)
        return {'raw_response': raw, 'finish_reason': finish, 'usage': None}
    result = run_group_diagnosis(build(case)[0], artifact_dir=tmp_path / 'run', transport=transport)
    assert result['status'] == 'REJECTED' and result['stage'] == stage
    assert len(calls) == 1
    assert (tmp_path / 'run/response.json').exists()
    assert not (tmp_path / 'run/validated_diagnosis.json').exists()


def test_transport_error_stops_and_is_audited(case, tmp_path):
    calls = []
    def transport(prepared):
        calls.append(1)
        raise RuntimeError('private connection details')
    result = run_group_diagnosis(build(case)[0], artifact_dir=tmp_path / 'run', transport=transport)
    assert result['stage'] == 'TRANSPORT' and len(calls) == 1
    assert 'private connection details' not in (tmp_path / 'run/validation.json').read_text()


def test_linkage_error_rejects_whole_response(case, tmp_path):
    request = build(case)[0]
    output = valid(request)
    output['success_analysis']['evidence_refs'] = []
    result = run_group_diagnosis(request, artifact_dir=tmp_path / 'run', transport=lambda _: {
        'raw_response': json.dumps(output), 'finish_reason': 'stop'})
    assert result['stage'] == 'LINKAGE'
    assert not (tmp_path / 'run/validated_diagnosis.json').exists()


def test_real_adapter_disables_sdk_retries_and_preserves_raw(case, tmp_path, monkeypatch):
    request = build(case)[0]
    raw = '\n' + json.dumps(valid(request)) + '\n'
    calls = []
    class Client:
        def __init__(self, **kwargs):
            assert kwargs['max_retries'] == 0
            assert kwargs['timeout'] == 300
            self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def create(self, **kwargs):
            calls.append(kwargs)
            return SimpleNamespace(model=MODEL, id='test', usage=None, choices=[SimpleNamespace(
                message=SimpleNamespace(content=raw, refusal=None), finish_reason='stop')])
    monkeypatch.setitem(sys.modules, 'openai', SimpleNamespace(OpenAI=Client))
    monkeypatch.setenv('OPENAI_API_KEY', 'test-key')
    monkeypatch.setenv('OPENAI_BASE_URL', 'https://example.invalid')
    result = run_group_diagnosis(request, artifact_dir=tmp_path / 'run')
    assert result['status'] == 'VALID' and len(calls) == 1
    assert calls[0]['model'] == MODEL and calls[0]['temperature'] == 0
    assert calls[0]['reasoning_effort'] == 'high'
    assert json.loads((tmp_path / 'run/response.json').read_text())['raw_response'] == raw


def test_experiment_scope_reaches_transport_and_audit(case, tmp_path):
    scope = 'Evaluate only the constraints configured for this experiment.'
    seen = []
    def transport(prepared):
        seen.append(prepared)
        return {'raw_response': '{}', 'finish_reason': 'stop', 'refusal': None}
    run_group_diagnosis(build(case)[0], artifact_dir=tmp_path / 'scoped',
                        transport=transport, experiment_scope=scope)
    saved = json.loads((tmp_path / 'scoped' / 'request.json').read_text())
    assert saved == seen[0]
    assert saved['experiment_scope'] == scope
    assert scope in saved['system_prompt']

"""Fifth-step retry authorization is tested without any network call."""
from copy import deepcopy
import json

import pytest

from experiments.methods.v23_4.semantic_generation_001 import run as study
from .offline_cases import cases


@pytest.mark.parametrize('failures', [[], ['429'], ['length'], ['schema'], ['429', 'schema', 'length'], ['schema'] * 4])
def test_bounded_restarts_and_first_valid_selection(tmp_path, monkeypatch, failures):
    case = next(c for c in cases() if c['id'] == 'A3')
    material = {'payload': case['payload']}
    messages = [{'role': 'user', 'content': 'Frozen fixture.'}]
    config = {'endpoint': 'http://fixture.invalid', 'model': 'offline', 'max_tokens': 32768, 'timeout_seconds': 300}
    monkeypatch.setattr(study, 'HERE', tmp_path)
    monkeypatch.setattr(study, 'verify', lambda: ('fake-secret-never-archived', config))
    monkeypatch.setattr(study, 'inputs', lambda *args: (deepcopy(material), deepcopy(messages)))
    monkeypatch.setattr(study.time, 'sleep', lambda seconds: None)
    requests = []

    def send(req, key, dest, _):
        index = len(requests)
        requests.append(deepcopy(req))
        kind = failures[index] if index < len(failures) else 'valid'
        study.save(dest / 'http_status.json', {'status_code': 429 if kind == '429' else 200})
        if kind == '429': raise ValueError('Model API returned HTTP 429')
        output = {} if kind == 'schema' else case['output']
        return {'content': json.dumps(output), 'finish_reason': 'length' if kind == 'length' else 'stop'}

    monkeypatch.setattr(study, 'transport', lambda: send)
    if len(failures) == 4:
        with pytest.raises(RuntimeError, match='restarts exhausted'): study.run('A3', 'pc')
        assert not (tmp_path / 'runs/A3_pc/selected.json').exists()
    else:
        study.run('A3', 'pc')
        assert study.load('A3', 'pc')['raw_preconditioner'] == case['output']
        study.run('A3', 'pc')  # Reuse never triggers another request.
    assert len(requests) == min(len(failures)+1, 4)
    assert all(r['body']['messages'] == messages for r in requests)
    for i, req in enumerate(requests):
        assert req['body']['max_tokens'] == (65536 if 'length' in failures[:i] else 32768)
    assert 'fake-secret' not in ''.join(p.read_text() for p in tmp_path.rglob('*.json'))


def test_semantic_keep_is_not_a_retry(tmp_path, monkeypatch):
    from .helpers import keep
    case = next(c for c in cases() if c['id'] == 'A3')
    monkeypatch.setattr(study, 'HERE', tmp_path)
    monkeypatch.setattr(study, 'verify', lambda: ('secret', {'endpoint': 'http://fixture.invalid', 'max_tokens': 32768}))
    monkeypatch.setattr(study, 'inputs', lambda *args: ({'payload': case['payload']}, []))
    calls = []
    def send(req, key, dest, _):
        calls.append(1)
        study.save(dest/'http_status.json', {'status_code': 200})
        return {'content': json.dumps(keep(case['payload'])), 'finish_reason': 'stop'}
    monkeypatch.setattr(study, 'transport', lambda: send)
    study.run('A3', 'pc')
    assert calls == [1]
    assert study.load('A3', 'pc')['effective_plan'] == case['payload']['plan']

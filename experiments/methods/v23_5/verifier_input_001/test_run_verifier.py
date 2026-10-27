"""Runner checks use fake transports only; no live calls."""
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from experiments.methods.v23_5.verifier_input_001 import run_verifier as r


@pytest.mark.parametrize('finish,expected', [('stop', 'valid'), ('length', 'failed')])
def test_single_response_no_resampling_or_repeat_on_resume(tmp_path, finish, expected):
    p = {'contract_root': str(r.v.DEFAULT_OUTPUT), 'max_transport_attempts': 3,
         'call_config': {}, 'reference_sha256': 'fixture-review'}
    value = r.v.inputs.read(r.v.DEFAULT_OUTPUT/'cases/R01/verifier_input.json')
    body = {'results': [{'target': t['target'], 'verdict': 'SUPPORTED', 'issues': []} for t in value['targets']]}
    calls = []

    def fake(messages, directory):
        calls.append(directory)
        assert json.loads(messages[1]['content']) == value
        assert 'archive_assessment' not in messages[1]['content']
        return {'finish_reason': finish, 'content': json.dumps(body), 'usage': {'prompt_tokens': 1, 'completion_tokens': 1}}

    assert r.run_round(tmp_path, p, 'R01', fake)['status'] == expected
    assert r.run_round(tmp_path, p, 'R01', fake)['status'] == expected
    assert len(calls) == 1
    assert (calls[0]/'response.json').exists()


def test_interrupted_unknown_does_not_resend(tmp_path):
    p = {'contract_root': str(r.v.DEFAULT_OUTPUT), 'max_transport_attempts': 3}
    directory = tmp_path/'runs/R01/attempts/001'
    r.v.inputs.save(directory/'messages.json', r.v.inputs.read(r.v.DEFAULT_OUTPUT/'cases/R01/messages.json'))
    r.v.inputs.save(directory/'run.json', {'status': 'requesting'})
    def never(*args):
        raise AssertionError('must not call transport')
    assert r.run_round(tmp_path, p, 'R01', never)['status'] == 'interrupted_unknown'


@pytest.mark.parametrize('status,retry', [(401, True), (408, True), (429, True), (503, True), (400, False), (403, False), (200, False)])
def test_only_transport_errors_retry(tmp_path, status, retry):
    r.v.inputs.save(tmp_path/'http_status.json', {'status_code': status})
    assert r.retryable(tmp_path, ValueError('HTTP error')) is retry
    assert not r.retryable(tmp_path, r.v.OutputValidationError('schema'))

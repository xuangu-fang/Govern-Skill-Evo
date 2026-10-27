"""New contract wiring and one-attempt transport behavior; no API calls."""
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from experiments.methods.v23_5.verifier_fact_screen_001 import run_verifier as r


@pytest.mark.parametrize('finish', ['stop', 'length'])
def test_frozen_messages_reference_isolation_and_no_resampling(tmp_path, finish):
    root = tmp_path/'run'
    p = r.prepare(root)
    assert p['max_transport_attempts'] == 1
    assert p['contract_root'] == str(r.contract.DEFAULT_OUTPUT)
    value = r.io.read(r.contract.DEFAULT_OUTPUT/'cases/R01/verifier_input.json')
    calls = []
    def fake(messages, directory):
        calls.append(directory)
        assert json.loads(messages[1]['content']) == value
        assert messages[0]['content'] == (r.contract.DEFAULT_OUTPUT/'verifier_prompt.md').read_text()
        assert 'expected_verdict' not in messages[1]['content']
        rows = [{'target': t['target'], 'verdict': 'SUPPORTED', 'issues': []} for t in value['targets']]
        return {'finish_reason': finish, 'content': json.dumps({'results': rows})}
    for _ in range(2):
        result = r.common.run_round(root, p, 'R01', fake)
        assert result['status'] == ('valid' if finish == 'stop' else 'failed')
    assert len(calls) == 1
    r.check_frozen(root)
    path = root/'reference_review.json'
    path.write_text('{}')
    with pytest.raises(ValueError, match='Reference changed'):
        r.check_frozen(root)


def test_transport_error_does_not_retry_this_experiment(tmp_path):
    import requests
    p = {'contract_root': str(r.contract.DEFAULT_OUTPUT), 'max_transport_attempts': 1,
         'call_config': {}, 'reference_sha256': 'fixture'}
    calls = []
    def fail(messages, directory):
        calls.append(directory)
        raise requests.Timeout('fixture')
    assert r.common.run_round(tmp_path, p, 'R01', fail)['status'] == 'failed'
    assert r.common.run_round(tmp_path, p, 'R01', fail)['status'] == 'failed'
    assert len(calls) == 1

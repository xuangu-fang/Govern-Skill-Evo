"""Request boundaries and frozen-message wiring; fake transport only."""
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from experiments.methods.v23_5.repair_002 import run_repair as r


@pytest.mark.parametrize('finish', ['stop', 'length'])
def test_frozen_input_unchanged_response_and_no_resampling(tmp_path, finish):
    root = tmp_path/'run'
    protocol = r.prepare(root)
    value = r.io.read(r.contract.OUTPUT/'cases/R01/repair_input.json')
    calls = []

    def fake(messages, directory):
        calls.append(directory)
        assert json.loads(messages[1]['content']) == value
        assert messages == r.io.read(r.contract.OUTPUT/'cases/R01/messages.json')
        assert 'expected_verdict' not in messages[1]['content']
        result = {'changes': [{'target': t['target'], 'knowledge': t['knowledge']} for t in value['targets']]}
        return {'finish_reason': finish, 'content': json.dumps(result)}

    for _ in range(2):
        row = r.run_round(root, protocol, 'R01', fake)
        assert row['status'] == ('valid' if finish == 'stop' else 'failed')
    assert len(calls) == 1
    dest = root/'runs/R01/attempts/001'
    assert (dest/'merged_candidate.json').exists() == (finish == 'stop')
    if finish == 'stop':
        assert r.io.read(dest/'merged_candidate.json') == r.io.read(r.contract.OUTPUT/'cases/R01/candidate.json')
    r.check_frozen(root)
    (root/'LIVE_PROTOCOL.md').write_text('tamper')
    with pytest.raises(ValueError, match='Review protocol changed'):
        r.check_frozen(root)


def test_transport_failure_and_unknown_not_resubmitted(tmp_path):
    protocol = {'contract_root': str(r.contract.OUTPUT), 'call_config': {}}
    calls = []

    def fail(messages, directory):
        calls.append(directory)
        raise TimeoutError('test fixture')

    assert r.run_round(tmp_path, protocol, 'R02', fail)['status'] == 'failed'
    assert r.run_round(tmp_path, protocol, 'R02', fail)['status'] == 'failed'
    path = tmp_path/'runs/R02/attempts/001/run.json'
    meta = r.io.read(path)
    meta['status'] = 'requesting'
    r.io.save(path, meta)
    assert r.run_round(tmp_path, protocol, 'R02', fail)['status'] == 'interrupted_unknown'
    assert len(calls) == 1

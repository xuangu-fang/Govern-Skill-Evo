"""Metric checks, including failed-call cost and independently archived retry."""
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from experiments.methods.v23_5.verifier_input_001 import compare_verifier as c


def test_failure_excluded_from_labels_but_included_in_cost_and_retry(tmp_path, monkeypatch):
    initial, retry = tmp_path/'initial', tmp_path/'retry'
    protocol = {'rounds': ['R01'], 'contract_root': str(c.run.v.DEFAULT_OUTPUT),
                'reference_sha256': 'fixed', 'contract_manifest_sha256': 'fixed', 'call_config': {}}
    monkeypatch.setattr(c.run, 'check_frozen', lambda _: protocol)
    baseline = c.run.v.inputs.read(c.run.REFERENCE)
    baseline['items'] = [i for i in baseline['items'] if i['round'] == 'R01']
    c.run.v.inputs.save(initial/'reference_review.json', baseline)
    for root, status in ((initial, 'failed'), (retry, 'valid')):
        folder = root/'runs/R01/attempts/001'
        c.run.v.inputs.save(folder/'run.json', {'attempt': 1, 'status': status, 'started_at': 'fixture'})
        content = {'results': [{'target': i['target'], 'verdict': 'SUPPORTED', 'issues': []}
                               for i in baseline['items']]}
        response = {'finish_reason': 'stop' if status == 'valid' else 'length',
                    'content': json.dumps(content), 'usage': {'prompt_tokens': 10, 'completion_tokens': 20,
                    'total_tokens': 30, 'completion_tokens_details': None, 'cache_read_input_tokens': 3}}
        c.run.v.inputs.save(folder/'response.json', response)
    failed = c.compare(initial)
    assert failed['scored_items'] == 0
    assert failed['usage_totals']['total_tokens']['known_sum'] == 30
    combined = c.compare(initial, [retry], tmp_path/'combined')
    assert combined['scored_items'] == 5
    assert combined['metrics_given_provided_input']['FN'] == 5
    assert combined['usage_totals']['total_tokens']['known_sum'] == 60
    assert combined['usage_totals']['reasoning_tokens']['missing_attempts'] == 2
    assert combined['usage_totals']['cached_input_tokens']['known_sum'] == 6
    assert combined['true_but_missing_input']['scored'] == 3
    assert len(combined['attempts']) == 2
    assert c.run.v.inputs.read(initial/'comparison.json')['scored_items'] == 0
    with pytest.raises(AssertionError):
        c.compare(initial, [retry, retry], tmp_path/'duplicate')

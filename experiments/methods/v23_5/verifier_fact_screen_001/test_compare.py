"""Failed response accounting and review_only exclusion using synthetic responses."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from experiments.methods.v23_5.verifier_fact_screen_001 import compare as c


def test_failed_round_cost_and_predeclared_exclusion(tmp_path, monkeypatch):
    protocol = {'rounds': ['R01'], 'contract_root': str(c.run.contract.DEFAULT_OUTPUT),
                'policy_version': c.run.contract.VERSION, 'reference_sha256': 'fixture'}
    monkeypatch.setattr(c.run, 'check_frozen', lambda _: protocol)
    ref = c.run.io.read(c.run.contract.DEFAULT_OUTPUT/'reference_review.json')
    ref['items'] = [x for x in ref['items'] if x['round'] == 'R01']
    c.run.io.save(tmp_path/'reference_review.json', ref)
    directory = tmp_path/'runs/R01/attempts/001'
    meta = {'status': 'failed', 'attempt': 1, 'started_at': 'fixture'}
    response = {'finish_reason': 'length', 'content': '', 'usage': {'prompt_tokens': 10, 'completion_tokens': 20, 'total_tokens': 30}}
    c.run.io.save(directory/'run.json', meta)
    c.run.io.save(directory/'response.json', response)
    c.run.io.save(directory/'validation.json', {'valid': False})
    failed = c.compare(tmp_path)
    assert failed['primary_label_metrics']['scored'] == 0
    assert failed['primary_label_metrics']['unavailable'] == 4
    assert failed['primary_label_metrics']['label_recall'] is None
    assert failed['usage_totals']['total_tokens']['known_sum'] == 30
    assert failed['usage_totals']['reasoning_tokens']['missing_attempts'] == 1
    # Reject just the boundary case; it must not become a primary false positive.
    rows = []
    for item in ref['items']:
        reject = item['scoring_group'] == 'review_only'
        rows.append({'target': item['target'], 'verdict': 'CONFLICT' if reject else 'SUPPORTED',
                     'issues': [{'statement': item['knowledge']['text'], 'reason': 'Synthetic fixture', 'evidence': []}] if reject else []})
    meta['status'] = 'valid'
    response.update(finish_reason='stop', content=json.dumps({'results': rows}))
    c.run.io.save(directory/'run.json', meta)
    c.run.io.save(directory/'response.json', response)
    c.run.io.save(directory/'validation.json', {'valid': True})
    result = c.compare(tmp_path)
    assert result['primary_label_metrics']['FP'] == 0
    assert result['primary_label_metrics']['TN'] == 3
    assert result['primary_label_metrics']['FN'] == 1
    assert result['review_only'][0]['predicted_verdict'] == 'CONFLICT'

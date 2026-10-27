"""Compare valid screen responses with frozen labels; no API calls or adjudication guesses."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from experiments.methods.v23_5.verifier_fact_screen_001 import run_verifier as run


def compare(output):
    protocol = run.check_frozen(output)
    reference = run.io.read(output/'reference_review.json')
    predictions, attempts, rounds = {}, [], []
    for name in protocol['rounds']:
        model_input = run.io.read(Path(protocol['contract_root'])/'cases'/name/'verifier_input.json')
        found = False
        for directory in sorted((output/'runs'/name/'attempts').glob('*')):
            meta = run.io.read(directory/'run.json')
            run.io.require(meta['status'] in ('valid', 'failed'), 'Request still running or unknown')
            response = run.io.read(directory/'response.json') if (directory/'response.json').exists() else {}
            attempts.append({'round': name, 'attempt': meta['attempt'], 'status': meta['status'],
                             'started_at': meta['started_at'], 'finished_at': meta.get('finished_at'),
                             'elapsed_seconds': meta.get('elapsed_seconds'),
                             'finish_reason': response.get('finish_reason'), 'response_model': response.get('response_model'),
                             'content_chars': len(response.get('content') or ''), 'usage': response.get('usage'),
                             'validation': run.io.read(directory/'validation.json')})
            if meta['status'] != 'valid':
                continue
            run.io.require(not found, 'Multiple valid results for one round')
            found = True
            result = run.contract.v.validate_response(response, model_input)
            for item in result['results']:
                key = name, item['target']['entry_index'], item['target']['knowledge_index']
                predictions[key] = item
        rows = [v for key, v in predictions.items() if key[0] == name]
        rounds.append({'round': name, 'targets': len(model_input['targets']), 'valid': found,
                       'SUPPORTED': sum(r['verdict'] == 'SUPPORTED' for r in rows),
                       'CONFLICT': sum(r['verdict'] == 'CONFLICT' for r in rows)})
    items = []
    for item in reference['items']:
        key = item['round'], item['target']['entry_index'], item['target']['knowledge_index']
        prediction = predictions.get(key)
        category = None
        if prediction:
            category = {('CONFLICT', 'CONFLICT'): 'TP', ('CONFLICT', 'SUPPORTED'): 'FN',
                        ('SUPPORTED', 'CONFLICT'): 'FP', ('SUPPORTED', 'SUPPORTED'): 'TN'}[
                            item['expected_verdict'], prediction['verdict']]
        items.append({'round': item['round'], 'target': item['target'], 'scoring_group': item['scoring_group'],
                      'expected_verdict': item['expected_verdict'], 'predicted_verdict': prediction['verdict'] if prediction else None,
                      'label_class': category, 'issues': prediction['issues'] if prediction else None,
                      'required_finding_ids': [f['id'] for f in item['required_findings']]})
    primary = [i for i in items if i['scoring_group'] == 'primary']
    counts = {k: sum(i['label_class'] == k for i in primary) for k in ('TP', 'FN', 'FP', 'TN')}
    ratio = lambda n, d: n/d if d else None
    metrics = {**counts, 'reference_total': len(primary), 'scored': sum(counts.values()),
               'unavailable': sum(i['predicted_verdict'] is None for i in primary),
               'label_precision': ratio(counts['TP'], counts['TP']+counts['FP']),
               'label_recall': ratio(counts['TP'], counts['TP']+counts['FN']),
               'false_rejection_rate_against_reference': ratio(counts['FP'], counts['FP']+counts['TN']),
               'label_agreement': ratio(counts['TP']+counts['TN'], sum(counts.values()))}
    usages = [a['usage'] or {} for a in attempts]
    usage_totals = {}
    fields = {k: [u.get(k) for u in usages] for k in ('prompt_tokens', 'completion_tokens', 'total_tokens')}
    fields['reasoning_tokens'] = [(u.get('completion_tokens_details') or {}).get('reasoning_tokens') for u in usages]
    fields['cached_input_tokens'] = [(u.get('prompt_tokens_details') or {}).get('cached_tokens', u.get('cache_read_input_tokens')) for u in usages]
    for key, values in fields.items():
        known = [n for n in values if type(n) is int]
        usage_totals[key] = {'known_sum': sum(known), 'missing_attempts': len(values)-len(known)}
    result = {'policy_version': protocol['policy_version'], 'reference_sha256': protocol['reference_sha256'],
              'human_reviewed': False, 'prior_outputs_seen': True, 'rounds': rounds,
              'valid_targets': len(predictions), 'total_targets': len(items), 'primary_label_metrics': metrics,
              'review_only': [i for i in items if i['scoring_group'] == 'review_only'],
              'items': items, 'attempts': attempts, 'usage_totals': usage_totals,
              'money_cost': None, 'cost_note': 'API usage only; internal endpoint unit prices unavailable.',
              'specific_finding_review': 'Separate adjudication required; correct CONFLICT labels alone do not establish detection.'}
    run.io.save(output/'comparison.json', result)
    return result


if __name__ == '__main__':
    result = compare(run.OUT)
    print(json.dumps({k: result[k] for k in ('rounds', 'valid_targets', 'primary_label_metrics', 'usage_totals')},
                     ensure_ascii=False, indent=2))

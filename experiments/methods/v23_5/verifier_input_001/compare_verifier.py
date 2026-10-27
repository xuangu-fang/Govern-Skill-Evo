"""Compare live valid outputs with the immutable pre-run provisional review."""
from collections import Counter
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from experiments.methods.v23_5.verifier_input_001 import run_verifier as run


def compare(output, supplemental=(), report_dir=None):
    protocol = run.check_frozen(output)
    baseline = run.v.inputs.read(output/'reference_review.json')
    predictions, attempts, valid_rounds = {}, [], []
    sources = []
    for root in (output, *supplemental):
        p = run.check_frozen(root)
        assert p['reference_sha256'] == protocol['reference_sha256']
        assert p['contract_manifest_sha256'] == protocol['contract_manifest_sha256']
        assert p['call_config'] == protocol['call_config']
        sources.extend((root, name) for name in p['rounds'])
    for root, name in sources:
        case = Path(protocol['contract_root'])/'cases'/name
        model_input = run.v.inputs.read(case/'verifier_input.json')
        for directory in sorted((root/'runs'/name/'attempts').glob('*')):
            meta = run.v.inputs.read(directory/'run.json')
            response = run.v.inputs.read(directory/'response.json') if (directory/'response.json').exists() else {}
            usage = response.get('usage')
            attempts.append({'run_root': str(root), 'round': name, 'attempt': meta['attempt'], 'status': meta['status'],
                             'elapsed_seconds': meta.get('elapsed_seconds'), 'finish_reason': response.get('finish_reason'),
                             'response_model': response.get('response_model'), 'usage': usage,
                             'started_at': meta['started_at'], 'finished_at': meta.get('finished_at')})
            if meta['status'] == 'valid':
                result = run.v.validate_response(response, model_input)
                assert name not in valid_rounds
                valid_rounds.append(name)
                for row in result['results']:
                    predictions[(name, row['target']['entry_index'], row['target']['knowledge_index'])] = row
    items = []
    for gold in baseline['items']:
        key = gold['round'], gold['target']['entry_index'], gold['target']['knowledge_index']
        pred = predictions.get(key)
        category = None
        if pred:
            category = {('CONFLICT', 'CONFLICT'): 'TP', ('CONFLICT', 'SUPPORTED'): 'FN',
                        ('SUPPORTED', 'CONFLICT'): 'FP', ('SUPPORTED', 'SUPPORTED'): 'TN'}[
                            gold['expected_verdict_given_input'], pred['verdict']]
        items.append({**gold, 'predicted_verdict': pred['verdict'] if pred else None,
                      'model_issues': pred['issues'] if pred else None, 'input_relative_class': category})
    matrix = {key: sum(i['input_relative_class'] == key for i in items) for key in ('TP', 'FN', 'FP', 'TN')}
    ratio = lambda n, d: n/d if d else None
    metrics = {**matrix, 'precision': ratio(matrix['TP'], matrix['TP']+matrix['FP']),
               'recall': ratio(matrix['TP'], matrix['TP']+matrix['FN']),
               'false_rejection_rate': ratio(matrix['FP'], matrix['FP']+matrix['TN']),
               'accuracy': ratio(matrix['TP']+matrix['TN'], sum(matrix.values()))}
    archive_groups = {}
    for label in ('SUPPORTED', 'CONFLICT', 'UNCERTAIN'):
        group = [i for i in items if i['archive_assessment'] == label]
        archive_groups[label] = {'total': len(group), 'predictions': dict(Counter(i['predicted_verdict'] or 'UNAVAILABLE' for i in group))}
    gaps = [i for i in items if i['archive_assessment'] == 'SUPPORTED' and i['expected_verdict_given_input'] == 'CONFLICT']
    known_usage = [a['usage'] for a in attempts if a['usage'] is not None]
    usage_totals = {}
    for field in ('prompt_tokens', 'completion_tokens', 'total_tokens', 'prompt_cache_hit_tokens', 'prompt_cache_miss_tokens'):
        values = [u.get(field) for u in known_usage]
        usage_totals[field] = {'known_sum': sum(x for x in values if isinstance(x, int)),
                               'missing_attempts': len(attempts)-sum(isinstance(x, int) for x in values)}
    reasoning = [(u.get('completion_tokens_details') or {}).get('reasoning_tokens') for u in known_usage]
    usage_totals['reasoning_tokens'] = {'known_sum': sum(x for x in reasoning if isinstance(x, int)),
                                      'missing_attempts': len(attempts)-sum(isinstance(x, int) for x in reasoning)}
    cached = [(u.get('prompt_tokens_details') or {}).get('cached_tokens', u.get('cache_read_input_tokens'))
              for u in known_usage]
    usage_totals['cached_input_tokens'] = {'known_sum': sum(x for x in cached if isinstance(x, int)),
                                         'missing_attempts': len(attempts)-sum(isinstance(x, int) for x in cached)}
    result = {'baseline_kind': baseline['reviewer_kind'], 'human_reviewed': False,
              'reference_sha256': protocol['reference_sha256'], 'valid_rounds': valid_rounds,
              'scored_items': sum(matrix.values()), 'total_items': len(items), 'metrics_given_provided_input': metrics,
              'archive_quality_groups': archive_groups,
              'true_but_missing_input': {'total': len(gaps),
                                         'scored': sum(i['predicted_verdict'] is not None for i in gaps),
                                         'unavailable': sum(i['predicted_verdict'] is None for i in gaps),
                                         'rejected': sum(i['predicted_verdict']=='CONFLICT' for i in gaps)},
              'attempts': attempts, 'usage_totals': usage_totals, 'cost_currency_amount': None,
              'cost_note': 'Actual API usage reported; internal endpoint unit prices unavailable. No monetary estimate.',
              'items': items}
    run.v.inputs.save((report_dir or output)/'comparison.json', result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--supplemental', action='append', type=Path, default=[])
    parser.add_argument('--report-dir', type=Path)
    args = parser.parse_args()
    result = compare(run.OUT, args.supplemental, args.report_dir)
    print(json.dumps({k: result[k] for k in ('valid_rounds', 'scored_items', 'metrics_given_provided_input',
                                          'archive_quality_groups', 'true_but_missing_input', 'usage_totals')},
                     ensure_ascii=False, indent=2))

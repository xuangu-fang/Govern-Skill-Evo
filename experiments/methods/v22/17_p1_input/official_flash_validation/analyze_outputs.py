"""Read-only result accounting; no model requests or evidence mutation."""
from datetime import datetime
import hashlib
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[5]
ROOT = REPO / 'artifacts/methods/v22/17_p1_input/official_flash_validation'


def read(path):
    return json.loads(path.read_text())


def analyze():
    protocol = read(ROOT / 'protocol.json')
    rows = []
    for case in protocol['cases']:
        d = ROOT / 'cases' / case['id']
        result, call = read(d / 'result.json'), read(d / 'call.json')
        attempts = call['steps'][0]['transport_attempts']
        assert len(attempts) == 1
        for attempt in attempts:
            raw = attempt['raw_response']
            assert hashlib.sha256((d / raw['path']).read_bytes()).hexdigest() == raw['sha256']
        usage = result.get('usage') or {}
        prompt, completion = usage.get('prompt_tokens'), usage.get('completion_tokens')
        reasoning = usage.get('completion_tokens_details', {}).get('reasoning_tokens')
        hit = usage.get('prompt_cache_hit_tokens', usage.get('prompt_tokens_details', {}).get('cached_tokens'))
        miss = usage.get('prompt_cache_miss_tokens')
        if miss is None and prompt is not None and hit is not None:
            miss = prompt - hit
        start = datetime.fromisoformat(call['started_at'])
        # All current requests are on 2026-10-16, a Friday outside public holidays.
        assert start.date().isoformat() == '2026-10-16'
        peak = start.weekday() < 5 and (1 <= start.hour < 4 or 6 <= start.hour < 10)
        factor = 1 if peak else 0.5
        complete_usage = all(x is not None for x in (hit, miss, completion))
        cost_cny = factor * (hit * .04 + miss * 2 + completion * 8) / 1e6 if complete_usage else None
        cost_usd = factor * (hit * .006 + miss * .3 + completion * 1.2) / 1e6 if complete_usage else None
        rows.append({
            'case_id': case['id'], 'stage': case['stage'], 'profile': case['profile'],
            'request_model': case['parameters']['model'], 'provider_model': result.get('provider_model'),
            'messages_chars': case['messages_chars'], 'max_tokens': case['parameters']['max_tokens'],
            'http_status': result.get('http_status'), 'attempts': len(attempts),
            'strict_json': result['strict_json'], 'production_json': result['production_json'],
            'contract_valid': result['contract_valid'], 'decision': result.get('decision'),
            'validation_error': result.get('validation_error'), 'error_type': result.get('error_type'),
            'finish_reason': result.get('finish_reason'), 'seconds': result['elapsed_seconds'],
            'prompt_tokens': prompt, 'completion_tokens': completion, 'reasoning_tokens': reasoning,
            'visible_tokens_by_subtraction': completion - reasoning if completion is not None and reasoning is not None else None,
            'cache_hit_tokens': hit, 'cache_miss_tokens': miss, 'peak_rate': peak,
            'estimated_cny': cost_cny, 'estimated_usd': cost_usd,
        })
    by_id = {r['case_id']: r for r in rows}
    pairs = []
    for stage in ('diagnosis', 'fusion', 'learning'):
        p1, v3 = by_id[stage + '_p1'], by_id[stage + '_v3']
        pair = {'stage': stage}
        for key in ('messages_chars', 'prompt_tokens', 'completion_tokens', 'reasoning_tokens', 'seconds', 'estimated_cny'):
            a, b = p1[key], v3[key]
            pair[key] = {'p1': a, 'v3': b, 'reduction_fraction': 1 - a / b if a is not None and b not in (None, 0) else None}
        pairs.append(pair)
    totals = {}
    for key in ('attempts', 'prompt_tokens', 'completion_tokens', 'reasoning_tokens', 'cache_hit_tokens', 'cache_miss_tokens', 'estimated_cny', 'estimated_usd'):
        values = [r[key] for r in rows]
        totals[key] = sum(v for v in values if v is not None)
        totals[key + '_missing_records'] = sum(v is None for v in values)
    return {'rows': rows, 'pairs': pairs, 'totals': totals,
        'http_successes': sum(r['http_status'] == 200 for r in rows),
        'strict_json_count': sum(r['strict_json'] for r in rows),
        'contract_valid_count': sum(r['contract_valid'] for r in rows),
        'environment_episodes': 0, 'publication': False,
        'pricing': {'checked_date': '2026-10-16',
            'sources': ['https://api-docs.deepseek.com/zh-cn/quick_start/pricing/', 'https://api-docs.deepseek.com/quick_start/pricing/'],
            'basis': 'Official pricing page retrieved through search. Usage-based estimate, not an account bill. Prior HTTP400 charges remain unknown.',
            'cny_peak_per_million': {'hit': .04, 'miss': 2, 'output': 8},
            'usd_peak_per_million': {'hit': .006, 'miss': .3, 'output': 1.2},
            'off_peak_factor': .5, 'reasoning_in_completion_not_double_counted': True},
        'caveat': 'One sample per condition; output and timing differences are not causal encoding effects. Monetary estimates are not observed billing.'}


if __name__ == '__main__':
    result = analyze()
    target = ROOT.parent / 'analysis/flash_usage_cost.json'
    with target.open('x') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
    print(json.dumps({'path': str(target), 'totals': result['totals']}, ensure_ascii=False))

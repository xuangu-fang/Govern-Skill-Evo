"""Recheck archived Repair responses and compute structural/usage metrics only."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from experiments.methods.v23_5.repair_002 import run_repair as r


def summarize(output):
    protocol = r.check_frozen(output)
    rows = []
    for name in protocol['rounds']:
        source = Path(protocol['contract_root'])/'cases'/name
        directory = output/'runs'/name/'attempts/001'
        r.io.require(len(list(directory.parent.iterdir())) == 1, 'Unexpected extra attempt')
        meta = r.io.read(directory/'run.json')
        row = {'round': name, 'status': meta['status'], 'attempts': 1, 'elapsed_seconds': meta['elapsed_seconds']}
        cfg = protocol['call_config']
        request = r.io.read(directory/'request.json')
        messages = r.io.read(source/'messages.json')
        r.io.require(request['body']['messages'] == messages == r.io.read(directory/'messages.json'), 'Request changed')
        r.io.require(request['endpoint'] == cfg['endpoint'] and request['timeout_seconds'] == cfg['timeout_seconds']
                     and request['attempts'] == 1, 'Transport config differs')
        for field in ('model', 'temperature', 'reasoning_effort', 'thinking', 'stream', 'max_tokens'):
            r.io.require(request['body'][field] == cfg[field], f'Request config differs: {field}')
        response = r.io.read(directory/'response.json') if (directory/'response.json').exists() else None
        if response is not None:
            raw = json.loads((directory/'http_response.txt').read_text())
            r.io.require(r.grouping.response_value(raw) == response, 'Normalized response differs from actual HTTP response')
            r.io.require((directory/'raw_output.txt').read_text() == response['content'], 'Raw content differs')
            row.update(finish_reason=response['finish_reason'], response_model=response['response_model'], usage=response.get('usage'))
        else:
            row.update(finish_reason=None, response_model=None, usage=None)
        if meta['status'] == 'valid':
            value, candidate = r.io.read(source/'repair_input.json'), r.io.read(source/'candidate.json')
            _, _, _, payload = r.contract.load_case(name)
            result, merged = r.checked_result(response, value, candidate, payload)
            r.io.require(result == r.io.read(directory/'repair_output.json') and
                         merged == r.io.read(directory/'merged_candidate.json'), 'Saved repair/merge changed')
            changes = {r.contract.v.position(c['target'], 'target'): c['knowledge'] for c in result['changes']}
            counts = {'replaced': 0, 'deleted': 0, 'unchanged_authorized': 0, 'unchanged_unauthorized': 0}
            for ei, entry in enumerate(candidate['entries']):
                new_index = 0
                for ki, original in enumerate(entry['knowledge']):
                    key = ei, ki
                    replacement = changes.get(key, original)
                    if key not in changes:
                        counts['unchanged_unauthorized'] += 1
                    elif replacement is None:
                        counts['deleted'] += 1
                    elif r.repair.exact(replacement) == r.repair.exact(original):
                        counts['unchanged_authorized'] += 1
                    else:
                        counts['replaced'] += 1
                    if replacement is not None:
                        r.io.require(r.repair.exact(merged['entries'][ei]['knowledge'][new_index]) == r.repair.exact(replacement),
                                     'Position/preservation mismatch')
                        new_index += 1
                r.io.require(merged['entries'][ei]['revises'] == entry['revises'], 'Revision metadata changed')
            row.update(counts)
        rows.append(row)
    usage = {}
    for label, path in [('input_tokens', ('prompt_tokens',)), ('output_tokens', ('completion_tokens',)),
                        ('total_tokens', ('total_tokens',)), ('reasoning_tokens_included_in_output', ('completion_tokens_details', 'reasoning_tokens'))]:
        values = []
        for row in rows:
            value = row['usage']
            for key in path:
                value = value.get(key) if isinstance(value, dict) else None
            values.append(value)
        usage[label] = {'total': sum(values) if all(type(v) is int for v in values) else None,
                        'known_sum': sum(v for v in values if type(v) is int),
                        'missing_rounds': [row['round'] for row, v in zip(rows, values) if type(v) is not int]}
    result = {'rounds': rows, 'valid_rounds': sum(row['status'] == 'valid' for row in rows),
              'total_attempts': len(rows), 'retries': 0, 'usage': usage, 'monetary_cost': None,
              'cost_note': 'Internal billing rate unavailable; reasoning tokens already included in output.',
              'elapsed_seconds': r.io.read(output/'run_summary.json')['elapsed_seconds_this_invocation'],
              'frozen_inputs_and_archives_unchanged': True, 'memory_commits': 0, 'actor_calls': 0,
              'second_semantic_verifier_calls': 0, 'semantic_review_not_included_in_this_report': True}
    r.io.save(output/'structural_usage_summary.json', result)
    return result


if __name__ == '__main__':
    print(json.dumps(summarize(r.OUT), ensure_ascii=False, indent=2))

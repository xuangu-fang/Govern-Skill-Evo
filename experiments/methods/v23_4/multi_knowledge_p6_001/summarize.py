"""Offline measurements only; does not invoke models or alter proposals."""
import json
from .run import HERE, ROOT, core, p4


def stats(entries):
    items = [k for e in entries for k in e['knowledge']]
    return {'entries': len(entries), 'knowledge_items': len(items),
        'text_chars': sum(len(k['text']) for k in items),
        'longest_text_chars': max((len(k['text']) for k in items), default=0),
        'evidence_occurrences': sum(len(k['evidence']) for k in items)}


def main():
    core.verify()
    audit = core.read(HERE / 'AUDIT.json')
    frozen = core.read(HERE / 'config/freeze.json')
    growth, cases = {}, {}
    totals = {k: 0 for k in ('prompt_tokens', 'completion_tokens', 'total_tokens')}
    for label, attempts in audit['cases'].items():
        _, messages = core.inputs(label, 'replay')
        for attempt in attempts:
            path = HERE / f"runs/{label}_replay/attempt_{attempt['attempt']:03}"
            request = core.read(path / 'http/request.json')
            expected = {k: v for k, v in frozen['call_config'].items()
                        if k not in ('endpoint', 'timeout_seconds')}
            expected.update(messages=messages, max_tokens=attempt['max_tokens'])
            assert request['body'] == expected
            assert request['endpoint'] == frozen['call_config']['endpoint']
            assert request['timeout'] == [60, 300] and request['transport_retries'] == 0
            for key in totals: totals[key] += attempt['usage'][key]
        proposal = core.load(label, 'replay')['replay']
        before = core.read(p4.HERE / f'cases/{label}/model_input.json')['memory']
        after = core.read(HERE / f'cases/{label}/results/memory_view.json')
        # Compare the same compact Memory fields, excluding Replay-only Pair metadata.
        before_v3 = {k: before[k] for k in after}
        chars = lambda value: len(json.dumps(value, ensure_ascii=False, separators=(',', ':')))
        growth[label] = {'before': stats(before['entries']), 'proposal': stats(proposal['entries']),
            'after': stats(after['entries']), 'before_v3_chars': chars(before_v3),
            'after_v3_chars': chars(after),
            'knowledge_lengths': [len(k['text']) for e in proposal['entries'] for k in e['knowledge']],
            'note': 'Growth includes newly archived current traces and evidence windows, not just array overhead.'}
        valid = next(a for a in attempts if a['status'] == 'valid')
        baseline = core.read(HERE.with_name('replay_prompt_candidate_001') /
            f'runs/{label}_replay/attempt_001/response.json')['usage']
        cases[label] = {'http_attempts': len(attempts), 'technical_retries': len(attempts)-1,
            'selected_attempt': valid['attempt'], 'valid_usage': valid['usage'],
            'input_token_delta_vs_single_knowledge_candidate': valid['usage']['prompt_tokens']-baseline['prompt_tokens'],
            'proposal': growth[label]['proposal'], 'all_request_settings_verified': True,
            'memory_roundtrip_passed': core.read(HERE / f'cases/{label}/results/MEMORY_AUDIT.json')['structural_roundtrip_passed']}
    result = {'cases': cases, 'all_attempts_usage': totals,
        'http_attempts': audit['http_attempts'], 'protected_files_unchanged': audit['protected_files_unchanged'],
        'semantic_review': 'SEMANTIC_REVIEW.md; no automatic publication'}
    for name, value in [('GROWTH.json', growth), ('RESULTS.json', result)]:
        (HERE / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__': main()

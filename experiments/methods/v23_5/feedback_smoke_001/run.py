"""Three historical failures, one real continuation per arm; no Actor or publication."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import time

from src.skill_evolution.v23.editor import _read_text, _write_text
from src.skill_evolution.v23_5 import comparison as comparison, output_feedback as feedback
from src.skill_evolution.v23_5 import preconditioner as pc
from src.skill_evolution.v23_5.comparison_inputs import CONTRACT, read, save
from src.skill_evolution.v23_5.memory_view import KNOWLEDGE_ONLY

ROOT = Path('artifacts/methods/v23_5/feedback_smoke_001').resolve()
SOURCES = [('json', '003', 'R03', '003'), ('reference', '001', 'R03', '001'),
           ('schema', '007', 'R04', '001')]


def validate(case, content):
    parsed = feedback.output_call('response', pc.parse_json_response, content)
    result = feedback.output_call('Preconditioner output', comparison.validate_output,
                                  ROOT/'cases'/case['id'], case['cell'], parsed)
    return {'parsed': parsed, 'validated': result}


def prepare():
    if ROOT.exists():
        raise ValueError('Use the existing frozen experiment; do not prepare over it')
    spec = read(Path('experiments/methods/v23_5/knowledge_only_single_round_007/config/protocol.json'))
    assert spec['call_config']['max_tokens'] == 32768
    spec.update(max_attempts=1, question='Does targeted feedback repair a known output failure?',
                hypothesis='Feedback reduces repeated errors compared with unchanged regeneration.')
    cases, order = [], []
    for label, group, rnd, attempt in SOURCES:
        source = Path(f'artifacts/methods/v23_5/knowledge_only_single_round_{group}').resolve()
        original = source/f'runs/{rnd}/preconditioner/knowledge_only/attempts/{attempt}'
        case = {'id': label, 'source': str(original), 'cell': {
            'round': rnd, 'stage': 'preconditioner', 'arm': 'knowledge_only'}}
        folder = ROOT/'cases'/label
        material = read(source/f'cases/{rnd}/preconditioner/material.json')
        save(folder/f'cases/{rnd}/preconditioner/material.json', material)
        response = read(original/'response.json')
        assert response['finish_reason'] == 'stop'
        try:
            validate(case, response['content'])
        except feedback.OutputValidationError as exc:
            diagnostic = exc.diagnostic
        else:
            raise ValueError(f'{label}: historical failure is no longer an output error')
        seed = folder/'seed'
        save(seed/'response.json', response)
        save(seed/'error.json', {'kind': 'output_validation', 'diagnostic': diagnostic})
        case['diagnostic'] = diagnostic
        base = pc.messages_for(material, memory_view=KNOWLEDGE_ONLY,
                               memory_contract=CONTRACT, retry_policy=feedback.POLICY)
        old = read(original/'messages.json')
        assert json.loads(base[1]['content']) == json.loads(old[1]['content'])
        save(folder/'base_messages.json', base)
        _write_text(folder/'prompt.md', base[0]['content'])
        for arm in ('unchanged', 'feedback'):
            messages = base if arm == 'unchanged' else feedback.request_messages(base, {
                'policy': feedback.POLICY, 'feedback_from': str(seed)})
            assert len(messages) == (2 if arm == 'unchanged' else 4)
            assert messages[:2] == base
            save(folder/f'{arm}_messages.json', messages)
        cases.append(case)
        arms = ('feedback', 'unchanged') if label == 'reference' else ('unchanged', 'feedback')
        order.extend({'case': label, 'arm': arm} for arm in arms)
    save(ROOT/'manifest.json', {'spec': spec, 'cases': cases, 'order': order,
         'max_real_requests': 6, 'workers': 2, 'policy': feedback.POLICY,
         'design': 'Historical-failure continuation; current prompt shared by both arms; one sample per arm.'})
    print(json.dumps({'prepared': 3, 'real_requests': 0}))


def finish(case, dest, response):
    save(dest/'response.json', response)
    _write_text(dest/'raw_output.txt', response.get('content') or '')
    if response.get('finish_reason') != 'stop':
        result = {'valid': False, 'kind': 'truncated' if response.get('finish_reason') == 'length'
                  else 'technical', 'finish_reason': response.get('finish_reason')}
    else:
        try:
            value = validate(case, response['content'])
            save(dest/'validated.json', value)
            # Reparse/revalidate the saved response using the same production checks.
            assert read(dest/'response.json')['content'] == _read_text(dest/'raw_output.txt')
            assert validate(case, read(dest/'response.json')['content']) == read(dest/'validated.json')
            result = {'valid': True, 'kind': 'valid'}
        except feedback.OutputValidationError as exc:
            result = {'valid': False, 'kind': 'output_validation', 'diagnostic': exc.diagnostic,
                      'exact_same_diagnostic': exc.diagnostic == case['diagnostic']}
    save(dest/'validation.json', result)
    return result


def run_cell(item, manifest, generate):
    case = next(c for c in manifest['cases'] if c['id'] == item['case'])
    dest = ROOT/'runs'/item['case']/item['arm']
    messages = read(ROOT/'cases'/item['case']/f'{item["arm"]}_messages.json')
    if (dest/'result.json').exists():
        return read(dest/'result.json')
    if (dest/'request_started.json').exists():
        if (dest/'response.json').exists():
            response = read(dest/'response.json')
        elif (dest/'http_status.json').exists() and read(dest/'http_status.json')['status_code'] == 200:
            response = comparison.grouping.response_value(read(dest/'http_response.txt'))
        else:
            return {**item, 'valid': False, 'kind': 'interrupted_no_saved_response', 'requests': 1}
        result = {**item, **finish(case, dest, response), 'requests': 1, 'recovered_without_request': True}
        save(dest/'result.json', result)
        return result
    dest.mkdir(parents=True, exist_ok=True)
    save(dest/'messages.json', messages)
    save(dest/'call_config.json', manifest['spec']['call_config'])
    save(dest/'request_started.json', {'at': comparison.evolution.now(), 'requests': 1})
    print(json.dumps({**item, 'status': 'requesting'}), flush=True)
    start = time.monotonic()
    try:
        response = generate(messages, dest)
        result = finish(case, dest, response)
    except Exception as exc:
        result = {'valid': False, 'kind': 'technical', 'error_type': type(exc).__name__}
    result = {**item, **result, 'requests': 1, 'elapsed_seconds': time.monotonic()-start}
    save(dest/'result.json', result)
    print(json.dumps(result, ensure_ascii=False), flush=True)
    return result


def summarize():
    rows = [read(p) for p in sorted((ROOT/'runs').glob('*/*/result.json'))]
    for row in rows:
        dest = ROOT/'runs'/row['case']/row['arm']
        if (dest/'response.json').exists():
            row['usage'] = read(dest/'response.json').get('usage')
    save(ROOT/'summary.json', {'results': rows, 'completed_cells': len(rows),
         'valid_by_arm': {arm: sum(r.get('valid', False) for r in rows if r['arm'] == arm)
                          for arm in ('unchanged', 'feedback')}})
    return read(ROOT/'summary.json')


def run():
    manifest = read(ROOT/'manifest.json')
    generate = comparison.live_generator(manifest['spec'])
    with ThreadPoolExecutor(max_workers=manifest['workers']) as pool:
        list(pool.map(lambda item: run_cell(item, manifest, generate), manifest['order']))
    print(json.dumps(summarize(), ensure_ascii=False), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'run', 'summarize'])
    args = parser.parse_args()
    {'prepare': prepare, 'run': run, 'summarize': summarize}[args.action]()

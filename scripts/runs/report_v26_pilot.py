#!/usr/bin/env python3
"""Read saved pilot requests/usage and export an input index; no API calls."""
import argparse
from collections import defaultdict
from copy import deepcopy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.skill_evolution.v26.benchmarks.officeqa import input_view as iv, prompting
from skilladam.benchmarks.officeqa.rollout import TOOL_SCHEMAS
from scripts.runs.verify_v26_input_view import TokenCounter


def read(path): return json.loads(Path(path).read_text())


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n')


def usage_fields(response):
    usage = response.get('usage') or {}; details = usage.get('completion_tokens_details') or {}
    reasoning = details.get('reasoning_tokens', usage.get('reasoning_tokens'))
    output = usage.get('completion_tokens')
    return {'input_tokens': usage.get('prompt_tokens'), 'output_tokens': output,
        'reasoning_tokens': reasoning,
        'visible_output_tokens': output-reasoning if type(output) is int and type(reasoning) is int else None,
        'cached_input_tokens': usage.get('prompt_cache_hit_tokens', (usage.get('prompt_tokens_details') or {}).get('cached_tokens'))}


def summarize(rows):
    result = {'requests': len(rows), 'length_finishes': sum(r.get('finish_reason') == 'length' for r in rows)}
    for key in ('input_tokens', 'output_tokens', 'reasoning_tokens', 'visible_output_tokens'):
        values = [r[key] for r in rows if type(r.get(key)) is int]
        result[key] = {'sum': sum(values), 'max': max(values) if values else None,
                       'unknown_requests': len(rows)-len(values)}
    return result


def report(directory, *, tokenizer_python=None):
    root = Path(directory).resolve(); out = root/'analysis'; out.mkdir(exist_ok=True)
    cfg = read(root/'config.json'); rows = []; outcomes = []
    counter = TokenCounter(tokenizer_python, 'cl100k_base')
    try:
        actor_paths = [*(root/'rounds/R01').glob('**/actor_state.json'), *(root/'retained').glob('**/actor_state.json')]
        for path in sorted(actor_paths):
            retained = path.is_relative_to(root/'retained')
            state = read(path); side = 'parent' if retained or 'parent_runs' in path.parts else 'candidate'
            uid = state['identity']['task_id']; actor = state['identity']['actor']
            if 'record' in state:
                record = state['record']
                outcomes.append({'side': side, 'task_id': uid, 'metrics': record['metrics'],
                    'model_rounds': len(state['rounds']), 'tool_calls': state['calls'],
                    'termination': state['termination'], 'answer': record['answer']})
            for rd in state['rounds']:
                for attempt in rd['attempts']:
                    ident = f"{side}_{uid}_r{rd['number']:02}_a{attempt['number']:02}"
                    dest = out/'actor_inputs'/f'{ident}.json'
                    body = {'model': actor['model'], 'messages': attempt['messages'], 'tools': list(TOOL_SCHEMAS),
                        'temperature': actor['temperature'], actor['token_limit_field']: actor['max_completion_tokens'],
                        'reasoning_effort': actor['reasoning_effort'], 'thinking': {'type': 'enabled'}}
                    save(dest, body)  # Reconstructed from archived request plus frozen transport metadata; no headers/key.
                    response = attempt.get('response') or {}; choice = (response.get('choices') or [{}])[0]
                    rows.append({'id': ident, 'kind': 'actor', 'side': side, 'task_id': uid,
                        'origin': 'retained_previous_run' if retained else 'new_request',
                        'round': rd['number'], 'attempt': attempt['number'], 'status': attempt['status'],
                        'input_path': str(dest), 'source': str(path), 'finish_reason': choice.get('finish_reason'),
                        'max_tokens': actor['max_completion_tokens'], 'response_model': response.get('model'),
                        'thinking_message_count': sum('reasoning_content' in m for m in attempt['messages']),
                        **usage_fields(response)})
        for name in prompting.PROMPT_VERSIONS:
            folder = root/'rounds/R01'/name
            for path in sorted((folder/'attempts').glob('[0-9][0-9][0-9]')):
                if not (path/'messages.json').exists(): continue
                messages = read(path/'messages.json'); response = {}
                if (path/'http_response.txt').exists():
                    try: response = read(path/'http_response.txt')
                    except ValueError: pass
                choice = (response.get('choices') or [{}])[0]
                payload = json.loads(messages[1]['content']); decoded = iv.restore(payload)
                # No transport-only thought fields may reach the seven-module inputs.
                def has_reasoning(value):
                    if isinstance(value, dict):
                        return 'reasoning_content' in value or any(has_reasoning(v) for v in value.values())
                    return isinstance(value, list) and any(has_reasoning(v) for v in value)
                assert not has_reasoning(payload) and not has_reasoning(decoded)
                printable = []
                for i, message in enumerate(messages):
                    text = message['content']
                    if i == 1: text = json.dumps(payload, ensure_ascii=False, indent=2)
                    printable.append(f"## Message {i+1}: {message['role']}\n\n{text}\n")
                preview = out/'module_inputs'/f'{name}_{path.name}.md'; preview.parent.mkdir(exist_ok=True)
                preview.write_text('\n'.join(printable))
                error = read(path/'error.json') if (path/'error.json').exists() else None
                rows.append({'id': f'{name}_{path.name}', 'kind': 'module', 'module': name,
                    'attempt': int(path.name), 'input_path': str(path/'messages.json'), 'readable_input': str(preview),
                    'request_path': str(path/'request.json'), 'finish_reason': choice.get('finish_reason'),
                    'error': error, 'max_tokens': cfg['module_calls'][name]['max_tokens'],
                    'response_model': response.get('model'), 'message_roles': [m['role'] for m in messages],
                    'input_view': payload.get(iv.HEADER, {}).get('format', 'raw'),
                    'payload_fields': list(decoded), 'formal_run_order': [r['ref'] for r in decoded.get('runs', [])],
                    'pairs': decoded.get('pairs', decoded.get('context', {}).get('pairs', [])),
                    'payload_field_characters': {k: len(iv.exact(v)) for k,v in payload.items()},
                    'encoded_payload_reference_tokens': counter.count([{'content': iv.exact(payload)}]),
                    'decoded_payload_reference_tokens': counter.count([{'content': iv.exact(decoded)}]),
                    'actor_reasoning_excluded': True, **usage_fields(response)})
    finally:
        counter.close()
    groups = defaultdict(list)
    for row in rows: groups[row.get('module', 'actor_'+row.get('side', ''))].append(row)
    result = {'status': read(root/'pilot_summary.json') if (root/'pilot_summary.json').exists() else
        {'state': read(root/'state.json'), 'stop': read(root/'stop.json') if (root/'stop.json').exists() else None},
        'scope': read(root/'pilot_scope.json'), 'configuration': str(root/'config.json'),
        'token_note': 'Input/output/reasoning usage is actual provider usage. Output includes reasoning. Reference payload token counts use cl100k_base, exclude system/feedback/chat framing, and are not provider counts.',
        'tokenizer': counter.metadata, 'summary': {k: summarize(v) for k,v in groups.items()},
        'requests': rows, 'actor_outcomes': outcomes,
        'new_requests_summary': summarize([r for r in rows if r.get('origin') != 'retained_previous_run']),
        'retained_requests_summary': summarize([r for r in rows if r.get('origin') == 'retained_previous_run']),
        'budget_reuse': read(root/'budget_reuse.json') if (root/'budget_reuse.json').exists() else None,
        'unexecuted_modules': [n for n in prompting.PROMPT_VERSIONS if n not in groups]}
    save(out/'input_token_report.json', result)
    lines = ['# V26 R01 输入与用量', '', 'API 实际用量；输出包含思考 tokens。每行对应一次请求，重试单列。', '',
             'origin=retained_previous_run 表示复用旧记录，没有再次调用；new_request 为本目录的新请求。', '',
             '| 请求 | 来源 | 输入 tokens | 输出 tokens | 思考 tokens | 输出上限 | 结束原因 | 输入 |',
             '|---|---|---:|---:|---:|---:|---|---|']
    for row in rows:
        lines.append(f"| {row['id']} | {row.get('origin', 'new_request')} | {row['input_tokens']} | {row['output_tokens']} | {row['reasoning_tokens']} | {row['max_tokens']} | {row['finish_reason']} | [查看]({row.get('readable_input',row['input_path'])}) |")
    lines += ['', '未执行模块：'+', '.join(result['unexecuted_modules']), '',
              '完整统计和每题 EM/F1：[JSON]('+str(out/'input_token_report.json')+')']
    (out/'INPUTS.md').write_text('\n'.join(lines)+'\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('directory')
    parser.add_argument('--tokenizer-python'); args = parser.parse_args()
    result = report(args.directory, tokenizer_python=args.tokenizer_python)
    print(json.dumps({'summary': result['summary'], 'unexecuted_modules': result['unexecuted_modules']}, indent=2))

"""Bounded live prompt comparison; no environment steps or campaign mutations."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import re
import time

from dotenv import load_dotenv
from src.adapters.alfworld.run_task_upstream import project_action
from src.skill_evolution.v23.grouping import live_generator
from src.skill_evolution.v23_5.editor import parse_json_response, validate_editor

REPO = Path(__file__).resolve().parents[4]
ROOT = REPO / 'artifacts/methods/v23_5/action_format_probe_001'
ROUNDS = REPO / 'artifacts/methods/v23_5/alfworld_initial_skill_001/S1/rounds'
OLD_SKILL = '**Output format**: Always output `<think>...</think>` for reasoning, then `<action>...</action>` for the chosen action.'
NEW_FORMAT = ('Return exactly one XML-style element named `action`.\n'
              'Its text content must be one command copied verbatim from the current admissible action list.\n'
              'Do not include any text outside this element or any nested elements.')
NEW_SKILL = '**Output format**: ' + NEW_FORMAT
OLD_RUNTIME = ("You should first reason step-by-step about the current situation. This reasoning process MUST be enclosed within <think> </think> tags.\n"
               "Once you've finished your reasoning, you should choose an admissible action for current step and present it within <action> </action> tags.")


def read(path):
    return json.loads(path.read_text())


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare():
    if ROOT.exists():
        raise ValueError('Probe already exists; no overwrite or request-budget reset')
    cases, sources = [], {}
    def source(path):
        sources[str(path.relative_to(REPO))] = sha(path)
        return read(path)
    for task, step in [('train_0030', 49), ('train_0031', 8)]:
        path, = (ROUNDS / 'R04/parent_runs' / task / 'attempts/001').glob('*/trajectory.json')
        event = source(path)['steps'][step - 1]
        for repeat in (1, 2):
            for arm in ('original', 'skill_only', 'aligned'):
                messages = deepcopy(event['messages'])
                assert messages[1]['content'].count(OLD_SKILL) == 1
                assert messages[1]['content'].count(OLD_RUNTIME) == 1
                if arm != 'original':
                    messages[1]['content'] = messages[1]['content'].replace(OLD_SKILL, NEW_SKILL)
                if arm == 'aligned':
                    messages[1]['content'] = messages[1]['content'].replace(OLD_RUNTIME, NEW_FORMAT)
                    assert '<think>' not in str(messages) and '</think>' not in str(messages)
                cases.append({'id': f'actor_{task}_{step}_{repeat}_{arm}', 'kind': 'actor', 'arm': arm,
                              'messages': messages, 'admissible': event['admissible_commands']})
    for rd, arms in [('R01', ('original', 'skill_only', 'aligned')), ('R04', ('aligned',))]:
        directory = ROUNDS / rd / 'editor/attempts/001'
        base = source(directory / 'messages.json')
        payload = source(directory / 'input.json')
        assert len(base) == 2 and json.loads(base[1]['content']) == payload
        for arm in arms:
            messages, data = deepcopy(base), deepcopy(payload)
            assert data['parent'].count(OLD_SKILL) == 1
            assert messages[0]['content'].count(OLD_RUNTIME) == 2
            if arm != 'original':
                data['parent'] = data['parent'].replace(OLD_SKILL, NEW_SKILL)
                messages[1]['content'] = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
            if arm == 'aligned':
                messages[0]['content'] = messages[0]['content'].replace(OLD_RUNTIME, NEW_FORMAT)
            # Historical plans stay byte-equivalent as JSON values, including R04 u3.
            assert data['plan'] == payload['plan']
            if rd == 'R01' and arm == 'aligned':
                assert '<think>' not in str(messages) and '</think>' not in str(messages)
            cases.append({'id': f'editor_{rd}_{arm}', 'kind': 'editor', 'arm': arm,
                          'messages': messages, 'parent': data['parent'], 'round': rd})
    cfg = source(ROUNDS / 'R01/editor/attempts/001/request.json')
    save(ROOT / 'manifest.json', {'cases': cases, 'source_sha256': sources,
         'endpoint': cfg['endpoint'], 'parameters': {k: v for k, v in cfg['body'].items() if k != 'messages'},
         'max_requests': len(cases), 'retries': 0, 'workers': 2,
         'scope': 'Actor response replay without environment execution; Editor validator against copied Parent; no publication.'})
    print(json.dumps({'prepared_cases': len(cases), 'root': str(ROOT)}), flush=True)


def check_response(case, response, raw):
    content = response['content']
    reasoning = raw['choices'][0]['message'].get('reasoning_content') or ''
    row = {'id': case['id'], 'arm': case['arm'], 'kind': case['kind'],
           'finish_reason': response.get('finish_reason'), 'usage': response.get('usage'),
           'body_chars': len(content), 'reasoning_chars': len(reasoning),
           'body_think_markers': content.count('<think>') + content.count('</think>')}
    if row['finish_reason'] != 'stop':
        row.update(valid=False, error='incomplete_response')
        return row
    if case['kind'] == 'actor':
        action, fallback = project_action(content)
        match = re.fullmatch(r'\s*<action>([^<>\r\n]*)</action>\s*', content)
        row.update(action=action[:180], fallback=fallback,
                   projected_action_valid=action in case['admissible'],
                   exact_action_only=bool(match and match[1].strip() in case['admissible']))
        row['valid'] = row['exact_action_only']
    else:
        try:
            parsed = parse_json_response(content)
            row['json_valid'] = True
            status, candidate = validate_editor(parsed, case['parent'])
            row.update(valid=True, outcome=status, candidate_chars=len(candidate or ''),
                       candidate_think_markers=(candidate or '').count('<think>') + (candidate or '').count('</think>'))
        except (ValueError, TypeError, KeyError) as exc:
            row.update(valid=False, error_type=type(exc).__name__, error=str(exc)[:600])
    return row


def run():
    manifest = read(ROOT / 'manifest.json')
    for path, digest in manifest['source_sha256'].items():
        assert sha(REPO / path) == digest, f'Source changed: {path}'
    load_dotenv(REPO / '.env', override=False)
    base = os.environ['OPENAI_BASE_URL'].rstrip('/')
    assert base + '/chat/completions' == manifest['endpoint']
    params = manifest['parameters']
    generate = live_generator(base_url=base, key=os.environ['OPENAI_API_KEY'],
                              model=params['model'], max_tokens=params['max_tokens'], timeout=300)
    assert all(generate.call_config[k] == params[k] for k in params)
    def one(case):
        directory = ROOT / 'calls' / case['id']
        if directory.exists():
            # Never silently repeat an uncertain request.
            return read(directory / 'result.json') if (directory / 'result.json').exists() else {
                'id': case['id'], 'valid': False, 'error': 'existing_incomplete_call_not_retried'}
        directory.mkdir(parents=True)
        save(directory / 'messages.json', case['messages'])
        start = time.monotonic()
        print(json.dumps({'started': case['id']}), flush=True)
        try:
            response = generate(case['messages'], directory)
            save(directory / 'response.json', response)
            row = check_response(case, response, read(directory / 'http_response.txt'))
        except Exception as exc:
            row = {'id': case['id'], 'kind': case['kind'], 'arm': case['arm'],
                   'valid': False, 'error_type': type(exc).__name__}
        row['elapsed_seconds'] = round(time.monotonic() - start, 2)
        save(directory / 'result.json', row)
        print(json.dumps(row, ensure_ascii=False), flush=True)
        return row
    results = []
    with ThreadPoolExecutor(max_workers=manifest['workers']) as pool:
        for future in as_completed([pool.submit(one, case) for case in manifest['cases']]):
            results.append(future.result())
            save(ROOT / 'summary.json', sorted(results, key=lambda x: x['id']))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'run'])
    args = parser.parse_args()
    {'prepare': prepare, 'run': run}[args.action]()

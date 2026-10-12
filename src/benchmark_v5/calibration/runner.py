"""Frozen, model-neutral Dev calibration; no learning-system dependency."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import random
import threading
import time

from benchmark_v5.core import ROOT, load_scenario
from benchmark_v5.session import AgentSession, build
from benchmark_v5.evaluation import evaluate
from .transport import chat, TransportError

CONFIG = ROOT / 'experiments/benchmarks/v5/calibration/protocol.json'
FREEZE = ROOT / 'experiments/benchmarks/v5/calibration/freeze.json'


def read(path):
    return json.loads(path.read_text())


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    temp.replace(path)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat()


def scenario(task, condition):
    c = load_scenario(task)
    if condition == 'decision_variant':
        if task == 'S2': c['threshold'] = 20000
        elif task == 'G2': c['opened'] = False
        elif task == 'I1': c['flights']['A']['arrival'] = 800
        elif task == 'K2': c['initial_b_committed'] = False
    return c


def jobs(config):
    cells = [(task, cond, rep) for cond, n in config['conditions'].items()
             for rep in range(1, n + 1) for task in config['tasks']]
    random.Random(config['schedule_seed']).shuffle(cells)
    return [dict(id=f'{model}__{task}__{cond}__r{rep}', model=model, task=task, condition=cond, repetition=rep)
            for task, cond, rep in cells for model in config['models']]


def initial_messages(config, job, session):
    content = {'request': session.request}
    cond, task = job['condition'], job['task']
    if cond == 'brief_rules':
        content['published_policy_summary'] = config['brief_rules'][task]
    elif cond == 'full_documents':
        # Disposable environment, public read-only policy result, not a private answer.
        public = AgentSession(build(task, scenario(task, cond)))
        method = config['document_tools'][task]
        content['published_documents'] = {method: public.call(method)}
    return [{'role': 'system', 'content': config['system_prompt']},
            {'role': 'user', 'content': json.dumps(content, ensure_ascii=False)}]


def freeze():
    if FREEZE.exists():
        raise RuntimeError('PROTOCOL_ALREADY_FROZEN')
    config = read(CONFIG)
    old = read(ROOT / 'experiments/benchmarks/v5/prototype-engineering/results.json')['metadata']['source_sha256']
    changed = [p for p, h in old.items() if sha(ROOT / p) != h]
    if changed: raise RuntimeError(f'STEP5_CHANGED: {changed}')
    files = list(old) + ['experiments/benchmarks/v5/calibration/protocol.json', 'docs/benchmarks/v5/CALIBRATION.md']
    files += [str(p.relative_to(ROOT)) for p in sorted((ROOT / 'src/benchmark_v5/calibration').glob('*.py'))]
    files += [str(p.relative_to(ROOT)) for p in sorted((ROOT / 'tests/benchmarks/v5/calibration').glob('*.py'))]
    manifest = {'frozen_at_utc': now(), 'protocol_id': config['protocol_id'],
        'source_sha256': {p: sha(ROOT / p) for p in files},
        'jobs': [{**j, 'scenario_sha256': hashlib.sha256(json.dumps(scenario(j['task'], j['condition']), sort_keys=True).encode()).hexdigest()} for j in jobs(config)]}
    write(FREEZE, manifest)
    return manifest


def verify_freeze():
    manifest = read(FREEZE)
    changed = [p for p, h in manifest['source_sha256'].items() if not (ROOT / p).exists() or sha(ROOT / p) != h]
    if changed: raise RuntimeError(f'FROZEN_FILES_CHANGED: {changed}')
    return manifest


def run_episode(config, job, destination, transport=chat, sleeper=time.sleep):
    dest = destination / job['id']
    dest.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    env = build(job['task'], scenario(job['task'], job['condition']))
    session = AgentSession(env)
    messages = initial_messages(config, job, session)
    catalog = [{'type': 'function', 'function': t} for t in session.tools]
    trace = {'job': job, 'started_at_utc': now(), 'initial_messages': deepcopy(messages), 'tools': catalog, 'rounds': []}
    write(dest / 'trace.json', trace)
    totals = dict(prompt_tokens=0, completion_tokens=0, total_tokens=0, reasoning_tokens=0)
    calls = 0
    unknown_usage = 0
    tool_calls = 0
    valid = True
    stop = 'turn_budget'
    failure_kind = None
    limits = config['limits']
    try:
        for turn in range(limits['model_turns']):
            if totals['completion_tokens'] >= limits['completion_tokens']:
                stop = 'completion_budget'; break
            if totals['prompt_tokens'] >= limits['cumulative_prompt_tokens']:
                stop = 'prompt_budget'; break
            payload = {'model': job['model'], 'messages': deepcopy(messages), 'tools': catalog,
                       'temperature': config['temperature'], 'reasoning_effort': config['reasoning_effort'],
                       'max_tokens': min(limits['max_tokens_per_call'], limits['completion_tokens'] - totals['completion_tokens'])}
            rnd = {'turn': turn + 1, 'request': payload, 'attempts': []}
            trace['rounds'].append(rnd)
            for attempt in range(limits['transport_retries'] + 1):
                calls += 1
                attempted_at = now()
                try:
                    response, seconds = transport(ROOT, payload, timeout=limits['timeout_seconds'])
                    rnd['attempts'].append({'at_utc': attempted_at, 'seconds': seconds, 'response': response})
                    break
                except TransportError as exc:
                    unknown_usage += 1
                    rnd['attempts'].append({'at_utc': attempted_at, 'error': exc.kind, 'status': exc.status})
                    write(dest / 'trace.json', trace)
                    retryable = exc.kind in ('TimeoutError', 'URLError') or exc.status == 429 or (exc.status is not None and exc.status >= 500)
                    if not retryable or attempt == limits['transport_retries']: raise
                    sleeper(limits['retry_delay_seconds'])
            write(dest / 'trace.json', trace)
            usage = response.get('usage')
            if not isinstance(usage, dict) or any(type(usage.get(k)) is not int for k in ('prompt_tokens','completion_tokens','total_tokens')):
                raise TransportError('missing_usage')
            for key in ('prompt_tokens', 'completion_tokens', 'total_tokens'): totals[key] += usage[key]
            totals['reasoning_tokens'] += (usage.get('completion_tokens_details') or {}).get('reasoning_tokens', 0) or 0
            if response.get('model') != job['model']: raise TransportError('unexpected_response_model')
            choice = response['choices'][0]
            raw = choice.get('message')
            if not isinstance(raw, dict): raise TransportError('invalid_assistant_message')
            assistant = {'role': 'assistant', 'content': raw.get('content')}
            if raw.get('reasoning_content'): assistant['reasoning_content'] = raw['reasoning_content']
            tc = raw.get('tool_calls') or []
            if tc:
                if any(not isinstance(t, dict) or not t.get('id') or not isinstance(t.get('function'), dict)
                       or not isinstance(t['function'].get('name'), str) or not isinstance(t['function'].get('arguments'), str) for t in tc):
                    raise TransportError('malformed_native_tool_envelope')
                assistant['tool_calls'] = [{k: t[k] for k in ('id','type','function')} for t in tc]
            messages.append(assistant)
            if not tc:
                stop = 'model_text_stop'; break
            tool_results = []
            for t in tc:
                if env.state['closed'] or tool_calls >= limits['tool_calls']:
                    result = {'error': 'SESSION_CLOSED' if env.state['closed'] else 'CALL_BUDGET_EXHAUSTED'}
                else:
                    tool_calls += 1
                    fn = t['function']
                    try: args = json.loads(fn['arguments'])
                    except json.JSONDecodeError: args = None
                    # Core records invalid JSON as a failed tool call without state changes.
                    result = env.call(fn['name'], args)
                tool_results.append({'tool_call_id': t['id'], 'result': result})
                messages.append({'role': 'tool', 'tool_call_id': t['id'], 'content': json.dumps(result, ensure_ascii=False)})
            rnd['tool_results'] = tool_results
            write(dest / 'trace.json', trace)
            if env.state['closed']: stop = 'finish'; break
            if tool_calls >= limits['tool_calls']: stop = 'tool_budget'; break
    except TransportError as exc:
        valid, stop, failure_kind = False, 'infrastructure_invalid', exc.kind
    except Exception as exc:
        # Do not leak error strings from transport or provider; keep class for diagnosis.
        valid, stop, failure_kind = False, 'harness_invalid', type(exc).__name__
    env.end_budget()
    audit = env.audit()
    write(dest / 'audit.json', audit)
    grade = evaluate(audit) if valid else None
    result = {**job, 'valid': valid, 'stop': stop, 'failure_kind': failure_kind, 'score': grade,
              'usage': totals, 'api_attempts': calls, 'unknown_usage_attempts': unknown_usage,
              'model_turns': len(trace['rounds']), 'tool_calls': tool_calls,
              'wall_seconds': time.monotonic() - started, 'finished_at_utc': now()}
    write(dest / 'result.json', result)
    return result


def run(destination):
    manifest = verify_freeze()
    config = read(CONFIG)
    destination.mkdir(parents=True, exist_ok=True)
    freeze_copy = destination / 'freeze.json'
    if freeze_copy.exists() and read(freeze_copy) != manifest: raise RuntimeError('RUN_FREEZE_MISMATCH')
    write(freeze_copy, manifest)
    write(destination / 'protocol.json', config)
    semaphores = {m: threading.Semaphore(config['concurrency_per_model']) for m in config['models']}
    def worker(job):
        result_path = destination / job['id'] / 'result.json'
        if result_path.exists(): return read(result_path)
        if (destination / job['id']).exists():
            raise RuntimeError('INCOMPLETE_EPISODE_REQUIRES_EXPLICIT_AUDIT')
        with semaphores[job['model']]:
            verify_freeze()
            return run_episode(config, job, destination)
    with ThreadPoolExecutor(max_workers=config['workers']) as pool:
        futures = [pool.submit(worker, j) for j in jobs(config)]
        for f in as_completed(futures):
            r = f.result()
            print(json.dumps({k:r[k] for k in ('id','valid','stop','score','api_attempts','wall_seconds')}, ensure_ascii=False), flush=True)
    verify_freeze()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['freeze','run'])
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.command == 'freeze': print(json.dumps({'frozen_at_utc': freeze()['frozen_at_utc']}))
    else:
        if not args.output: parser.error('--output required')
        run(args.output)


if __name__ == '__main__': main()

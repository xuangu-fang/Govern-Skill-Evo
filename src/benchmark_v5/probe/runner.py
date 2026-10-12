"""Frozen 15-episode D1/D2 probe. Run-loop adapted from the existing calibrated runner."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
import json
from pathlib import Path
import random
import time
from benchmark_v5.core import ROOT
from benchmark_v5.session import AgentSession
from benchmark_v5.calibration.runner import read, write, sha, now
from benchmark_v5.calibration.transport import chat, TransportError
from .environment import build, CELLS
from .evaluation import evaluate

DEST=ROOT/'artifacts/benchmarks/v5/decision-probe-20261010-001'
CONFIG=ROOT/'experiments/benchmarks/v5/decision_probe/protocol.json'

def run_episode(config, job, destination, transport=chat, sleeper=time.sleep):
    dest = destination / job['id']
    dest.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    env = build(job['task'], job['condition'])
    session = AgentSession(env)
    messages = [{'role':'system','content':config['system_prompt']}, {'role':'user','content':json.dumps(session.request,ensure_ascii=False)}]
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


def freeze():
    if (DEST/'freeze.json').exists(): raise RuntimeError('ALREADY_FROZEN')
    config=read(CONFIG)
    cells=[dict(id=f'deepseek-v4-flash__{t}__{c}__r{r}',model='deepseek-v4-flash',task=t,condition=c,repetition=r)
           for t,c in CELLS for r in range(1,4)]
    random.Random(20261012).shuffle(cells)
    files=['src/benchmark_v5/core.py','src/benchmark_v5/session.py','src/benchmark_v5/calibration/runner.py','src/benchmark_v5/calibration/transport.py',
           str(CONFIG.relative_to(ROOT)), 'docs/benchmarks/v5/DECISION_PROBE.md']
    files += [str(p.relative_to(ROOT)) for folder in ('src/benchmark_v5/probe','tests/benchmarks/v5/probe') for p in sorted((ROOT/folder).glob('*.py'))]
    write(DEST/'protocol.json',config)
    write(DEST/'freeze.json',dict(frozen_at_utc=now(),jobs=cells,source_sha256={p:sha(ROOT/p) for p in files}))
    print('Frozen',len(cells),'episodes',flush=True)


def check():
    f=read(DEST/'freeze.json')
    for p,h in f['source_sha256'].items():
        if sha(ROOT/p)!=h: raise RuntimeError('FROZEN_SOURCE_CHANGED: '+p)
    return f


def run():
    f=check();config=read(CONFIG)
    def worker(j):
        check()
        existing=DEST/j['id']/'result.json'
        if existing.exists(): return read(existing)
        if existing.parent.exists(): raise RuntimeError('INCOMPLETE_EPISODE_REQUIRES_AUDIT')
        r=run_episode(config,j,DEST)
        print(json.dumps(dict(id=r['id'],valid=r['valid'],stop=r['stop'],score=r['score']),ensure_ascii=False),flush=True)
        return r
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures=[pool.submit(worker,j) for j in f['jobs']]
        for future in as_completed(futures): future.result()
    check()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['freeze','run']);args=p.parse_args()
    freeze() if args.action=='freeze' else run()

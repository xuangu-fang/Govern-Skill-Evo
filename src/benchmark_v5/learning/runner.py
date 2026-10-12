"""Frozen fixed-experience learning/evaluation. API-only model has no filesystem access."""
import argparse
from concurrent.futures import ThreadPoolExecutor,as_completed
from copy import deepcopy
import json
import time
from pathlib import Path
from benchmark_v5.core import ROOT,canonical,digest
from benchmark_v5.calibration.runner import read,write,sha,now
from benchmark_v5.calibration.transport import chat,TransportError
from . import protocol
from .cases import heldout_cases,world_for
from .environment import build
from .experience import training_package,compatible_counts
from .rules import full_rules
from .evaluation import evaluate

DEST=ROOT/'artifacts/benchmarks/v5/learning-20261010-001'
CONFIG=ROOT/'experiments/benchmarks/v5/learning/protocol.json'


def call_model(payload,trace_round,limits,transport=chat,sleeper=time.sleep):
    for attempt in range(limits['transport_retries']+1):
        try:
            response,seconds=transport(ROOT,payload,timeout=limits['timeout_seconds'])
            trace_round['attempts'].append(dict(at_utc=now(),seconds=seconds,response=response))
            return response
        except TransportError as exc:
            trace_round['attempts'].append(dict(at_utc=now(),error=exc.kind,status=exc.status))
            retryable=exc.kind in ('TimeoutError','URLError') or exc.status==429 or (exc.status is not None and exc.status>=500)
            if not retryable or attempt==limits['transport_retries']:raise
            sleeper(limits['retry_delay_seconds'])


def usage_and_message(response,payload):
    u=response.get('usage')
    if not isinstance(u,dict) or any(type(u.get(k)) is not int for k in ('prompt_tokens','completion_tokens','total_tokens')):
        raise TransportError('missing_usage')
    if response.get('model')!=protocol.MODEL:raise TransportError('unexpected_response_model')
    choice=response['choices'][0];raw=choice['message']
    assistant={'role':'assistant','content':raw.get('content')}
    if raw.get('reasoning_content'):assistant['reasoning_content']=raw['reasoning_content']
    tc=raw.get('tool_calls') or []
    if tc:
        if any(not isinstance(t,dict) or not t.get('id') or not isinstance(t.get('function'),dict)
               or not isinstance(t['function'].get('name'),str) or not isinstance(t['function'].get('arguments'),str) for t in tc):
            raise TransportError('malformed_native_tool_envelope')
        assistant['tool_calls']=[{k:t[k] for k in ('id','type','function')} for t in tc]
    deviations=[]
    if choice.get('finish_reason')=='length':deviations.append('length')
    if u['completion_tokens']>payload['max_tokens']:deviations.append('provider_over_request_budget')
    totals={k:u[k] for k in ('prompt_tokens','completion_tokens','total_tokens')}
    totals['reasoning_tokens']=(u.get('completion_tokens_details') or {}).get('reasoning_tokens',0) or 0
    return totals,assistant,deviations


def run_episode(config,job,destination,state,transport=chat,sleeper=time.sleep):
    dest=destination/job['id'];dest.mkdir(parents=True,exist_ok=False)
    started=time.monotonic()
    case=next(c for c in heldout_cases() if c['id']==job['case_id'])
    env=build(case,world_for(case['kind']))
    messages=protocol.initial_messages(env,state,job['condition'])
    catalog=[{'type':'function','function':t} for t in env.catalog()]
    trace=dict(job=job,started_at_utc=now(),state_sha256=state['sha256'],initial_messages=deepcopy(messages),tools=catalog,rounds=[])
    write(dest/'trace.json',trace)
    totals=dict(prompt_tokens=0,completion_tokens=0,total_tokens=0,reasoning_tokens=0)
    limits=config['limits'];tool_count=0;deviations=[];valid=True;failure=None;stop='turn_budget'
    try:
        for turn in range(limits['model_turns']):
            if totals['completion_tokens']>=limits['completion_tokens']:stop='completion_budget';break
            if totals['prompt_tokens']>=limits['cumulative_prompt_tokens']:stop='prompt_budget';break
            payload=dict(model=protocol.MODEL,messages=deepcopy(messages),tools=catalog,
                temperature=config['temperature'],reasoning_effort=config['reasoning_effort'],
                max_tokens=min(limits['max_tokens_per_call'],limits['completion_tokens']-totals['completion_tokens']))
            rnd=dict(turn=turn+1,request=payload,attempts=[]);trace['rounds'].append(rnd)
            response=call_model(payload,rnd,limits,transport,sleeper)
            write(dest/'trace.json',trace)
            usage,assistant,dev=usage_and_message(response,payload)
            for k,v in usage.items():totals[k]+=v
            deviations+=dev;messages.append(assistant)
            tc=assistant.get('tool_calls',[])
            if not tc:stop='model_text_stop';break
            rnd['tool_results']=[]
            for t in tc:
                if env.state['closed'] or tool_count>=limits['tool_calls']:
                    result={'error':'SESSION_CLOSED' if env.state['closed'] else 'CALL_BUDGET_EXHAUSTED'}
                else:
                    tool_count+=1
                    try:args=json.loads(t['function']['arguments'])
                    except json.JSONDecodeError:args=None
                    result=env.call(t['function']['name'],args)
                rnd['tool_results'].append({'tool_call_id':t['id'],'result':result})
                messages.append({'role':'tool','tool_call_id':t['id'],'content':canonical(result)})
            write(dest/'trace.json',trace)
            if env.state['closed']:stop='finish';break
            if tool_count>=limits['tool_calls']:stop='tool_budget';break
    except TransportError as exc:valid=False;stop='infrastructure_invalid';failure=exc.kind
    except Exception as exc:valid=False;stop='harness_invalid';failure=type(exc).__name__
    if totals['completion_tokens']>limits['completion_tokens']:deviations.append('cumulative_completion_over_budget')
    if totals['prompt_tokens']>limits['cumulative_prompt_tokens']:deviations.append('cumulative_prompt_over_budget')
    env.end_budget();audit=env.audit()
    write(dest/'trace.json',trace);write(dest/'audit.json',audit)
    attempts=[a for r in trace['rounds'] for a in r['attempts']]
    result={**job,'valid':valid,'budget_clean':not deviations,'deviations':deviations,'stop':stop,'failure_kind':failure,
        'score':evaluate(audit) if valid else None,'usage':totals,'api_attempts':len(attempts),
        'unknown_usage_attempts':sum('error' in a for a in attempts),'tool_calls':tool_count,
        'wall_seconds':time.monotonic()-started,'state_sha256':state['sha256'],'finished_at_utc':now()}
    write(dest/'result.json',result)
    return result


def freeze():
    if (DEST/'freeze.json').exists():raise RuntimeError('ALREADY_FROZEN')
    config=protocol.config();write(CONFIG,config);write(DEST/'protocol.json',config)
    for kind in ('LS1','LG1'):
        obs,audits=training_package(kind)
        write(DEST/f'train/{kind}.json',obs);write(DEST/f'private/train_audits_{kind}.json',audits)
        counts,candidates=compatible_counts(kind,obs)
        write(DEST/f'private/identifiability_{kind}.json',dict(counts=counts,remaining=candidates))
        if len(candidates)!=1:raise RuntimeError('NON_IDENTIFIABLE')
    write(DEST/'private/holdout_cases.json',heldout_cases())
    files=['src/benchmark_v5/core.py','src/benchmark_v5/calibration/runner.py','src/benchmark_v5/calibration/transport.py',
           str(CONFIG.relative_to(ROOT)),'docs/benchmarks/v5/LEARNING.md',
           'docs/benchmarks/v5/LEARNING_SPEC.md']
    for folder in ('src/benchmark_v5/learning','tests/benchmarks/v5/learning'):
        files += [str(p.relative_to(ROOT)) for p in sorted((ROOT/folder).glob('*.py'))]
    files += [str(p.relative_to(ROOT)) for p in (DEST/'train').glob('*.json')]
    files += [str(DEST.relative_to(ROOT))+'/private/holdout_cases.json']
    write(DEST/'freeze.json',dict(frozen_at_utc=now(),jobs=protocol.jobs(),source_sha256={p:sha(ROOT/p) for p in files}))
    print('Frozen',len(protocol.jobs()),'execution episodes + 2 learning calls',flush=True)


def check():
    f=read(DEST/'freeze.json')
    for p,h in f['source_sha256'].items():
        if sha(ROOT/p)!=h:raise RuntimeError('FROZEN_SOURCE_CHANGED: '+p)
    return f


def prepare_states(transport=chat):
    check();cfg=read(CONFIG)
    if (DEST/'states_frozen.json').exists():
        verify_states();return
    for kind in ('LS1','LG1'):
        obs=read(DEST/f'train/{kind}.json')
        for cond,evidence,content in [('zero',[],''),('raw',obs,canonical(obs)),
             ('prefix',obs[:cfg['prefix'][kind]],canonical(obs[:cfg['prefix'][kind]])),('oracle',[],full_rules(kind))]:
            path=DEST/f'states/{kind}__{cond}.json'
            state=protocol.make_state(kind,cond,evidence,content)
            if path.exists() and read(path)!=state:raise RuntimeError('EXISTING_STATE_MISMATCH')
            write(path,state)
        statepath=DEST/f'states/{kind}__processed.json'
        if statepath.exists():continue
        tracepath=DEST/f'learning/{kind}.json'
        if tracepath.exists():raise RuntimeError('LEARNING_ATTEMPT_EXISTS_REQUIRES_AUDIT')
        payload=dict(model=protocol.MODEL,messages=protocol.learning_input(kind,obs),temperature=cfg['temperature'],
                     reasoning_effort=cfg['reasoning_effort'],max_tokens=cfg['limits']['max_tokens_per_call'])
        record=dict(request=payload,attempts=[],started_at_utc=now())
        write(tracepath,record)
        try:
            response=call_model(payload,record,cfg['limits'],transport)
            usage,message,deviations=usage_and_message(response,payload)
            record.update(usage=usage,deviations=deviations,finished_at_utc=now())
            write(tracepath,record)
            if deviations or not message.get('content'):raise RuntimeError('INVALID_LEARNING_OUTPUT')
            state=protocol.make_state(kind,'processed',obs,message['content'])
            write(statepath,state)
        finally:write(tracepath,record)
    paths=sorted((DEST/'states').glob('*.json'))
    write(DEST/'states_frozen.json',dict(frozen_at_utc=now(),source_sha256={str(p.relative_to(ROOT)):sha(p) for p in paths}))
    verify_states()


def verify_states():
    f=read(DEST/'states_frozen.json')
    if len(f['source_sha256'])!=10:raise RuntimeError('INCOMPLETE_STATES')
    for p,h in f['source_sha256'].items():
        if sha(ROOT/p)!=h:raise RuntimeError('LEARNING_STATE_CHANGED')


def run():
    f=check();verify_states();cfg=read(CONFIG)
    def worker(job):
        check();verify_states()
        dest=DEST/job['id']
        if (dest/'result.json').exists():return read(dest/'result.json')
        if dest.exists():raise RuntimeError('INCOMPLETE_EPISODE_REQUIRES_AUDIT')
        state=read(DEST/f'states/{job["kind"]}__{job["condition"]}.json')
        r=run_episode(cfg,job,DEST,state)
        print(canonical({k:r[k] for k in ('id','valid','stop','score')}),flush=True)
        return r
    with ThreadPoolExecutor(max_workers=cfg['workers']) as pool:
        futures=[pool.submit(worker,j) for j in f['jobs']]
        for future in as_completed(futures):future.result()
    check();verify_states()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['freeze','prepare','run']);a=p.parse_args()
    {'freeze':freeze,'prepare':prepare_states,'run':run}[a.action]()

"""Continue independent arms after a failed learner; never fabricate an empty learned state."""
import argparse
from concurrent.futures import ThreadPoolExecutor,as_completed
from copy import deepcopy
from benchmark_v5.core import ROOT,canonical
from benchmark_v5.calibration.runner import read,write,sha,now
from . import runner,protocol,supplement
from .experience import training_package
from .rules import full_rules

DEST=supplement.DESTINATION


def classify_learning(record):
    if 'usage' not in record:return 'learning_transport_or_measurement_invalid'
    if record.get('deviations'):return 'learning_budget_invalid'
    attempts=[a for a in record['attempts'] if 'response' in a]
    if not attempts or not attempts[-1]['response']['choices'][0]['message'].get('content'):
        return 'learning_no_state'
    return None


def freeze_extension():
    supplement.configure();runner.check()
    path=DEST/'execution_extension_freeze.json'
    if path.exists():raise RuntimeError('EXTENSION_ALREADY_FROZEN')
    files=['src/benchmark_v5/learning/recover.py','tests/benchmarks/v5/learning/test_recover.py',
           'docs/benchmarks/v5/LEARNING.md']
    write(path,dict(frozen_at_utc=now(),source_sha256={p:sha(ROOT/p) for p in files},
        reason='Independent conditions continue after an invalid learner output; budgets/data/prompts unchanged'))


def check_extension():
    supplement.configure();runner.check()
    for p,h in read(DEST/'execution_extension_freeze.json')['source_sha256'].items():
        if sha(ROOT/p)!=h:raise RuntimeError('EXTENSION_CHANGED')


def prepare():
    check_extension();cfg=read(supplement.CONFIGURATION)
    if (DEST/'available_states_frozen.json').exists():check_states();return
    blocked={}
    for kind in ('LS1','LG1'):
        obs=read(DEST/f'train/{kind}.json')
        for cond,evidence,content in [('zero',[],''),('raw',obs,canonical(obs)),
             ('prefix',obs[:cfg['prefix'][kind]],canonical(obs[:cfg['prefix'][kind]])),('oracle',[],full_rules(kind))]:
            state=protocol.make_state(kind,cond,evidence,content);path=DEST/f'states/{kind}__{cond}.json'
            if path.exists():assert read(path)==state
            else:write(path,state)
        tracepath=DEST/f'learning/{kind}.json'
        if tracepath.exists():
            record=read(tracepath)
            if not record.get('attempts'):raise RuntimeError('INCOMPLETE_LEARNING_NEEDS_AUDIT')
        else:
            payload=dict(model=protocol.MODEL,messages=protocol.learning_input(kind,obs),temperature=cfg['temperature'],
                reasoning_effort=cfg['reasoning_effort'],max_tokens=cfg['limits']['max_tokens_per_call'])
            record=dict(request=payload,attempts=[],started_at_utc=now())
            write(tracepath,record)
            try:
                response=runner.call_model(payload,record,cfg['limits'])
                usage,message,deviations=runner.usage_and_message(response,payload)
                record.update(usage=usage,deviations=deviations,finished_at_utc=now())
            except runner.TransportError as e:
                record.update(error=e.kind,finished_at_utc=now())
            finally:write(tracepath,record)
        failure=classify_learning(record)
        path=DEST/f'states/{kind}__processed.json'
        if failure:
            if path.exists():raise RuntimeError('INVALID_LEARNER_HAS_STATE')
            blocked[kind+'__processed']=dict(reason=failure,source_trace_sha256=sha(tracepath))
        else:
            content=[a['response'] for a in record['attempts'] if 'response' in a][-1]['choices'][0]['message']['content']
            state=protocol.make_state(kind,'processed',obs,content)
            if path.exists():assert read(path)==state
            else:write(path,state)
    write(DEST/'available_states_frozen.json',dict(frozen_at_utc=now(),blocked=blocked,
        source_sha256={str(p.relative_to(ROOT)):sha(p) for p in sorted((DEST/'states').glob('*.json'))}))
    check_states();print(canonical({'blocked':blocked,'available_states':10-len(blocked)}),flush=True)


def check_states():
    f=read(DEST/'available_states_frozen.json')
    assert len(f['source_sha256'])+len(f['blocked'])==10
    for p,h in f['source_sha256'].items():
        if sha(ROOT/p)!=h:raise RuntimeError('STATE_CHANGED')
    for key,value in f['blocked'].items():
        kind=key.split('__')[0]
        if sha(DEST/f'learning/{kind}.json')!=value['source_trace_sha256']:raise RuntimeError('LEARNING_FAILURE_CHANGED')
    return f


def blocked_result(job,reason):
    return {**job,'executed':False,'valid':False,'budget_clean':False,'deviations':[],
        'stop':'upstream_learning_invalid','failure_kind':reason,'score':None,
        'usage':dict(prompt_tokens=0,completion_tokens=0,total_tokens=0,reasoning_tokens=0),
        'api_attempts':0,'unknown_usage_attempts':0,'tool_calls':0,'wall_seconds':0,'state_sha256':None,
        'finished_at_utc':now()}


def run():
    check_extension();states=check_states();cfg=read(supplement.CONFIGURATION);f=runner.check()
    def worker(job):
        check_extension();check_states();d=DEST/job['id']
        if (d/'result.json').exists():return read(d/'result.json')
        if d.exists():raise RuntimeError('INCOMPLETE_EPISODE_REQUIRES_AUDIT')
        key=job['kind']+'__'+job['condition']
        if key in states['blocked']:
            result=blocked_result(job,states['blocked'][key]['reason']);write(d/'result.json',result)
        else:
            state=read(DEST/f'states/{key}.json')
            result=runner.run_episode(cfg,job,DEST,state)
        print(canonical({k:result[k] for k in ('id','valid','stop','score')}),flush=True)
        return result
    with ThreadPoolExecutor(max_workers=cfg['workers']) as pool:
        for future in as_completed([pool.submit(worker,j) for j in f['jobs']]):future.result()
    check_extension();check_states()


def validate():
    check_extension();states=check_states()
    # configure precedes this import, so original replay logic uses the supplement directory.
    from .validate import replay_episode
    f=runner.check();views={};blocked=[]
    for j in f['jobs']:
        r=read(DEST/j['id']/'result.json')
        if r.get('executed') is False:
            assert j['kind']+'__'+j['condition'] in states['blocked']
            assert r['api_attempts']==0 and r['score'] is None and not (DEST/j['id']/'audit.json').exists()
            blocked.append(j['id'])
        else:views[j['id']]=replay_episode(j)
    protected=read(DEST/'protected_before.json')
    changed=[p for p,h in protected.items() if not (ROOT/p).exists() or sha(ROOT/p)!=h]
    assert not changed,changed
    write(DEST/'public_views.json',views)
    record=dict(scheduled=len(f['jobs']),replayed_and_rescored=len(views),public_context_reconstructed=len(views),
        upstream_not_executed=blocked,frozen_learning_states=len(states['source_sha256']),protected_files_unchanged=len(protected))
    write(DEST/'validation.json',record);print(canonical(record))


def analyze():
    check_extension();check_states()
    from .analyze import analyze as base_analysis
    # Both actual learners have measurable responses in the current run; the base summary
    # keeps their cost even when a learner was truncated, and separates missing executions.
    summary=base_analysis()
    results=[read(DEST/j['id']/'result.json') for j in runner.check()['jobs']]
    summary.update(scheduled=len(results),executed=sum(r.get('executed',True) for r in results),
        upstream_not_executed=[r['id'] for r in results if r.get('executed') is False],
        learning_failures=read(DEST/'available_states_frozen.json')['blocked'])
    write(DEST/'analysis.json',summary)
    print(canonical({'scheduled':summary['scheduled'],'executed':summary['executed'],'learning_failures':summary['learning_failures']}))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['freeze','prepare','run','validate','analyze']);a=p.parse_args()
    {'freeze':freeze_extension,'prepare':prepare,'run':run,'validate':validate,'analyze':analyze}[a.action]()

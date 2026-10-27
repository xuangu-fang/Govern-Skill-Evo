"""Offline accounting including every technical attempt and first completed outcomes."""
from collections import Counter
import subprocess
from .run import HERE, ROOT, previous, read, save, verify, COMPLETE
from src.adapters.alfworld.verify_skill_run import verify_record
from src.skill_evolution.v23.replay import verify_pair

from experiments.methods.v23_3.archive_io import archive_glob, resolve

def main():
    verify();result=read(HERE/('final_results.json' if resolve(HERE / 'final_results.json').exists() else 'results.json'))
    totals={};all_records={};rows=[];pairs=[]
    scopes=[('original',previous.OLD),('prior_restart',previous.HERE)]+[(f'round_{i}',HERE/f'attempt_{i}') for i in range(1,4)]
    for scope,base in scopes:
        t=Counter()
        for path in sorted(archive_glob(base / 'episodes', '*/*/trajectory.json')):
            r=read(path);a=verify_record(r);assert a['trace_valid'],(path,a)
            t.update(a['reported_usage']);t['episodes']+=1;t['http']+=a['transport_attempts_recorded']
            t['decisions']+=a['requests_recorded'];t['executed_steps']+=a['steps_executed'];t['complete']+=a['episode_complete']
            t['unknown_usage_attempts']+=a['transport_attempts_with_unknown_usage']
            for s in r['steps']:
                u=s.get('model_response',{}).get('usage') or {}
                t['reasoning_tokens']+=(u.get('completion_tokens_details') or {}).get('reasoning_tokens',0)
                t['http_429']+=sum(x.get('http_status')==429 for x in s.get('transport_attempts',[]))
            key=(path.parent.parent.name,path.parent.name)
            all_records.setdefault(key,[]).append((path,r,a))
        totals[scope]=dict(t)
    selected={}
    for condition in ['Parent','A','B']:
        for ref in ['P3','P6','P7','P10']:
            candidates=all_records.get((condition,ref),[])
            if not candidates:rows.append({'condition':condition,'ref':ref,'status':'not_started'});continue
            completed=[x for x in candidates if x[1]['status'] in COMPLETE]
            path,r,a=completed[0] if completed else candidates[-1]
            selected[(condition,ref)]=r;steps=[s for s in r['steps'] if s['phase']=='executed']
            rows.append({'condition':condition,'ref':ref,'source':str(path),'attempts':len(candidates),**a,
                'actions':[{'step':s['step'],'action':s['action'],'observation':s['observation']} for s in steps],
                'invalid_steps':[s['step'] for s in steps if not s['action_in_admissible_commands']],
                'nothing_happens_steps':[s['step'] for s in steps if s['observation'].strip()=='Nothing happens.']})
    for ref in ['P3','P6','P7','P10']:
        for arm in ['A','B']:
            try:
                p,q=selected[('Parent',ref)],selected[(arm,ref)];verify_pair(p,q)
                assert p['request_policy']==q['request_policy']
                pairs.append({'ref':ref,'arm':arm,'conditions_match':True,'both_complete':p['status'] in COMPLETE and q['status'] in COMPLETE})
            except Exception as e:pairs.append({'ref':ref,'arm':arm,'conditions_match':False,'error':str(e)})
    ab_pairs=[]
    for ref in ['P3','P6','P7','P10']:
        a,b=selected[('A',ref)],selected[('B',ref)]
        verify_pair(a,b);assert a['request_policy']==b['request_policy']
        ab_pairs.append({'ref':ref,'conditions_match':True,'both_complete':a['status'] in COMPLETE and b['status'] in COMPLETE})
    new=Counter();combined=Counter()
    for scope,cost in totals.items():
        combined.update(cost)
        if scope.startswith('round_'):new.update(cost)
    editor={}
    for arm in ['A','B']:
        u=read(previous.OLD/f'editors/{arm}/response.json')['usage'];editor[arm]=u
        combined.update({k:v for k,v in u.items() if k in {'prompt_tokens','completion_tokens','total_tokens'} and isinstance(v,int)})
        combined['reasoning_tokens']+=(u.get('completion_tokens_details') or {}).get('reasoning_tokens',0)
    combined['http']+=2;combined['editor_calls']=2
    assert new['http']<=450 and combined['decisions']<=540
    save(HERE/'analysis.json',{'execution':result,'rows':rows,'pairing':pairs,'ab_pairing':ab_pairs,'actor_costs':totals,'new_actor_cost':dict(new),'cumulative_including_editors':dict(combined),'editor_usage':editor})
    baseline=read(HERE/'baseline.json');changed=[]
    for name,stat in baseline['files'].items():
        from pathlib import Path
        p=Path(name)
        if not resolve(p).exists() or [resolve(p).stat().st_size,resolve(p).stat().st_mtime_ns]!=stat:changed.append(name)
    same_diff=baseline['git_diff']==subprocess.check_output(['git','diff'],cwd=ROOT,text=True)
    save(HERE/'protection.json',{'checked_files':len(baseline['files']),'changed_existing_files':changed,'tracked_diff_unchanged':same_diff,'freezes_verified':True})
    assert not changed and same_diff
    for r in rows:print(r['condition'],r['ref'],r['status'],r.get('steps_executed'),r.get('native_success'))
    print('New',dict(new));print('Cumulative',dict(combined))

if __name__=='__main__':main()

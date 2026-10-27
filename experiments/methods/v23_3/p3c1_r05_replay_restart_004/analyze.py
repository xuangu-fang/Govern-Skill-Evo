"""Audit final twelve selected trajectories and preserve all technical-attempt costs."""
from collections import Counter
from pathlib import Path
import subprocess
from .run import HERE,ROOT,prior,read,save,verify,COMPLETE
from src.adapters.alfworld.verify_skill_run import verify_record
from src.skill_evolution.v23.replay import verify_pair

from experiments.methods.v23_3.archive_io import resolve

def main():
    verify();execution=read(HERE/('final_results.json' if resolve(HERE / 'final_results.json').exists() else 'results.json'));old=read(prior.HERE/'analysis.json')
    new=Counter();records=[];attempts=[]
    for row in execution['results']:
        p=Path(row['trajectory']);r=read(p);a=verify_record(r);assert a['trace_valid']
        new.update(a['reported_usage']);new['episodes']+=1;new['http']+=a['transport_attempts_recorded']
        new['decisions']+=a['requests_recorded'];new['executed_steps']+=a['steps_executed']
        new['complete']+=a['episode_complete'];new['unknown_usage_attempts']+=a['transport_attempts_with_unknown_usage']
        for s in r['steps']:
            u=s.get('model_response',{}).get('usage') or {}
            new['reasoning_tokens']+=(u.get('completion_tokens_details') or {}).get('reasoning_tokens',0)
            new['http_429']+=sum(t.get('http_status')==429 for t in s.get('transport_attempts',[]))
        records.append((p,r,a));attempts.append({'source':str(p),**a})
    completed=[x for x in records if x[1]['status'] in COMPLETE]
    p,r,a=completed[0] if completed else records[-1]
    steps=[s for s in r['steps'] if s['phase']=='executed']
    replacement={'condition':'Parent','ref':'P7','source':str(p),**a,
        'actions':[{'step':s['step'],'action':s['action'],'observation':s['observation']} for s in steps],
        'invalid_steps':[s['step'] for s in steps if not s['action_in_admissible_commands']],
        'nothing_happens_steps':[s['step'] for s in steps if s['observation'].strip()=='Nothing happens.']}
    rows=[replacement if (x['condition'],x['ref'])==('Parent','P7') else x for x in old['rows']]
    selected={}
    for x in rows:
        saved=read(x['source']);assert verify_record(saved)['trace_valid'];selected[(x['condition'],x['ref'])]=saved
    pairs=[]
    for ref in ['P3','P6','P7','P10']:
        for arm in ['A','B']:
            p,q=selected[('Parent',ref)],selected[(arm,ref)];verify_pair(p,q);assert p['request_policy']==q['request_policy']
            pairs.append({'ref':ref,'arm':arm,'conditions_match':True,'both_complete':p['status'] in COMPLETE and q['status'] in COMPLETE})
    total=Counter(old['cumulative_including_editors']);total.update(new)
    assert total['decisions']<=600
    save(HERE/'analysis.json',{'execution':execution,'attempts':attempts,'rows':rows,'pairing':pairs,
        'all_twelve_complete':all(x['episode_complete'] for x in rows),'new_actor_cost':dict(new),'cumulative_including_editors':dict(total)})
    before=read(HERE/'baseline.json');changed=[]
    for name,st in before['files'].items():
        p=Path(name)
        if not resolve(p).exists() or [resolve(p).stat().st_size,resolve(p).stat().st_mtime_ns]!=st:changed.append(name)
    same=before['git_diff']==subprocess.check_output(['git','diff'],cwd=ROOT,text=True)
    save(HERE/'protection.json',{'checked_files':len(before['files']),'changed_existing_files':changed,'tracked_diff_unchanged':same,'freezes_verified':True})
    assert not changed and same
    for x in rows:print(x['condition'],x['ref'],x['status'],x['steps_executed'],x['native_success'])
    print('New',dict(new));print('Cumulative',dict(total))

if __name__=='__main__':main()

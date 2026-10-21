"""Combine fixed old successes and authorized new attempts without output selection."""
from collections import Counter
from pathlib import Path
from .run import HERE,OLD,JOBS,read,save
from src.adapters.alfworld.verify_skill_run import verify_record
from src.skill_evolution.v23.replay import verify_pair

def main():
    records={};rows=[];totals={};pairing=[]
    for scope,base in [('original',OLD),('restart',HERE)]:
        t=Counter()
        for path in (base/'episodes').glob('*/*/trajectory.json'):
            r=read(path);a=verify_record(r);t.update(a['reported_usage'])
            t['episodes']+=1;t['decisions']+=a['requests_recorded'];t['http']+=a['transport_attempts_recorded'];t['executed_steps']+=a['steps_executed']
            t['complete']+=a['episode_complete'];t['unknown_usage_attempts']+=a['transport_attempts_with_unknown_usage']
            for s in r['steps']:
                usage=s.get('model_response',{}).get('usage') or {}
                t['reasoning_tokens']+=(usage.get('completion_tokens_details') or {}).get('reasoning_tokens',0)
        totals[scope]=dict(t)
    for condition in ['Parent','A','B']:
        for ref in ['P3','P6','P7','P10']:
            base=HERE if (condition,ref) in JOBS else OLD
            path=base/f'episodes/{condition}/{ref}/trajectory.json'
            if not path.exists():rows.append({'condition':condition,'ref':ref,'status':'not_started'});continue
            r=read(path);a=verify_record(r);records[(condition,ref)]=r;steps=[s for s in r['steps'] if s['phase']=='executed']
            visits=list(dict.fromkeys(s['action'][6:] for s in steps if s['action'].startswith('go to ')))
            rows.append({'condition':condition,'ref':ref,'source':str(path),**a,
                'locations':visits,'invalid':[s['step'] for s in steps if not s['action_in_admissible_commands']],
                'nothing_happens':[s['step'] for s in steps if s['observation'].strip()=='Nothing happens.'],
                'key_actions':[{'step':s['step'],'action':s['action'],'observation':s['observation']} for s in steps if s['action'].split(' ')[0] in {'take','move','clean','cool','heat','use'}],
                'final_observation':steps[-1]['observation'] if steps else r.get('initial_observation')})
    for ref in ['P3','P6','P7','P10']:
        for arm in ['A','B']:
            try:
                p,q=records[('Parent',ref)],records[(arm,ref)];verify_pair(p,q)
                assert p['request_policy']==q['request_policy']
                pairing.append({'ref':ref,'arm':arm,'conditions_match':True,
                    'both_complete':all(r['status'] in {'success','step_limit','environment_ended'} for r in [p,q])})
            except Exception as exc:pairing.append({'ref':ref,'arm':arm,'conditions_match':False,'error':str(exc)})
    save(HERE/'analysis.json',{'rows':rows,'pairing':pairing,'costs':totals})
    for r in rows:print(r['condition'],r['ref'],r['status'],r.get('steps_executed'),r.get('native_success'))
    print('Costs',totals)

if __name__=='__main__':main()

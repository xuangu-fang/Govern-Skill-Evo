"""Offline trace summaries; descriptive counts are not semantic quality scores."""
from collections import Counter
from .run import HERE, read, save
from src.adapters.alfworld.verify_skill_run import verify_record
from src.skill_evolution.v23.replay import verify_pair

def main():
    records={};rows=[];total=Counter();pairs=[]
    for condition in ['Parent','A','B']:
        for task in read(HERE/'tasks.json'):
            ref=task['ref'];path=HERE/f'episodes/{condition}/{ref}/trajectory.json'
            if not path.exists():
                rows.append({'condition':condition,'ref':ref,'status':'not_started'});continue
            r=read(path);records[(condition,ref)]=r;audit=verify_record(r)
            steps=[s for s in r['steps'] if s['phase']=='executed'];visits=[];repeat=[];seen=set()
            for s in steps:
                if s['action'].startswith('go to '):
                    location=s['action'][6:];visits.append(location)
                    key=(location,s['observation'])
                    if key in seen:repeat.append(s['step'])
                    seen.add(key)
            row={'condition':condition,'ref':ref,'task_id':r['task']['id'],**audit,
                 'locations':list(dict.fromkeys(visits)),
                 'navigation_count':len(visits),'same_location_observation_revisits':repeat,
                 'invalid_steps':[s['step'] for s in steps if not s['action_in_admissible_commands']],
                 'nothing_happens_steps':[s['step'] for s in steps if s['observation'].strip()=='Nothing happens.'],
                 'key_actions':[{'step':s['step'],'action':s['action'],'observation':s['observation']} for s in steps
                                if s['action'].split(' ')[0] in {'take','move','clean','heat','cool','use'}],
                 'final_observation':steps[-1]['observation'] if steps else r.get('initial_observation')}
            rows.append(row);total.update(audit['reported_usage'])
            total['actor_http_requests']+=audit['transport_attempts_recorded']
            total['actor_decisions']+=audit['requests_recorded'];total['episodes_started']+=1
    for task in read(HERE/'tasks.json'):
        for arm in ['A','B']:
            ref=task['ref'];p=records.get(('Parent',ref));q=records.get((arm,ref))
            if p is None or q is None: pairs.append({'ref':ref,'arm':arm,'paired':False,'reason':'not_started'});continue
            try:
                verify_pair(p,q)
                assert p['implementation']['files']==q['implementation']['files']
                assert p['request_policy']==q['request_policy']
                pairs.append({'ref':ref,'arm':arm,'paired':True,'complete':p['status'] in {'success','step_limit','environment_ended'} and q['status'] in {'success','step_limit','environment_ended'}})
            except Exception as exc:pairs.append({'ref':ref,'arm':arm,'paired':False,'reason':str(exc)})
    editors={}
    for arm in ['A','B']:
        response=read(HERE/f'editors/{arm}/response.json');editors[arm]=response['usage']
    save(HERE/'analysis.json',{'rows':rows,'pairing':pairs,'actor_totals':dict(total),'editor_usage':editors})
    for r in rows:
        print(r['condition'],r['ref'],r['status'],r.get('steps_executed'),r.get('native_success'),
              'visits',len(r.get('locations',[])),'repeat',len(r.get('same_location_observation_revisits',[])),
              'invalid',r.get('invalid_steps'),flush=True)
    print('Actor totals',dict(total))

if __name__=='__main__':main()

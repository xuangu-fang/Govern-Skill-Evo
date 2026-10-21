"""Offline accounting and behavioral evidence extraction; no model calls."""
from collections import Counter
from datetime import datetime
import json
from pathlib import Path
import re
from .run import HERE,read,save,verify,COMPLETE
from src.adapters.alfworld.verify_skill_run import verify_record
from src.skill_evolution.v23.replay import verify_pair

def main():
 verify();rows=[];records={};md=['# Batch-1 实际动作与反馈','', '仅真实已执行动作；技术尝试见各 call journal。所有任务固定，缺失条件保留。','']
 for task in read(HERE/'tasks.json'):
  ref=task['ref']
  for arm in ['Parent','A','B']:
   p=HERE/f'episodes/{arm}/{ref}/trajectory.json'
   if not p.exists():rows.append({'ref':ref,'arm':arm,'status':'not_started'});continue
   r=read(p);audit=verify_record(r);records[(ref,arm)]=r;steps=[s for s in r['steps'] if s['phase']=='executed'];locs=[];seen=set();repeats=[]
   for s in steps:
    if s['action'].startswith('go to '):
     loc=s['action'][6:];locs.append(loc);k=(loc,s['observation'])
     if k in seen:repeats.append(s['step'])
     seen.add(k)
   unique=list(dict.fromkeys(locs));target=task['item']['gamefile'].split('/')[2].split('-')[1].lower();observed=[s['step'] for s in steps if re.search(r'\b'+re.escape(target)+r' \d+\b',s['observation'],re.I)]
   row={'ref':ref,'arm':arm,'source':str(p),'task_id':task['item']['id'],'task_request':task['task_request'],**audit,'locations':unique,'classes':list(dict.fromkeys(re.sub(r' \d+$','',x) for x in unique)),'navigation_count':len(locs),'same_location_observation_repeats':repeats,'invalid_steps':[s['step'] for s in steps if not s['action_in_admissible_commands']],'nothing_happens_steps':[s['step'] for s in steps if s['observation'].strip()=='Nothing happens.'],'fallback_steps':[s['step'] for s in steps if s.get('fallback')],'target_category':target,'first_target_observed_feedback_step':min(observed) if observed else None,'key_actions':[{'step':s['step'],'action':s['action']} for s in steps if s['action'].split()[0] in {'take','move','clean','cool','heat','use','put'}]};rows.append(row)
   md += [f'## {ref} {arm}','',f"{task['task_request']} — {r['status']}, {audit['steps_executed']} executed steps. [raw]({p})",'','| 步 | 动作 | 反馈 |','|---|---|---|']
   md += [f"| {s['step']} | `{s['action'] if s['action_in_admissible_commands'] else '[候选外动作，见 raw]'}` | {s['observation'].replace(chr(10),' ').replace('|',' / ')} |" for s in steps];md+=['']
 pairs=[]
 for task in read(HERE/'tasks.json'):
  ref=task['ref']
  for a,b in [('Parent','A'),('Parent','B'),('A','B')]:
   p,q=records.get((ref,a)),records.get((ref,b));row={'ref':ref,'arms':[a,b],'conditions_match':False,'both_complete':False}
   if p and q:
    try:
     verify_pair(p,q);assert p['request_policy']==q['request_policy'];assert p['implementation']['files']==q['implementation']['files'];row.update(conditions_match=True,both_complete=p['status'] in COMPLETE and q['status'] in COMPLETE)
    except Exception as exc:row['error']=str(exc)
   pairs.append(row)
 calls=[];tot=Counter()
 for p in sorted(HERE.rglob('state.json')):
  if p.parent.name!='call' and not p.parent.name.startswith('step_'):continue
  s=read(p);tot['logical_calls']+=1;tot['journal_attempts']+=len(s['attempts']);tot['wait_seconds']+=s['wait_seconds'];tot['actor_logical_calls' if '/episodes/' in str(p) else 'upstream_logical_calls']+=1
  for a in s['attempts']:
   tot['post_attempts']+=bool(a.get('request_sent'));tot['http_429']+=a.get('http_status')==429;tot['unknown_usage_attempts']+=not isinstance(a.get('usage'),dict)
   u=a.get('usage') or {}
   for k in ['prompt_tokens','completion_tokens','total_tokens']:
    if isinstance(u.get(k),int):tot[k]+=u[k]
   tot['reasoning_tokens']+=(u.get('completion_tokens_details') or {}).get('reasoning_tokens',0)
  calls.append({'source':str(p),**s})
 assert tot['actor_logical_calls']<=900 and tot['upstream_logical_calls']<=read(HERE/'config.json')['max_modules']
 intervals=[]
 for r in records.values():
  for step in r['steps']:
   for a in step.get('transport_attempts',[]):
    if a.get('finished_at'):
     intervals.extend([(datetime.fromisoformat(a['started_at']).timestamp(),1),(datetime.fromisoformat(a['finished_at']).timestamp(),-1)])
 active=peak=0
 for _,change in sorted(intervals):active+=change;peak=max(peak,active)
 tot['observed_peak_actor_post_concurrency']=peak
 save(HERE/'analysis.json',{'rows':rows,'pairs':pairs,'totals':dict(tot),'calls':calls,'currency_cost':None,'reasoning_in_completion':True})
 (HERE/'TRAJECTORY_EVIDENCE.md').write_text('\n'.join(md))
 print(json.dumps({'rows':[{k:r[k] for k in ['ref','arm','status','steps_executed','native_success'] if k in r} for r in rows],'totals':dict(tot)},ensure_ascii=False,indent=2))
if __name__=='__main__':main()

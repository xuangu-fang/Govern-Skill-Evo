"""Read-only actual artifact accounting and evidence tables; no model calls."""
import json
from pathlib import Path
from collections import Counter
from datetime import datetime
from src.adapters.alfworld.skill_runtime import write_record
ROOT=Path('artifacts/methods/v23/v23_replay_memory_001')
EXP=Path('experiments/methods/v23/v23_replay_memory_001')
BROOT=Path('artifacts/methods/v23/v23_preconditioner_with_memory_001')
BEXP=Path('experiments/methods/v23/v23_preconditioner_with_memory_001')
def read(p):return json.loads(Path(p).read_text())
def model_usage(d):
 if not (d/'response.json').exists():return {'status':read(d/'run.json')['status']} if (d/'run.json').exists() else None
 r=read(d/'response.json');meta=read(d/'run.json')
 return {'status':meta['status'],'usage':r.get('usage'),'model':r.get('response_model'),
         'elapsed_seconds':(datetime.fromisoformat(meta['finished_at'])-datetime.fromisoformat(meta['started_at'])).total_seconds(),
         'input_chars':meta['input_chars'],'attempts':r.get('api_attempts')}
def episode(path):
 r=read(path);steps=[s for s in r['steps'] if s['phase']=='executed']
 usage=Counter();reasoning=0;attempts=0;response_models=set();seen=set()
 for s in r['steps']:
  attempts+=len(s.get('transport_attempts',[]))
  response=s.get('model_response',{})
  if response.get('response_model'):response_models.add(response['response_model'])
  for k,v in (response.get('usage') or {}).items():
   if isinstance(v,int):usage[k]+=v
  reasoning+=(response.get('usage') or {}).get('completion_tokens_details',{}).get('reasoning_tokens',0)
  for a in s.get('transport_attempts',[]):
   if a.get('http_status')!=200:seen.add(a.get('http_status'))
 return {'path':str(path),'task':r['task']['id'],'run_id':r['run_id'],'status':r['status'],'steps':len(steps),
         'requests':len(r['steps']),'transport_attempts':attempts,'response_models':sorted(response_models),
         'usage':dict(usage),'reasoning_tokens':reasoning,'non_200_statuses':sorted(seen,key=str),
         'invalid_actions':[s['step'] for s in steps if not s['action_in_admissible_commands']],
         'elapsed_seconds':(datetime.fromisoformat(r['finished_at'])-datetime.fromisoformat(r['started_at'])).total_seconds()}
plan=read(EXP/'config/plan.json');summaries=[];lines=['# Actual paired execution evidence','', 'No model-generated summaries; actions and observations below are copied from recorded executed events.','']
for pp,cr in zip(plan['parent_sources'],read(ROOT/'candidate_results.json')):
 qp=cr['trajectories'][0];summaries.append({'parent':episode(pp),'candidate':episode(qp)})
 for prefix,path in [('P',pp),('Q',qp)]:
  r=read(path);lines.extend([f"## {r['task']['id']} {prefix} — {r['status']}",''])
  for s in r['steps']:
   if s['phase']=='executed':lines.append(f"- {s['step']}: `{s['action']}` — {s['observation'].replace(chr(10),' ')}")
  lines.append('')
(EXP/'results/paired_evidence.md').write_text('\n'.join(lines)+'\n')
summary={'pairs':summaries,'replay':model_usage(ROOT/'replay'),
         'new_parent_episodes':0,'new_candidate_episodes':len(summaries),
         'billing':'Provider response records token usage but no monetary billed amount; no currency estimate fabricated.'}
if (ROOT/'memory_view.json').exists():summary['memory_entries']=len(read(ROOT/'memory_view.json')['entries'])
write_record(EXP/'results/summary.json',summary)
for name in ['replay.json','validation.json']:
 if (ROOT/'replay'/name).exists(): (EXP/'results'/name).write_bytes((ROOT/'replay'/name).read_bytes())
if (ROOT/'memory_view.json').exists(): (EXP/'results/memory_view.json').write_bytes((ROOT/'memory_view.json').read_bytes())
bs={'empty':model_usage(BROOT/'empty'),'real':model_usage(BROOT/'real'),'scope':'same-batch retrospective test; no new Candidate execution'}
write_record(BEXP/'results/summary.json',bs)
if (BROOT/'comparison.json').exists():(BEXP/'results/comparison.json').write_bytes((BROOT/'comparison.json').read_bytes())
print(json.dumps(summary,ensure_ascii=False,indent=2))
print(json.dumps(bs,ensure_ascii=False,indent=2))

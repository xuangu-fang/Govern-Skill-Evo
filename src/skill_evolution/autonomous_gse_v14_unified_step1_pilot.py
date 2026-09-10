"""Closed-loop Unified Step-1 pilot; v14 learner components remain unchanged."""
import argparse,copy,dataclasses,json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
ROOT=Path(__file__).resolve().parents[2]
SUITE=ROOT/'benchmarks/tau2_governed_evolution/phase_a_final_unified_benchmark_v1'
CAL=SUITE/'calibration'
PILOT_ROOT=ROOT/'experiments/phase_a_unified_v14_step1_pilot'
OUT=PILOT_ROOT/'attempt_3_clean_adapter'
from dotenv import load_dotenv
load_dotenv(ROOT/'.env',override=True)
from src.skill_evolution.diagnosis_v14 import call_diagnosis,DiagnosisResponse
from src.skill_evolution.autonomous_gse_v14_proposal import MultiRolloutDiagnosisProposalOperator,DiagnosisEditorRequest,EditorContractError
from src.skill_evolution.autonomous_gse_v03_proposal import ProposalContext
from src.learners.stwebagentbench.generate_governed_skill_v14 import call_governed_editor
from src.skill_evolution.autonomous_gse_v13_benchmark_runtime import load_authoritative_domain_contexts
from src.skill_evolution.unified_pilot_learner_adapter import (
 build_learner_safe_request,write_preflight_artifacts,
)

def load(p):return json.loads(p.read_text())
def write(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def prepare_requests():
 parent=(ROOT/'experiments/campaigns/autonomous_gse_v14/skills/S0_empty_skill.md').read_text().replace('# Operational Skill', '# SuiteCRM Operational Skill', 1)
 specs=load(SUITE/'metadata/task_role_manifest.json')['tasks'];results={(r['task_id'],r['rollout_index']):r for r in load(CAL/'measurement_revision/revised_success_results.json')};ev=[];manifest=[]
 states={'CS':'compliant_success','CF':'compliant_failure','VS':'violating_success','VF':'violating_failure'}
 for n,s in enumerate(specs,1):
  for i in range(1,4):
   id=s['task_id'];r=results[id,i];path=CAL/'trajectories'/f'{id}_{i:02d}.json';e=copy.deepcopy(load(path)['evidence']);source=f'T{n:03d}_R{i}';e.update(source_id=source,domain=s['domain'],task_id=f'T{n:03d}',rollout_index=i,task_success=bool(r['new_success']),state=states[r['new_quadrant']]);e['task_evaluation'].update(success=bool(r['new_success']),reward=float(r['new_success']))
   e['task_evaluation']['revised_success_evidence']=r['reward_info']
   instr=e.get('goal',{}).get('instructions',{});e['goal']={k:instr[k] for k in ('known_info','task_instructions','unknown_info') if k in instr} if instr else e['goal']
   dirty=id=='retail_pa_v2_w9892465_cancel_funds_w1242543' and i==2
   if dirty:e['evidence_quality']={'dirty':True,'reason':'UserSimulator opening adopts assistant role. Do not use this rollout as support for an Agent behavioral mechanism.'}
   ev.append(e);manifest.append({'learner_task_id':f'T{n:03d}','source_id':source,'task_id':id,'domain':s['domain'],'rollout_index':i,'seed':r['seed'],'path':str(path.relative_to(ROOT)),'dirty':dirty})
 domains=load_authoritative_domain_contexts(ROOT/'external/tau2-bench');requests=[];alias_maps=[]
 for n in range(34):
  group=tuple(ev[n*3:n*3+3]);domain=group[0]['domain']
  request,alias_map=build_learner_safe_request(learner_alias=f'T{n+1:03d}',parent_skill=parent,domain_context=domains[domain],rollouts=group)
  requests.append(request);alias_maps.append(alias_map)
 return parent,specs,requests,alias_maps,manifest,domains

def preflight():
 parent,specs,requests,alias_maps,evidence_manifest,domains=prepare_requests()
 report=write_preflight_artifacts(output_dir=OUT,requests=requests,actual_task_ids=[s['task_id'] for s in specs],alias_maps=alias_maps,manifest=load(SUITE/'metadata/task_role_manifest.json'))
 write(OUT/'pilot_config.json',{'scope':'SAME_UNIFIED_BENCHMARK_MATCHED_REPLAY','steps':1,'tasks':34,'domains':{'airline':20,'retail':14},'pairs':102,'learner':'existing v14 diagnosis/compiler/proposal/editor','gate':{'replicates':10000,'seed':200,'threshold':0.80,'epsilon_pair_count':1},'parent_reused':True,'mechanism_metadata_injected':False,'outcome_driven_candidate_retry':False,'previous_diagnoses_reused':False,'v14_learner_core_modified':False})
 print('LEARNER_INPUT_PREFLIGHT',f"{report['passed']}/{report['total_requests']}",'PASS' if report['failed']==0 else 'FAIL',flush=True)
 return report

def compile_and_edit(parent,requests,domains,response_cache):
 safe_ev=[item for q in requests for item in q.rollouts]
 request_by_id={q.diagnosis_id:q for q in requests}
 def compiled_diagnose(req):
  safe=request_by_id[req.diagnosis_id]
  if tuple(req.rollouts)!=tuple(safe.rollouts):raise RuntimeError(f'PREFLIGHT_REQUEST_DRIFT:{req.diagnosis_id}')
  return response_cache[req.diagnosis_id]
 dirty={r['source_id'] for r in safe_ev if r.get('evidence_quality',{}).get('dirty')}
 def editor(req):
  rejected=[x for x in req.eligible_diagnoses if x['support_evidence_refs'] and all(r['source_id'] in dirty for r in x['support_evidence_refs'])];clean=tuple(x for x in req.eligible_diagnoses if x not in rejected)
  write(OUT/'compiler/dirty_exclusions.json',{'policy':'A dirty rollout cannot solely support a Skill update; raw Diagnosis/compiler unchanged.','excluded':rejected,'forwarded':len(clean)})
  if not clean:raise RuntimeError('NO_CLEAN_ELIGIBLE_UPDATES')
  forwarded=dataclasses.replace(req,eligible_diagnoses=clean);serialized=json.loads(json.dumps(dataclasses.asdict(forwarded)));request_path=OUT/'candidate/editor_request.json'
  if request_path.exists() and load(request_path)!=serialized:raise RuntimeError('EDITOR_RECOVERY_REQUEST_DRIFT')
  write(request_path,serialized)
  try:response=call_governed_editor(forwarded)
  except EditorContractError as error:
   attempt=len(list((OUT/'candidate').glob('editor_attempt_*_error.json')))+1;write(OUT/'candidate'/f'editor_attempt_{attempt:02d}_error.json',error.as_dict());raise
  write(OUT/'candidate/editor_response.json',{'response':str(response),'transport':getattr(response,'editor_transport',None)});return response
 decision=MultiRolloutDiagnosisProposalOperator().propose(ProposalContext('STEP1_CANDIDATE',parent,tuple(safe_ev)),compiled_diagnose,editor,domain_contexts=domains)
 write(OUT/'compiler/compiled_updates.json',dataclasses.asdict(decision));write(OUT/'diagnosis/diagnosis_summary.json',{'diagnoses':decision.diagnoses,'eligible':decision.eligible_diagnosis_ids,'status':decision.proposal_status,'reason':decision.proposal_reason})
 if decision.candidate_skill:
  (OUT/'candidate/candidate_skill.md').write_text(decision.candidate_skill);write(OUT/'candidate/edit_provenance.json',{'applied':decision.applied_edits,'excluded':decision.excluded_edits,'audit':decision.provenance_audit})
 print('PROPOSAL',decision.proposal_status,decision.proposal_reason,flush=True)

def learn():
 parent,specs,requests,alias_maps,evidence_manifest,domains=prepare_requests()
 report_path=OUT/'adapter/adapter_preflight_report.json'
 if not report_path.exists():raise RuntimeError('PREFLIGHT_NOT_RUN')
 report=load(report_path)
 if report.get('total_requests')!=34 or report.get('passed')!=34 or report.get('failed')!=0:raise RuntimeError('ADAPTER_PREFLIGHT_FAILED')
 existing=list((OUT/'diagnosis/task_diagnoses').glob('diagnosis_*.json')) if (OUT/'diagnosis/task_diagnoses').exists() else []
 if existing:raise RuntimeError('CLEAN_ATTEMPT_ALREADY_HAS_DIAGNOSIS_OUTPUTS')
 request_by_id={q.diagnosis_id:q for q in requests};response_cache={}
 def model_diagnose(req):
  safe=request_by_id[req.diagnosis_id]
  path=OUT/'diagnosis/task_diagnoses'/f'{req.diagnosis_id}.json'
  response=call_diagnosis(safe);response_cache[req.diagnosis_id]=response;write(path,{'response':str(response),'mode':getattr(response,'structured_output_mode','unknown'),'fallback':getattr(response,'structured_output_fallback_reason',None)});print('DIAGNOSIS',req.diagnosis_id,flush=True);return response
 with ThreadPoolExecutor(max_workers=6) as pool:
  for f in as_completed([pool.submit(model_diagnose,q) for q in requests]):f.result()
 if len(response_cache)!=34:raise RuntimeError('DIAGNOSIS_BATCH_INCOMPLETE')
 compile_and_edit(parent,requests,domains,response_cache)

def recover_editor():
 parent,specs,requests,alias_maps,evidence_manifest,domains=prepare_requests();response_cache={}
 for request in requests:
  payload=load(OUT/'diagnosis/task_diagnoses'/f'{request.diagnosis_id}.json')
  response_cache[request.diagnosis_id]=DiagnosisResponse(payload['response'],payload['mode'],payload.get('fallback'))
 if len(response_cache)!=34:raise RuntimeError('DIAGNOSIS_BATCH_INCOMPLETE')
 compile_and_edit(parent,requests,domains,response_cache)
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('phase',choices=('preflight','learn','recover-editor'));args=parser.parse_args()
 {'preflight':preflight,'learn':learn,'recover-editor':recover_editor}[args.phase]()

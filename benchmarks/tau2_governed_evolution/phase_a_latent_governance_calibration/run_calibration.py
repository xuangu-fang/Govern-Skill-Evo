"""Frozen Empty-Skill calibration; never starts a learner or reruns trajectories."""
import json,hashlib,os,traceback,datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
from dotenv import load_dotenv
ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[2]
load_dotenv(REPO/'.env',override=True)
os.environ.pop('TAU2_AGENT_SKILL_PATH',None)
from loguru import logger
logger.remove()
from tau2.data_model.tasks import Task
from tau2.runner.build import build_text_orchestrator
from tau2.evaluator.evaluator import evaluate_simulation,EvaluationType
from tau2.orchestrator.modes import CommunicationMode
from benchmarks.tau2_governed_evolution.capability_expansion.run_phase_a_capability_empty_rollouts import _config
from benchmarks.tau2_governed_evolution.phase_a_success_v2.run_success_v2 import apply_context
from src.skill_evolution.autonomous_gse_v13_benchmark_runtime import _build_governed_evidence,load_authoritative_domain_contexts
from src.adapters.tau2.tau3_compliance_judge_v13 import default_judge_caller

def load(p):return json.loads(p.read_text())
def write(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def validate():
 f=load(ROOT/'latent_governance_calibration_manifest.json')
 for p,h in f['frozen_sha256'].items():assert sha(REPO/p)==h,p
 return f

def one(spec,task,seed,index,config,contexts):
 stem=ROOT/'trajectories'/f'{task.id}_{index:02d}';raw=Path(str(stem)+'_raw.json');out=Path(str(stem)+'.json');started=Path(str(stem)+'_started.json')
 if started.exists():return dict(task_id=task.id,index=index,status='REFUSED_RERUN')
 write(started,dict(seed=seed,utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
 try:
  o=build_text_orchestrator(_config(config,spec,seed),task,seed=seed)
  view=apply_context(o,spec['domain'])
  o.agent.domain_policy=(ROOT/'candidate_masks'/f'{spec["mask_id"]}.md').read_text()
  simulation=o.run()
  simulation.policy=o.agent.domain_policy
  write(raw,simulation.model_dump(mode='json'))
  reward=evaluate_simulation(simulation=simulation,task=task,evaluation_type=EvaluationType.ALL,solo_mode=False,domain=spec['domain'],mode=CommunicationMode.HALF_DUPLEX,nl_assertions_model=config['official_evaluator']['nl_assertions_model'],nl_assertions_llm_args={'temperature':config['official_evaluator']['nl_assertions_temperature']})
  simulation.reward_info=reward
  write(Path(str(stem)+'_evaluated.json'),simulation.model_dump(mode='json'))
  attempts=[]
  def caller(model,system,user,temperature):
   for n in range(3):
    response=default_judge_caller(model,system,user,temperature)
    attempts.append(dict(attempt=n+1,empty=not bool(response and response.strip())))
    if response and response.strip():return response
   raise RuntimeError('JUDGE_EMPTY_AFTER_3_ATTEMPTS')
  evidence=_build_governed_evidence(source_id=task.id+f'_{index}',domain=spec['domain'],task=task,simulation=simulation,domain_policy=contexts[spec['domain']]['original_domain_policy'],available_tool_contracts=contexts[spec['domain']]['available_tool_contracts'],judge_caller=caller)
  result=dict(task_id=task.id,candidate_id=spec['candidate_id'],native_state=spec['native_state'],index=index,seed=seed,mask_id=spec['mask_id'],evidence=evidence,judge_attempts=attempts,raw_sha256=sha(raw))
  write(out,result);return dict(task_id=task.id,index=index,status='completed',path=str(out))
 except Exception as e:
  write(Path(str(stem)+'_error.json'),dict(task_id=task.id,index=index,error_type=type(e).__name__,message=str(e),traceback=traceback.format_exc()))
  return dict(task_id=task.id,index=index,status='error',error_type=type(e).__name__)

def main():
 validate();config=load(ROOT/'run_config.json');specs=load(ROOT/'task_manifest.json')['tasks'];tasks={t['id']:Task.model_validate(t) for t in load(ROOT/'targeted_tasks.json')};seeds=load(ROOT/'seed_manifest.json')['seeds'];contexts=load_authoritative_domain_contexts(REPO/'external/tau2-bench')
 rows=[]
 with ThreadPoolExecutor(max_workers=4) as pool:
  futures=[pool.submit(one,s,tasks[s['task_id']],seed,i,config,contexts) for s in specs for i,seed in enumerate(seeds[s['task_id']],1)]
  for f in as_completed(futures):
   rows.append(f.result());write(ROOT/'run_progress.json',rows);print(json.dumps(dict(finished=len(rows),total=len(futures),last=rows[-1])),flush=True)
 write(ROOT/'run_summary.json',rows)
if __name__=='__main__':main()

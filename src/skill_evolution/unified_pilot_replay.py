"""Matched candidate replay plumbing for the one-step Unified pilot."""
import sys,os,traceback,json
from concurrent.futures import ThreadPoolExecutor,as_completed
from src.skill_evolution.autonomous_gse_v14_unified_step1_pilot import ROOT,OUT,SUITE,CAL,load,write
sys.path.insert(0,str(CAL))
import run_calibration as r
from tau2.data_model.simulation import RewardInfo

def one(spec,task,seed,index,config,contexts,revisions):
 stem=OUT/'candidate_rollouts'/f'{task.id}_{index:02d}';out=stem.with_suffix('.json');raw=stem.with_name(stem.name+'_raw.json');started=stem.with_name(stem.name+'_started.json')
 if out.exists():return load(out)
 if started.exists():raise RuntimeError('Existing partial trajectory: requires explicit infra/recovery inspection, never automatic behavioral rerun')
 write(started,{'seed':seed,'candidate':str(OUT/'candidate/candidate_skill.md')})
 try:
  cfg=r._config(config,spec,seed);cfg.agent='llm_agent_manual_skill';cfg.llm_args_agent['manual_skill_path']=str(OUT/'candidate/candidate_skill.md')
  o=r.build_text_orchestrator(cfg,task,seed=seed);cid=r.bind_agent_context(o,spec['domain']);initial=o.environment.tools.db.model_dump(mode='json');sim=o.run();sim.policy=o.agent.domain_policy;write(raw,sim.model_dump(mode='json'));final=o.environment.tools.db.model_dump(mode='json');write(stem.with_name(stem.name+'_final_db.json'),final)
  etask=task.model_copy(deep=True)
  if task.id in revisions:etask.evaluation_criteria.nl_assertions=revisions[task.id]['revised_nl_assertions']
  def native(t):return r.evaluate_simulation(simulation=sim,task=t,evaluation_type=r.EvaluationType.ALL,solo_mode=False,domain=spec['domain'],mode=r.CommunicationMode.HALF_DUPLEX,nl_assertions_model=config['official_evaluator']['nl_assertions_model'],nl_assertions_llm_args={'temperature':config['official_evaluator']['nl_assertions_temperature']})
  reward=r.evaluate_success(etask,initial,final,native)
  if task.id==r.UCA01:reward=RewardInfo(reward=float(reward['success']),info={'custom_goal_predicate':reward})
  sim.reward_info=reward;write(stem.with_name(stem.name+'_evaluated.json'),sim.model_dump(mode='json'));write(OUT/'evaluations/success'/f'{task.id}_{index:02d}.json',reward.model_dump(mode='json'))
  attempts=[]
  def caller(*args):
   for n in range(3):
    v=r.default_judge_caller(*args);attempts.append({'attempt':n+1,'empty':not bool(v and v.strip())})
    if v and v.strip():return v
   raise RuntimeError('JUDGE_EMPTY_AFTER_3_ATTEMPTS')
  e=r._build_governed_evidence(source_id=f'{task.id}_{index}',domain=spec['domain'],task=task,simulation=sim,domain_policy=contexts[spec['domain']]['original_domain_policy'],available_tool_contracts=contexts[spec['domain']]['available_tool_contracts'],judge_caller=caller)
  d={'task_id':task.id,'index':index,'seed':seed,'context_id':cid,'evidence':e,'raw_sha256':r.sha(raw),'judge_attempts':attempts};write(out,d);write(OUT/'evaluations/compliance'/f'{task.id}_{index:02d}.json',e['compliance_evaluation']);return {'task_id':task.id,'index':index,'state':e['state']}
 except Exception as e:
  write(stem.with_name(stem.name+'_error.json'),{'error':str(e),'traceback':traceback.format_exc()});return {'task_id':task.id,'index':index,'error':str(e)}
def main():
 assert (OUT/'candidate/candidate_skill.md').exists()
 specs=load(SUITE/'metadata/task_role_manifest.json')['tasks'];tasks={t['id']:r.Task.model_validate(t) for t in load(SUITE/'tasks/final_tasks.json')};seeds=load(SUITE/'metadata/calibration_seeds.json')['seeds'];conf=load(CAL/'run_config.json');contexts=r.load_authoritative_domain_contexts(ROOT/'external/tau2-bench');revs={x['task_id']:x for x in load(CAL/'measurement_revision/evaluator_revisions.json')['changes']};done=[]
 with ThreadPoolExecutor(max_workers=8) as pool:
  fs=[pool.submit(one,s,tasks[s['task_id']],seed,i,conf,contexts,revs) for s in specs for i,seed in enumerate(seeds[s['task_id']],1)]
  for f in as_completed(fs):done.append(f.result());write(OUT/'candidate_rollouts/progress.json',done);print('REPLAY',len(done),done[-1],flush=True)
if __name__=='__main__':main()

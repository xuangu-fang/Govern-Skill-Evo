"""Recover a missing evaluation from immutable raw trajectory; no rollout."""
import run_calibration as r
from tau2.data_model.simulation import SimulationRun
id='retail_pa_v2_w9318778_payment_items_address';i=2
stem=r.ROOT/'trajectories'/f'{id}_{i:02d}';raw=stem.with_name(stem.name+'_raw.json');out=stem.with_suffix('.json')
if out.exists():raise RuntimeError('Evaluation already present')
task=next(r.Task.model_validate(t) for t in r.load(r.SUITE/'tasks/final_tasks.json') if t['id']==id)
spec=next(t for t in r.load(r.SUITE/'metadata/task_role_manifest.json')['tasks'] if t['task_id']==id)
c=r.load(r.ROOT/'run_config.json');sim=SimulationRun.model_validate(r.load(raw))
sim.reward_info=r.evaluate_simulation(simulation=sim,task=task,evaluation_type=r.EvaluationType.ALL,solo_mode=False,domain='retail',mode=r.CommunicationMode.HALF_DUPLEX,nl_assertions_model=c['official_evaluator']['nl_assertions_model'],nl_assertions_llm_args={'temperature':c['official_evaluator']['nl_assertions_temperature']})
r.write(stem.with_name(stem.name+'_evaluated.json'),sim.model_dump(mode='json'));r.write(r.ROOT/'evaluations/success'/f'{id}_02.json',sim.reward_info.model_dump(mode='json'))
ctx=r.load_authoritative_domain_contexts(r.REPO/'external/tau2-bench');attempts=[]
def caller(*args):
 for n in range(3):
  text=r.default_judge_caller(*args);attempts.append({'attempt':n+1,'empty':not bool(text and text.strip())})
  if text and text.strip():return text
 raise RuntimeError('Empty judge')
e=r._build_governed_evidence(source_id=id+'_2',domain='retail',task=task,simulation=sim,domain_policy=ctx['retail']['original_domain_policy'],available_tool_contracts=ctx['retail']['available_tool_contracts'],judge_caller=caller)
r.write(out,dict(task_id=id,primary_role=spec['primary_role'],native_state=spec['native_state'],index=i,seed=r.load(r.SUITE/'metadata/calibration_seeds.json')['seeds'][id][1],context_id=spec['context_id'],evidence=e,judge_attempts=attempts,raw_sha256=r.sha(raw),evaluation_recovery=True))
r.write(r.ROOT/'evaluations/compliance'/f'{id}_02.json',e['compliance_evaluation'])
r.write(r.ROOT/'evaluation_recovery.json',{'task_id':id,'index':2,'reason':'Success evaluator malformed JSON','trajectory_rerun':False,'raw_sha256':r.sha(raw),'success_evaluation_retry':1,'completed':True})
print('evaluation recovery completed')

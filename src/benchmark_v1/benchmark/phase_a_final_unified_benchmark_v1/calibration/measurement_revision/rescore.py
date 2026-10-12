"""Success-only rescoring of saved trajectories; never invokes a rollout or Judge."""
import sys,json,hashlib,traceback
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
P=((Path(__file__).resolve().parents[6] / 'experiments/benchmarks/tau2/phase_v1_day30/benchmark/phase_a_final_unified_benchmark_v1/calibration/measurement_revision'))
from scripts.benchmarks.v1.benchmark.phase_a_final_unified_benchmark_v1.calibration import run_calibration as r
from tau2.data_model.simulation import SimulationRun
from tau2.registry import registry
revs={x['task_id']:x for x in r.load((Path(__file__).resolve().parents[6] / 'experiments/benchmarks/tau2/phase_v1_day30/benchmark/phase_a_final_unified_benchmark_v1/calibration/measurement_revision/evaluator_revisions.json'))['changes']}
tasks={t['id']:t for t in r.load(r.SUITE/'tasks/final_tasks.json')}
meta={t['task_id']:t for t in r.load(r.SUITE/'metadata/task_role_manifest.json')['tasks']}
def one(row):
 id=row['task_id'];i=row['rollout_index'];stem=f'{id}_{i:02d}';out=(Path(__file__).resolve().parents[6] / 'artifacts/benchmarks/tau2/phase_v1_day30/benchmark/phase_a_final_unified_benchmark_v1/calibration/measurement_revision/evaluations')/f'{stem}.json'
 if out.exists():return r.load(out)
 raw=(Path(__file__).resolve().parents[6] / 'artifacts/benchmarks/tau2/phase_v1_day30/benchmark/phase_a_final_unified_benchmark_v1/calibration/trajectories')/f'{stem}_raw.json';sim=SimulationRun.model_validate(r.load(raw));t=r.Task.model_validate(tasks[id]);config=r.load((Path(__file__).resolve().parents[6] / 'experiments/benchmarks/tau2/phase_v1_day30/benchmark/phase_a_final_unified_benchmark_v1/calibration/run_config.json'))
 if id in revs:t.evaluation_criteria.nl_assertions=revs[id]['revised_nl_assertions']
 try:
  if id==r.UCA01:
   env=registry.get_env_constructor('airline')(solo_mode=False)
   result=r.evaluate_success(t,env.tools.db.model_dump(mode='json'),r.load((Path(__file__).resolve().parents[6] / 'artifacts/benchmarks/tau2/phase_v1_day30/benchmark/phase_a_final_unified_benchmark_v1/calibration/trajectories')/f'{stem}_final_db.json'),None)
   score=float(result['success']);detail=result
  else:
   reward=r.evaluate_simulation(simulation=sim,task=t,evaluation_type=r.EvaluationType.ALL,solo_mode=False,domain=meta[id]['domain'],mode=r.CommunicationMode.HALF_DUPLEX,nl_assertions_model=config['official_evaluator']['nl_assertions_model'],nl_assertions_llm_args={'temperature':config['official_evaluator']['nl_assertions_temperature']})
   score=reward.reward;detail=reward.model_dump(mode='json')
  new=int(score==1);data={**row,'old_success':row['Success'],'new_success':new,'old_quadrant':row['quadrant'],'new_quadrant':('C' if row['Compliance'] else 'V')+('S' if new else 'F'),'evaluator_changed':id in revs,'reward_info':detail,'raw_sha256':r.sha(raw),'Compliance_reused':True}
  r.write(out,data);return data
 except Exception as e:
  r.write((Path(__file__).resolve().parents[6] / 'artifacts/benchmarks/tau2/phase_v1_day30/benchmark/phase_a_final_unified_benchmark_v1/calibration/measurement_revision/errors')/f'{stem}.json',{'error':str(e),'traceback':traceback.format_exc()});return {'task_id':id,'index':i,'error':str(e)}
if __name__=='__main__':
 rows=r.load((Path(__file__).resolve().parents[6] / 'experiments/benchmarks/tau2/phase_v1_day30/benchmark/phase_a_final_unified_benchmark_v1/calibration/quadrant_results.json'))['results'];done=[]
 with ThreadPoolExecutor(max_workers=8) as pool:
  for f in as_completed([pool.submit(one,x) for x in rows]):
   done.append(f.result());r.write((Path(__file__).resolve().parents[6] / 'experiments/benchmarks/tau2/phase_v1_day30/benchmark/phase_a_final_unified_benchmark_v1/calibration/measurement_revision/rescore_progress.json'),done);print(len(done),done[-1]['task_id'],'ERROR' if 'error' in done[-1] else done[-1]['new_quadrant'],flush=True)
 r.write((Path(__file__).resolve().parents[6] / 'experiments/benchmarks/tau2/phase_v1_day30/benchmark/phase_a_final_unified_benchmark_v1/calibration/measurement_revision/revised_success_results.json'),done)

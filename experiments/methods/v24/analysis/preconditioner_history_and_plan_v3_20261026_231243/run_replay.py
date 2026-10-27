"""Preconditioner-only replay of V24 smoke and its explicitly inherited ALFWorld baseline."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[5]
sys.path.insert(0,str(ROOT))
from experiments.methods.v24.analysis.preconditioner_history_and_plan_v3_20261026_231243.archive_io import ARCHIVE, resolve_path
from src.skill_evolution.v24 import evolution as ev, preconditioner as pc, output_feedback as fb
from src.skill_evolution.v24.config import method_config
from src.skill_evolution.v24.benchmark import using_benchmark
from src.skill_evolution.v24.benchmarks.alfworld.adapter import ALFWorldAdapter
OUT=ARCHIVE
CASES={
 'v24_smoke_R01':('artifacts/methods/v24/alfworld_rc1_smoke_001/S1','R01','V24 real smoke; empty Memory; open-container and limited-history plan defects'),
 'inherited_v23_5_R03':('artifacts/methods/v23_5/alfworld_verified_feedback_001/S1','R03','V24 migration baseline; historical Knowledge and a reasonable transform requirement'),
 'inherited_v23_5_R06':('artifacts/methods/v23_5/alfworld_verified_feedback_001/S1','R06','V24 migration baseline; history and coordination of return-to-source versus anti-revisit requirements'),
}
def case_input(source,rn):
 source=resolve_path(source)
 stage=source/'rounds'/rn/'preconditioner';selected=stage/ev.read(stage/'result.json')['path']
 return selected,ev.read(selected/'input.json'),ev.read(selected/'run.json')
def run_one(name,source,rn,config):
 with using_benchmark(ALFWorldAdapter()):
  selected,saved,meta=case_input(source,rn)
  expected=json.loads(ev.read(selected/'messages.json')[1]['content']);expected.pop('grouping',None)
  def invoke(path,generate,cfg):
   result=pc.run_preconditioner(meta['grouping_directory'],meta['diagnosis_directory'],path,
     generate=generate,call_config=cfg,max_input_chars=meta['max_input_chars'],memory=saved['memory'],
     memory_view=meta['memory_view'],memory_contract=meta['memory_contract'],diagnosis_version=meta['diagnosis_version'])
   assert ev.read(path/'input.json')==saved
   assert json.loads(ev.read(path/'messages.json')[1]['content'])==expected
   return result
  print(name+': starting Preconditioner only',flush=True)
  try:
   path,result=ev._model_stage(OUT,OUT/name,'preconditioner',invoke,config,None,False)
   summary={'status':'valid','selected':str(path),'adjustments':result['raw_preconditioner']['adjustments'],
            'checks':result['raw_preconditioner']['checks'],'original_input_preserved':True,
            'model_input_change':'grouping removed; all other fields identical'}
  except Exception as exc:
   summary={'status':'failed','error_type':type(exc).__name__,'error':str(exc)[:1000]}
  ev.save(OUT/name/'summary.json',summary);print(name+': '+summary['status'],flush=True)
  return name,summary

def main():
 assert not (OUT/'manifest.json').exists(),'Already initialized; never reset request budgets.'
 records={};jobs=[];metadata={}
 with using_benchmark(ALFWorldAdapter()):
  ev.save(OUT/'contract.json',ev.frozen_contract())
  for name,(relative,rn,scope) in CASES.items():
   source=ROOT/relative;selected,saved,meta=case_input(source,rn)
   cfg=deepcopy(ev.read(source/'config.json'));cfg['method']=method_config()
   assert ev.stage_call_config(cfg,'preconditioner')==meta['call_config']
   ev.check_live_environment(cfg)
   assert {**pc.read_upstream(meta['grouping_directory'],meta['diagnosis_directory']),'memory':saved['memory']}==saved
   messages=pc.messages_for(saved,memory_view=meta['memory_view'],memory_contract=meta['memory_contract'],retry_policy=fb.POLICY)
   expected=json.loads(ev.read(selected/'messages.json')[1]['content']);expected.pop('grouping',None)
   assert json.loads(messages[1]['content'])==expected
   (OUT/name).mkdir();ev.save(OUT/name/'replay_config.json',cfg)
   ev.save(OUT/name/'baseline_output.json',ev.read(selected/'parsed.json'))
   ev.save(OUT/name/'expected_model_input.json',expected)
   for folder in [selected,Path(meta['grouping_directory']),Path(meta['diagnosis_directory'])]:
    for f in folder.iterdir():
     if f.is_file():records[str(f)]=f.read_bytes()
   records[str(source/'config.json')]=(source/'config.json').read_bytes()
   metadata[name]={'source':str(source),'selected':str(selected),'round':rn,'scope':scope,
      'memory_entries':len(saved['memory']['entries']),'old_prompt_version':meta['prompt_version'],
      'call_config':meta['call_config'],'request_limit':cfg['max_attempts'],'retry_delay_seconds':cfg['retry_delay_seconds']}
   jobs.append((name,source,rn,cfg))
  ev.save(OUT/'manifest.json',{'started_at':ev.now(),'prompt_version':pc.KNOWLEDGE_PROMPT_VERSION,
      'cases':metadata,'original_files':list(records),'scope':'Only Preconditioner calls; no Actor, Editor, Memory publication or full training.',
      'comparison_limit':'Original archives predate history_primary_v2; do not claim controlled v2-v3 improvement. Grouping removed from model input only; other fields unchanged.',
      'semantic_resampling':False,'local_validation':'Not run by this entry point.'})
 summaries={}
 with ThreadPoolExecutor(max_workers=3) as pool:
  for f in as_completed([pool.submit(run_one,*args) for args in jobs]):
   name,s=f.result();summaries[name]=s
 unchanged=all(Path(p).read_bytes()==content for p,content in records.items())
 ev.save(OUT/'completion.json',{'finished_at':ev.now(),'original_archives_unchanged':unchanged,
                              'cases':{n:s['status'] for n,s in summaries.items()}})
 assert unchanged
 print('Replays finished; original archives unchanged.',flush=True)
if __name__=='__main__':main()

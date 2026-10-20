"""One explicitly authorized identical-request recovery, with no failure feedback.
Run at repository root with PYTHONPATH=.; an existing live directory forbids rerun.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from dotenv import load_dotenv
from src.adapters.alfworld.skill_runtime import write_record
from src.skill_evolution.v23 import editor
from src.skill_evolution.v23.preconditioner import load_preconditioner

EXP=Path('experiments/methods/v23/v23_editor_recovery_001')
ROOT=Path('artifacts/methods/v23/v23_editor_recovery_001')
LIVE=ROOT/'live'
OLD=Path('artifacts/methods/v23/v23_editor_001/live')
OLD_EXP=Path('experiments/methods/v23/v23_editor_001')
PRE=Path('artifacts/methods/v23/v23_preconditioner_001/live')
assert not LIVE.exists(), 'Only one new recovery request is authorized'
request=json.loads((OLD/'request.json').read_text())
old_plan=json.loads((OLD_EXP/'config/plan.json').read_text())
config=old_plan['call_config']
load_dotenv('.env',override=False)
assert os.environ.get('OPENAI_API_KEY')
base_url=os.environ['OPENAI_BASE_URL']
assert editor.call_configuration(base_url=base_url,model=config['model'],max_tokens=config['max_tokens'],timeout=config['timeout_seconds'])==config
saved=load_preconditioner(PRE)
assert editor.editor_input(saved)==json.loads((OLD/'input.json').read_text())
assert editor.messages_for(saved)==request['body']['messages']
assert saved==json.loads((OLD/'upstream.json').read_text())
for path in (OLD_EXP/'config/source').iterdir():
    assert path.read_bytes()==(Path('src/skill_evolution/v23')/path.name).read_bytes()

def snapshot(directory):
    return {str(p.relative_to(directory)):p.read_bytes() for p in directory.rglob('*') if p.is_file()}
protected=[OLD_EXP,Path('artifacts/methods/v23/v23_editor_001'),PRE,
           Path('artifacts/methods/v23/v23_prompt_alignment_001/grouping'),
           Path('artifacts/methods/v23/v23_prompt_alignment_001/diagnosis')]
before={str(path):snapshot(path) for path in protected}
write_record(ROOT/'protected_files.json',{d:{name:hashlib.sha256(data).hexdigest() for name,data in files.items()} for d,files in before.items()})
(ROOT/'frozen_request.json').write_bytes((OLD/'request.json').read_bytes())
(ROOT/'frozen_input.json').write_bytes((OLD/'input.json').read_bytes())
(ROOT/'frozen_messages.json').write_bytes((OLD/'messages.json').read_bytes())
(EXP/'results').mkdir(parents=True,exist_ok=True)
write_record(EXP/'config/plan.json',{
    **old_plan,'frozen_at':datetime.now(timezone.utc).isoformat(),'output_directory':str(LIVE),
    'recovery_of':str(OLD),'authorization':'User authorized one identical-request technical recovery; no failure feedback or patch repair.',
    'max_new_calls':1,'failure_feedback_added':False,'patch_repair_allowed':False,
    'source_snapshot':str(OLD_EXP/'config/source'),'prior_regression_log':'artifacts/methods/v23/v23_editor_001/offline_tests.txt'})
print('Parent, Plan, full messages, all request parameters and implementation equal original. Starting ONE authorized recovery.',flush=True)
base_generate=editor.live_generator(base_url=base_url,key=os.environ['OPENAI_API_KEY'],model=config['model'],max_tokens=config['max_tokens'],timeout=config['timeout_seconds'])
calls=[]
def generate(messages,directory):
    assert messages==request['body']['messages'] and not calls
    calls.append(1)
    return base_generate(messages,directory)
generate.call_config=config
result=None;error=None
try:
    result=editor.run_editor(PRE,LIVE,generate=generate,max_input_chars=old_plan['max_input_chars'],call_config=config)
except (Exception,KeyboardInterrupt) as exc:
    error=type(exc).__name__
assert len(calls)==1
assert json.loads((LIVE/'request.json').read_text())==request
assert all(snapshot(Path(path))==files for path,files in before.items())
for path in (OLD_EXP/'config/source').iterdir():
    assert path.read_bytes()==(Path('src/skill_evolution/v23')/path.name).read_bytes()
reuse=False;failure_refused=False
live_before=snapshot(LIVE)
def forbidden(*_):raise AssertionError('No further requests authorized')
if result is not None:
    assert editor.run_editor(PRE,LIVE,generate=forbidden,call_config=config)==result
    reuse=True
else:
    try:editor.run_editor(PRE,LIVE,generate=forbidden,call_config=config)
    except ValueError:failure_refused=True
    else:raise AssertionError('Failed result was reused')
assert live_before==snapshot(LIVE)
for name in ('parsed.json','editor.json','patch.diff','candidate.md','actual.diff','validation.json'):
    if (LIVE/name).exists():(EXP/'results'/name).write_bytes((LIVE/name).read_bytes())
response=json.loads((LIVE/'response.json').read_text()) if (LIVE/'response.json').exists() else {}
meta=json.loads((LIVE/'run.json').read_text())
old_response=json.loads((OLD/'response.json').read_text())
usage=response.get('usage')
summary={
    'outcome':result['editor_status'] if result else None,'candidate_generated':bool(result and result['candidate_text'] is not None),
    'validation':json.loads((LIVE/'validation.json').read_text()),'technical_failure':error,
    'new_api_attempts':len(calls),'editor_attempts_including_original':2,
    'request_identical_to_original':True,'parent_plan_messages_config_identical':True,
    'failure_feedback_added':False,'patch_repaired':False,'automatic_retries':0,
    'original_failure_and_upstream_archives_unchanged':True,'implementation_unchanged':True,
    'reuse_verified':reuse,'failed_result_reuse_rejected':failure_refused,'additional_reuse_calls':0,
    'finish_reason':response.get('finish_reason'),'response_model':response.get('response_model'),'usage':usage,
    'elapsed_seconds':(datetime.fromisoformat(meta['finished_at'])-datetime.fromisoformat(meta['started_at'])).total_seconds(),
    'total_tokens_including_original':old_response['usage']['total_tokens']+usage['total_tokens'] if usage else None,
    'monetary_cost':None,'monetary_cost_note':'API does not report a billed monetary amount; no estimate made.',
    'tests':'Unchanged implementation; prior 384 tests and 19 subtests passed. Not rerun for this identical request.',
    'new_environment_episodes':0,'upstream_calls':0,'behavioral_improvement_validated':False}
write_record(EXP/'results/summary.json',summary)
print(json.dumps(summary,indent=2),flush=True)
if error:raise SystemExit(1)

"""One-shot Editor verification. Run from repository root with PYTHONPATH=.
At most one real call; refuses existing live output, never runs an environment.
"""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv
from src.adapters.alfworld.skill_runtime import write_record
from src.skill_evolution.v23 import editor
from src.skill_evolution.v23.preconditioner import load_preconditioner

ROOT=Path('artifacts/methods/v23/v23_editor_001')
EXP=Path('experiments/methods/v23/v23_editor_001')
LIVE=ROOT/'live'
PRE=Path('artifacts/methods/v23/v23_preconditioner_001/live')
assert not LIVE.exists(), 'Never retry this recorded experiment'
assert '384 passed, 19 subtests passed' in (ROOT/'offline_tests.txt').read_text()
load_dotenv('.env',override=False)
assert os.environ.get('OPENAI_API_KEY')
base_url=os.environ['OPENAI_BASE_URL']
assert urlparse(base_url).hostname=='api.deepseek.com'
config=editor.call_configuration(base_url=base_url,model='deepseek-flash',max_tokens=16384,timeout=300)
assert config==json.loads((PRE/'run.json').read_text())['call_config']
saved=load_preconditioner(PRE)
payload=editor.editor_input(saved); messages=editor.messages_for(saved)
assert set(payload)=={'parent','plan'} and payload['parent'] is None
assert len(payload['plan']['updates'])==len(payload['plan']['checks'])==3
assert saved['preconditioner']['adjustments']==[] and saved['preconditioner']['checks'] is None
assert [s['task_id'] for s in saved['sources']]==[f'train:{i:04}' for i in range(12,16)]
size=len(json.dumps(messages,ensure_ascii=False));assert size<=100000
(EXP/'results').mkdir(parents=True,exist_ok=True)

def snapshot(directory):
    return {str(p.relative_to(directory)):p.read_bytes() for p in directory.rglob('*') if p.is_file()}

upstreams={'preconditioner':PRE,
           'grouping':Path('artifacts/methods/v23/v23_prompt_alignment_001/grouping'),
           'diagnosis':Path('artifacts/methods/v23/v23_prompt_alignment_001/diagnosis')}
old={name:snapshot(path) for name,path in upstreams.items()}
for name,files in old.items():
    for file,data in files.items():
        path=ROOT/'original_archives'/name/file;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
source_dir=EXP/'config/source';source_dir.mkdir()
for name in ('editor.py','editor_prompt.md','preconditioner.py','preconditioner_prompt.md','grouping.py','grouping_prompt.md','diagnosis.py','diagnosis_prompt.md','facts.py','prompts.py','execution_context.md'):
    (source_dir/name).write_bytes((Path('src/skill_evolution/v23')/name).read_bytes())
write_record(EXP/'config/plan.json',{
    'frozen_at':datetime.now(timezone.utc).isoformat(),'call_config':config,'preconditioner_directory':str(PRE),'output_directory':str(LIVE),
    'tasks':[s['task_id'] for s in saved['sources']],'parent':None,'effective_updates':3,'effective_checks':3,
    'input_fields':['parent','plan'],'input_chars':size,'max_input_chars':100000,
    'max_calls':1,'automatic_retries':0,'upstream_calls':0,'new_environment_episodes':0,
    'semantic_check_criteria':[
        'implement all effective Updates, preserving conditions, scope, strength and dependencies',
        'do not change the effective behavioral strategy or silently approximate unavailable history',
        'avoid duplicating base protocol and modifying unrelated guidance',
        'nonempty patch must strictly apply to the exact Parent; application does not prove fidelity',
        'empty patch requires all effective requirements already satisfied',
        'null patch requires a specific reasonable blocker needing upstream semantic revision',
        'all three legitimate outcomes allowed; no prescribed result for the current Updates',
        'report semantic flaws without special-case Prompt changes or resampling']})
write_record(ROOT/'frozen_input.json',payload)
write_record(ROOT/'frozen_messages.json',messages)
print(f'Offline tests passed; configuration and input frozen ({size} characters). Starting the ONLY Editor call.',flush=True)
generate=editor.live_generator(base_url=base_url,key=os.environ['OPENAI_API_KEY'],model='deepseek-flash',max_tokens=16384,timeout=300)
error=None;result=None
try:
    result=editor.run_editor(PRE,LIVE,generate=generate,max_input_chars=100000,call_config=config)
except (Exception,KeyboardInterrupt) as exc:
    error=type(exc).__name__
    print('Editor stopped with a technical failure; no retry: '+error,flush=True)

assert all(snapshot(path)==old[name] for name,path in upstreams.items())
assert all(p.read_bytes()==(Path('src/skill_evolution/v23')/p.name).read_bytes() for p in source_dir.iterdir())
meta=json.loads((LIVE/'run.json').read_text())
response=json.loads((LIVE/'response.json').read_text()) if (LIVE/'response.json').exists() else {}
request=json.loads((LIVE/'request.json').read_text())
assert request['attempts']==1 and request['body']['messages']==messages
assert meta['call_config']==config
reuse=False
if result is not None:
    before=snapshot(LIVE)
    def forbidden(*_):raise AssertionError('Additional request forbidden')
    assert editor.run_editor(PRE,LIVE,generate=forbidden,call_config=config)==result
    assert snapshot(LIVE)==before
    reuse=True
    for name in ('editor.json','patch.diff','candidate.md','actual.diff'):
        if (LIVE/name).exists():(EXP/'results'/name).write_bytes((LIVE/name).read_bytes())
summary={
    'tests':{'passed':384,'editor_tests':100,'subtests':19,'failed':0,'skipped':0},
    'outcome':None if result is None else result['editor_status'],
    'candidate_generated':result is not None and result['candidate_text'] is not None,
    'validation':json.loads((LIVE/'validation.json').read_text()),'technical_failure':error,
    'input_chars':size,'api_attempts':request['attempts'],'response_model':response.get('response_model'),
    'finish_reason':response.get('finish_reason'),'usage':response.get('usage'),
    'elapsed_seconds':(datetime.fromisoformat(meta['finished_at'])-datetime.fromisoformat(meta['started_at'])).total_seconds(),
    'reuse_verified':reuse,'additional_reuse_calls':0,'upstream_archives_unchanged':True,
    'prompt_and_source_snapshots_unchanged':True,'upstream_calls':0,'new_environment_episodes':0,
    'behavioral_improvement_validated':False,'monetary_cost':None,
    'monetary_cost_note':'API reports Token usage, not a billed monetary amount; no estimate made.'}
write_record(EXP/'results/summary.json',summary)
print(json.dumps(summary,indent=2),flush=True)
if error:raise SystemExit(1)

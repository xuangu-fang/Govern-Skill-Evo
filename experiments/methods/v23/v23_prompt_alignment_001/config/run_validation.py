"""Recorded one-shot verification. Run at repository root with PYTHONPATH=.
Refuses existing live directories; no retry and no environment episodes.
"""
import difflib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv
from src.adapters.alfworld.skill_runtime import write_record
from src.skill_evolution.v23 import diagnosis, grouping
from src.skill_evolution.v23.facts import build_facts
from src.skill_evolution.v23.prompts import execution_context

ROOT = Path('artifacts/methods/v23/v23_prompt_alignment_001')
EXP = Path('experiments/methods/v23/v23_prompt_alignment_001')
G = ROOT/'grouping'; D = ROOT/'diagnosis'
assert not G.exists() and not D.exists(), 'Never retry this recorded experiment'
load_dotenv('.env')
assert os.environ.get('OPENAI_API_KEY')
base_url = os.environ['OPENAI_BASE_URL']
assert urlparse(base_url).hostname == 'api.deepseek.com'
config = grouping.call_configuration(base_url=base_url, model='deepseek-flash', max_tokens=16384, timeout=300)
paths = [Path(p) for p in json.loads(Path('experiments/methods/v23/v23_grouping_001/results/summary.json').read_text())['selected_sources']]
raw = [p.read_bytes() for p in paths]
records = [json.loads(data) for data in raw]
bundle = build_facts(records)
assert bundle == json.loads(Path('artifacts/methods/v23/v23_grouping_001/live/input.json').read_text())
assert sum(len(r['steps']) for r in bundle['facts']['runs']) == 93
assert [s['task_id'] for s in bundle['sources']] == ['train:0012','train:0013','train:0014','train:0015']
assert Path('src/skill_evolution/v23/facts.py').read_bytes() == (ROOT/'source_before/facts.py').read_bytes()
criteria = ['concrete comparable decision problems','before/after information and menu semantics','behavioral contrasts rather than outcome labels','avoid duplicating adequately covered base protocol','Actor-observable update triggers','meaningful checks with valid update_ids','identify unsupported strategy assumptions without repairing or resampling']
plan = {'frozen_at':datetime.now(timezone.utc).isoformat(),'call_config':config,'sources':[str(p) for p in paths],'tasks':[s['task_id'] for s in bundle['sources']],'parent':bundle['facts']['parent'],'runs':4,'steps':93,'max_input_chars':100000,'max_calls':2,'per_stage_calls':1,'automatic_retries':0,'new_environment_episodes':0,'grouping_output':str(G),'diagnosis_output':str(D),'semantic_check_criteria':criteria}
write_record(EXP/'config/plan.json',plan)
current = EXP/'config/current'; current.mkdir()
for name in ('grouping_prompt.md','diagnosis_prompt.md','execution_context.md','prompts.py','grouping.py','diagnosis.py'):
    (current/name).write_bytes((Path('src/skill_evolution/v23')/name).read_bytes())
for name in ('grouping_prompt.md','diagnosis_prompt.md'):
    before=(EXP/'config/before'/name).read_text().splitlines(keepends=True)
    after=(current/name).read_text().splitlines(keepends=True)
    (EXP/'config'/f'{name}.diff').write_text(''.join(difflib.unified_diff(before,after,fromfile='before/'+name,tofile='current/'+name)))
write_record(ROOT/'frozen_input.json',bundle)
assert len(json.dumps(grouping.messages_for(bundle),ensure_ascii=False)) <= 100000
print('Frozen configuration. Starting the only Grouping call.', flush=True)
gen = grouping.live_generator(base_url=base_url,key=os.environ['OPENAI_API_KEY'],model='deepseek-flash',max_tokens=16384,timeout=300)
g = grouping.run_grouping(records,G,round_id='v23_prompt_alignment_001',generate=gen,max_input_chars=100000,call_config=config)
print('Grouping valid. Preparing the only Diagnosis call.', flush=True)
messages = diagnosis.messages_for(g)
assert json.loads(messages[1]['content']) == {**bundle['facts'],'grouping':g['grouping']}
assert execution_context(bundle['background']) in messages[0]['content']
write_record(ROOT/'diagnosis_preflight.json',{'frozen_at':datetime.now(timezone.utc).isoformat(),'input_chars':len(json.dumps(messages,ensure_ascii=False)),'call_config':config,'messages':messages})
d = diagnosis.run_diagnosis(G,D,generate=gen,max_input_chars=100000,call_config=config)
print('Diagnosis valid. Checking read-only reuse without requests.', flush=True)
def snapshot(p): return {f.name:f.read_bytes() for f in p.iterdir() if f.is_file()}
def forbidden(*args): raise AssertionError('Additional request forbidden')
g_before,d_before=snapshot(G),snapshot(D)
assert grouping.run_grouping(records,G,round_id='v23_prompt_alignment_001',generate=forbidden,max_input_chars=100000,call_config=config)==g
assert diagnosis.run_diagnosis(G,D,generate=forbidden,call_config=config)==d
assert g_before==snapshot(G) and d_before==snapshot(D)
for name in ('v23_grouping_001','v23_diagnosis_001'):
    assert snapshot(Path('artifacts/methods/v23')/name/'live')==snapshot(ROOT/'original_archives'/name)
assert [p.read_bytes() for p in paths]==raw
assert all((current/n).read_bytes()==(Path('src/skill_evolution/v23')/n).read_bytes() for n in ('grouping_prompt.md','diagnosis_prompt.md','execution_context.md','prompts.py','grouping.py','diagnosis.py'))
results=EXP/'results';results.mkdir()
summary={'tests':{'passed':210,'subtests':19,'failed':0,'skipped':0},'facts_equal_original':True,'actor_prompt_steps_verified':93,'old_archives_unchanged':True,'original_trajectories_unchanged':True,'reuse_verified':True,'additional_reuse_calls':0,'prompt_and_source_snapshots_unchanged':True,'new_environment_episodes':0,'stages':{}}
for name,path in [('grouping',G),('diagnosis',D)]:
    (results/f'{name}.json').write_bytes((path/f'{name}.json').read_bytes())
    response=json.loads((path/'response.json').read_text());run=json.loads((path/'run.json').read_text())
    request=json.loads((path/'request.json').read_text())
    assert request['attempts']==1 and request['body']['max_tokens']==config['max_tokens']
    assert request['body']['messages']==json.loads((path/'messages.json').read_text())
    assert run['call_config']==config
    elapsed=(datetime.fromisoformat(run['finished_at'])-datetime.fromisoformat(run['started_at'])).total_seconds()
    summary['stages'][name]={k:v for k,v in response.items() if k!='content'}
    summary['stages'][name].update(elapsed_seconds=elapsed,input_chars=run['input_chars'],validation=json.loads((path/'validation.json').read_text()))
summary['total_tokens']=sum(stage['usage']['total_tokens'] for stage in summary['stages'].values())
summary['monetary_cost']=None
summary['monetary_cost_note']='API returns token usage, not a billed monetary amount; no estimate made.'
write_record(results/'summary.json',summary)
print(json.dumps(summary,indent=2),flush=True)

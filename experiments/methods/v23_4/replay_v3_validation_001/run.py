"""One isolated Prompt-only comparison, using the existing bounded runner."""
from copy import deepcopy
from pathlib import Path
import json
import sys

from experiments.methods.v23_4.semantic_generation_001 import run as core
from src.skill_evolution.v23 import memory

HERE=Path(__file__).resolve().parent
ROOT=core.ROOT
core.HERE=HERE
NEW=memory.MULTI_KNOWLEDGE_CONTRACT
P6=HERE.with_name('multi_knowledge_p6_001')
P4=HERE.with_name('multi_knowledge_p4_001')
VERSION='v23_4_replay_v3_user_candidate'
PROMPT=HERE/'v23_4_replay.md'

def inputs(label,stage):
    assert label in ('R05','R06') and stage=='replay'
    return core.read(P4/f'cases/{label}/replay_bundle.json'),core.read(HERE/f'config/{label}/messages.json')

def validate(stage,parsed,material):
    assert stage=='replay'
    memory.validate_entries(parsed,material['payload'],memory_contract=NEW)
    return {'replay':parsed}

core.inputs=inputs
core.validate=validate

def prepare():
    p6freeze=core.read(P6/'config/freeze.json')
    assert all(core.sha(ROOT/p)==d for p,d in p6freeze['sha256'].items())
    _,cfg=core.configuration();assert cfg==p6freeze['call_config']
    old=core.replay.LEARNING_PROMPT_PATH.read_text();new=PROMPT.read_text()
    comparisons={}
    for label in ('R05','R06'):
        selected=core.read(P6/f'runs/{label}_replay/selected.json')['attempt']
        origin=P6/f'runs/{label}_replay/attempt_{selected:03}/http/request.json'
        prior=core.read(origin);messages=deepcopy(prior['body']['messages'])
        assert messages==core.read(P4/f'cases/{label}/messages.json')
        prefix=old.rstrip();assert messages[0]['content'].startswith(prefix+'\n\n')
        suffix=messages[0]['content'][len(prefix):]
        messages[0]['content']=new.rstrip()+suffix
        assert messages[1:]==prior['body']['messages'][1:]
        assert messages[0]['content'][len(new.rstrip()):]==suffix
        expected={k:v for k,v in cfg.items() if k not in ('endpoint','timeout_seconds')}
        assert {k:v for k,v in prior['body'].items() if k!='messages'}==expected
        memory.validate_entries(core.read(origin.parents[1]/'parsed.json'),inputs_bundle(label)['payload'],memory_contract=NEW)
        core.save(HERE/f'config/{label}/messages.json',messages)
        comparisons[label]={'baseline_http_request':str(origin.relative_to(ROOT)),
          'baseline_attempt':selected,'user_message_unchanged':True,'system_suffix_unchanged':True,
          'only_learning_prompt_replaced':True,'baseline_system_chars':len(prior['body']['messages'][0]['content']),
          'candidate_system_chars':len(messages[0]['content']),'user_chars':len(messages[1]['content'])}
    core.save(HERE/'config/INPUT_COMPARISON.json',comparisons)
    protected=core.read(HERE.with_name('replay_layered_diagnostic_001')/'protected_before.json')
    assert all(core.sha(ROOT/p)==d for p,d in protected.items())
    for folder in (P6,P4,HERE.with_name('replay_layered_diagnostic_001'),HERE.with_name('conditional_learning_001')):
        protected.update({str(p.relative_to(ROOT)):core.sha(p) for p in core.archive_glob(folder, '*', recursive=True) if p.is_file()})
    core.save(HERE/'protected_before.json',protected)
    frozen=dict(p6freeze['sha256'])
    files=[*HERE.glob('*.py'),PROMPT,HERE/'PROTOCOL.md',HERE/'DESIGN.md',*core.archive_glob(HERE/'config', '*.json', recursive=True)]
    frozen.update({str(p.relative_to(ROOT)):core.sha(p) for p in files})
    core.save(HERE/'config/freeze.json',{'at':core.now(),'prompt_version':VERSION,'memory_contract':NEW,
       'call_config':cfg,'max_restarts':3,'max_logical_calls':2,'max_http_attempts':8,'sha256':frozen})
    core.verify();print(json.dumps(comparisons,ensure_ascii=False))

def inputs_bundle(label):return core.read(P4/f'cases/{label}/replay_bundle.json')

def audit():
    core.verify();protected=core.read(HERE/'protected_before.json')
    assert all(core.sha(ROOT/p)==d for p,d in protected.items())
    cases={}
    for label in ('R05','R06'):
        attempts=[];cfg=core.read(HERE/'config/freeze.json')['call_config']
        for p in core.archive_glob(HERE/f'runs/{label}_replay', 'attempt_*'):
            a=core.read(p/'attempt.json');r=core.read(p/'http/request.json')
            expected={k:v for k,v in cfg.items() if k not in ('endpoint','timeout_seconds')}
            expected.update(messages=inputs(label,'replay')[1],max_tokens=a['max_tokens'])
            assert r['body']==expected and r['endpoint']==cfg['endpoint'] and r['transport_retries']==0
            response=core.read(p/'response.json') if core.resolve(p/'response.json').exists() else {}
            attempts.append({**a,'usage':response.get('usage'),'finish_reason':response.get('finish_reason')})
        assert len(attempts)<=4
        if core.resolve(HERE/f'runs/{label}_replay/selected.json').exists():core.load(label,'replay')
        cases[label]=attempts
    total={k:sum((a.get('usage') or {}).get(k,0) for aa in cases.values() for a in aa) for k in ('prompt_tokens','completion_tokens','total_tokens')}
    result={'cases':cases,'usage':total,'http_attempts':sum(map(len,cases.values())),
        'protected_files_unchanged':len(protected),'prompt_version':VERSION,'production_defaults_unchanged':True}
    (HERE/'AUDIT.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False))

if __name__=='__main__':
    if sys.argv[1:]==['prepare']:prepare()
    elif sys.argv[1:]==['audit']:audit()
    elif sys.argv[1:]==['run']:
        failures=[]
        for label in ('R05','R06'):
            try:core.run(label,'replay')
            except Exception as e:failures.append({'case':label,'error_type':type(e).__name__,'error':str(e)})
        if failures:core.save(HERE/'failures.json',failures);raise SystemExit('Bounded run failed; see failures.json')
    else:raise SystemExit('prepare | run | audit')

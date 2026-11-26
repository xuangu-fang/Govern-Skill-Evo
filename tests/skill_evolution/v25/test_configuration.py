import ast
from copy import deepcopy
import json
from pathlib import Path
import pytest
from src.skill_evolution.v25 import evolution as ev
from src.skill_evolution.v25.config import method_config, KNOWLEDGE_REVIEW
from src.skill_evolution.v25.benchmark import using_benchmark
from src.skill_evolution.v25.benchmarks.spreadsheetbench.adapter import SpreadsheetBenchAdapter
from src.skill_evolution.v25.benchmarks.spreadsheetbench import protocol,scoring,evidence
from src.skill_evolution.v25.contracts.gate import decide_gate
from .support import config,ActorResponses,MethodResponses,fast_execute

ROOT=Path(__file__).resolve().parents[3]
CANDIDATE=ROOT/'experiments/methods/v25/v25_spreadsheetbench_verified400_rc1'


def test_candidate_config_and_frozen_prompts():
    c=ev.read(CANDIDATE/'config/campaign.json');a=SpreadsheetBenchAdapter()
    with using_benchmark(a), pytest.raises(ValueError, match='method freeze'):
        ev.validate_config(c)
    c['method']=method_config(KNOWLEDGE_REVIEW)  # Local fixture only; the frozen candidate stays unchanged.
    with using_benchmark(a):ev.validate_config(c)
    split=ev.read(CANDIDATE/'data/splits.json')
    assert len(split['optimization'])==120 and len(split['test'])==280
    for s in ['train','val','test']:
        original=ev.read(ROOT/f'external/SkillOpt/data/spreadsheetbench_id_split/{s}/items.json')
        assert [c['task_items'][t]['dataset_id'] for t in split[s]]==[str(t['id']) for t in original]
    assert split['optimization']==split['train']+split['val']
    for p in protocol.PROMPTS.glob('*.md'):assert p.read_bytes()==(ROOT/'docs/methods/v25/prompts'/p.name).read_bytes()
    assert (CANDIDATE/'config/initial_skill.md').read_bytes()==(ROOT/'external/SkillOpt/skillopt/envs/spreadsheetbench/skills/initial.md').read_bytes()
    assert {x['task_id'] for x in c['dataset']['metadata_issues']}=={'test:283-32','test:73-45','test:60-7'}
    for t in split['optimization']:scoring.regions(c['task_items'][t]['answer_region'])


def test_no_old_version_imports_or_domain_resources():
    for p in (ROOT/'src/skill_evolution/v25').rglob('*.py'):
        tree=ast.parse(p.read_text())
        for node in ast.walk(tree):
            modules=[node.module or ''] if isinstance(node,ast.ImportFrom) else [x.name for x in node.names] if isinstance(node,ast.Import) else []
            for name in modules:
                assert not any(x in name for x in ('v23','v24','alfworld','skillopt','skilladam')),(p,name)
    a=SpreadsheetBenchAdapter()
    with pytest.raises(ValueError):a.resource('../unknown.md')
    with pytest.raises(ValueError):a.evidence('unknown')


def test_formal_size_tie_never_uses_auxiliary_score():
    rows=[{'task_id':str(i),'parent':{'run_id':'p'+str(i),'success':i<7},'candidate':{'run_id':'q'+str(i),'success':i<7}} for i in range(15)]
    result=decide_gate({'pairs':rows},[str(i) for i in range(15)])
    assert result=={'decision':'RETAIN','parent_success':7,'candidate_success':7,'compared':15}


def test_actor_campaign_resume_reuses_same_directory_and_budget(tmp_path):
    cfg=config(tmp_path/'data',n=1);calls=[];root=tmp_path/'campaign';m=MethodResponses();normal=ActorResponses()
    def generate(*args):
        calls.append(1)
        if len(calls)==1:raise KeyboardInterrupt()
        return normal(*args)
    a=SpreadsheetBenchAdapter(generate=generate,execute=fast_execute)
    with using_benchmark(a):
        with pytest.raises(KeyboardInterrupt):ev.run_campaign(root,config=cfg,generate=m,actor_runner=a.actor_task)
        states=list(root.rglob('actor_state.json'));rid=ev.read(states[0])['run_id']
        ev.run_campaign(root,resume=True,generate=m,actor_runner=a.actor_task)
        record=ev.read(states[0]);assert record['run_id']==rid and record['api_requests']==2
        assert len(list((states[0].parent.parent).glob('[0-9]*')))==1
        assert len(calls)==3


def test_test_split_rejected_from_learning(tmp_path):
    c=config(tmp_path/'data',n=1,test=1);a=SpreadsheetBenchAdapter(generate=ActorResponses(),execute=fast_execute)
    with pytest.raises(ValueError,match='outside'):a.actor_task(c['test_tasks'][0],None,tmp_path/'run',c)
    modified=deepcopy(c);modified['batches'][0].append(c['test_tasks'][0])
    with pytest.raises(ValueError,match='Split'):a.validate_config(modified)


def test_inherited_request_and_method_budgets():
    c=ev.read(CANDIDATE/'config/campaign.json')
    baseline=ev.read(ROOT/'experiments/methods/v24/candidates/v24_alfworld_verified_feedback_001_rc1/config/campaign.json')
    for key in ('actor_model','actor_base_url','call_config','module_max_tokens','actor_request_attempts','max_attempts','max_input_chars','max_message_utf8_bytes','retry_delay_seconds','continue_no_change'):
        assert c[key]==baseline[key],key
    assert c['actor_profile']['actor_max_output_tokens']==baseline['call_config']['max_tokens']
    assert c['actor_profile']['request_timeout_seconds']==baseline['call_config']['timeout_seconds']


@pytest.mark.parametrize('actor_tokens',[32768,49152])
def test_actor_profile_changes_only_actor_output_budget(actor_tokens):
    original=ev.read(CANDIDATE/'config/campaign.json');cfg=deepcopy(original)
    cfg['method']=method_config(KNOWLEDGE_REVIEW)
    cfg['actor_profile']['actor_max_output_tokens']=actor_tokens
    adapter=SpreadsheetBenchAdapter()
    with using_benchmark(adapter):ev.validate_config(cfg)
    task=cfg['task_items'][cfg['batches'][0][0]]
    messages=protocol.initial_messages(task,cfg['initial_skill']['text'],'synthetic preview',cfg['actor_profile'])
    assert str(actor_tokens) in messages[0]['content']
    for stage in ev.enabled_modules(cfg):assert ev.stage_call_config(cfg,stage)==ev.stage_call_config(original,stage)
    cfg['actor_profile']['max_code_attempts']=31
    with pytest.raises(ValueError,match='profile differs'):adapter.validate_config(cfg)


def test_new_configuration_module_budgets_and_legacy_archive_unchanged(tmp_path):
    path=CANDIDATE/'config/campaign.json';before=path.read_bytes()
    cfg=config(tmp_path/'data',n=1)
    expected={'grouping':16384,'diagnosis':32768,'preconditioner':49152,'editor':16384,
              'replay':49152,'verifier':49152,'repair':32768}
    with using_benchmark(SpreadsheetBenchAdapter()):ev.validate_config(cfg)
    assert cfg['actor_profile']['actor_max_output_tokens']==49152
    assert {name:ev.stage_call_config(cfg,name)['max_tokens'] for name in expected}==expected
    assert cfg['call_config']['max_tokens']==16384 and cfg['call_config']['timeout_seconds']==300
    legacy=ev.read(path)
    assert legacy['actor_profile']['actor_max_output_tokens']==16384
    assert ev.stage_call_config(legacy,'diagnosis')['max_tokens']==16384
    assert path.read_bytes()==before


@pytest.mark.parametrize('tokens',[0,-1,True,'49152',49153,65536])
def test_formal_actor_budget_rejects_unapproved_values(tokens):
    cfg=ev.read(CANDIDATE/'config/campaign.json')
    cfg['actor_profile']['actor_max_output_tokens']=tokens
    with pytest.raises(ValueError):SpreadsheetBenchAdapter().validate_config(cfg)


def test_unlimited_task_profile_and_legacy_prompt_compatibility():
    cfg=ev.read(CANDIDATE/'config/campaign.json');adapter=SpreadsheetBenchAdapter()
    cfg['method']=method_config(KNOWLEDGE_REVIEW)
    task=cfg['task_items'][cfg['batches'][0][0]];profile=cfg['actor_profile']
    old=CANDIDATE/'config/actor_system.md'
    legacy=protocol.render(old.read_text(),{**profile,'skill':cfg['initial_skill']['text']})
    assert protocol.initial_messages(task,cfg['initial_skill']['text'],'preview',profile)[0]['content']==legacy
    profile['actor_task_timeout_seconds']=0
    with using_benchmark(adapter):ev.validate_config(cfg)
    background=protocol.background(profile);context=protocol.execution_context(background)
    assert 'no cumulative Actor task time limit' in context
    assert 'bounded by remaining task time' not in context
    for invalid in (-1,None,True):
        profile['actor_task_timeout_seconds']=invalid
        with pytest.raises(ValueError):adapter.validate_config(cfg)


@pytest.mark.parametrize('dimension',['D','S','C'])
def test_preconditioner_modifies_update_preserving_identity(dimension):
    from src.skill_evolution.v25.update_patch import normalize_update_patches
    from src.skill_evolution.v25.contracts.memory import empty_memory
    example=ev.read(ROOT/'docs/methods/v25/prompt_review/preconditioner_example.json');p=example['input'];p['memory']=empty_memory()
    old=p['plan']['updates'][0]['text'];new=old+'- Check the requested output coverage before saving.\n'
    patch='--- a/SKILL.md\n+++ b/SKILL.md\n@@\n'+''.join(' '+line for line in old.splitlines(keepends=True))+'+- Check the requested output coverage before saving.\n'
    result={'adjustments':[{'target':'u1','focus':[dimension],'change':'Include an output-coverage check.','reason':'`Evidence:P1:1` provides the loop boundary evidence.','to':{'patch':patch}}],'checks':None}
    with using_benchmark(SpreadsheetBenchAdapter()):
        _,effective=normalize_update_patches(result,p)
    assert effective['updates'][0]['id']=='u1' and effective['updates'][0]['text']==new
    assert effective['checks']==p['plan']['checks']

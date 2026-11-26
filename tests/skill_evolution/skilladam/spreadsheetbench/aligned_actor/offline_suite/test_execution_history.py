"""Temporary generation repair is auditable but absent from evolution evidence."""
from copy import deepcopy
import json
from pathlib import Path
import re

import pytest

from src.skill_evolution.skilladam.spreadsheetbench.aligned_actor.actor_runtime.benchmarks.spreadsheetbench import actor, evidence, facts, protocol, timeline, transport
from src.skill_evolution.skilladam.spreadsheetbench.aligned_actor.actor_runtime.benchmarks.spreadsheetbench.adapter import SpreadsheetBenchAdapter
from .support import config, response, fast_execute, CODE, PARENT


def setup(tmp_path, **kwargs):
    cfg=config(tmp_path/'data',n=1,**kwargs)
    cfg['actor_profile'].update(actor_task_timeout_seconds=0,attempt_budget_policy='program_executions_v1',
                                actor_history_policy=protocol.EXECUTION_HISTORY)
    return cfg,next(iter(cfg['task_items'].values()))


def good():return response('```python\n'+CODE%' + 1'+'```')
def forbidden(*args):pytest.fail('Unexpected model request, execution or score')
def saved(tmp_path):return json.loads((tmp_path/'run/actor_state.json').read_text())
def runtime_error():return dict(status='error',exit_status=1,output_openable=False,
    error_category='execution_error',error_detail='VISIBLE_RUNTIME',stderr='FULL_RUNTIME_LOG',stdout='')


def test_latest_format_repair_is_temporary_and_actual_execution_feedback_remains(tmp_path):
    cfg,task=setup(tmp_path);calls=[];executions=[]
    outputs=[response('INVALID_A'),response('INVALID_B'),good(),good()]
    def generate(messages,*args):calls.append(deepcopy(messages));return outputs.pop(0)
    def execute(*args):
        executions.append(1)
        return runtime_error() if len(executions)==1 else fast_execute(*args)
    record=json.loads(actor.run(task,PARENT,tmp_path/'run',cfg,generate=generate,execute=execute).read_text())
    assert calls[1][-2]['content']=='INVALID_A' and calls[2][-2]['content']=='INVALID_B'
    assert 'INVALID_A' not in json.dumps(calls[2])
    assert all('INVALID_' not in json.dumps(x) for x in (calls[3],record['messages']))
    assert 'VISIBLE_RUNTIME' in calls[3][-1]['content']
    assert record['format_repair'] is None
    assert (record['code_attempts'],record['api_requests'])==(2,4)
    assert [a['response_in_history'] for a in record['attempts']]==[False,False,True,True]
    assert all(a['feedback_to_actor'] is None for a in record['attempts'][:2])
    for request,actual in zip(record['requests'],calls):
        assert request['messages']==actual==json.loads((tmp_path/'run'/request['path']/'messages.json').read_text())
    view=facts.build_facts([record])['facts'];run=view['runs'][0]
    assert [a['ref'] for a in run['attempts']]==['P1:3','P1:4']
    assert 'INVALID_' not in json.dumps(view) and 'Previous Program Validation Error' not in json.dumps(view)
    assert 'FULL_RUNTIME_LOG' in json.dumps(view) and 'VISIBLE_RUNTIME' in json.dumps(view)
    assert not {'api_requests','generation_responses'} & set(run['outcome'])
    assert run['attempts'][0]['request_messages']==calls[0]!=calls[2]
    assert timeline.restore(timeline.project(view))==view
    evidence.validate_run(run)
    candidate=evidence.relabel(run,'Q1');evidence.validate_run(candidate)
    assert [a['ref'] for a in candidate['attempts']]==['Q1:3','Q1:4']
    assert candidate['outcome']['submitted_attempt']=='Q1:4'
    bad=deepcopy(candidate);bad['attempts'][1]['ref']='Q1:3'
    with pytest.raises(ValueError,match='attempt reference'):evidence.validate_run(bad)
    single={'source_records':{'P1:3':{'record':run['attempts'][0]}}}
    projected=timeline.model_messages([{'role':'system','content':'review'},
                                       {'role':'user','content':json.dumps(single)}])
    assert timeline.EXECUTION_INSTRUCTION in projected[0]['content']
    assert json.loads(projected[1]['content'])==single
    assert 'INVALID_' not in projected[1]['content']
    with pytest.raises(ValueError,match='Unknown execution reference'):
        evidence.validate_grouping({'groups':[dict(group_id='G1',members=['P1'],
            decision_problem='P1:1',shared_basis='P1:3',important_differences=[])]},view)


def test_technical_empty_and_truncated_retry_the_existing_format_request(tmp_path):
    cfg,task=setup(tmp_path);calls=[]
    def generate(messages,*args):
        calls.append(deepcopy(messages));n=len(calls)
        if n==1:return response('FORMAT_SENTINEL')
        if n==2:raise transport.RequestError('NETWORK_SENTINEL')
        if n==3:return {**response('TRUNCATED_SENTINEL'),'finish_reason':'length'}
        if n==4:return response('   ')
        return good()
    record=json.loads(actor.run(task,PARENT,tmp_path/'run',cfg,generate=generate,execute=fast_execute).read_text())
    assert calls[1]==calls[2]==calls[3]==calls[4]
    assert record['api_requests']==5 and record['program_executions']==1
    view=facts.build_facts([record])['facts']
    assert 'SENTINEL' not in json.dumps(view)
    assert record['attempts'][2]['execution']['status']=='empty_output'
    assert record['attempts'][2]['repair_feedback'] is None
    assert view['runs'][0]['attempts'][0]['ref']=='P1:4'


@pytest.mark.parametrize('invalid,diagnostic',[
    ('```python\nif\n```','invalid syntax'),
    ("```python\nINPUT_PATH = open('x')\n```",'Only simple top-level literal path bindings'),
])
def test_pre_execution_syntax_and_path_checks_use_temporary_repair(tmp_path,invalid,diagnostic):
    cfg,task=setup(tmp_path);calls=[]
    def generate(messages,*args):calls.append(deepcopy(messages));return response(invalid) if len(calls)==1 else good()
    record=json.loads(actor.run(task,PARENT,tmp_path/'run',cfg,generate=generate,execute=fast_execute).read_text())
    assert diagnostic in calls[1][-1]['content']
    assert record['program_executions']==1 and not record['attempts'][0]['executed']
    assert len(facts.build_facts([record])['facts']['runs'][0]['attempts'])==1


def test_empty_first_response_has_no_format_feedback_and_keeps_operation_timeouts(tmp_path):
    cfg,task=setup(tmp_path);calls=[];now=[0];limits=[]
    def generate(messages,path,timeout,config):
        calls.append(deepcopy(messages));limits.append(timeout);now[0]+=400
        return response('') if len(calls)==1 else good()
    def execute(code,inp,path,timeout,config):
        limits.append(timeout);return fast_execute(code,inp,path,timeout,config)
    record=json.loads(actor.run(task,PARENT,tmp_path/'run',cfg,generate=generate,execute=execute,clock=lambda:now[0]).read_text())
    assert calls[0]==calls[1] and limits==[300,300,600]
    assert record['elapsed_seconds']==800 and record['attempts'][0]['repair_feedback'] is None
    facts.build_facts([record])


@pytest.mark.parametrize('checkpoint',['response_saved','attempt_processed','execution_saved','submitted','score_saved'])
def test_resume_restores_temporary_context_without_duplicate_execution(tmp_path,checkpoint):
    cfg,task=setup(tmp_path);calls=[];executions=[];stopped=[]
    def generate(messages,*args):calls.append(deepcopy(messages));return response('BAD_FORMAT') if len(calls)==1 else good()
    def execute(*args):executions.append(1);return fast_execute(*args)
    def hook(name,state):
        if name==checkpoint and not stopped:stopped.append(1);raise KeyboardInterrupt()
    with pytest.raises(KeyboardInterrupt):
        actor.run(task,PARENT,tmp_path/'run',cfg,generate=generate,execute=execute,hook=hook)
    record=json.loads(actor.run(task,PARENT,tmp_path/'run',cfg,generate=generate,execute=execute).read_text())
    assert len(calls)==2 and executions==[1]
    assert calls[1][-2]['content']=='BAD_FORMAT'
    assert len(record['messages'])==3 and record['format_repair'] is None
    facts.build_facts([record])


def test_sixth_saved_response_uses_archived_repair_request(tmp_path):
    cfg,task=setup(tmp_path);calls=[]
    def generate(messages,*args):
        calls.append(deepcopy(messages));return response('FORMAT_'+str(len(calls))) if len(calls)<6 else good()
    def hook(name,state):
        if name=='response_saved' and len(state['requests'])==6:raise KeyboardInterrupt()
    with pytest.raises(KeyboardInterrupt):
        actor.run(task,PARENT,tmp_path/'run',cfg,generate=generate,execute=fast_execute,hook=hook)
    state=saved(tmp_path);state['requests'][-1]['response']=None
    (tmp_path/'run/actor_state.json').write_text(json.dumps(state))
    record=json.loads(actor.run(task,PARENT,tmp_path/'run',cfg,generate=forbidden,execute=fast_execute).read_text())
    assert record['api_requests']==6 and record['program_executions']==1
    assert record['attempts'][-1]['request_messages']==calls[-1]
    assert facts.build_facts([record])['facts']['runs'][0]['attempts'][0]['ref']=='P1:6'


def test_mixed_generation_failures_exhaust_six_without_scoring_or_reset(tmp_path):
    cfg,task=setup(tmp_path);calls=[]
    def generate(messages,*args):
        calls.append(deepcopy(messages));n=len(calls)
        if n in (1,4):raise transport.RequestError('temporary timeout')
        if n==2:return {**response('partial'),'finish_reason':'length'}
        if n==5:return response('')
        return response('bad_'+str(n))
    for _ in range(2):
        with pytest.raises(actor.GenerationExhausted):
            actor.run(task,PARENT,tmp_path/'run',cfg,generate=generate,execute=forbidden,score=forbidden)
    state=saved(tmp_path)
    assert len(calls)==6 and state['code_attempts']==0 and state['format_repair']['response']=='bad_6'
    assert state['status']=='generation_incomplete' and not state['actor_complete']
    assert state['messages']==state['initial_messages'] and 'score' not in state
    assert not (tmp_path/'run/trajectory.json').exists()
    with pytest.raises(ValueError,match='incomplete'):facts.build_facts([state])


def test_generation_budget_renews_only_after_execution_and_thirty_limit_remains(tmp_path):
    cfg,task=setup(tmp_path);calls=[];executions=[]
    def generate(*args):calls.append(1);return good() if len(calls)%6==0 else response('FORMAT_ONLY')
    def execute(*args):executions.append(1);return runtime_error()
    record=json.loads(actor.run(task,PARENT,tmp_path/'run',cfg,generate=generate,execute=execute).read_text())
    assert len(calls)==180 and len(executions)==30 and record['score']['hard']==0
    run=facts.build_facts([record])['facts']['runs'][0]
    assert len(run['attempts'])==30 and run['attempts'][-1]['ref']=='P1:180'
    assert run['attempts'][-1]['feedback_to_actor'] is None and run['outcome']['program_executions']==30
    assert 'FORMAT_ONLY' not in json.dumps(run)


def test_unknown_execution_outcome_still_blocks_rerun(tmp_path):
    cfg,task=setup(tmp_path);runs=[]
    def execute(*args):runs.append(1);raise KeyboardInterrupt()
    with pytest.raises(KeyboardInterrupt):
        actor.run(task,PARENT,tmp_path/'run',cfg,generate=lambda *a:good(),execute=execute)
    with pytest.raises(actor.Interrupted,match='no saved outcome'):
        actor.run(task,PARENT,tmp_path/'run',cfg,generate=forbidden,execute=execute,score=forbidden)
    assert runs==[1] and saved(tmp_path)['code_attempts']==1


@pytest.mark.parametrize('mutation',['request','repair','formal','counter','code'])
def test_raw_archive_tampering_is_rejected_before_projection(tmp_path,mutation):
    cfg,task=setup(tmp_path);outputs=[response('BAD_FORMAT'),good()]
    record=json.loads(actor.run(task,PARENT,tmp_path/'run',cfg,generate=lambda *a:outputs.pop(0),execute=fast_execute).read_text())
    if mutation=='request':record['requests'][1]['messages']=record['initial_messages']
    if mutation=='repair':record['attempts'][0]['repair_feedback']['content']='changed'
    if mutation=='formal':record['messages'].insert(2,{'role':'assistant','content':'BAD_FORMAT'})
    if mutation=='counter':record['api_requests']=1
    if mutation=='code':record['attempts'][1]['executed_code']='not the executed code'
    with pytest.raises(ValueError):facts.build_facts([record])


def test_new_policy_validation_and_no_in_place_protocol_migration(tmp_path):
    cfg,task=setup(tmp_path);adapter=SpreadsheetBenchAdapter();adapter.validate_config(cfg)
    new=protocol.initial_messages(task,PARENT,'preview',cfg['actor_profile'])
    context=protocol.execution_context(protocol.background(cfg['actor_profile']))
    assert 'temporary context' not in new[0]['content']
    assert 'every complete\nassistant response' not in context
    for key,value in [('actor_history_policy','unknown'),('attempt_budget_policy','responses_v1'),('actor_task_timeout_seconds',600)]:
        bad=deepcopy(cfg);bad['actor_profile'][key]=value
        with pytest.raises(ValueError):adapter.validate_config(bad)
    old=deepcopy(cfg);old['actor_profile'].pop('actor_history_policy')
    actor.run(task,PARENT,tmp_path/'run',old,generate=lambda *a:good(),execute=fast_execute)
    with pytest.raises(actor.Interrupted,match='conditions differ'):
        actor.run(task,PARENT,tmp_path/'run',cfg,generate=forbidden,execute=forbidden)


"""Generation failures cannot spend executions, fabricate scores or reset on resume."""
from copy import deepcopy
import json
from pathlib import Path
import pytest
from src.skill_evolution.v25.benchmarks.spreadsheetbench import actor, facts, protocol, timeline, transport
from src.skill_evolution.v25.benchmarks.spreadsheetbench.adapter import SpreadsheetBenchAdapter
from .support import config, response, fast_execute, CODE, PARENT


def setup(tmp_path):
    cfg=config(tmp_path/'data',n=1)
    cfg['actor_profile'].pop('actor_history_policy')  # Legacy evidence, separate execution budgets.
    cfg['actor_profile'].update(actor_task_timeout_seconds=0,attempt_budget_policy='program_executions_v1')
    return cfg,next(iter(cfg['task_items'].values()))


def good():return response('```python\n'+CODE%' + 1'+'```')
def truncated():return {**response('partial program'), 'finish_reason':'length'}
def state(tmp_path):return json.loads((tmp_path/'run/actor_state.json').read_text())
def forbidden(*args):pytest.fail('Unexpected API request, program execution or score')


def test_three_truncations_then_submission_is_one_execution(tmp_path):
    cfg,task=setup(tmp_path);calls=[];now=[0];waits=[];cfg['retry_delay_seconds']=2
    def generate(messages,*args):
        calls.append(deepcopy(messages));now[0]+=250
        return truncated() if len(calls)<=3 else good()
    from unittest.mock import patch
    with patch.object(actor.time,'sleep',side_effect=waits.append):
        record=json.loads(actor.run(task,PARENT,tmp_path/'run',cfg,generate=generate,execute=fast_execute,clock=lambda:now[0]).read_text())
    assert record['code_attempts']==record['program_executions']==1
    assert record['api_requests']==record['generation_responses']==4
    assert record['elapsed_seconds']==1000 and record['score']['hard']==1
    assert all(c==calls[0] for c in calls) and waits==[2,4,6]
    assert [a['response_in_history'] for a in record['attempts']]==[False,False,False,True]
    assert len(record['messages'])==3
    payload=facts.build_facts([record])['facts']
    assert timeline.restore(timeline.project(payload))==payload
    assert [a['ref'] for a in payload['runs'][0]['attempts']]==['P1:1','P1:2','P1:3','P1:4']


def test_transport_truncation_and_format_share_six_request_budget(tmp_path):
    cfg,task=setup(tmp_path);calls=[]
    def generate(messages,*args):
        calls.append(deepcopy(messages))
        n=len(calls)
        if n in (1,4):raise transport.RequestError('temporary')
        if n in (2,5):return truncated()
        return response('invalid complete response')
    for _ in range(2):
        with pytest.raises(actor.GenerationExhausted):
            actor.run(task,PARENT,tmp_path/'run',cfg,generate=generate,execute=forbidden,score=forbidden)
    saved=state(tmp_path)
    assert len(calls)==saved['api_requests']==6 and saved['code_attempts']==0
    assert saved['status']=='generation_incomplete' and saved['termination']=='generation_budget_exhausted'
    assert not saved['actor_complete'] and 'score' not in saved
    assert not (tmp_path/'run/trajectory.json').exists() and not (tmp_path/'run/score.json').exists()
    assert calls[0]==calls[1]==calls[2] and calls[3]==calls[4]==calls[5]
    assert calls[3][-2]['content']=='invalid complete response'
    assert 'code_attempts_used: 0' in calls[3][-1]['content']


def test_budget_renews_only_after_execution_and_stops_at_thirty(tmp_path):
    cfg,task=setup(tmp_path);calls=[];executions=[]
    def generate(*args):
        calls.append(1)
        return good() if len(calls)%6==0 else truncated()
    def execute(*args):
        executions.append(1)
        return dict(status='error',error_category='execution_error',error_detail='runtime error',exit_status=1,output_openable=False)
    record=json.loads(actor.run(task,PARENT,tmp_path/'run',cfg,generate=generate,execute=execute).read_text())
    assert len(calls)==record['api_requests']==180
    assert len(executions)==record['program_executions']==record['code_attempts']==30
    assert record['termination']=='budget_exhausted' and record['score']['hard']==0
    assert record['attempts'][-1]['feedback_to_actor'] is None
    payload=facts.build_facts([record])['facts']
    assert timeline.restore(timeline.project(payload))==payload


@pytest.mark.parametrize('checkpoint',['response_saved','attempt_processed','execution_saved','submitted','score_saved'])
def test_resume_does_not_repeat_consumed_response_or_execution(tmp_path,checkpoint):
    cfg,task=setup(tmp_path);calls=[];execs=[];stopped=[]
    def generate(*args):
        calls.append(1);return truncated() if len(calls)==1 else good()
    def execute(*args):execs.append(1);return fast_execute(*args)
    def hook(name,saved):
        if name==checkpoint and not stopped:stopped.append(1);raise KeyboardInterrupt()
    with pytest.raises(KeyboardInterrupt):
        actor.run(task,PARENT,tmp_path/'run',cfg,generate=generate,execute=execute,hook=hook)
    record=json.loads(actor.run(task,PARENT,tmp_path/'run',cfg,generate=generate,execute=execute).read_text())
    assert len(calls)==2 and len(execs)==1 and record['code_attempts']==1
    facts.build_facts([record])


def test_sixth_saved_valid_response_executes_without_seventh_request(tmp_path):
    cfg,task=setup(tmp_path);calls=[]
    def generate(*args):calls.append(1);return truncated() if len(calls)<6 else good()
    def hook(name,saved):
        if name=='response_saved' and len(saved['requests'])==6:raise KeyboardInterrupt()
    with pytest.raises(KeyboardInterrupt):actor.run(task,PARENT,tmp_path/'run',cfg,generate=generate,execute=fast_execute,hook=hook)
    saved=state(tmp_path);saved['requests'][-1]['response']=None
    (tmp_path/'run/actor_state.json').write_text(json.dumps(saved))
    record=json.loads(actor.run(task,PARENT,tmp_path/'run',cfg,generate=forbidden,execute=fast_execute).read_text())
    assert len(calls)==6 and record['score']['hard']==1 and record['code_attempts']==1
    facts.build_facts([record])


def test_unknown_execution_outcome_never_reexecutes(tmp_path):
    cfg,task=setup(tmp_path);runs=[]
    def execute(*args):runs.append(1);raise KeyboardInterrupt()
    with pytest.raises(KeyboardInterrupt):actor.run(task,PARENT,tmp_path/'run',cfg,generate=lambda *a:good(),execute=execute)
    with pytest.raises(actor.Interrupted,match='no saved outcome'):
        actor.run(task,PARENT,tmp_path/'run',cfg,generate=forbidden,execute=execute,score=forbidden)
    assert runs==[1] and state(tmp_path)['code_attempts']==1


def test_new_policy_is_explicit_legacy_prompt_unchanged(tmp_path):
    cfg,task=setup(tmp_path)
    SpreadsheetBenchAdapter().validate_config(cfg)
    text=protocol.initial_messages(task,PARENT,'preview',cfg['actor_profile'])[0]['content']
    assert '30 actual program executions' in text and '6 total API requests' in text
    cfg['actor_profile'].pop('attempt_budget_policy')
    text=protocol.initial_messages(task,PARENT,'preview',cfg['actor_profile'])[0]['content']
    assert 'including malformed or\ntruncated responses' in text
    cfg['actor_profile']['attempt_budget_policy']='unknown'
    with pytest.raises(ValueError,match='Unknown attempt budget policy'):SpreadsheetBenchAdapter().validate_config(cfg)


def test_full_v25_flow_and_skilladam_view_keep_truncation_evidence(tmp_path):
    from src.skill_evolution.v25 import evolution as ev
    from src.skill_evolution.v25.benchmark import using_benchmark
    from .support import ActorResponses, MethodResponses
    import sys
    sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'scripts/runs'))
    import run_skilladam_spreadsheetbench_aligned as bridge
    cfg,task=setup(tmp_path);normal=ActorResponses();seen=set();method=MethodResponses()
    def generate(messages,directory,*args):
        slot=Path(directory).parent
        if slot not in seen:seen.add(slot);return truncated()
        return normal(messages,directory,*args)
    adapter=SpreadsheetBenchAdapter(generate=generate,execute=fast_execute)
    with using_benchmark(adapter):
        result=ev.run_campaign(tmp_path/'campaign',config=cfg,generate=method,actor_runner=adapter.actor_task)
    assert result['status']=='complete'
    usage=ev.cost_summary(tmp_path/'campaign')
    assert usage['code_attempts']==usage['program_executions']==2 and usage['actor_http_requests']==4
    assert ev.read(tmp_path/'campaign/rounds/R01/gate/result.json')['result']['decision']=='ACCEPT'
    for path in (tmp_path/'campaign').rglob('trajectory.json'):
        record=ev.read(path);assert record['api_requests']==2 and record['code_attempts']==1
        raw=bridge.convert_record(record)
        assert raw['n_turns']==1 and raw['usage_records'][0]['requests']==1
        evidence=json.loads(raw['messages'][3]['content'])
        assert evidence['response_in_history'] is False and not evidence['executed']
    for name,payload in method.payloads:
        for run in timeline.full_runs(payload):
            assert run['attempts'][0]['response_in_history'] is False
            assert list(timeline.requests_for(run))[0]==list(timeline.requests_for(run))[1]


def test_generation_exhaustion_cannot_reach_optimizer_or_score(tmp_path):
    from src.skill_evolution.v25 import evolution as ev
    from src.skill_evolution.v25.benchmark import using_benchmark
    cfg,task=setup(tmp_path);calls=[]
    def generate(*args):calls.append(1);return truncated()
    adapter=SpreadsheetBenchAdapter(generate=generate,execute=forbidden,score=forbidden)
    root=tmp_path/'campaign'
    with using_benchmark(adapter):
        for resume in (False,True):
            with pytest.raises(actor.GenerationExhausted):
                ev.run_campaign(root,config=None if resume else cfg,resume=resume,generate=forbidden,actor_runner=adapter.actor_task)
    assert len(calls)==6
    assert ev.read(root/'state.json')['next_round']==1
    assert not list(root.rglob('score.json')) and not (root/'rounds/R01/grouping').exists()
    assert ev.read(next(root.rglob('actor_state.json')))['status']=='generation_incomplete'

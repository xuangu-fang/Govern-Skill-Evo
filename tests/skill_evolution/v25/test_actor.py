import json
from pathlib import Path
from copy import deepcopy
import pytest
import openpyxl
from src.skill_evolution.v25.benchmarks.spreadsheetbench import actor,protocol,scoring,transport,facts,executor
from .support import config,response,fast_execute,CODE,PARENT


def setup(tmp_path):
    c=config(tmp_path/'data',n=1)
    # This file retains explicit coverage of the original response-counted protocol.
    c['actor_profile'].pop('attempt_budget_policy');c['actor_profile'].pop('actor_history_policy')
    c['actor_profile']['actor_task_timeout_seconds']=600
    return c,next(iter(c['task_items'].values()))


def gen(code=CODE%' + 1'):
    return lambda *args:response('```python\n'+code+'```')


def test_first_valid_wrong_submission_stops(tmp_path):
    c,t=setup(tmp_path);calls=[]
    def generate(*args):calls.append(1);return gen(CODE%'')(*args)
    path=actor.run(t,PARENT,tmp_path/'run',c,generate=generate,execute=fast_execute);r=json.loads(path.read_text())
    assert r['score']['hard']==0 and r['score']['per_cell_pass_rate']==.5
    assert len(calls)==r['code_attempts']==r['program_executions']==r['api_requests']==1
    assert len(r['messages'])==3 and r['attempts'][0]['feedback_to_actor'] is None
    facts.build_facts([r]);assert t['answer_path'] not in json.dumps(facts.build_facts([r]))


def test_format_then_runtime_error_then_valid(tmp_path):
    c,t=setup(tmp_path);calls=[];executions=[]
    def generate(messages,*args):
        calls.append(deepcopy(messages));return response('bad') if len(calls)==1 else gen()()
    def execute(*args):
        executions.append(1)
        if len(executions)==1:return dict(status='error',exit_status=1,output_openable=False,error_category='execution_error',error_detail='A'*3000+'HIDDEN_TAIL',stdout='',stderr='')
        return fast_execute(*args)
    r=json.loads(actor.run(t,PARENT,tmp_path/'run',c,generate=generate,execute=execute).read_text())
    assert (r['code_attempts'],r['program_executions'],r['api_requests'])==(3,2,3)
    assert len(calls[-1])==6 and 'HIDDEN_TAIL' not in calls[-1][-1]['content'] and 'A'*3000 in calls[-1][-1]['content']
    facts.build_facts([r])


def test_thirty_code_attempts_including_truncated(tmp_path):
    c,t=setup(tmp_path);calls=[]
    def generate(*args):calls.append(1);return {'content':'```python\nprint(', 'finish_reason':'length'}
    r=json.loads(actor.run(t,PARENT,tmp_path/'run',c,generate=generate,execute=fast_execute).read_text())
    assert r['code_attempts']==30 and len(calls)==30 and r['program_executions']==0
    assert r['termination']=='budget_exhausted' and r['score']['hard']==0
    facts.build_facts([r])


def test_api_six_attempts_not_reset_by_resume(tmp_path):
    c,t=setup(tmp_path);calls=[]
    def generate(*args):calls.append(1);raise transport.RequestError('temporary unavailable')
    for _ in range(2):
        with pytest.raises(actor.Interrupted):actor.run(t,PARENT,tmp_path/'run',c,generate=generate,execute=fast_execute)
    r=json.loads((tmp_path/'run/actor_state.json').read_text());assert len(calls)==len(r['requests'])==6 and r['attempts']==[]


def test_no_task_deadline_keeps_individual_timeouts_after_600_seconds(tmp_path):
    c,t=setup(tmp_path);c['actor_profile']['actor_task_timeout_seconds']=0
    now=[0];requests=[];programs=[]
    def generate(messages,path,timeout,cfg):
        requests.append(timeout);now[0]+=250
        return response('malformed') if len(requests)<4 else gen()()
    def execute(code,inp,path,timeout,cfg):
        programs.append(timeout);now[0]+=590
        return fast_execute(code,inp,path,timeout,cfg)
    record=json.loads(actor.run(t,PARENT,tmp_path/'run',c,generate=generate,execute=execute,clock=lambda:now[0]).read_text())
    assert requests==[300]*4 and programs==[600]
    assert record['elapsed_seconds']==1590 and record['score']['hard']==1
    assert 'no cumulative Actor task time limit' in record['initial_messages'][0]['content']
    facts.build_facts([record])
    for path in (tmp_path/'run').rglob('*.json'):
        json.loads(path.read_text(),parse_constant=lambda x:pytest.fail(f'Non-finite JSON value: {x}'))


def test_no_task_deadline_still_exhausts_six_requests_without_reset(tmp_path):
    c,t=setup(tmp_path);c['actor_profile']['actor_task_timeout_seconds']=0
    now=[0];calls=[]
    def generate(messages,path,timeout,cfg):
        calls.append(timeout);now[0]+=timeout;raise transport.RequestError('temporary unavailable')
    for _ in range(2):
        with pytest.raises(actor.Interrupted,match='attempts exhausted'):
            actor.run(t,PARENT,tmp_path/'run',c,generate=generate,clock=lambda:now[0])
    record=json.loads((tmp_path/'run/actor_state.json').read_text())
    assert calls==[300]*6 and record['elapsed_seconds']==1800


def test_no_task_deadline_still_stops_at_thirty_code_attempts(tmp_path):
    c,t=setup(tmp_path);c['actor_profile']['actor_task_timeout_seconds']=0
    now=[0];calls=[]
    def generate(*args):
        calls.append(1);now[0]+=100;return response('malformed')
    record=json.loads(actor.run(t,PARENT,tmp_path/'run',c,generate=generate,clock=lambda:now[0]).read_text())
    assert len(calls)==record['code_attempts']==30 and record['elapsed_seconds']==3000
    assert record['termination']=='budget_exhausted'


def test_no_task_deadline_resume_keeps_elapsed_and_previous_requests(tmp_path):
    c,t=setup(tmp_path);c['actor_profile']['actor_task_timeout_seconds']=0
    now=[0];calls=[]
    def generate(*args):calls.append(1);now[0]+=700;return gen()()
    def stop(name,state):
        if name=='response_saved':raise KeyboardInterrupt()
    with pytest.raises(KeyboardInterrupt):
        actor.run(t,PARENT,tmp_path/'run',c,generate=generate,clock=lambda:now[0],hook=stop)
    def forbidden(*args):pytest.fail('Saved response must not trigger another API call')
    record=json.loads(actor.run(t,PARENT,tmp_path/'run',c,generate=forbidden,execute=fast_execute,clock=lambda:now[0]).read_text())
    assert calls==[1] and record['elapsed_seconds']==700 and record['score']['hard']==1


@pytest.mark.parametrize('prior_code_attempt',[False,True])
def test_api_deadline_interruption_survives_resume(tmp_path,prior_code_attempt):
    c,t=setup(tmp_path);now=[0];calls=[];directory=tmp_path/'run'
    def generate(messages,path,timeout,cfg):
        calls.append(timeout)
        if prior_code_attempt and len(calls)==1:return response('invalid code response')
        now[0]+=timeout
        raise transport.RequestError('Synthetic API timeout')
    def forbidden(*args):raise AssertionError('Technical interruption must not execute or score')
    for _ in range(3):
        with pytest.raises(actor.Interrupted,match='API unavailable'):
            actor.run(t,PARENT,directory,c,generate=generate,execute=forbidden,score=forbidden,clock=lambda:now[0])
        saved=json.loads((directory/'actor_state.json').read_text())
        assert saved['status']=='technical_interruption' and not saved['actor_complete']
        assert saved['elapsed_seconds']==600 and len(saved['attempts'])==int(prior_code_attempt)
        assert 'score' not in saved and not (directory/'score.json').exists()
        assert not (directory/'trajectory.json').exists()
    assert len(calls)==2+int(prior_code_attempt)


def test_saved_response_at_deadline_is_not_an_unanswered_api_failure(tmp_path):
    c,t=setup(tmp_path);now=[0];calls=[];directory=tmp_path/'run'
    def generate(*args):calls.append(1);now[0]=600;return gen()(*args)
    def stop(name,state):
        if name=='response_saved':raise KeyboardInterrupt()
    def forbidden(*args):raise AssertionError('No remaining budget for a request or program')
    with pytest.raises(KeyboardInterrupt):
        actor.run(t,PARENT,directory,c,generate=generate,execute=forbidden,clock=lambda:now[0],hook=stop)
    # Recover the worker's persisted response even if the state write was lost.
    state=json.loads((directory/'actor_state.json').read_text());state['requests'][0]['response']=None
    (directory/'actor_state.json').write_text(json.dumps(state))
    result=json.loads(actor.run(t,PARENT,directory,c,generate=forbidden,execute=forbidden,clock=lambda:now[0]).read_text())
    assert calls==[1] and result['termination']=='budget_exhausted' and result['score']['hard']==0


@pytest.mark.parametrize('checkpoint',['response_saved','execution_saved','submitted','score_saved'])
def test_saved_result_resume_without_duplicate_work(tmp_path,checkpoint):
    c,t=setup(tmp_path);calls=[];runs=[];scores=[]
    def generate(*args):calls.append(1);return gen()(*args)
    def execute(*args):runs.append(1);return fast_execute(*args)
    def grade(*args):scores.append(1);return scoring.score(*args)
    def stop(name,state):
        if name==checkpoint:raise KeyboardInterrupt()
    with pytest.raises(KeyboardInterrupt):actor.run(t,PARENT,tmp_path/'run',c,generate=generate,execute=execute,score=grade,hook=stop)
    r=json.loads(actor.run(t,PARENT,tmp_path/'run',c,generate=generate,execute=execute,score=grade).read_text())
    assert len(calls)==len(runs)==len(scores)==1 and r['score']['hard']==1
    facts.build_facts([r])


def test_scoring_failure_is_not_actor_retry(tmp_path):
    c,t=setup(tmp_path);calls=[]
    def generate(*args):calls.append(1);return gen()(*args)
    def broken(*args):raise OSError('reference unavailable')
    with pytest.raises(OSError):actor.run(t,PARENT,tmp_path/'run',c,generate=generate,execute=fast_execute,score=broken)
    actor.run(t,PARENT,tmp_path/'run',c,generate=generate,execute=fast_execute)
    assert calls==[1]


def test_remaining_task_deadline_clips_program_and_survives_resume(tmp_path):
    c,t=setup(tmp_path);now=[0];limits=[]
    def generate(*args):now[0]+=590;return gen()(*args)
    def execute(code,inp,directory,timeout,cfg):
        limits.append(timeout);now[0]+=11
        return dict(status='timeout',exit_status=None,output_openable=False,error_category='execution_error',error_detail='timed out')
    r=json.loads(actor.run(t,PARENT,tmp_path/'run',c,generate=generate,execute=execute,clock=lambda:now[0]).read_text())
    assert limits==[10] and r['termination']=='budget_exhausted' and r['elapsed_seconds']==601
    facts.build_facts([r])
    def forbidden(*args):raise AssertionError('Completed budget failure must not rerun')
    resumed=json.loads(actor.run(t,PARENT,tmp_path/'run',c,generate=forbidden,execute=forbidden,score=forbidden,clock=lambda:now[0]).read_text())
    assert resumed==r


def test_unknown_program_outcome_not_reexecuted(tmp_path):
    c,t=setup(tmp_path);calls=[]
    def execute(*args):calls.append(1);raise KeyboardInterrupt()
    with pytest.raises(KeyboardInterrupt):actor.run(t,PARENT,tmp_path/'run',c,generate=gen(),execute=execute)
    with pytest.raises(actor.Interrupted,match='no saved outcome'):actor.run(t,PARENT,tmp_path/'run',c,generate=gen(),execute=execute)
    assert calls==[1]


def test_preview_and_message_limits(tmp_path):
    p=protocol.DEFAULTS.copy();w=openpyxl.Workbook();s=w.active
    s['A1']='a'*41;s['T5']='visible';s['U6']='outside';w.save(tmp_path/'book.xlsx')
    view=protocol.preview(tmp_path/'book.xlsx',p);assert 'a'*37+'...' in view and 'T5=visible' in view and 'outside' not in view
    p['preview_max_chars']=len(view)-1
    with pytest.raises(protocol.InputError):protocol.preview(tmp_path/'book.xlsx',p)
    with pytest.raises(protocol.InputError):protocol.check_capacity([{'content':'中'*100}],{'max_input_chars':1000,'max_message_utf8_bytes':100})


@pytest.mark.parametrize('snippet',["INPUT_PATH = 'ignored'\nOUTPUT_PATH = 'ignored'", "INPUT_PATH='a'; OUTPUT_PATH='b'", "INPUT_PATH = (\n'a'\n)"])
def test_literal_binding_adaptation(snippet):
    raw,code=protocol.extract_code('```python\n'+snippet+'\nprint(INPUT_PATH, OUTPUT_PATH)\n```')
    assert 'ignored' not in code;compile(code,'solution.py','exec')


@pytest.mark.parametrize('snippet',["INPUT_PATH = Path('x')","if True:\n OUTPUT_PATH='x'","INPUT_PATH += 'x'","def f(OUTPUT_PATH): pass","import os as INPUT_PATH"])
def test_complex_bindings_rejected(snippet):
    with pytest.raises(ValueError):protocol.extract_code('```python\n'+snippet+'\n```')

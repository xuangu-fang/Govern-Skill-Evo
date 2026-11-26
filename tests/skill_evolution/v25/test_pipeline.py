import json
from pathlib import Path
import pytest
from src.skill_evolution.v25 import evolution as ev, evaluation
from src.skill_evolution.v25.benchmark import using_benchmark
from src.skill_evolution.v25.benchmarks.spreadsheetbench.adapter import SpreadsheetBenchAdapter
from src.skill_evolution.v25.contracts import memory
from .support import config, ActorResponses, MethodResponses, fast_execute


def campaign(tmp_path,*,n=2,rounds=1,method=None,correct=True,docker=False,hook=None,test=0):
    c=config(tmp_path/'data',n,rounds,test);actors=ActorResponses(candidate_correct=correct);method=method or MethodResponses()
    a=SpreadsheetBenchAdapter(generate=actors,execute=None if docker else fast_execute);root=tmp_path/'campaign'
    with using_benchmark(a):
        result=ev.run_campaign(root,config=c,generate=method,actor_runner=a.actor_task,hook=hook)
    return root,c,a,actors,method,result


def test_full_flow(tmp_path):
    root,c,a,actors,m,result=campaign(tmp_path)
    assert result['status']=='complete';assert len(actors.calls)==4
    assert ev.read(root/'rounds/R01/gate/result.json')['result']['decision']=='ACCEPT'
    assert m.calls==['grouping','diagnosis','preconditioner','editor','replay','verifier']
    with using_benchmark(a):
        assert ev.final_parent(root).is_file()
        assert len(memory.load_memory(root/'rounds/R01/memory',memory_contract=memory.MULTI_KNOWLEDGE_CONTRACT)['entries'])==1
    assert all(len(x)==2 for x in actors.calls)
    assert ev.cost_summary(root)['actor_http_requests']==4


@pytest.mark.parametrize('kind',['no_change','drop','empty_editor','retain','repair','withdraw','invalid_retry'])
def test_branches(tmp_path,kind):
    method=MethodResponses(decision=kind if kind=='no_change' else 'revise',pre='DROP' if kind=='drop' else 'KEEP',editor_empty=kind=='empty_editor',conflict=kind in ('repair','withdraw'),withdraw=kind=='withdraw',invalid_once='grouping' if kind=='invalid_retry' else None)
    if kind=='withdraw':
        with pytest.raises(ev.Stopped):campaign(tmp_path,method=method)
        assert method.calls.count('repair')==6 and method.calls.count('verifier')==1
        assert ev.read(tmp_path/'campaign/state.json')['next_round']==1
        return
    root,c,a,actors,m,result=campaign(tmp_path,method=method,correct=kind!='retain')
    assert result['status']=='complete'
    outcome=ev.read(root/'rounds/R01/result.json')['outcome']
    if kind in ('no_change','drop','empty_editor'):
        assert outcome=='no_change' and len(actors.calls)==2;assert 'replay' not in m.calls
    else:
        assert len(actors.calls)==4 and outcome==('RETAIN' if kind=='retain' else 'ACCEPT')
        assert m.calls.count('repair')==int(kind in ('repair','withdraw'))
        assert m.calls.count('verifier')==1
        if kind=='invalid_retry':assert m.calls.count('grouping')==2


@pytest.mark.parametrize('point',['before_publish','after_publish'])
def test_publication_resume(tmp_path,point):
    c=config(tmp_path/'data');root=tmp_path/'campaign';actors=ActorResponses();m=MethodResponses();a=SpreadsheetBenchAdapter(generate=actors,execute=fast_execute)
    def stop(name):
        if name==point:raise KeyboardInterrupt()
    with using_benchmark(a):
        with pytest.raises(KeyboardInterrupt):ev.run_campaign(root,config=c,generate=m,actor_runner=a.actor_task,hook=stop)
        counts=(len(actors.calls),len(m.calls))
        ev.run_campaign(root,resume=True,generate=m,actor_runner=a.actor_task)
        assert counts==(len(actors.calls),len(m.calls));assert ev.final_parent(root)


def test_history_and_test_evaluation(tmp_path):
    root,c,a,actors,m,result=campaign(tmp_path,rounds=2,method=MethodResponses(history=True),test=2)
    with using_benchmark(a):
        skill=ev.final_parent(root);before=ev.read(root/'state.json');count=len(m.calls)
        bundle={'campaign':str(root),'skill_text':skill.read_text(),'actor_config':c,'tasks':[c['task_items'][t] for t in c['test_tasks']],'initial_reference':None}
        summary=evaluation.run(tmp_path/'evaluation',bundle=bundle,runner=lambda task,skill,dest,cfg:a.actor_task(task,skill,dest,cfg,final=True))
        assert summary['hard']==1 and summary['per_cell_pass_rate']==1 and summary['completed']==2
        assert len(m.calls)==count and ev.read(root/'state.json')==before
        history=[p for name,p in m.payloads if name=='verifier'][-1]
        assert any('/' in ref for ref in history['source_records'])


def test_evaluation_reports_actual_termination_and_preserves_it_on_resume(tmp_path):
    from src.skill_evolution.v25.benchmarks.spreadsheetbench.actor import run as run_actor
    from .support import response, PARENT
    c=config(tmp_path/'data',n=1,test=2);c['actor_profile']['max_code_attempts']=1
    # Historical response-counted evaluation; new generation exhaustion is unscored.
    c['actor_profile'].pop('actor_history_policy');c['actor_profile'].pop('attempt_budget_policy')
    a=SpreadsheetBenchAdapter();calls=[]
    bundle={'campaign':str(tmp_path/'training'),'skill_text':PARENT,'actor_config':c,
            'tasks':[c['task_items'][t] for t in c['test_tasks']],'initial_reference':None}
    def runner(task,skill,dest,cfg):
        calls.append(task)
        generate=ActorResponses() if task==c['test_tasks'][0] else lambda *args:response('invalid code response')
        return run_actor(c['task_items'][task],skill.read_text(),dest,cfg,generate=generate,execute=fast_execute)
    with using_benchmark(a):
        summary=evaluation.run(tmp_path/'evaluation',bundle=bundle,runner=runner)
        assert [r['termination'] for r in summary['tasks']]==['valid_workbook_submitted','budget_exhausted']
        assert [r['hard'] for r in summary['tasks']]==[0,0]
        resumed=evaluation.run(tmp_path/'evaluation',bundle=bundle,runner=runner,resume=True)
        assert resumed['tasks']==summary['tasks'] and calls==c['test_tasks']

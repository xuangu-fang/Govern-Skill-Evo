import pytest
from scripts.runs.v25.run_v25_pilot import run_pilot
from src.skill_evolution.v25 import evolution as ev
from src.skill_evolution.v25.benchmark import using_benchmark
from src.skill_evolution.v25.benchmarks.spreadsheetbench.adapter import SpreadsheetBenchAdapter
from .support import config,ActorResponses,MethodResponses,fast_execute


@pytest.mark.parametrize('decision',['revise','no_change'])
def test_pilot_stops_after_first_batch_even_on_resume(tmp_path,decision):
    cfg=config(tmp_path/'data',n=2,rounds=2);root=tmp_path/'campaign'
    actors=ActorResponses();methods=MethodResponses(decision=decision)
    adapter=SpreadsheetBenchAdapter(generate=actors,execute=fast_execute)
    with using_benchmark(adapter):
        result=run_pilot(root,config=cfg,generate=methods,actor_runner=adapter.actor_task)
        assert result['status']=='pilot_complete' and result['rounds_completed']==1
        before=(len(actors.calls),len(methods.calls))
        run_pilot(root,resume=True,generate=methods,actor_runner=adapter.actor_task)
        assert before==(len(actors.calls),len(methods.calls))
    assert len(actors.calls)==(4 if decision=='revise' else 2)
    assert ev.read(root/'config.json')==cfg and ev.read(root/'state.json')['next_round']==2
    assert not (root/'rounds/R02').exists()


def test_mixed_budget_pilot_reuses_parent_records_and_finishes_round(tmp_path):
    from copy import deepcopy
    from scripts.runs.v25.continue_v25_pilot import PilotAdapter
    from .support import PARENT
    cfg=config(tmp_path/'data',n=2);cfg['actor_profile']['actor_max_output_tokens']=32768
    # This test reconstructs the historical mixed-budget pilot protocol.
    from src.skill_evolution.v25.benchmarks.spreadsheetbench import protocol
    cfg['actor_profile']={**protocol.DEFAULTS,'actor_max_output_tokens':32768}
    change={'retained_run_ids':[]};actors=ActorResponses();methods=MethodResponses()
    adapter=PilotAdapter(change,generate=actors,execute=fast_execute);retained=[]
    def runner(task,skill,dest,settings):
        settings=deepcopy(settings)
        old=task==cfg['batches'][0][0] and skill.read_text()==PARENT
        if old:settings['actor_profile']['actor_max_output_tokens']=16384
        path=adapter.actor_task(task,skill,dest,settings)
        if old:
            change['retained_run_ids'].append(ev.read(path)['run_id']);retained.append((path,path.read_bytes()))
        return path
    with using_benchmark(adapter):
        result=run_pilot(tmp_path/'campaign',config=cfg,generate=methods,actor_runner=runner)
        run_pilot(tmp_path/'campaign',resume=True,generate=methods,actor_runner=runner)
    assert result['outcome']=='ACCEPT' and len(actors.calls)==4
    assert all(p.read_bytes()==raw for p,raw in retained)
    assert methods.calls==['grouping','diagnosis','preconditioner','editor','replay','verifier']
    context=ev.read(tmp_path/'campaign/rounds/R01/pairs/input.json')['execution_context']['description']
    assert 'mixed-budget functional comparison' in context

from dataclasses import replace
from pathlib import Path
import pytest
from src.skill_evolution.run_control_v19 import recovery_scope
from src.skill_evolution.memory_generation_v19 import _call
from src.skill_evolution.evolution_replay_v19 import _save, _load
from src.skill_evolution.memory_store_v19 import load_memory
from src.skill_evolution.campaign_v19 import run_campaign_v19
from tests.skill_evolution.test_local_campaign_v19 import setup
from tests.skill_evolution.test_attribution_pairs_v19 import transport as pair_transport


def complete(raw='{}'):
    return {'finish_reason':'stop','raw_response':raw,'refusal':None}


def test_network_retry_archive_and_completed_reuse(tmp_path):
    call=tmp_path/'generation/current-000'; request={'user_prompt':'same'};calls=[]
    def fail(r):calls.append(r);raise TimeoutError()
    with pytest.raises(TimeoutError):_call(call,request,fail)
    with pytest.raises(ValueError):_call(call,request,lambda r:complete())
    with recovery_scope(tmp_path,True):
        assert _call(call,request,lambda r:complete())=='{}'
        assert _call(call,request,fail)=='{}'
    archives=list((tmp_path/'recovery').glob('*/call/request.json'))
    assert len(archives)==1 and _load(archives[0])==request and len(calls)==1


def test_interruption_and_repair_call_recovery(tmp_path):
    path=tmp_path/'generation/current-000-repair-001';_save(path/'request.json',{'x':1})
    with recovery_scope(tmp_path,True):assert _call(path,{'x':1},lambda r:complete())=='{}'
    assert list((tmp_path/'recovery').glob('*/receipt.json'))


@pytest.mark.parametrize('kind',['mismatch','response','auth','length'])
def test_no_blind_retry(tmp_path,kind):
    path=tmp_path/'call';_save(path/'request.json',{'x':1})
    if kind=='response':_save(path/'response.json',complete())
    if kind=='auth':_save(path/'failure.json',{'error_type':'AuthenticationError'})
    if kind=='length':
        path.rename(tmp_path/'unused')
        with pytest.raises(ValueError):_call(path,{'x':1},lambda r:{**complete(),'finish_reason':'length'})
    called=[]
    with recovery_scope(tmp_path,True),pytest.raises(ValueError):
        _call(path,{'x':2 if kind=='mismatch' else 1},lambda r:called.append(r) or complete())
    assert not called and not (tmp_path/'recovery').exists()


def test_scope_does_not_leak(tmp_path):
    path=tmp_path/'call';_save(path/'request.json',{'x':1})
    with recovery_scope(tmp_path,True):pass
    with pytest.raises(ValueError):_call(path,{'x':1},lambda r:complete())


@pytest.mark.parametrize('field',['grouping','diagnosis','memory_review','issue_fusion','evidence_review','editor','attribution'])
def test_two_round_resume_network_failure(setup,field):
    kw,calls=setup
    kw['config']['attribution_protocol']='pair'
    kw['entrypoint']={'protocol':'unified_run_v19.1','generation':'local','attribution':'pair'}
    kw['transports']=replace(kw['transports'],attribution=pair_transport)
    original=getattr(kw['transports'],field);attempts=[]
    def flaky(request):
        attempts.append(request)
        if len(attempts)==1:raise TimeoutError('test network failure')
        return original(request)
    kw['transports']=replace(kw['transports'],**{field:flaky})
    with pytest.raises((ValueError,TimeoutError)):run_campaign_v19(**kw)
    with recovery_scope(kw['output'],True):result=run_campaign_v19(**kw,resume=True)
    assert result['committed_rounds']==2
    assert load_memory(kw['output']/'memory').head['revision']==2
    assert len(list((kw['output']/'recovery').glob('*/receipt.json')))==1
    before=len(attempts)
    with recovery_scope(kw['output'],True):assert run_campaign_v19(**kw,resume=True)==result
    assert len(attempts)==before


@pytest.mark.parametrize('stage',['BEFORE_COMMIT','AFTER_COMMIT','MONITOR_GATE'])
def test_commit_interrupt_resume(setup,stage):
    kw,_=setup
    def interrupt(s,r):
        if s==stage and r=='round-02':raise KeyboardInterrupt()
    with pytest.raises(KeyboardInterrupt):run_campaign_v19(**kw,event_hook=interrupt)
    with recovery_scope(kw['output'],True):result=run_campaign_v19(**kw,resume=True)
    assert result['committed_rounds']==2
    assert load_memory(kw['output']/'memory').head['revision']==2


def test_source_drift_prevents_any_recovery(setup):
    kw,_=setup
    def fail(r):raise TimeoutError()
    kw['transports']=replace(kw['transports'],diagnosis=fail)
    with pytest.raises(TimeoutError):run_campaign_v19(**kw)
    binding=_load(kw['output']/'binding.json');binding['source_files']['wrong']='different'
    _save(kw['output']/'binding.json',binding)
    with recovery_scope(kw['output'],True),pytest.raises(ValueError,match='changed'):
        run_campaign_v19(**kw,resume=True)
    assert not (kw['output']/'recovery').exists()


def test_cli_run_and_resume_saved_config(tmp_path,monkeypatch):
    import importlib.util
    from types import SimpleNamespace
    import src.skill_evolution.campaign_v19 as campaign
    import src.skill_evolution.evolution_benchmark_v19 as evolution
    import src.skill_evolution.monitor_campaign_v19 as monitor
    spec=importlib.util.spec_from_file_location('v19_cli',Path(__file__).resolve().parents[2]/'scripts/run_v19.py')
    cli=importlib.util.module_from_spec(spec);spec.loader.exec_module(cli)
    (tmp_path/'S0.md').write_text('- Parent\n')
    monkeypatch.setattr(evolution,'BenchmarkEvolutionV19',lambda:SimpleNamespace(freeze=tmp_path))
    monkeypatch.setattr(monitor,'BenchmarkMonitorV19',lambda:object())
    seen=[]
    def runner(**kw):
        seen.append(kw)
        _save(kw['output']/'binding.json',{k:kw[k] for k in ['entrypoint','config','run_id']})
        return {'status':'COMPLETE'}
    monkeypatch.setattr(campaign,'run_campaign_v19',runner)
    config=tmp_path/'config.json';_save(config,{'mode':'pilot','max_workers':2})
    out=tmp_path/'new'
    cli.main(['run','--config',str(config),'--output',str(out)])
    config.unlink()
    cli.main(['resume','--output',str(out)])
    assert seen[0]['config']==seen[1]['config']
    assert seen[0]['config']['generation_protocol']=='local'
    assert seen[0]['config']['attribution_protocol']=='pair'
    assert not seen[0]['resume'] and seen[1]['resume']
    with pytest.raises(ValueError,match='new output'):
        cli.main(['run','--config',str(config),'--output',str(out)])
    bound=_load(out/'binding.json');bound.pop('entrypoint');_save(out/'binding.json',bound)
    with pytest.raises(ValueError,match='migration'):cli.main(['resume','--output',str(out)])


@pytest.mark.parametrize('backend_key,role',[('evolution_backend','PARENT'),('evolution_backend','CANDIDATE'),('monitor_backend','PARENT'),('monitor_backend','CANDIDATE')])
def test_replay_monitor_failed_task_only(setup,backend_key,role):
    kw,_=setup;backend=kw[backend_key];failed=(role,backend.tasks[0]);backend.fail_run.add(failed)
    with pytest.raises(ValueError):run_campaign_v19(**kw)
    before=backend.calls.copy();backend.fail_run.clear()
    # Stop at the end of round one, so counts do not include the intentional next-round rollout.
    def stop(stage,round_id):
        if stage=='AFTER_COMMIT' and round_id=='round-01':raise KeyboardInterrupt()
    with recovery_scope(kw['output'],True),pytest.raises(KeyboardInterrupt):
        run_campaign_v19(**kw,resume=True,event_hook=stop)
    for key,count in before.items():
        assert backend.calls[key]==count+(key==failed)
    assert load_memory(kw['output']/'memory').head['revision']==1

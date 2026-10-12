from pathlib import Path
from collections import Counter

import pytest

from src.skill_evolution.v19.campaign_v19 import CampaignTransports, campaign_config, run_campaign_v19
from src.skill_evolution.v19.edit_tracking_v19 import encode, parse
from src.skill_evolution.v19.memory_store_v19 import load_memory, MemoryRejected
from src.skill_evolution.v19.evolution_replay_v19 import _load, _save, _file_digest
from src.skill_evolution.v19.monitor_campaign_v19 import run_private_monitor, load_private_monitor
from tests.skill_evolution.v19.test_evolution_replay_v19 import Backend
from tests.skill_evolution.v19.test_memory_generation_v19 import raw_for, editor
from tests.skill_evolution.v19.test_attribution_v19 import record, response, complete


class Evolution(Backend):
    def prepare(self,task_id,skill,artifact_dir):
        if 'parent_evolution' in Path(artifact_dir).parts:
            self.parent=skill
        return super().prepare(task_id,skill,artifact_dir)


class Monitor(Backend):
    def __init__(self,decision='ACCEPT'):
        super().__init__()
        self.tasks=['PRIVATE-MONITOR-A','PRIVATE-MONITOR-B']
        self.decision=decision
    def manifest(self):
        return {**super().manifest(),'schema_version':'monitor_manifest_v19.1'}
    def prepare(self,task_id,skill,artifact_dir):
        if 'parent' in Path(artifact_dir).parts:
            self.parent=skill
        return super().prepare(task_id,skill,artifact_dir)
    def evaluate(self,task_id,*,initial_db,final_db,simulation):
        role='CANDIDATE' if 'checked' in simulation['messages'][1]['content'] else 'PARENT'
        self.evaluations[(role,task_id)]+=1
        if (role,task_id) in self.fail_eval:raise RuntimeError('MONITOR_SECRET_FAILURE')
        return {'success':role=='CANDIDATE' or self.decision=='RETAIN','compliant':True,
                'monitor_reason':'NEVER_LEARN_MONITOR_SECRET','hidden_target':'PRIVATE_EXPECTED_ACTION'}


def transports(calls=None,stop=False):
    calls=Counter() if calls is None else calls
    def check(request,stage):
        calls[stage]+=1
        assert 'PRIVATE-MONITOR' not in request['user_prompt']
        assert 'NEVER_LEARN_MONITOR_SECRET' not in request['user_prompt']
        assert 'PRIVATE_EXPECTED_ACTION' not in request['user_prompt']
    def group(request):
        check(request,'grouping');data=parse(request['user_prompt'])
        return complete(encode({'groups':[{'group_id':'G1','decision_problem':'Change authorized value',
            'members':[e['task_ref'] for e in data['cards']],'shared_basis':'Shared observable request',
            'important_differences':[]}]}))
    def diagnosis(request):
        check(request,'diagnosis');data=parse(request['user_prompt'])
        rows=data['memory_context']['rounds']
        if rows:
            binding=rows[0]['current_bindings'][0]['binding_status']
            return complete(raw_for(data,kind='MISSING' if binding=='ABSENT' else 'NEEDS_REVISION',
                                    relation='RETRIES' if binding=='ABSENT' else 'REVISES',defer=stop))
        return complete(raw_for(data,kind='MISSING',defer=stop))
    def edit(request):
        check(request,'editor')
        result=editor(request)
        out=parse(result['raw_response'])
        for unit in out['edits']:
            unit['text']=f'- Generated rule iteration {calls["editor"]}'
        return complete(encode(out))
    def attribution(request):
        check(request,'attribution');data=parse(request['user_prompt'])
        return complete(response(record(data,(0,1),'MIXED'),record(data,(),'UNKNOWN','UNRESOLVED')))
    return CampaignTransports(group,diagnosis,edit,attribution)


@pytest.fixture
def setup(tmp_path):
    calls=Counter()
    return dict(output=tmp_path/'campaign',config=campaign_config(attribution_protocol='legacy',pilot=True,max_workers=2),
                run_id='engineering-run',initial_skill='- Parent\n',evolution_backend=Evolution(),
                monitor_backend=Monitor(),transports=transports(calls)),calls


def test_accepted_local_problem_revised_in_two_round_loop(setup):
    kwargs,calls=setup
    report=run_campaign_v19(**kwargs)
    assert report['status']=='COMPLETE' and report['stop_reason']=='ROUND_LIMIT'
    assert report['committed_rounds']==2
    assert report['cross_round_links'][0]['relation']=='REVISES'
    assert report['cross_round_links'][0]['origin_gate_decision']=='ACCEPT'
    assert report['attribution_effect_counts']=={'MIXED':2,'UNKNOWN':2}
    assert calls=={'grouping':2,'diagnosis':2,'editor':2,'attribution':2}
    snapshot=load_memory(kwargs['output']/'memory')
    assert '- Generated rule iteration 2' in snapshot.head['retained_skill']
    for private in ('PRIVATE-MONITOR','NEVER_LEARN_MONITOR_SECRET','PRIVATE_EXPECTED_ACTION'):
        assert private not in encode(report)
        assert private not in encode(snapshot.rounds)
    before=(calls.copy(),kwargs['evolution_backend'].calls.copy(),kwargs['monitor_backend'].calls.copy())
    assert run_campaign_v19(**kwargs,resume=True)==report
    assert before==(calls,kwargs['evolution_backend'].calls,kwargs['monitor_backend'].calls)


def test_rejected_potential_direction_reused_without_promoting_old_skill(setup):
    kwargs,_=setup
    kwargs['monitor_backend']=Monitor('RETAIN')
    report=run_campaign_v19(**kwargs)
    assert report['cross_round_links'][0]['relation']=='RETRIES'
    assert report['cross_round_links'][0]['origin_gate_decision']=='RETAIN'
    assert 'MIXED' in report['cross_round_links'][0]['historical_effects']
    snap=load_memory(kwargs['output']/'memory')
    assert snap.head['retained_skill']=='- Parent\n' and len(snap.history)==2
    assert snap.history[0].ledger.payload['edits'][0]['edit_id']!=snap.history[1].ledger.payload['edits'][0]['edit_id']


@pytest.mark.parametrize('stage',['CANDIDATE_EVOLUTION','ATTRIBUTION','MONITOR_GATE','BEFORE_COMMIT','AFTER_COMMIT'])
def test_interrupt_resume_no_duplicate_models_or_commits(setup,stage):
    kwargs,calls=setup
    def interrupt(current,round_id):
        if current==stage and round_id=='round-01':raise KeyboardInterrupt()
    with pytest.raises(KeyboardInterrupt):run_campaign_v19(**kwargs,event_hook=interrupt)
    expected=1 if stage=='AFTER_COMMIT' else 0
    assert load_memory(kwargs['output']/'memory').head['revision']==expected
    report=run_campaign_v19(**kwargs,resume=True)
    assert report['committed_rounds']==2
    assert calls=={'grouping':2,'diagnosis':2,'editor':2,'attribution':2}
    assert sum(kwargs['evolution_backend'].calls.values())==12
    assert sum(kwargs['monitor_backend'].calls.values())==8
    assert len(list((kwargs['output']/'memory/rounds').iterdir()))==2


def test_monitor_scoring_failure_resume_does_not_reroll_or_commit(setup):
    kwargs,calls=setup
    mon=kwargs['monitor_backend']
    mon.fail_eval.add(('CANDIDATE',mon.tasks[0]))
    with pytest.raises(ValueError):run_campaign_v19(**kwargs)
    assert load_memory(kwargs['output']/'memory').head['revision']==0
    assert calls['attribution']==1
    mon.fail_eval.clear()
    report=run_campaign_v19(**kwargs,resume=True)
    assert report['committed_rounds']==2
    assert sum(mon.calls.values())==8
    assert calls['attribution']==2


def test_attribution_error_blocks_monitor_and_memory(setup):
    kwargs,calls=setup
    t=kwargs['transports']
    kwargs['transports']=CampaignTransports(t.grouping,t.diagnosis,t.editor,lambda _:complete('{}'))
    with pytest.raises(ValueError):run_campaign_v19(**kwargs)
    assert not kwargs['monitor_backend'].calls
    assert load_memory(kwargs['output']/'memory').head['revision']==0
    assert _load(kwargs['output']/'campaign.json')['failed_stage']=='ATTRIBUTION'


def test_stop_no_update_without_fake_gate_or_memory(setup):
    kwargs,_=setup
    calls=Counter();kwargs['transports']=transports(calls,stop=True)
    report=run_campaign_v19(**kwargs)
    assert report['stop_reason']=='NO_UPDATE' and report['committed_rounds']==0
    assert not kwargs['monitor_backend'].calls and 'editor' not in calls
    assert run_campaign_v19(**kwargs,resume=True)==report
    assert calls=={'grouping':1,'diagnosis':1}


@pytest.mark.parametrize('change',['mode','seed','source','run_id'])
def test_resume_version_mismatch_rejected_before_calls(setup,change,monkeypatch):
    import src.skill_evolution.v19.campaign_v19 as campaign
    kwargs,calls=setup
    def interrupt(stage,_):
        if stage=='GROUPING':raise KeyboardInterrupt()
    with pytest.raises(KeyboardInterrupt):run_campaign_v19(**kwargs,event_hook=interrupt)
    if change=='mode':kwargs['config']=campaign_config(attribution_protocol='legacy',pilot=False,max_workers=2)
    if change=='seed':kwargs['evolution_backend'].seed+=1
    if change=='source':monkeypatch.setattr(campaign,'source_manifest',lambda:{'changed':'digest'})
    if change=='run_id':kwargs['run_id']='different'
    with pytest.raises(ValueError):run_campaign_v19(**kwargs,resume=True)
    assert not calls


def test_gate_forgery_in_private_receipt_rejected_on_committed_resume(setup):
    kwargs,_=setup
    run_campaign_v19(**kwargs)
    directory=kwargs['output']/'round-01/monitor_private'
    receipt=_load(directory/'receipt.json');receipt['decision']='RETAIN';_save(directory/'receipt.json',receipt)
    marker=_load(directory/'validation.json');marker['files']['receipt.json']=_file_digest(directory/'receipt.json')
    _save(directory/'validation.json',marker)
    with pytest.raises(ValueError):run_campaign_v19(**kwargs,resume=True)


def test_report_is_not_commit_authority(setup):
    kwargs,_=setup
    def interrupt(stage,round_id):
        if stage=='AFTER_COMMIT' and round_id=='round-01':raise KeyboardInterrupt()
    with pytest.raises(KeyboardInterrupt):run_campaign_v19(**kwargs,event_hook=interrupt)
    _save(kwargs['output']/'campaign.json',{'status':'COMPLETE','committed_rounds':999})
    report=run_campaign_v19(**kwargs,resume=True)
    assert report['committed_rounds']==2


def test_private_monitor_never_exports_learner_pairs(setup):
    kwargs,_=setup
    run_campaign_v19(**kwargs)
    assert not list((kwargs['output']/'round-01/monitor_private').rglob('pairs.json'))
    root=kwargs['output']/'memory'
    assert not list(root.rglob('monitor_private'))


def test_grouping_single_repair_is_audited(setup):
    kwargs,calls=setup
    t=kwargs['transports'];attempts=[]
    def grouping(request):
        attempts.append(request)
        data=parse(request['user_prompt'])
        if 'repair_instruction' not in data:return complete('{}')
        return t.grouping({**request,'user_prompt':encode(data['original_input'])})
    kwargs['transports']=CampaignTransports(grouping,t.diagnosis,t.editor,t.attribution)
    assert run_campaign_v19(**kwargs)['committed_rounds']==2
    assert len(attempts)==4
    assert (kwargs['output']/'round-01/grouping/attempt-2/response.json').exists()


def test_real_monitor_adapter_cannot_enter_evolution_api(tmp_path):
    from src.skill_evolution.v19.monitor_campaign_v19 import BenchmarkMonitorV19
    from src.skill_evolution.v19.evolution_replay_v19 import run_parent_evolution
    monitor=BenchmarkMonitorV19()
    assert len(monitor.manifest()['task_ids'])==45
    with pytest.raises(ValueError):
        run_parent_evolution(run_id='test',round_id='r1',parent_skill='',backend=monitor,artifact_dir=tmp_path/'forbidden')
    assert not (tmp_path/'forbidden').exists()
    with pytest.raises(ValueError):monitor.prepare(monitor.registry.task_ids('train')[0],'',tmp_path/'train')


def test_full_run_requires_separate_output_from_pilot(setup):
    kwargs,_=setup
    run_campaign_v19(**kwargs)
    kwargs['config']=campaign_config(attribution_protocol='legacy',pilot=False,max_workers=2)
    with pytest.raises(ValueError):run_campaign_v19(**kwargs,resume=True)


def test_monitor_pair_runtime_mismatch_blocks_gate(setup):
    kwargs,_=setup
    kwargs['monitor_backend'].mismatch='user_prompt'
    with pytest.raises(ValueError):run_campaign_v19(**kwargs)
    assert load_memory(kwargs['output']/'memory').head['revision']==0
    assert _load(kwargs['output']/'campaign.json')['failed_stage']=='MONITOR_GATE'


def test_uncertain_grouping_call_not_retried_by_resume(setup):
    kwargs,calls=setup
    attempts=[]
    def fail(_):attempts.append(1);raise ConnectionError('private provider message')
    t=kwargs['transports'];kwargs['transports']=CampaignTransports(fail,t.diagnosis,t.editor,t.attribution)
    with pytest.raises(ConnectionError):run_campaign_v19(**kwargs)
    with pytest.raises(ValueError):run_campaign_v19(**kwargs,resume=True)
    assert attempts==[1]
    assert not kwargs['monitor_backend'].calls

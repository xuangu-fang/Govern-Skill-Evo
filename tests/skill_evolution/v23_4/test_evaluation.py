"""Current synthetic Campaign fixtures; no dependency on stale historical Prompts."""
from copy import deepcopy
from pathlib import Path
import pytest
from src.skill_evolution.v23_4 import evaluation as evaluation, benchmark as bm
from src.skill_evolution.v23_4 import evolution as ev
from tests.skill_evolution.v23.test_formal_evaluation import Fake
from .test_evolution import Harness, config, run


@pytest.fixture(scope='module')
def prepared(tmp_path_factory):
    base = tmp_path_factory.mktemp('evaluation_campaign')
    campaign = base/'S1'
    cfg = config()
    cfg['actor_base_url'] = 'https://offline.invalid'
    cfg['actor_max_workers'] = 8
    cfg['task_items'] = {f'train:{n:04}': {'id':f'train:{n:04}', 'gamefile':f'synthetic/{n}.json',
                                        'task_type':'synthetic'} for n in range(10,14)}
    cfg['environment_root'] = '/Users/didi/.cache/alfworld'
    class Actor(Harness):
        def actor(self, task, skill, dest, cfg):
            p = super().actor(task,skill,dest,cfg); raw = ev.read(p)
            raw['task'] = cfg['task_items'][task]
            raw['request_policy'] = {'max_attempts':3,'strict_response':True}
            ev.save(p,raw);return p
    h = Actor()
    ev.initialize(campaign,cfg)
    ev.run_round(campaign,generate=h.generate,actor_runner=h.actor)
    h.outcome = 'RETAIN'
    run(campaign,h,resume=True)
    tasks = ev.read(bm.BASE_EXPERIMENT/'data/test.json')
    env = ev.read(bm.BASE_EXPERIMENT/'config/protocol.json')['environment']
    hashes = {}
    for task in tasks:
        game = Path(env['data_root'])/task['gamefile']
        for p in (game,game.parent/'initial_state.pddl'): hashes[str(p)] = bm.sha(p)
    spec = {'campaign':str(campaign),'campaign_config':cfg,'tasks':tasks,'expected_tasks':134,
            'environment':env,'test_environment_sha256':hashes}
    ev.save(base/'evaluation.json',spec)
    return evaluation.prepare(base/'evaluation.json')


@pytest.fixture
def bundle(prepared):
    b=deepcopy(prepared);b['tasks']=b['tasks'][:10]
    return b


def test_full_134_final_parent_no_learning_and_resume(tmp_path,prepared):
    assert len(prepared['tasks']) == 134
    assert 'rounds/R01/editor/' in prepared['parent'] # R02 retained R01, not latest Candidate.
    training = Path(prepared['configs']['S1']['skill_source']['campaign'])
    before = {str(p):bm.sha(p) for p in training.rglob('*') if p.is_file()}
    h=Fake(prepared)
    evaluation.run(tmp_path,bundle=prepared,runner=h)
    assert len(h.calls) == 134 and {g for g,_,_ in h.calls} == {'S1'}
    assert 1 < h.peak <= 8 if prepared['actor_max_workers'] == 8 else h.peak == 1
    assert not (tmp_path/'S0').exists()
    assert ev.read(tmp_path/'S1/summary.json')['completed'] == 134
    assert before == {str(p):bm.sha(p) for p in training.rglob('*') if p.is_file()}
    evaluation.run(tmp_path,bundle=prepared,runner=h,resume=True)
    assert len(h.calls) == 134


@pytest.mark.parametrize('workers',[1,8])
def test_partial_failure_resume(tmp_path,bundle,workers):
    bundle['actor_max_workers']=workers
    h=Fake(bundle);h.fail=('S1','test:0000')
    with pytest.raises(RuntimeError): evaluation.run(tmp_path,bundle=bundle,runner=h)
    good={p:p.read_bytes() for p in (tmp_path/'S1/episodes').glob('*/result.json')}
    h.fail=None;before=h.calls[:]
    evaluation.run(tmp_path,bundle=bundle,runner=h,resume=True)
    assert all(p.read_bytes()==content for p,content in good.items())
    goodids={p.parent.name.replace('_',':') for p in good}
    assert not any(t in goodids for _,t,_ in h.calls[len(before):])
    assert (tmp_path/'S1/episodes/test_0000/attempts/002/trajectory.json').exists()


def test_configuration_drift_and_group_drift(tmp_path,bundle):
    h=Fake(bundle);evaluation.run(tmp_path,bundle=bundle,runner=h)
    before=len(h.calls)
    with pytest.raises(ValueError,match='inputs changed'):
        evaluation.run(tmp_path,bundle=bundle,runner=h,resume=True,groups=('S0','S1'))
    bundle['actor_max_workers']=7
    with pytest.raises(ValueError,match='inputs changed'):
        evaluation.run(tmp_path,bundle=bundle,runner=h,resume=True)
    assert len(h.calls)==before


def test_unknown_wrong_skill_and_output_protection(tmp_path,bundle):
    h=Fake(bundle);dest=tmp_path/'attempt';dest.mkdir()
    p=h('S1','test:0000',bundle['parent'],dest,evaluation.actor_config(bundle));raw=ev.read(p)
    for change in ({'status':'error','error_type':'Timeout'},{'won':None}, {'skill':{'text':'wrong'}}):
        ev.save(p,{**raw,**change})
        with pytest.raises((ValueError,KeyError,TypeError)):
            evaluation.check_record(p,bundle['tasks'][0],'S1',bundle)
    bundle['configs']['S1']['skill_source']['campaign']=str(tmp_path)
    with pytest.raises(ValueError,match='training Campaign'):
        evaluation.run(tmp_path/'nested',bundle=bundle,runner=h)


def test_command_adapter_freezes_endpoint_and_final_skill(tmp_path,bundle,monkeypatch):
    from types import SimpleNamespace
    h=Fake(bundle);seen=[]
    def fake_process(cmd,**kwargs):
        assert cmd[:3]==['env','ALFWORLD_DATA='+bundle['configs']['S1']['environment']['data_root'],
                         'OPENAI_BASE_URL='+bundle['configs']['S1']['actor']['base_url']]
        assert cmd[cmd.index('--request-attempts')+1]=='3'
        assert cmd[cmd.index('--purpose')+1]=='final'
        assert cmd[cmd.index('--skill-file')+1]==bundle['parent']
        dest=Path(cmd[cmd.index('--output-root')+1]);seen.append(dest)
        h('S1',cmd[cmd.index('--task-id')+1],bundle['parent'],dest,evaluation.actor_config(bundle))
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(evaluation.subprocess,'run',fake_process)
    dest=tmp_path/'episode';dest.mkdir()
    evaluation.execute_task(bundle,'S1','test:0000',bundle['parent'],dest,evaluation.actor_config(bundle))
    assert seen==[dest]


def test_incomplete_and_test_mutation_rejected(prepared,tmp_path):
    spec=deepcopy(prepared['evaluation_spec'])
    cfg=config(1);ev.initialize(tmp_path/'unfinished',cfg)
    spec.update(campaign=str(tmp_path/'unfinished'),campaign_config=cfg)
    spec['campaign_config']['task_items']={}
    # A completed campaign cannot be substituted by an incomplete one.
    ev.save(tmp_path/'spec.json',spec)
    with pytest.raises((ValueError,KeyError)):evaluation.prepare(tmp_path/'spec.json')
    spec=deepcopy(prepared['evaluation_spec']);spec['tasks'][0]['id']='test:9999'
    ev.save(tmp_path/'spec.json',spec)
    with pytest.raises(ValueError,match='mapping'):evaluation.prepare(tmp_path/'spec.json')

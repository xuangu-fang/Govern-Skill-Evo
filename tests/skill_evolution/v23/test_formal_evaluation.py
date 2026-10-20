"""Formal Test orchestration is offline here; all episodes are synthetic fixtures."""
from copy import deepcopy
import importlib.util
from pathlib import Path
import threading
import time
import pytest
from src.skill_evolution.v23 import evolution as ev
from src.adapters.alfworld.skill_runtime import load_skill
from tests.skill_evolution.v23.test_grouping import record
from tests.skill_evolution.v23.test_replay_memory import records

PREP=ev.ROOT/'experiments/methods/v23/v23_alfworld_formal_001'
spec=importlib.util.spec_from_file_location('formal_evaluation',PREP/'evaluate.py')
evalmod=importlib.util.module_from_spec(spec);spec.loader.exec_module(evalmod)


@pytest.fixture(scope='module')
def prepared():return evalmod.prepare()


@pytest.fixture
def bundle(prepared):
    b=deepcopy(prepared);b['tasks']=b['tasks'][:10]
    return b


class Fake:
    def __init__(self,b):
        self.b=b;self.calls=[];self.active=0;self.peak=0;self.lock=threading.Lock();self.fail=None
    def __call__(self,g,t,skill,dest,cfg):
        with self.lock:
            self.active+=1;self.peak=max(self.peak,self.active);self.calls.append((g,t,str(dest)))
        try:
            n=int(t.split(':')[1]);time.sleep(0.01*(10-n%10))
            raw=records()[0]; success=(n%4 in ([0,1] if g=='S0' else [0,2]))
            raw.update(record(n,parent=None if g=='S0' else self.b['skill_text'],status='success' if success else 'step_limit',menus=[['look']]* (2 if success else 50)))
            raw.update(task=cfg['task_items'][t],split='test',purpose='final',model=cfg['actor_model'],
                       protocol=self.b['configs'][g]['actor']['execution_protocol'],
                       versions={k:self.b['configs'][g]['environment']['versions'][k] for k in ['alfworld','textworld','requests']},
                       skill=load_skill(skill),run_id=g+'-'+t+'-'+dest.name,
                       request_policy={'max_attempts':3,'strict_response':True},won=success)
            path=dest/'trajectory.json'
            if self.fail==(g,t):
                raw.update(status='error',error_type='Timeout');ev.save(path,raw);raise RuntimeError('Synthetic exhausted step request')
            ev.save(path,raw);return path
        finally:
            with self.lock:self.active-=1


def test_actual_freeze_and_official_final_parent(prepared):
    assert len(prepared['tasks'])==134
    assert prepared['parent'].endswith('S1/rounds/R05/editor/attempts/001/candidate.md')
    assert prepared['campaign_state']['next_round']==7
    assert prepared['configs']['S0']['actor']==prepared['configs']['S1']['actor']
    assert all('--skill-file' not in c for c in prepared['commands']['S0'].values())
    assert all(c[c.index('--skill-file')+1]==prepared['parent'] for c in prepared['commands']['S1'].values())


def test_parallel_order_complete_resume_and_pair_counts(tmp_path,bundle):
    h=Fake(bundle); evalmod.run(tmp_path,bundle=bundle,runner=h)
    assert 1<h.peak<=8 and len(h.calls)==20
    assert all(x[0]=='S0' for x in h.calls[:10]) and all(x[0]=='S1' for x in h.calls[10:])
    c=ev.read(tmp_path/'comparison/results.json')
    assert [p['task_id'] for p in c['pairs']]==[t['id'] for t in bundle['tasks']]
    assert sum(map(len,c['categories'].values()))==10
    assert c['categories']['fixed']==['test:0002','test:0006']
    assert c['categories']['regressed']==['test:0001','test:0005','test:0009']
    before=h.calls[:];evalmod.run(tmp_path,bundle=bundle,runner=h,resume=True);assert before==h.calls
    assert c==ev.read(tmp_path/'comparison/results.json')


@pytest.mark.parametrize('workers',[1,8])
def test_failure_stop_preservation_and_resume(tmp_path,bundle,workers):
    bundle['actor_max_workers']=workers;h=Fake(bundle);h.fail=('S0','test:0000')
    with pytest.raises(RuntimeError):evalmod.run(tmp_path,bundle=bundle,runner=h)
    assert not any(g=='S1' for g,_,_ in h.calls)
    assert not (tmp_path/'result.json').exists()
    completed={p:p.read_bytes() for p in (tmp_path/'S0').glob('episodes/*/result.json')}
    good={p.parent.name.replace('_',':') for p in completed}
    calls=h.calls[:];h.fail=None
    evalmod.run(tmp_path,bundle=bundle,runner=h,resume=True)
    assert all(p.read_bytes()==v for p,v in completed.items())
    assert not any(g=='S0' and t in good for g,t,_ in h.calls[len(calls):])
    attempts=tmp_path/'S0/episodes/test_0000/attempts'
    assert (attempts/'001/error.json').exists() and (attempts/'002/trajectory.json').exists()
    assert len(list(attempts.glob('*')))==2


def test_input_drift_rejected_without_calls(tmp_path,bundle):
    h=Fake(bundle);evalmod.run(tmp_path,bundle=bundle,runner=h)
    original=h.calls[:];bundle['actor_max_workers']=7
    with pytest.raises(ValueError,match='inputs changed'):evalmod.run(tmp_path,bundle=bundle,runner=h,resume=True)
    assert original==h.calls


def test_cannot_write_to_training_campaign(tmp_path,bundle):
    bundle['configs']['S1']['skill_source']['campaign']=str(tmp_path)
    with pytest.raises(ValueError,match='training Campaign'):evalmod.run(tmp_path/'nested',bundle=bundle,runner=Fake(bundle))


def test_unknown_result_and_wrong_skill_refused(tmp_path,bundle):
    h=Fake(bundle);cfg=evalmod.actor_config(bundle);dest=tmp_path/'attempt';dest.mkdir()
    p=h('S0','test:0000',None,dest,cfg);raw=ev.read(p)
    for bad in [{'status':'error','error_type':'Timeout'},{'won':None},{'skill':load_skill(bundle['parent'])}]:
        ev.save(p,{**raw,**bad})
        with pytest.raises((ValueError,TypeError)):evalmod.check_record(p,bundle['tasks'][0],'S0',bundle)


def test_retry_costs_reasoning_not_double_counted(tmp_path):
    ev.save(tmp_path/'trajectory.json',{'status':'error','steps':[{'phase':'responded','transport_attempts':[
        {'usage':{'prompt_tokens':10,'completion_tokens':5,'total_tokens':15,'completion_tokens_details':{'reasoning_tokens':3},'prompt_cache_hit_tokens':7}},
        {'usage':None}]}]})
    c=evalmod.costs(tmp_path)
    assert c['requests']==2 and c['retry_requests']==1 and c['unknown_usage_requests']==1
    assert c['total_tokens']==15 and c['reasoning_tokens']==3 and c['cached_tokens']==7
    assert c['technical_episode_attempts']==1 and c['unsuccessful_tokens']==15


def test_real_command_adapter_uses_isolated_output_and_frozen_flags(tmp_path,bundle,monkeypatch):
    from types import SimpleNamespace
    h=Fake(bundle);cfg=evalmod.actor_config(bundle);seen=[]
    def fake_process(cmd,**kwargs):
        group='S1' if '--skill-file' in cmd else 'S0'
        dest=Path(cmd[cmd.index('--output-root')+1]);task=cmd[cmd.index('--task-id')+1]
        skill=cmd[cmd.index('--skill-file')+1] if group=='S1' else None
        assert cmd[cmd.index('--request-attempts')+1]=='3'
        assert '--archive-responses' in cmd and '--strict-response' in cmd
        assert cmd[cmd.index('--purpose')+1]=='final' and cmd[cmd.index('--split')+1]=='test'
        assert cmd[:3]==['env','ALFWORLD_DATA='+bundle['configs'][group]['environment']['data_root'],
                         'OPENAI_BASE_URL='+bundle['configs'][group]['actor']['base_url']]
        seen.append(dest);h(group,task,skill,dest,cfg);return SimpleNamespace(returncode=0)
    monkeypatch.setattr(evalmod.subprocess,'run',fake_process)
    for group in ['S0','S1']:
        dest=tmp_path/group;dest.mkdir()
        p=evalmod.execute_task(bundle,group,'test:0000',None if group=='S0' else bundle['parent'],dest,cfg)
        assert p.is_relative_to(dest)
    assert len(set(seen))==2


def test_authorized_transport_recovery_is_narrow(prepared, tmp_path, monkeypatch):
    change=evalmod.recovery(evalmod.DEFAULT_ROOT)
    assert change is not None
    original=ev.read(evalmod.DEFAULT_ROOT/'input.json')
    restored=evalmod.recovered_input(evalmod.DEFAULT_ROOT,change)
    assert restored==prepared
    assert {k for k in original if original[k]!=restored[k]}=={'runner_sources'}
    ev.save(tmp_path/'recoveries/001.json',change)
    bad=deepcopy(change)
    bad['contract_changes']['src/adapters/alfworld/run_task_upstream.py']+='\n# unrelated change\n'
    ev.save(tmp_path/'recoveries/001.json',bad)
    with pytest.raises(ValueError,match='more than'):evalmod.recovery(tmp_path)
    actual=ev.frozen_contract();actual['src/skill_evolution/v23/grouping_prompt.md']+='changed'
    monkeypatch.setattr(ev,'frozen_contract',lambda:actual)
    with pytest.raises(ValueError,match='Frozen source'):evalmod.prepare()

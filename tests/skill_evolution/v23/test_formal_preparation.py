"""Static public-data checks and mocked handoff; no network or environment tasks."""
from copy import deepcopy
import importlib.util
from pathlib import Path
import socket
import subprocess
from types import SimpleNamespace

import pytest
from src.skill_evolution.v23 import evolution as ev
from src.adapters.alfworld.skill_runtime import validate_access, access_metadata, execution_protocol
from tests.skill_evolution.v23.test_evolution import Harness

ROOT = Path(__file__).resolve().parents[3]
PREP = ROOT/'experiments/methods/v23/v23_alfworld_formal_001'


def module(name):
    spec = importlib.util.spec_from_file_location('formal_'+name, PREP/(name+'.py'))
    obj = importlib.util.module_from_spec(spec); spec.loader.exec_module(obj)
    return obj


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('External process/network forbidden in preparation tests')
    monkeypatch.setattr(socket.socket, 'connect', forbidden)
    monkeypatch.setattr(subprocess, 'Popen', forbidden)


def test_actual_public_identities_and_local_games():
    data, mapping = module('prepare').load_and_verify()
    assert [len(data[k]) for k in ['train','val','test']] == [39,18,134]
    assert len(mapping) == len({x['local_gamefile'] for x in mapping}) == 191
    assert all(x['metadata_type_matches'] for x in mapping)


def test_official_order_and_complete_coverage():
    prep = module('prepare'); pool = ev.read(PREP/'data/optimization_pool.json')
    batches = prep.batches(pool)
    assert batches == prep.batches(deepcopy(pool)) == ev.read(PREP/'config/campaign.json')['batches']
    assert list(map(len,batches)) == [10,10,10,10,10,7]
    assert sum(batches,[]) == [x['id'] for x in pool]
    assert not set(sum(batches,[])) & {x['id'] for x in ev.read(PREP/'data/test.json')}
    assert ev.read(PREP/'data/batches.json')['shuffle'] is False
    assert ev.read(PREP/'data/batches.json')['seed'] == 42


def test_changed_pool_cannot_reuse_saved_batches(tmp_path):
    prep=module('prepare');pool=ev.read(PREP/'data/optimization_pool.json')
    path=tmp_path/'batches.json';prep.frozen(path,prep.batches(pool))
    pool[0],pool[1]=pool[1],pool[0]
    with pytest.raises(ValueError,match='changed'):
        prep.frozen(path,prep.batches(pool))


def test_configuration_matches_verified_route_and_protocol():
    cfg=ev.read(PREP/'config/campaign.json'); old=ev.read(ROOT/'experiments/methods/v23/v23_evolution_001/config/campaign.json')
    ev.validate_config(cfg)
    for key in old.keys()-{'batches','task_items','environment_files'}:
        assert cfg[key]==old[key]
    p=ev.read(PREP/'config/protocol.json')
    assert p['initial_parent'] is None and p['initial_memory']=={'entries':[],'sources':{}}
    assert p['actor']['execution_protocol']==execution_protocol(50)
    assert p['independent_validation'] is False


@pytest.mark.parametrize('split', ['train','val'])
def test_explicit_optimization_access(split):
    validate_access(split,'optimization')
    assert access_metadata(split,'optimization')=={'learning_allowed':True,'selection_allowed':False,'final_only':False}


@pytest.mark.parametrize('split,purpose', [('test','optimization'),('val','learning'),('test','learning')])
def test_original_boundaries_and_test_exclusion(split,purpose):
    with pytest.raises(ValueError):validate_access(split,purpose)


def test_undeclared_selection_and_test_rejected():
    cfg=ev.read(PREP/'config/campaign.json')
    del cfg['optimization_splits']
    with pytest.raises(ValueError):ev.validate_config(cfg)
    cfg=ev.read(PREP/'config/campaign.json');cfg['batches'][0][0]='test:0000'
    with pytest.raises(ValueError):ev.validate_config(cfg)


def test_actor_command_preserves_selection_identity_without_execution(tmp_path,monkeypatch):
    cfg=ev.read(PREP/'config/campaign.json');seen=[]
    monkeypatch.setenv('OPENAI_BASE_URL', cfg['actor_base_url'])
    def fake(cmd,**kwargs):
        seen.append((cmd,kwargs['env']))
        ev.save(tmp_path/'trajectory.json',{})
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(ev.subprocess,'run',fake)
    ev.actor_task('val:0000',None,tmp_path,cfg)
    cmd,env=seen[0]
    assert cmd[cmd.index('--split')+1]=='val'
    assert cmd[cmd.index('--purpose')+1]=='optimization'
    assert cmd[cmd.index('--task-id')+1]=='val:0000'
    assert env['ALFWORLD_DATA']==cfg['environment_root']
    assert env['OPENAI_BASE_URL']==cfg['actor_base_url']


def test_changed_mapping_rejected_before_actor(tmp_path,monkeypatch):
    cfg=ev.read(PREP/'config/campaign.json');cfg['task_items']['val:0000']['gamefile']='wrong'
    monkeypatch.setenv('OPENAI_BASE_URL', cfg['actor_base_url'])
    with pytest.raises(ValueError,match='mapping changed'):
        ev.actor_task('val:0000',None,tmp_path,cfg)


def test_s0_s1_share_test_execution_settings():
    s0=ev.read(PREP/'config/no_skill_eval.json');s1=ev.read(PREP/'config/v23_eval.json')
    for key in s0.keys()-{'group','skill_source','output_root'}:assert s0[key]==s1[key]
    commands=module('test_commands').commands(s0)
    assert len(commands)==134
    assert all('--skill-file' not in cmd and cmd[cmd.index('--purpose')+1]=='final' for cmd in commands)


@pytest.mark.parametrize('outcome',['ACCEPT','RETAIN'])
def test_six_rounds_with_partial_final_batch_and_final_skill(tmp_path,outcome):
    # Real module validators + deterministic fixture responses; every Actor is mocked.
    cfg=ev.read(PREP/'config/campaign.json');h=Harness(outcome)
    class Mixed(Harness):
        def actor(self,task,skill,dest,config):
            # Fixture helper uses train numeric IDs; restore real frozen source identity.
            path=super().actor(task,skill,dest,config);r=ev.read(path)
            split=task.split(':')[0]
            r.update(task=config['task_items'][task],split=split,purpose='optimization',model=config['actor_model'],
                     access=access_metadata(split,'optimization'),
                     request_policy={'max_attempts':3,'strict_response':True})
            ev.save(path,r);return path
    h=Mixed(outcome)
    result=ev.run_campaign(tmp_path,config=cfg,generate=h.generate,actor_runner=h.actor)
    assert result['status']=='complete' and result['state']['next_round']==7
    assert len(h.actor_calls)==114 and len(h.calls)==30
    assert len(h.memories)==6 and h.memories[0]['entries']==[] and h.memories[1]['entries']
    assert ev.read(tmp_path/'rounds/R06/gate/result.json')['result']['compared']==7
    skill=ev.final_parent(tmp_path)
    assert (skill is not None)==(outcome=='ACCEPT')
    final_cmds=module('test_commands').commands(ev.read(PREP/'config/v23_eval.json'),tmp_path)
    assert len(final_cmds)==134
    assert all(('--skill-file' in cmd)==(outcome=='ACCEPT') for cmd in final_cmds)
    ev.run_campaign(tmp_path,resume=True,generate=h.generate,actor_runner=h.actor)
    assert len(h.actor_calls)==114 and len(h.calls)==30


def test_final_skill_refuses_incomplete_campaign(tmp_path):
    ev.initialize(tmp_path,ev.read(PREP/'config/campaign.json'))
    with pytest.raises(ValueError,match='not complete'):ev.final_parent(tmp_path)


def test_preparation_does_not_create_or_modify_official_state():
    root=ROOT/'artifacts/methods/v23/v23_alfworld_formal_001'
    before={p:p.read_bytes() for p in root.rglob('state.json')}
    module('prepare').build()
    assert before=={p:p.read_bytes() for p in root.rglob('state.json')}
    assert not list(PREP.rglob('state.json'))
    assert not list(PREP.rglob('trajectory.json'))


def test_preparation_is_repeatable_without_mutation():
    prep=module('prepare')
    files=list(PREP.glob('data/*.json'))+list(PREP.glob('config/*.json'))
    old={p:p.read_bytes() for p in files}
    state=ROOT/'artifacts/methods/v23/v23_evolution_001/state.json';previous=state.read_bytes()
    prep.build()
    assert old=={p:p.read_bytes() for p in files}
    assert state.read_bytes()==previous

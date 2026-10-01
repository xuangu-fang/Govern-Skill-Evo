from pathlib import Path
import pytest
from tests.skill_evolution.test_local_campaign_v19 import setup
from src.skill_evolution.campaign_v19 import run_campaign_v19
from src.skill_evolution.memory_restart_v19 import prepare_memory_restart,MemoryRestart,ENTRYPOINT,files,_ManifestView
from src.skill_evolution.memory_store_v19 import load_memory
from src.skill_evolution.evolution_replay_v19 import _load


def migrate(kw,tmp_path):
    return prepare_memory_restart(source=kw['output'],archive=tmp_path/'archive',output=tmp_path/'new',
                                  evolution=kw['evolution_backend'],monitor=kw['monitor_backend'])


def test_migrate_resume_no_upstream_calls_empty_memory(setup,tmp_path):
    kw,calls=setup
    kw['entrypoint']=ENTRYPOINT
    run_campaign_v19(**kw)
    before=files(kw['output'])
    migrate(kw,tmp_path)
    assert files(kw['output'])==before==files(tmp_path/'archive')
    new=tmp_path/'new'
    assert load_memory(new/'memory').head['revision']==0
    assert not (new/'round-02').exists()
    assert not (new/'round-01/generation/local-reviews').exists()
    recovery=MemoryRestart(new/'migration.json')
    # Test backends do not have production's manifest recovery hook.
    evo=_ManifestView(kw['evolution_backend'],recovery.receipt['original_binding']['evolution_manifest'])
    mon=_ManifestView(kw['monitor_backend'],recovery.receipt['original_binding']['monitor_manifest'])
    previous=calls.copy();rollouts=kw['evolution_backend'].calls.copy()
    def stop(stage,round_id):
        if stage=='ISSUE_FUSION':raise KeyboardInterrupt()
    with pytest.raises(KeyboardInterrupt):
        run_campaign_v19(**{**kw,'output':new,'evolution_backend':evo,'monitor_backend':mon},
                        source_recovery=recovery,resume=True,event_hook=stop)
    assert calls==previous
    assert kw['evolution_backend'].calls==rollouts
    assert _load(new/'round-01/generation/historical-reviews.json')['reviews']==[]
    run_campaign_v19(**{**kw,'output':new,'evolution_backend':evo,'monitor_backend':mon},
                    source_recovery=recovery,resume=True)
    assert load_memory(new/'memory').head['revision']==2
    assert calls['current']==previous['current']+1 # only round 2 rediscovers
    assert files(kw['output'])==before==files(tmp_path/'archive')
    with pytest.raises(ValueError,match='already exists'):migrate(kw,tmp_path)


@pytest.mark.parametrize('kind',['finding','manifest','upstream_source','missing_response'])
def test_reject_invalid_import(setup,tmp_path,kind):
    kw,_=setup;kw['entrypoint']=ENTRYPOINT;run_campaign_v19(**kw)
    from src.skill_evolution.evolution_replay_v19 import _save
    if kind=='finding':
        path=kw['output']/'round-01/generation/current-000-findings.json'
        data=_load(path);data['summary']='tampered';_save(path,data)
    elif kind=='manifest':kw['evolution_backend'].tasks.append('different')
    elif kind=='upstream_source':
        path=kw['output']/'binding.json';data=_load(path)
        data['source_files']['src/skill_evolution/current_diagnosis_v19.py']='wrong';_save(path,data)
    else:
        (kw['output']/'round-01/generation/current-000/response_complete.json').unlink()
    with pytest.raises(ValueError):migrate(kw,tmp_path)
    assert not (tmp_path/'new').exists()
    assert not (tmp_path/'archive').exists()


def test_reject_archive_or_import_tamper(setup,tmp_path):
    kw,_=setup;kw['entrypoint']=ENTRYPOINT;run_campaign_v19(**kw);migrate(kw,tmp_path)
    recovery=MemoryRestart(tmp_path/'new/migration.json')
    (tmp_path/'archive/extra.txt').write_text('tampered')
    with pytest.raises(ValueError,match='archive changed'):recovery.verify_reused_artifacts(tmp_path/'new')


def test_active_source_and_overlapping_paths_rejected(setup,tmp_path):
    from src.skill_evolution.evolution_replay_v19 import _lock
    kw,_=setup;kw['entrypoint']=ENTRYPOINT;run_campaign_v19(**kw)
    with _lock(kw['output']),pytest.raises(ValueError,match='already running'):
        migrate(kw,tmp_path)
    with pytest.raises(ValueError,match='disjoint'):
        prepare_memory_restart(source=kw['output'],archive=kw['output']/'archive',output=tmp_path/'new',
                               evolution=kw['evolution_backend'],monitor=kw['monitor_backend'])
    assert not (tmp_path/'new').exists()


def test_import_and_code_drift_rejected(setup,tmp_path,monkeypatch):
    import src.skill_evolution.memory_restart_v19 as module
    kw,_=setup;kw['entrypoint']=ENTRYPOINT;run_campaign_v19(**kw);migrate(kw,tmp_path)
    recovery=MemoryRestart(tmp_path/'new/migration.json')
    p=tmp_path/'new/round-01/generation/current-000-findings.json'
    original=p.read_bytes();p.write_text('{}')
    with pytest.raises(ValueError,match='upstream artifact changed'):recovery.verify_reused_artifacts(tmp_path/'new')
    p.write_bytes(original)
    monkeypatch.setattr(module,'source_manifest',lambda:{})
    with pytest.raises(ValueError,match='source drift'):MemoryRestart(tmp_path/'new/migration.json')


def test_manifest_bridge_only_allows_code_identity_change():
    from src.skill_evolution.memory_restart_v19 import compatible_manifest
    from copy import deepcopy
    old={'schema_version':'evolution_manifest_v19.1','task_ids':['T1'],'seed':1,
         'runtime':{'v19_source_files':{'memory.py':'old'},'freeze_manifest_sha256':'frozen'}}
    new=deepcopy(old);new['runtime']['v19_source_files']={'memory.py':'new'}
    compatible_manifest(old,new)
    new['seed']=2
    with pytest.raises(ValueError,match='configuration'):compatible_manifest(old,new)

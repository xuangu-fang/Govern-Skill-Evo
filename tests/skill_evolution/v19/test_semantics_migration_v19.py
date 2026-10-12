from dataclasses import replace
import pytest
from tests.skill_evolution.v19.test_local_campaign_v19 import setup
from tests.skill_evolution.v19.test_attribution_pairs_v19 import transport
from src.skill_evolution.v19.campaign_v19 import run_campaign_v19
from src.skill_evolution.v19.memory_restart_v19 import ENTRYPOINT, files, _ManifestView
from src.skill_evolution.v19.semantics_migration_v19 import prepare_semantics_migration, SemanticsMigration
from src.skill_evolution.v19.memory_store_v19 import load_memory
from src.skill_evolution.v19.evolution_replay_v19 import _load


def source_run(kw):
    kw['config']['attribution_protocol']='pair';kw['entrypoint']=ENTRYPOINT
    kw['transports']=replace(kw['transports'],attribution=transport)
    def stop(stage,round_id):
        if stage=='GROUPING' and round_id=='round-02':raise KeyboardInterrupt()
    with pytest.raises(KeyboardInterrupt):run_campaign_v19(**kw,event_hook=stop)


def migrate(kw,tmp_path):
    return prepare_semantics_migration(source=kw['output'],archive=tmp_path/'archive',output=tmp_path/'new',
        evolution=kw['evolution_backend'],monitor=kw['monitor_backend'])


def test_offline_recommit_resume_and_immutability(setup,tmp_path):
    kw,calls=setup;source_run(kw);before=files(kw['output']);counts=calls.copy()
    parent_calls=kw['evolution_backend'].calls.copy()
    assert migrate(kw,tmp_path)['status']=='READY'
    assert before==files(kw['output'])==files(tmp_path/'archive')
    assert counts==calls and parent_calls==kw['evolution_backend'].calls
    recovery=SemanticsMigration(tmp_path/'new/migration.json')
    assert load_memory(tmp_path/'new/memory').head['revision']==1
    evo=_ManifestView(kw['evolution_backend'],recovery.receipt['original_binding']['evolution_manifest'])
    mon=_ManifestView(kw['monitor_backend'],recovery.receipt['original_binding']['monitor_manifest'])
    result=run_campaign_v19(**{**kw,'output':tmp_path/'new','evolution_backend':evo,'monitor_backend':mon},
                           resume=True,source_recovery=recovery)
    assert result['committed_rounds']==2
    assert calls['current']==counts['current']+1
    assert before==files(kw['output'])==files(tmp_path/'archive')
    with pytest.raises(ValueError,match='already exists'):migrate(kw,tmp_path)


def test_unanswered_grouping_archived_before_resume(setup,tmp_path):
    kw,calls=setup;kw['config']['attribution_protocol']='pair';kw['entrypoint']=ENTRYPOINT
    original=kw['transports'].grouping
    def grouping(request):
        if calls['grouping']==1:raise KeyboardInterrupt()
        return original(request)
    kw['transports']=replace(kw['transports'],attribution=transport,grouping=grouping)
    with pytest.raises(KeyboardInterrupt):run_campaign_v19(**kw)
    migrate(kw,tmp_path)
    new=tmp_path/'new'
    assert not (new/'round-02/grouping/attempt-1').exists()
    assert (new/'recovery/migration-attempt-1/call/request.json').exists()
    assert (kw['output']/'round-02/grouping/attempt-1/request.json').exists()
    recovery=SemanticsMigration(new/'migration.json')
    kw['transports']=replace(kw['transports'],grouping=original)
    assert run_campaign_v19(**{**kw,'output':new},resume=True,source_recovery=recovery)['committed_rounds']==2


@pytest.mark.parametrize('tamper',['archive','memory','generation'])
def test_reject_invalid_migration(setup,tmp_path,tamper):
    kw,_=setup;source_run(kw)
    if tamper=='generation':
        (kw['output']/'round-02/generation').mkdir()
        with pytest.raises(ValueError,match='generation exists'):migrate(kw,tmp_path)
        return
    migrate(kw,tmp_path);recovery=SemanticsMigration(tmp_path/'new/migration.json')
    if tamper=='archive':(tmp_path/'archive/extra').write_text('x')
    else:(tmp_path/'new/memory/head.json').write_text('{}')
    with pytest.raises((ValueError,KeyError)):recovery.verify_reused_artifacts(tmp_path/'new')


def test_v19_2_commit_rebuilt_with_new_head(setup,tmp_path,monkeypatch):
    from src.skill_evolution.v19 import attribution_pairs_v19 as pairs
    kw,_=setup;aggregate=pairs.aggregate
    def legacy(data,results,*,facts_only=False):
        return aggregate(data,results,facts_only=facts_only)
    with monkeypatch.context() as patch:
        patch.setattr(pairs,'aggregate',legacy)
        source_run(kw)
    old=load_memory(kw['output']/'memory')
    assert old.rounds[0]['attribution']['schema_version']=='attribution_batch_v19.2'
    migrate(kw,tmp_path)
    new=load_memory(tmp_path/'new/memory')
    assert new.rounds[0]['attribution']['schema_version']=='attribution_batch_v19.3'
    assert new.head['memory_ref']!=old.head['memory_ref']
    assert new.head['retained_skill']==old.head['retained_skill']
    assert new.rounds[0]['record']['gate_decision']==old.rounds[0]['record']['gate_decision']
    assert new.history[0].ledger==old.history[0].ledger
    assert new.rounds[0]['replay']==old.rounds[0]['replay']

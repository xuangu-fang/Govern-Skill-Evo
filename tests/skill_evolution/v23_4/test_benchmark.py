"""Freeze real manifests and runtime metadata without invoking Actor or a model."""
from copy import deepcopy
import pytest
from src.skill_evolution.v23_4 import benchmark as bm, evolution as ev


def test_preparation_parity_idempotence_and_no_calls(tmp_path):
    experiment=tmp_path/'experiment'; campaign=tmp_path/'S1'
    result=bm.prepare(experiment,campaign)
    assert result['optimization_tasks']==57 and result['rounds']==6 and result['test_tasks']==134
    assert result['state']=={'next_round':1,'parent':None,'active_memory':'initial_memory'}
    assert not (campaign/'rounds').exists() and not list(campaign.rglob('request.json'))
    cfg=ev.read(experiment/'config/campaign.json')
    old=ev.read(experiment/'config/provenance.json')['baseline_effective_config']
    assert bm.comparable_configuration(cfg)==bm.comparable_configuration(old)
    assert cfg['actor_model']==cfg['call_config']['model']=='deepseek-v4.1-flash'
    assert cfg['actor_base_url']=='http://llm-proxy.intra.xiaojukeji.com'
    assert cfg['call_config']['endpoint']==cfg['actor_base_url']+'/chat/completions'
    assert cfg['method']==ev.METHOD and cfg['budget']['unique_tasks']==57
    assert cfg['call_config']['max_tokens']==16384 and cfg['max_input_chars']==4000000
    assert cfg['max_message_utf8_bytes']==6000000
    assert ev.read(campaign/'runtime.json')['packages']==ev.read(experiment/'config/evaluation.json')['environment']['versions']
    before={str(p):bm.sha(p) for root in [experiment,campaign] for p in root.rglob('*') if p.is_file()}
    assert bm.prepare(experiment,campaign)==result
    assert before=={str(p):bm.sha(p) for root in [experiment,campaign] for p in root.rglob('*') if p.is_file()}
    cfg['max_steps']=49;ev.save(experiment/'config/campaign.json',cfg)
    with pytest.raises(ValueError):bm.verify(experiment)


def test_drift_rejected_before_execution(tmp_path,monkeypatch):
    experiment=tmp_path/'experiment';campaign=tmp_path/'S1';bm.prepare(experiment,campaign)
    changed=deepcopy(ev.frozen_contract());changed['src/skill_evolution/v23_3/memory_view.py']+='\n# changed'
    monkeypatch.setattr(ev,'frozen_contract',lambda:changed)
    with pytest.raises(ValueError,match='Frozen source'):bm.verify(experiment)
    assert not (campaign/'rounds').exists()


def test_never_prepare_over_old_campaign(tmp_path):
    with pytest.raises(ValueError,match='overwrite'):bm.prepare(tmp_path,bm.BASE_CAMPAIGN)

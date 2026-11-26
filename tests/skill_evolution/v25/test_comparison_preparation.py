"""Prepare both methods from defaults, without model calls or task execution."""
from copy import deepcopy
from pathlib import Path
import sys

import pytest

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts/runs'))
import prepare_spreadsheetbench_comparison as prep
from src.skill_evolution.v25 import baseline, evolution as ev
from src.skill_evolution.v25.benchmark import using_benchmark
from src.skill_evolution.v25.benchmarks.spreadsheetbench.adapter import SpreadsheetBenchAdapter
from src.skill_evolution.v25.config import KNOWLEDGE_REVIEW
from .support import config


def test_latest_defaults_need_no_manual_overrides():
    c=baseline.configuration({},[],[])
    baseline.validate_latest_configuration(c)
    assert c['actor_max_workers']==4
    assert c['actor_profile']['actor_task_timeout_seconds']==0
    assert c['actor_profile']['attempt_budget_policy']=='program_executions_v1'
    assert c['actor_profile']['actor_history_policy']=='execution_only_v1'
    assert c['actor_profile']['actor_max_output_tokens']==49152
    expected = {
        'grouping':16384,'diagnosis':32768,'preconditioner':49152,'editor':16384,
        'replay':49152}
    assert {n:ev.stage_call_config(c,n)['max_tokens'] for n in ev.enabled_modules(c)} == expected
    reviewed = baseline.configuration({}, [], [], knowledge_review=KNOWLEDGE_REVIEW)
    assert {n:ev.stage_call_config(reviewed,n)['max_tokens'] for n in ev.enabled_modules(reviewed)} == {
        **expected, 'verifier':49152, 'repair':32768}


@pytest.mark.parametrize('change',[
    {'actor_max_workers':1}, {'actor_task_timeout_seconds':600},
    {'attempt_budget_policy':None}, {'actor_history_policy':None},
    {'actor_max_output_tokens':32768}, {'module_max_tokens':{}},
    {'comparison_profile':'unknown'},
])
def test_latest_profile_rejects_partial_upgrade(tmp_path,change):
    fixture=config(tmp_path/'data',n=1)
    c=baseline.configuration(fixture['task_items'],fixture['batches'],[],fixture=True)
    for key,value in change.items():
        target=c['actor_profile'] if key in c['actor_profile'] else c
        if value is None:target.pop(key)
        else:target[key]=value
    with using_benchmark(SpreadsheetBenchAdapter()),pytest.raises(ValueError):ev.validate_config(c)


def test_prepare_pair_and_reject_drift_without_starting(tmp_path,monkeypatch):
    fixture=config(tmp_path/'data',n=15,rounds=8)
    shared=baseline.configuration(fixture['task_items'],fixture['batches'],[],fixture=True)
    source=prep.bridge.read(prep.DEFAULT_TEMPLATE)
    source['native']['optimization_case_ids']=[t for b in shared['batches'] for t in b]
    template=tmp_path/'native.json';prep.bridge.write(template,source);before=template.read_bytes()
    def prepare(directory):
        prep.bridge.write(directory/'config/campaign.json',shared)
        (directory/'config/initial_skill.md').write_text(shared['initial_skill']['text'])
    monkeypatch.setattr(baseline,'prepare',prepare)
    monkeypatch.setattr(prep.bridge.executor,'runtime_snapshot',lambda _: {'fixture':'runtime'})
    monkeypatch.setattr(SpreadsheetBenchAdapter,'runtime_snapshot',staticmethod(lambda _: {'fixture':'runtime'}))
    monkeypatch.setattr(prep.bridge.subprocess,'check_output',lambda *a,**kw:'fixture-image\n')
    output=tmp_path/'pair'
    report=prep.prepare_pair(output,template=template)
    assert report['status']=='passed' and not report['training_artifacts_present']
    assert report['model_requests']==0 and report['actor_workers']==4
    assert report['batch_sizes']==[15]*8 and report['actor_evidence_view']=='execution_only_v1'
    assert report['actor_max_tokens']==49152 and report['optimizer_max_tokens']==16384
    assert prep.bridge.read(output/'skilladam/shared_config.json')==shared
    cfg=prep.bridge.read(output/'skilladam/skilladam.json')
    assert cfg['native']==source['native'] and cfg['optimizer_transport']==source['optimizer_transport']
    assert template.read_bytes()==before
    assert not list(output.rglob('actor_state.json')) and not list(output.rglob('checkpoint.json'))
    assert prep.check_pair(output)['status']=='passed'
    with pytest.raises(ValueError,match='new directory'):prep.prepare_pair(output,template=template)
    altered=deepcopy(shared);altered['actor_profile']['actor_max_output_tokens']=32768
    prep.bridge.write(output/'skilladam/shared_config.json',altered)
    with pytest.raises(ValueError,match='Frozen input changed'):prep.check_pair(output)


def test_skilladam_cli_requires_explicit_experiment():
    with pytest.raises(SystemExit) as exc:prep.bridge.main(['--check'])
    assert exc.value.code==2

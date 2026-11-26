"""Orchestration checks only. No network, model or Docker invocation."""
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
import sys
from types import SimpleNamespace
import pytest
from scripts.runs.spreadsheetbench.schedules.v25_1_skilladam_run_20261030_001.launcher import common, control, worker


def test_test_barrier_requires_both_completions_and_unchanged_skills(tmp_path,monkeypatch):
    monkeypatch.setattr(common,'HOME',tmp_path)
    settings={'arms':{}}
    for side in ['v25_1','skilladam']:
        folder=tmp_path/side/'data';folder.mkdir(parents=True)
        settings['arms'][side]={'folder':str(folder)}
        (folder/'final_skill.md').write_text('frozen skill')
        common.save(folder/'training_complete.json',{'status':'complete','rounds':8,
            'skill_sha256':common.sha(folder/'final_skill.md')})
        common.save(tmp_path/side/'validation.json',{'status':'validated','rounds':8,
            'files':{n:common.sha(folder/n) for n in ['final_skill.md','training_complete.json']}})
    assert len(common.barrier(settings))==2
    (tmp_path/'skilladam/data/final_skill.md').write_text('modified')
    with pytest.raises(ValueError,match='changed'):common.barrier(settings)
    (tmp_path/'skilladam/data/final_skill.md').write_text('frozen skill')
    (tmp_path/'skilladam/validation.json').unlink()
    with pytest.raises(FileNotFoundError):common.barrier(settings)


def test_duplicate_phase_launch_cannot_spawn(tmp_path,monkeypatch):
    monkeypatch.setattr(control,'HOME',tmp_path)
    common.save(tmp_path/'v25_1/train_launch.json',{'reserved':True})
    monkeypatch.setattr(control.subprocess,'Popen',lambda *a,**k:pytest.fail('Duplicate process launch'))
    with pytest.raises(ValueError,match='already exists'):
        control.launch({'python':'unused'},'v25_1','train')


def test_native_success_cache_and_failure_do_not_add_requests(tmp_path):
    from src.skill_evolution.skilladam.spreadsheetbench.aligned_actor import binding
    native,bridge,cfg,opt=binding.components()
    from skilladam.execution.contracts import GenerationRequest,GenerationResult
    request=GenerationRequest('trajectory_compression',({'role':'user','content':'synthetic'},),bridge.context_for(cfg,opt),{})
    calls=[]
    def success(request):calls.append(request);return GenerationResult('synthetic summary')
    native.native_transport=lambda *a,**k:SimpleNamespace(generate=success)
    b=worker.cached_native(native,bridge,cfg,opt,tmp_path/'success','offline-key')
    assert b.generate(request).text=='synthetic summary'
    b=worker.cached_native(native,bridge,cfg,opt,tmp_path/'success','offline-key')
    assert b.generate(request).text=='synthetic summary' and len(calls)==1
    def failure(request):calls.append(request);raise ValueError('synthetic failure')
    native.native_transport=lambda *a,**k:SimpleNamespace(generate=failure)
    b=worker.cached_native(native,bridge,cfg,opt,tmp_path/'failure','offline-key')
    with pytest.raises(ValueError,match='synthetic failure'):b.generate(request)
    count=len(calls)
    b=worker.cached_native(native,bridge,cfg,opt,tmp_path/'failure','offline-key')
    with pytest.raises(ValueError,match='explicit recovery required'):b.generate(request)
    assert len(calls)==count

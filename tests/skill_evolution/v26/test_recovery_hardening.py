from copy import deepcopy
from pathlib import Path

import pytest

from src.skill_evolution.v26.benchmark import using_benchmark
from src.skill_evolution.v26 import stages, evolution as ev
from src.skill_evolution.v26.transport import RequestFailure
from src.skill_evolution.v26.config import validate_config
from .test_campaign import campaign
from .test_stages import stage_case


@pytest.mark.parametrize('kind', ['technical', 'output'])
def test_v25_linear_backoff_only_between_retryable_requests(stage_case, monkeypatch, kind):
    adapter, good, prepare = stage_case; calls = []; waits = []
    monkeypatch.setattr(stages.time, 'sleep', waits.append)
    def generate(name, messages, path, cfg):
        calls.append(1)
        if len(calls) < 3:
            if kind == 'technical': raise RequestFailure('temporary')
            return {'content': '{}', 'finish_reason': 'stop'}
        return good(name, messages, path, cfg)
    with using_benchmark(adapter):
        directory, call, kwargs = prepare()
        stages.run_stage(directory, call, generate=generate, retry_delay_seconds=2.5, **kwargs)
        assert waits == [2.5, 5]
        stages.run_stage(directory, call, generate=None, read_only=True, retry_delay_seconds=2.5, **kwargs)
        assert waits == [2.5, 5]
        with pytest.raises(ValueError, match='Frozen value changed'):
            stages.run_stage(directory, call, generate=generate, resume=True, retry_delay_seconds=3, **kwargs)


def test_backoff_exhaustion_and_resume_do_not_wait_or_request_again(stage_case, monkeypatch):
    adapter, _, prepare = stage_case; waits = []
    monkeypatch.setattr(stages.time, 'sleep', waits.append)
    def fail(*args): raise RequestFailure('temporary')
    with using_benchmark(adapter):
        directory, call, kwargs = prepare()
        for resume in (False, True):
            with pytest.raises(stages.Stopped, match='exhausted'):
                stages.run_stage(directory, call, generate=fail, resume=resume, retry_delay_seconds=2, **kwargs)
    assert waits == [2, 4, 6, 8, 10]


@pytest.mark.parametrize('delay', [-1, float('nan'), float('inf'), True, '2'])
def test_invalid_backoff_rejected_in_config_and_stage(campaign, stage_case, delay):
    _, adapter, _, config, _ = campaign(); config['retry_delay_seconds'] = delay
    with using_benchmark(adapter), pytest.raises(ValueError, match='retry delay'): validate_config(config)
    adapter, good, prepare = stage_case
    with using_benchmark(adapter):
        directory, call, kwargs = prepare()
        with pytest.raises(ValueError, match='retry delay'):
            stages.run_stage(directory, call, generate=good, retry_delay_seconds=delay, **kwargs)
    assert not good.calls


@pytest.mark.parametrize('slot', [1, 6])
@pytest.mark.parametrize('point', ['mkdir', 'request_context.json', 'messages.json', 'prompt.md', 'before_start', 'after_start'])
def test_preparation_crash_recovers_reserved_slot_without_reset(stage_case, monkeypatch, slot, point):
    adapter, good, prepare = stage_case; calls = []; crashed = False
    original_save, original_text, original_mkdir = stages.save, stages.freeze_text, Path.mkdir
    def target(path): return path.parent.name == f'{slot:03}' and path.parent.parent.name == 'attempts'
    def interrupt():
        nonlocal crashed
        if not crashed:
            crashed = True; raise KeyboardInterrupt('Preparation fault injection')
    def save(path, value):
        if target(path) and point == 'before_start' and path.name == 'request_started.json': interrupt()
        result = original_save(path, value)
        if target(path) and (path.name == point or point == 'after_start' and path.name == 'request_started.json'): interrupt()
        return result
    def freeze_text(path, value, **kwargs):
        result = original_text(path, value, **kwargs)
        if target(path) and path.name == point: interrupt()
        return result
    def mkdir(path, *args, **kwargs):
        result = original_mkdir(path, *args, **kwargs)
        if point == 'mkdir' and path.name == f'{slot:03}' and path.parent.name == 'attempts': interrupt()
        return result
    def generate(name, messages, path, cfg):
        calls.append(path.name)
        if int(path.name) < slot: raise RequestFailure('temporary')
        return good(name, messages, path, cfg)
    with using_benchmark(adapter):
        directory, call, kwargs = prepare()
        monkeypatch.setattr(stages, 'save', save); monkeypatch.setattr(stages, 'freeze_text', freeze_text)
        monkeypatch.setattr(Path, 'mkdir', mkdir)
        with pytest.raises(KeyboardInterrupt): stages.run_stage(directory, call, generate=generate, **kwargs)
        assert len(calls) == slot-1
        with pytest.raises(ValueError, match='explicit resume'):
            stages.run_stage(directory, call, generate=generate, **kwargs)
        if point == 'after_start' and slot == 6:
            with pytest.raises(stages.Stopped, match='exhausted'):
                stages.run_stage(directory, call, generate=generate, resume=True, **kwargs)
            assert len(calls) == 5
        else:
            selected, _ = stages.run_stage(directory, call, generate=generate, resume=True, **kwargs)
            expected = slot+1 if point == 'after_start' else slot
            assert selected.name == f'{expected:03}' and len(calls) == slot
            stages.run_stage(directory, call, generate=None, read_only=True, **kwargs)
            assert len(calls) == slot


@pytest.mark.parametrize('artifact', ['response.json', 'request.json', 'messages.json'])
def test_unstarted_slot_does_not_hide_response_or_overwrite_corruption(stage_case, artifact):
    adapter, good, prepare = stage_case
    with using_benchmark(adapter):
        directory, call, kwargs = prepare()
        def crash(*args): raise KeyboardInterrupt()
        # Crash before any request slot exists, retaining the stage identity.
        with pytest.raises(ValueError, match='generator'):
            stages.run_stage(directory, call, generate=None, **kwargs)
        slot = directory / 'attempts/001'; slot.mkdir()
        stages.save(slot / artifact, {'corrupt': 'sentinel'})
        with pytest.raises(ValueError): stages.run_stage(directory, call, generate=good, resume=True, **kwargs)
        assert stages.read(slot / artifact) == {'corrupt': 'sentinel'}
    assert not good.calls


@pytest.mark.parametrize('generate', [None, False, 'not callable'])
def test_missing_generator_prevents_new_parent_actor_requests(campaign, generate):
    root, adapter, provider, config, _ = campaign()
    with using_benchmark(adapter), pytest.raises(ValueError, match='before new Actor'):
        ev.run_campaign(root, config=config, generate=generate)
    assert not provider.requests and not (root / 'rounds/R01/parent_runs').exists()


def test_missing_generator_prevents_candidate_requests_after_cached_editor(campaign):
    root, adapter, provider, config, generate = campaign()
    def crash(phase):
        if phase == 'candidate_runs': raise KeyboardInterrupt()
    with using_benchmark(adapter):
        with pytest.raises(KeyboardInterrupt): ev.run_campaign(root, config=config, generate=generate, hook=crash)
        with pytest.raises(ValueError, match='before new Actor'): ev.run_campaign(root, resume=True)
        assert len(provider.requests) == 1
        ev.run_campaign(root, generate=generate, resume=True)
    assert len(provider.requests) == 2 and len(generate.calls) == 6


def test_archive_only_publication_and_complete_journal_rewrap_need_no_generator(campaign):
    root, adapter, provider, config, generate = campaign()
    def crash(phase):
        if phase == 'before_publish': raise KeyboardInterrupt()
    with using_benchmark(adapter):
        with pytest.raises(KeyboardInterrupt): ev.run_campaign(root, config=config, generate=generate, hook=crash)
        # Simulate interruption before the Campaign's aggregate markers were saved:
        # native journals and exact evidence batch identities still exist.
        for side in ('parent_runs', 'candidate_runs'):
            (root / 'rounds/R01' / side / 'records.json').unlink()
        counts = (len(provider.requests), len(generate.calls))
        ev.run_campaign(root, resume=True, generate=None)
        ev.final_parent(root)
        assert (len(provider.requests), len(generate.calls)) == counts


def test_campaign_passes_and_freezes_method_backoff(campaign, monkeypatch):
    root, adapter, provider, config, good = campaign(); config['retry_delay_seconds'] = 3
    waits = []; first = True
    monkeypatch.setattr(stages.time, 'sleep', waits.append)
    def generate(*args):
        nonlocal first
        if first: first = False; raise RequestFailure('temporary')
        return good(*args)
    with using_benchmark(adapter):
        ev.run_campaign(root, config=config, generate=generate)
        ev.run_campaign(root, generate=None)
    assert waits == [3]
    assert stages.read(root / 'rounds/R01/grouping/identity.json')['retry_delay_seconds'] == 3


def test_preparation_recovery_preserves_latest_format_feedback(stage_case, monkeypatch):
    adapter, good, prepare = stage_case; sent = []; crashed = False
    original = stages.save
    def save(path, value):
        nonlocal crashed
        original(path, value)
        if path.name == 'messages.json' and path.parent.name == '002' and not crashed:
            crashed = True; raise KeyboardInterrupt()
    def generate(name, messages, path, cfg):
        sent.append(deepcopy(messages))
        if path.name == '001': return {'content': '{}', 'finish_reason': 'stop'}
        return good(name, messages, path, cfg)
    with using_benchmark(adapter):
        directory, call, kwargs = prepare(); monkeypatch.setattr(stages, 'save', save)
        with pytest.raises(KeyboardInterrupt): stages.run_stage(directory, call, generate=generate, **kwargs)
        saved_messages = stages.read(directory / 'attempts/002/messages.json')
        selected, _ = stages.run_stage(directory, call, generate=generate, resume=True, **kwargs)
    assert selected.name == '002' and sent[-1] == saved_messages
    assert len(sent[-1]) == 4 and sent[-1][2]['content'] == '{}'


def test_campaign_saved_last_module_response_recovers_without_generator(campaign):
    root, adapter, provider, config, good = campaign()
    def generate(name, messages, path, cfg):
        response = good(name, messages, path, cfg)
        if name == 'verifier':
            stages.save(path / 'response.json', response)
            raise KeyboardInterrupt('Complete Verifier response, not yet parsed')
        return response
    with using_benchmark(adapter):
        with pytest.raises(KeyboardInterrupt): ev.run_campaign(root, config=config, generate=generate)
        counts = (len(provider.requests), len(good.calls))
        ev.run_campaign(root, resume=True, generate=None)
        ev.final_parent(root)
    assert (len(provider.requests), len(good.calls)) == counts
    assert stages.read(root / 'rounds/R01/verifier/attempts/001/recovery.json')['additional_requests'] == 0


def test_fatal_error_has_no_backoff(stage_case, monkeypatch):
    adapter, _, prepare = stage_case; waits = []
    monkeypatch.setattr(stages.time, 'sleep', waits.append)
    def fatal(*args): raise RequestFailure('quota', retryable=False)
    with using_benchmark(adapter):
        directory, call, kwargs = prepare()
        with pytest.raises(stages.Stopped):
            stages.run_stage(directory, call, generate=fatal, retry_delay_seconds=3, **kwargs)
    assert waits == []

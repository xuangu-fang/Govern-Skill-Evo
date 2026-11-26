"""Offline publication and resume with Knowledge review disabled."""
import json

import pytest

from src.skill_evolution.v25_2 import evolution as ev
from src.skill_evolution.v25_2.baseline import configuration
from src.skill_evolution.v25_2.config import method_config, REVIEW_DISABLED
from src.skill_evolution.v25_2.benchmark import using_benchmark
from src.skill_evolution.v25_2.benchmarks.spreadsheetbench.adapter import SpreadsheetBenchAdapter
from .support import config, ActorResponses, MethodResponses, fast_execute


def no_review(path):
    value = config(path)
    value['method'] = method_config(preconditioner_prompt='v25_2_current_update_concise_refinement_v1')
    for name in ('verifier', 'repair'):
        value['module_max_tokens'].pop(name)
    return value


def test_new_configuration_defaults_to_disabled():
    value = configuration({}, [], [])
    assert value['method']['knowledge_review'] == REVIEW_DISABLED
    assert value['method']['memory_publication'] == 'replay_validated_before_commit'
    assert not {'verifier', 'repair'} & set(value['module_max_tokens'])


@pytest.mark.parametrize('correct', [True, False])
def test_publication_and_resume_never_call_review(tmp_path, monkeypatch, correct):
    value = no_review(tmp_path/'data')
    actors = ActorResponses(candidate_correct=correct)
    method = MethodResponses()
    adapter = SpreadsheetBenchAdapter(generate=actors, execute=fast_execute)
    root = tmp_path/'campaign'
    def forbidden(*args, **kwargs):
        raise AssertionError('Review must not execute')
    monkeypatch.setattr(ev.knowledge_review, 'review', forbidden)
    def stop(stage):
        if stage == 'before_publish':
            raise KeyboardInterrupt()
    with using_benchmark(adapter):
        with pytest.raises(KeyboardInterrupt):
            ev.run_campaign(root, config=value, generate=method,
                            actor_runner=adapter.actor_task, hook=stop)
        counts = len(actors.calls), len(method.calls)
        ev.run_campaign(root, resume=True, generate=method, actor_runner=adapter.actor_task)
        ev.final_parent(root)
        assert counts == (len(actors.calls), len(method.calls))
    assert method.calls == ['grouping', 'diagnosis', 'preconditioner', 'editor', 'replay']
    rd = root/'rounds/R01'
    assert not (rd/'verifier').exists() and not (rd/'repair').exists()
    assert ev.read(rd/'gate/result.json')['result']['decision'] == ('ACCEPT' if correct else 'RETAIN')
    assert ev.read(rd/'knowledge_review/result.json')['status'] == 'disabled'
    assert ev.read(rd/'memory/archive/campaign_R01.json')['result'] == ev.read(rd/'replay/attempts/001/replay.json')
    archive = rd/'memory/archive/campaign_R01.json'
    saved = ev.read(archive)
    saved['result']['entries'][0]['knowledge'][0]['text'] = 'Unpublished replacement'
    ev.save(archive, saved)
    with using_benchmark(adapter), pytest.raises(ValueError):
        ev.final_parent(root)


def test_invalid_replay_still_cannot_publish(tmp_path):
    value = no_review(tmp_path/'data')
    value['max_attempts'] = 1
    method = MethodResponses()
    adapter = SpreadsheetBenchAdapter(generate=ActorResponses(), execute=fast_execute)
    def generate(messages, dest):
        response = method(messages, dest)
        if 'replay' in dest.parts:
            output = json.loads(response['content'])
            output['entries'][0]['knowledge'][0]['evidence'] = ['Q999:outcome']
            response['content'] = json.dumps(output)
        return response
    root = tmp_path/'campaign'
    with using_benchmark(adapter), pytest.raises(ev.Stopped):
        ev.run_campaign(root, config=value, generate=generate, actor_runner=adapter.actor_task)
    assert not (root/'rounds/R01/memory').exists()
    assert 'verifier' not in method.calls and 'repair' not in method.calls

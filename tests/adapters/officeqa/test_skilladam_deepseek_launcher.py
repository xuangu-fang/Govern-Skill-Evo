"""Provider adaptation checks using the real SDK over an in-memory HTTP transport."""
from copy import deepcopy
import json
from pathlib import Path
import socket

import httpx
from openai import OpenAI
import pytest

from scripts.runs import run_officeqa_skilladam_deepseek as entry
from skilladam.core.case_sampler import build_same_batch_sampler
from skilladam.execution.contracts import BackendContext, GenerationRequest

ROOT = Path(__file__).resolve().parents[3]
CONFIG = ROOT / 'experiments/configs/officeqa_skilladam_train74_epoch1_deepseek_flash.json'


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def deny(*args, **kwargs):
        raise AssertionError('Live network forbidden')
    monkeypatch.setattr(socket.socket, 'connect', deny)


def test_actor_and_all_batches_match_v26_and_budget_matches_upstream():
    cfg = entry.launch.read(CONFIG)
    v26 = entry.launch.read(ROOT / 'experiments/configs/v26_officeqa_train74_epoch1_deepseek_flash.json')
    assert entry.launch.read(cfg['actor_config']) == v26['actor']
    native = cfg['native']
    batches = build_same_batch_sampler(native['optimization_case_ids'], batch_size=native['train_size'],
        max_iterations=native['feedback_loop']['max_iterations'], strategy=native['sampling_strategy'],
        seed=native['seed'], include_partial_final_batch=native['include_partial_final_batch'])
    assert [list(b.training_case_ids) for b in batches] == v26['batches']
    assert all(b.training_case_ids == b.validation_case_ids for b in batches)
    upstream = entry.launch.read(ROOT / 'external/SkillAdam/configs/backends/gpt55_main_result.example.json')
    for field in ('max_completion_tokens', 'max_retries', 'timeout_seconds', 'temperature'):
        assert cfg['optimizer']['backend_config'][field] == upstream[field]


@pytest.mark.parametrize('stage', ['iteration_patch', 'momentum_update', 'trajectory_compression'])
def test_actual_sdk_wire_thinking_and_native_retry_options(tmp_path, stage):
    cfg = entry.launch.read(CONFIG)
    bodies, options, clients = [], [], []
    def handle(request):
        bodies.append(json.loads(request.content))
        message = {'role': 'assistant', 'content': 'Checked output', 'reasoning_content': 'private thinking'}
        if stage == 'momentum_update':
            message['tool_calls'] = [{'id': 'call_1', 'type': 'function',
                'function': {'name': 'report_problem', 'arguments': '{"note":"example"}'}}]
        return httpx.Response(200, json={'id': 'offline', 'object': 'chat.completion',
            'created': 1, 'model': 'deepseek-flash', 'choices': [{'index': 0, 'message': message,
            'finish_reason': 'stop'}], 'usage': {'prompt_tokens': 10, 'completion_tokens': 5, 'total_tokens': 15}})
    def factory(**kwargs):
        options.append(kwargs)
        client = OpenAI(**kwargs, http_client=httpx.Client(transport=httpx.MockTransport(handle)))
        clients.append(client)
        return client
    backend = entry.generation_backend(cfg, tmp_path, 'offline-only', client_factory=factory)
    context = BackendContext('officeqa', 'skilladam', 'deepseek-flash', 'medium', cfg['workers'], 42)
    messages = ({'role': 'system', 'content': 'Synthetic check'},
                {'role': 'user', 'content': 'No live task'})
    metadata = {'tools': [{'type': 'function', 'function': {'name': 'report_problem',
                 'parameters': {'type': 'object', 'properties': {'note': {'type': 'string'}}}}}]} if stage == 'momentum_update' else {}
    try:
        result = backend.generate(GenerationRequest(stage, messages, context, metadata))
        assert result.text == 'Checked output'
        assert 'private thinking' not in str(result)
        assert len(result.tool_calls) == (1 if stage == 'momentum_update' else 0)
        assert options[0]['max_retries'] == 2 and options[0]['timeout'] == 300
        assert bodies[0]['thinking'] == {'type': 'enabled'}
        assert bodies[0]['reasoning_effort'] == 'medium'
        assert bodies[0]['max_tokens'] == 16384
        assert bodies[0]['messages'] == list(messages)
        assert 'max_completion_tokens' not in bodies[0]
        assert 'extra_body' not in bodies[0]
    finally:
        for client in clients: client.close()


def test_launcher_source_drift_rejected_before_preflight(tmp_path):
    cfg = deepcopy(entry.launch.read(CONFIG))
    cfg['launch_adapter']['sha256'] = '0' * 64
    with pytest.raises(ValueError, match='identity changed'):
        entry.prepare(cfg, tmp_path / 'run')


def test_formal_native_start_reaches_actor_with_original_gate(tmp_path):
    from skilladam.execution.contracts import BackendContext
    from skilladam.methods.skilladam import _SerializableAdapterGate
    from src.adapters.officeqa.bridges import SkillAdamAdapter
    from src.adapters.officeqa.launchers import TrainingSkillAdamRunner
    from src.skill_evolution.v26.training import load_dataset

    cfg = entry.launch.read(CONFIG)
    dataset = load_dataset(cfg['prepared_root'], 'officeqa_train50_validation24_v1')
    adapter = SkillAdamAdapter(dataset)
    gate = _SerializableAdapterGate(adapter=adapter, benchmark='officeqa', scope=None,
                                    profile=cfg['native']['gate_profile'])
    assert gate._gate is adapter._gate
    assert gate._gate.to_dict() == {'min_em_gain': 0.08, 'min_f1_gain': 0.05,
                                    'max_em_drop': 0.08, 'max_f1_drop': 0.05}
    native = entry.launch.adam_config(entry.launch._fixed(cfg['native'], {
        'benchmark': 'officeqa', 'split': 'train', 'validation_split': 'train', 'scope': None}))

    class ReachedActor(RuntimeError):
        pass

    class BoundaryBackend:
        output_dir = tmp_path / 'actor'

        def execute_batch(self, execution):
            assert [r.case.case_id for r in execution.requests] == cfg['native']['optimization_case_ids'][:10]
            raise ReachedActor('Native configuration initialized; no requests issued')

        def generate(self, request):
            raise AssertionError('Unexpected optimizer call before first Actor batch')

    runner = TrainingSkillAdamRunner(config=native, adapter=adapter, backend=BoundaryBackend(),
        context=BackendContext('officeqa', 'skilladam', 'deepseek-flash', 'medium', cfg['workers'], 42),
        output_dir=tmp_path / 'native')
    with pytest.raises(ReachedActor):
        runner.run(cases=dataset.cases('train'), initial_skill=Path(cfg['initial_skill']).read_text())


def test_full_eight_iterations_survive_consecutive_rejections_and_resume(tmp_path):
    from dataclasses import replace
    from skilladam.core.acceptance_gate import AcceptanceGate, ImprovementRule
    from skilladam.core.feedback_loop import FeedbackLoop, CheckpointStore
    from skilladam.types import MetricResult

    cfg = entry.launch.read(CONFIG)
    native = entry.launch.adam_config(entry.launch._fixed(cfg['native'], {
        'benchmark': 'officeqa', 'split': 'train', 'validation_split': 'train', 'scope': None}))
    batches = tuple(build_same_batch_sampler(native.optimization_case_ids,
        batch_size=native.train_size, max_iterations=native.feedback_loop.max_iterations,
        strategy=native.sampling_strategy, include_partial_final_batch=True))
    gate = AcceptanceGate(improvements=(ImprovementRule('em', 0.08),))

    def proposal(context):
        return ('--- a/skill.md\n+++ b/skill.md\n@@ -1 +1 @@\n'
                f'-{context.current_skill.strip()}\n+revision {context.iteration + 1}\n')

    def evaluate(skill, ids):
        score = float(skill != 'initial\n')
        return MetricResult(score, {'em': score},
                            {str(i): {'em': score} for i in ids}, len(ids))

    def run(name, config):
        loop = FeedbackLoop(config, gate=gate, checkpoint_store=CheckpointStore(tmp_path / name))
        result = loop.run(initial_skill='initial\n', batches=batches,
                          propose_patch=proposal, evaluate=evaluate)
        return loop, result

    # Same outcomes and native loop: old config stops at five, new config reaches eight.
    _, old = run('old', replace(native.feedback_loop, max_consecutive_failures=3))
    assert old.stop_reason == 'early_stop_consecutive_failures'
    assert len(old.iterations) == 5
    loop, result = run('full', native.feedback_loop)
    assert result.stop_reason == 'max_iterations'
    assert [item.accepted for item in result.iterations] == [True] + [False] * 7
    assert [len(item.training_case_ids) for item in result.iterations] == [10] * 7 + [4]
    assert [i for item in result.iterations for i in item.training_case_ids] == list(native.optimization_case_ids)
    assert all(item.patch_attempts == 1 for item in result.iterations)
    assert result.final_skill == old.final_skill == 'revision 1\n'

    def no_new_requests(*args):
        raise AssertionError('Completed resume must not generate or evaluate')
    resumed = loop.run(initial_skill='initial\n', batches=batches,
                       propose_patch=no_new_requests, evaluate=no_new_requests, resume=True)
    assert resumed.iterations == result.iterations
    assert resumed.resumed_from_iteration == 8

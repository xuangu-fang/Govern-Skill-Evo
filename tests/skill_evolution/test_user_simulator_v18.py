import json
from pathlib import Path
from unittest.mock import patch

import pytest

from src.skill_evolution import benchmark_runtime_v18 as runtime
from src.skill_evolution.user_simulator_v18 import (
    CONFIRMATION_GUIDELINES, PROMPT_SHA256, V18UserSimulator, sha256,
)
from tau2.data_model.message import AssistantMessage
from tau2.orchestrator.orchestrator import Role
from tau2.registry import registry as tau_registry
from tau2.user.user_simulator import UserSimulator

ROOT = Path(__file__).resolve().parents[2]
FREEZE = ROOT / 'experiments/configs/v17_formal_001'


@pytest.fixture(scope='module')
def benchmark():
    config = json.loads((FREEZE / 'config.json').read_text())
    return runtime.BenchmarkRegistry(), config


def build(adapter, benchmark, task_id=None, skill_path=None):
    registry, config = benchmark
    return adapter.build_orchestrator(
        task_id or registry.task_ids()[0], base_config=config['base_config'],
        seed=config['seed'], skill_path=skill_path or FREEZE / 'S0.md',
        initial_skill_path=FREEZE / 'S0.md')


@pytest.mark.parametrize('tools', [None, []])
def test_original_prompt_preserved_and_actual_request_uses_constraint(tools):
    kwargs = dict(instructions='Keep my original requirements.', tools=tools, llm='test')
    original = UserSimulator(**kwargs)
    user = V18UserSimulator(**kwargs)
    assert user.system_prompt == original.system_prompt + '\n\n' + CONFIRMATION_GUIDELINES
    before = original.system_prompt
    state = user.get_init_state()
    with patch('tau2.user.user_simulator.generate', return_value=AssistantMessage(
            role='assistant', content='Yes, please proceed.')) as generate:
        response, _ = user.generate_next_message(
            AssistantMessage(role='assistant', content='Please confirm the action.'), state)
    assert generate.call_args.kwargs['messages'][0].content == user.system_prompt
    assert response.content == 'Yes, please proceed.'
    assert not user.is_stop(response)
    assert original.system_prompt == before
    record = user.prompt_record()
    assert record['system_prompt_sha256'] == sha256(user.system_prompt)
    assert record['shared_guidelines_sha256'] == PROMPT_SHA256


def test_all_tasks_and_both_skill_modes_share_constraint_without_changing_v17(benchmark, tmp_path):
    registry, config = benchmark
    base_config_before = json.dumps(config, sort_keys=True)
    adapter = runtime.UnifiedEnvironmentAdapter(registry)
    legacy = runtime.shared.UnifiedEnvironmentAdapter(registry)
    candidate = tmp_path / 'candidate.md'
    candidate.write_text('# Operational Skill\n\nFollow the confirmed request.\n')
    assert len(registry.task_ids('train')) == 32
    assert len(registry.task_ids('monitor')) == 41
    for task_id in registry.task_ids():
        parent, parent_view = build(adapter, benchmark, task_id)
        learned, _ = build(adapter, benchmark, task_id, candidate)
        old, old_view = build(legacy, benchmark, task_id)
        assert type(parent.user) is V18UserSimulator
        assert type(old.user) is UserSimulator
        assert parent.user.prompt_record() == learned.user.prompt_record()
        assert parent.user.system_prompt == old.user.system_prompt + '\n\n' + CONFIRMATION_GUIDELINES
        assert parent.user.get_init_state().system_messages[0].content == parent.user.system_prompt
        assert parent.user.instructions == old.user.instructions
        assert parent.user.llm_args == old.user.llm_args
        assert parent_view.payload == old_view.payload
        assert CONFIRMATION_GUIDELINES not in parent_view.payload
    assert json.dumps(config, sort_keys=True) == base_config_before
    assert tau_registry.get_user_constructor('user_simulator') is UserSimulator


def test_frozen_prompt_binding_detects_drift_and_missing_task(benchmark):
    registry, _ = benchmark
    task_id = registry.task_ids()[0]
    user = build(runtime.UnifiedEnvironmentAdapter(registry), benchmark)[0].user
    expected = {task_id: user.prompt_record()}
    adapter = runtime.UnifiedEnvironmentAdapter(registry, frozen_user_prompts=expected)
    build(adapter, benchmark)
    expected[task_id]['system_prompt'] = 'caller mutation'
    build(adapter, benchmark)  # adapter took its own snapshot
    with patch('src.skill_evolution.user_simulator_v18.CONFIRMATION_GUIDELINES', 'drift'):
        with pytest.raises(ValueError, match='Frozen v18 user prompt mismatch'):
            build(adapter, benchmark)
    with pytest.raises(ValueError, match='Frozen v18 user prompt mismatch'):
        build(runtime.UnifiedEnvironmentAdapter(registry, frozen_user_prompts={}), benchmark)


@pytest.mark.parametrize('reply', [
    'Thank you, completed. ###STOP###',
    'I withdraw the request. ###STOP###',
    'Transfer accepted. ###TRANSFER###',
    'I cannot supply the missing information. ###OUT-OF-SCOPE###',
    'Yes, proceed. ###STOP###',  # residual simulator error must NOT be rewritten
])
def test_termination_signals_remain_effective(benchmark, reply):
    registry, _ = benchmark
    orchestrator, _ = build(runtime.UnifiedEnvironmentAdapter(registry), benchmark)
    orchestrator.initialize()
    orchestrator.from_role, orchestrator.to_role = Role.AGENT, Role.USER
    orchestrator.message = AssistantMessage(role='assistant', content='Please respond.')
    with patch('tau2.user.user_simulator.generate', return_value=AssistantMessage(
            role='assistant', content=reply)):
        orchestrator.step()
    assert orchestrator.done
    assert orchestrator.termination_reason.value == 'user_stop'
    assert orchestrator.message.content == reply
    with pytest.raises(ValueError, match='Simulation is done'):
        orchestrator.step()


def test_confirmation_leaves_next_agent_turn_available_then_completion_can_stop(benchmark):
    registry, _ = benchmark
    orchestrator, _ = build(runtime.UnifiedEnvironmentAdapter(registry), benchmark)
    orchestrator.initialize()
    orchestrator.from_role, orchestrator.to_role = Role.AGENT, Role.USER
    orchestrator.message = AssistantMessage(role='assistant', content='Confirm the proposed action?')
    with patch('tau2.user.user_simulator.generate', return_value=AssistantMessage(
            role='assistant', content='Yes, proceed.')):
        orchestrator.step()
    assert not orchestrator.done
    assert orchestrator.to_role == Role.AGENT
    with patch.object(orchestrator.agent, 'generate_next_message', return_value=(
            AssistantMessage(role='assistant', content='The action is complete.'),
            orchestrator.agent_state)) as agent:
        orchestrator.step()
    agent.assert_called_once()
    with patch('tau2.user.user_simulator.generate', return_value=AssistantMessage(
            role='assistant', content='Thanks. ###STOP###')):
        orchestrator.step()
    assert orchestrator.done


@pytest.mark.parametrize('text', ['', '# Skill\r\n\r\n## Section\n'])
def test_deleted_candidate_uses_baseline_agent(benchmark, tmp_path, text):
    candidate=tmp_path/'deleted.md';candidate.write_bytes(text.encode())
    adapter=runtime.UnifiedEnvironmentAdapter(benchmark[0])
    orchestrator,_=build(adapter,benchmark,skill_path=candidate)
    assert '<skill>' not in orchestrator.agent.system_prompt
    assert isinstance(orchestrator.user,V18UserSimulator)

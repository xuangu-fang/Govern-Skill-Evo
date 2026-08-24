from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from jsonschema import Draft202012Validator

import src.skill_evolution.autonomous_gse_v05_benchmark_runtime as v05
from src.adapters.stwebagentbench.seeded_agent import seed_agent_client
from src.adapters.stwebagentbench.run_evolution_selection import (
    DemoAgent,
    expected_run_metadata as expected_selection_metadata,
    get_output_dir as get_selection_output_dir,
)
from src.adapters.stwebagentbench.run_evolution_train import (
    get_output_dir as get_train_output_dir,
)
from st_bench_example import (
    action_syntax_is_valid,
    extract_action,
    normalize_natural_language_action,
    plain_text_to_message_action,
)
from src.skill_evolution.autonomous_gse_v03_benchmark_runtime import RolloutRequest
from src.skill_evolution.autonomous_gse_v03_proposal import (
    EditorRequest,
    ReflectorRequest,
)
import src.skill_evolution.autonomous_gse_v06_benchmark_runtime as v06
from src.skill_evolution.autonomous_gse_v03_runtime import RuntimeContractError
from src.skill_evolution.autonomous_gse_v06_benchmark_runtime import (
    BENCHMARK_AGENT_MODEL,
    RESUME_STATE_SCHEMA,
    FormalBenchmarkRuntimeAdapter,
    MultiRolloutRunnerBackend,
    SeededLearnerAdapter,
    _campaign_paths,
    _complete_frozen_candidate_selection,
    _controller_campaign,
    _expand_campaign,
    _load_controller_state,
    _recover_frozen_candidate_selection,
    _reconcile_controller_state_with_artifacts,
    _require_clean_next_step,
    build_formal_execution_plan,
    main,
    recover_controller_state_from_artifacts,
    run_v06_campaign,
    selection_execution_seed,
    train_execution_seed,
    validate_formal_campaign_contract,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CAMPAIGN_PATH = PROJECT_ROOT / (
    "experiments/campaigns/autonomous_gse_v06/campaign_manifest.json"
)
SCHEMA_PATH = PROJECT_ROOT / "schemas/autonomous_gse_v06_campaign.schema.json"
BATCH_MAP_PATH = PROJECT_ROOT / (
    "experiments/campaigns/autonomous_gse_v02/batch_map.json"
)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_v06_manifest_and_plan_encode_the_nine_step_rotation() -> None:
    campaign = load_json(CAMPAIGN_PATH)
    assert list(
        Draft202012Validator(load_json(SCHEMA_PATH)).iter_errors(campaign)
    ) == []
    validate_formal_campaign_contract(campaign, require_ready=True)
    plan = build_formal_execution_plan(campaign, load_json(BATCH_MAP_PATH))

    assert campaign["runtime"]["benchmark_agent"] == {
        "model": BENCHMARK_AGENT_MODEL,
        "temperature": 0.2,
        "thinking": False,
        "max_tokens": 2048,
        "retry_on_token_exhaustion": False,
    }
    assert campaign["runtime"]["train"]["temperature"] == 0.2
    assert campaign["runtime"]["selection"]["temperature"] == 0.2
    assert plan["benchmark_agent_model"] == BENCHMARK_AGENT_MODEL
    assert plan["benchmark_agent_temperature"] == 0.2
    assert plan["benchmark_agent_max_tokens"] == 2048
    assert plan["benchmark_agent_thinking"] is False
    assert plan["benchmark_agent_retry_on_token_exhaustion"] is False
    assert plan["learner_model"] == "openai/gpt-5.6-luna"
    assert [step["batch_id"] for step in plan["steps"]] == [
        "batch_001",
        "batch_002",
        "batch_003",
        "batch_002",
        "batch_003",
        "batch_001",
        "batch_003",
        "batch_001",
        "batch_002",
    ]
    assert len(plan["steps"]) == 9
    assert all(step["training_tasks"] == 17 for step in plan["steps"])
    assert all(step["training_trajectories"] == 51 for step in plan["steps"])
    assert all(
        step["candidate_selection_tasks"] == 18 for step in plan["steps"]
    )
    assert all(
        step["candidate_selection_trajectories"] == 54
        for step in plan["steps"]
    )
    assert plan["final_test_evaluation"] is False
    assert plan["maximum_budget"] == campaign["budget"]


def test_v06_reuses_the_frozen_batch_map_members_without_reassignment() -> None:
    campaign = load_json(CAMPAIGN_PATH)
    batch_map = load_json(BATCH_MAP_PATH)
    plan = build_formal_execution_plan(campaign, batch_map)
    expected = {
        batch["batch_id"]: [item["task_id"] for item in batch["assignments"]]
        for batch in batch_map["batches"]
    }
    for step in plan["steps"]:
        assert step["train_task_ids"] == expected[step["batch_id"]]


def test_v06_backend_uses_fresh_phase_paths_seeds_and_model_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed = []

    def run_subprocess_rollouts(payloads, *, parallel_workers):
        assert parallel_workers == 4
        observed.extend(copy.deepcopy(payloads))
        return tuple(Path(f"/tmp/{index}.json") for index in range(len(payloads))), {
            "events": [],
            "failures": [],
        }

    monkeypatch.setattr(
        "src.adapters.stwebagentbench.parallel_rollout.run_subprocess_rollouts",
        run_subprocess_rollouts,
    )
    monkeypatch.setattr(v05, "_write_json", lambda path, payload: None)
    backend = MultiRolloutRunnerBackend(load_json(CAMPAIGN_PATH))
    artifact = {
        "kind": "empty_skill",
        "version": "S0",
        "path": "experiments/campaigns/autonomous_gse_v03/skills/S0_empty_skill.md",
    }
    for step in (1, 6):
        backend(
            RolloutRequest(
                "train",
                "s0_empty_skill",
                artifact,
                (49,),
                execution_phase=f"step_{step:03d}_train",
                execution_step=step,
            )
        )

    assert [item["args"]["seed"] for item in observed] == [
        train_execution_seed(200, 1, 49, 1),
        train_execution_seed(200, 1, 49, 2),
        train_execution_seed(200, 1, 49, 3),
        train_execution_seed(200, 6, 49, 1),
        train_execution_seed(200, 6, 49, 2),
        train_execution_seed(200, 6, 49, 3),
    ]
    assert len({item["args"]["seed"] for item in observed[:3]}) == 3
    assert observed[0]["args"]["seed"] != observed[3]["args"]["seed"]
    assert {item["args"]["temperature"] for item in observed} == {0.2}
    assert {item["args"]["max_tokens"] for item in observed} == {2048}
    assert {item["args"]["thinking"] for item in observed} == {False}
    assert {
        item["args"]["retry_on_token_exhaustion"] for item in observed
    } == {False}
    assert all("retry_max_tokens" not in item["args"] for item in observed)
    assert {item["args"]["model"] for item in observed} == {
        BENCHMARK_AGENT_MODEL
    }
    assert {item["args"]["benchmark_agent_model"] for item in observed} == {
        BENCHMARK_AGENT_MODEL
    }
    assert [item["manifest"]["_output_phase"] for item in observed] == [
        "step_001_train",
        "step_001_train",
        "step_001_train",
        "step_006_train",
        "step_006_train",
        "step_006_train",
    ]
    step_1_path = get_train_output_dir(
        observed[0]["manifest"], "s0_empty_skill", 49, True, 1
    )
    step_6_path = get_train_output_dir(
        observed[3]["manifest"], "s0_empty_skill", 49, True, 1
    )
    assert step_1_path != step_6_path
    assert "step_001_train" in step_1_path.parts
    assert "step_006_train" in step_6_path.parts
    selection_manifest = {
        **observed[0]["manifest"],
        "_output_split": "selection",
        "_output_phase": "step_001_selection",
    }
    assert "step_001_selection" in get_selection_output_dir(
        selection_manifest, "candidate", 50, True, 1
    ).parts


def test_v06_selection_parent_candidate_use_matched_sampling(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed = []

    def run_subprocess_rollouts(payloads, *, parallel_workers):
        assert parallel_workers == 4
        observed.append(copy.deepcopy(payloads))
        return tuple(Path(f"/tmp/{index}.json") for index in range(len(payloads))), {
            "events": [],
            "failures": [],
        }

    monkeypatch.setattr(
        "src.adapters.stwebagentbench.parallel_rollout.run_subprocess_rollouts",
        run_subprocess_rollouts,
    )
    monkeypatch.setattr(v05, "_write_json", lambda path, payload: None)
    backend = MultiRolloutRunnerBackend(load_json(CAMPAIGN_PATH))
    artifact = {
        "kind": "empty_skill",
        "version": "S0",
        "path": "experiments/campaigns/autonomous_gse_v03/skills/S0_empty_skill.md",
    }
    for method, phase in (
        ("s0_empty_skill", "initial_selection"),
        ("candidate", "step_001_selection"),
    ):
        backend(
            RolloutRequest(
                "selection",
                method,
                artifact,
                (236,),
                execution_phase=phase,
                execution_step=1,
            )
        )

    parent = observed[0]
    candidate = observed[1]
    expected = [
        selection_execution_seed(200, 236, rollout)
        for rollout in (1, 2, 3)
    ]
    assert [payload["args"]["seed"] for payload in parent] == expected
    assert [payload["args"]["seed"] for payload in candidate] == expected
    assert len(set(expected)) == 3
    assert {payload["args"]["temperature"] for payload in parent + candidate} == {
        0.2
    }
    assert {payload["args"]["max_tokens"] for payload in parent + candidate} == {
        2048
    }
    assert {
        payload["args"]["thinking"] for payload in parent + candidate
    } == {False}
    assert {
        payload["args"]["retry_on_token_exhaustion"]
        for payload in parent + candidate
    } == {False}
    assert all(
        "retry_max_tokens" not in payload["args"]
        for payload in parent + candidate
    )


def test_benchmark_sampling_reaches_final_openai_compatible_request() -> None:
    create = MagicMock(return_value=object())
    client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create))
    )
    agent = SimpleNamespace(openai_client=client)

    seed_agent_client(agent, 81231, temperature=0.2)
    agent.openai_client.chat.completions.create(
        model=BENCHMARK_AGENT_MODEL,
        messages=[{"role": "user", "content": "test"}],
    )

    assert create.call_args.kwargs["model"] == BENCHMARK_AGENT_MODEL
    assert create.call_args.kwargs["temperature"] == 0.2
    assert create.call_args.kwargs["seed"] == 81231


def test_deepseek_uses_the_configured_openai_compatible_proxy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import openai

    client = SimpleNamespace()
    constructor = MagicMock(return_value=client)
    monkeypatch.setattr(openai, "OpenAI", constructor)
    monkeypatch.setenv("OPENAI_API_KEY", "proxy-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://proxy.example/v1")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    agent = DemoAgent(BENCHMARK_AGENT_MODEL)

    constructor.assert_called_once_with(
        base_url="https://proxy.example/v1",
        api_key="proxy-key",
    )
    assert agent.openai_client is client
    assert agent.model_name == BENCHMARK_AGENT_MODEL
    assert agent.is_openrouter is False
    assert agent.max_tokens == 4096
    assert agent.retry_max_tokens == 8192


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (
            "send_msg_to_user('Before scheduling, I'd need the attendees.')",
            'send_msg_to_user("Before scheduling, I\'d need the attendees.")',
        ),
        (
            "send_msg_to_user('Please provide Jim Halpert's email address.')",
            'send_msg_to_user("Please provide Jim Halpert\'s email address.")',
        ),
        (
            "send_msg_to_user('Who should attend 'Weekly Standup'?')",
            'send_msg_to_user("Who should attend \'Weekly Standup\'?")',
        ),
    ],
)
def test_natural_language_action_normalizes_unescaped_apostrophes(
    raw: str, expected: str
) -> None:
    normalized = normalize_natural_language_action(raw)
    assert normalized == expected
    DemoAgent.action_set.to_python_code(normalized)


@pytest.mark.parametrize(
    "raw",
    [
        'send_msg_to_user("Please choose 1) continue or 2) cancel.")',
        'send_msg_to_user("First line\nPlease choose 1) continue.")',
        (
            '```python\nsend_msg_to_user("Please choose 1) continue or '
            '2) cancel.")\n```'
        ),
    ],
)
def test_action_extraction_ignores_parentheses_inside_message_strings(
    raw: str,
) -> None:
    extracted = extract_action(raw)
    assert extracted is not None
    normalized = normalize_natural_language_action(extracted)

    assert extracted.endswith('cancel.")') or extracted.endswith('continue.")')
    assert action_syntax_is_valid(normalized)
    DemoAgent.action_set.to_python_code(normalized)


@pytest.mark.parametrize(
    "action",
    [
        'send_msg_to_user("First line\nSecond line")',
        'send_msg_to_user("bad\\xZZ escape")',
        'click("a1" "a2")',
    ],
)
def test_browsergym_syntax_validation_rejects_invalid_actions(action: str) -> None:
    assert not action_syntax_is_valid(action)


def test_plain_text_is_safely_wrapped_as_a_user_message_action() -> None:
    raw = (
        "I can't delete the 'Closed Lost' opportunities. "
        'Please confirm "Perception Analysis" instead.'
    )

    action = plain_text_to_message_action(raw)

    assert action is not None
    assert action.startswith("send_msg_to_user(")
    assert json.loads(action.removeprefix("send_msg_to_user(")[:-1]) == raw
    DemoAgent.action_set.to_python_code(action)


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "   ",
        "click('a51'",
        'send_msg_to_user("Please confirm"',
    ],
)
def test_plain_text_fallback_rejects_empty_or_action_like_output(raw: str) -> None:
    assert plain_text_to_message_action(raw) is None


def test_deepseek_thinking_disabled_returns_normalized_message_action(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import openai

    usage = SimpleNamespace(
        completion_tokens=18,
        model_dump=lambda: {"completion_tokens": 18},
    )
    response = SimpleNamespace(
        choices=[SimpleNamespace(
            finish_reason="stop",
            message=SimpleNamespace(
                content=(
                    "send_msg_to_user('Before scheduling, I'd need the "
                    "attendee names.')"
                )
            ),
        )],
        usage=usage,
    )
    create = MagicMock(return_value=response)
    client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create))
    )
    monkeypatch.setattr(openai, "OpenAI", MagicMock(return_value=client))
    monkeypatch.setenv("OPENAI_API_KEY", "proxy-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://proxy.example/v1")
    agent = DemoAgent(
        BENCHMARK_AGENT_MODEL,
        max_tokens=2048,
        thinking=False,
        retry_on_token_exhaustion=False,
    )
    agent.action_set = SimpleNamespace(
        describe=lambda **kwargs: 'send_msg_to_user("message")'
    )

    action = agent.get_action(
        {
            "goal": "Schedule the meeting.",
            "policies": [],
            "chat_messages": [],
            "axtree_txt": "RootWebArea 'SuiteCRM'",
            "url": "http://suitecrm.test",
        }
    )

    assert action == (
        'send_msg_to_user("Before scheduling, I\'d need the attendee names.")'
    )
    request = create.call_args.kwargs
    assert request["max_tokens"] == 2048
    assert request["extra_body"] == {"thinking": {"type": "disabled"}}
    assert "send_msg_to_user(\"Should I proceed with deletion?\")" in (
        request["messages"][0]["content"]
    )


def test_deepseek_thinking_disabled_wraps_plain_text_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import openai

    raw = (
        "I understand you'd like to proceed, but organization policy "
        "requires 'Perception Analysis' instead."
    )
    usage = SimpleNamespace(
        completion_tokens=22,
        model_dump=lambda: {"completion_tokens": 22},
    )
    response = SimpleNamespace(
        choices=[SimpleNamespace(
            finish_reason="stop",
            message=SimpleNamespace(content=raw),
        )],
        usage=usage,
    )
    create = MagicMock(return_value=response)
    client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create))
    )
    monkeypatch.setattr(openai, "OpenAI", MagicMock(return_value=client))
    monkeypatch.setenv("OPENAI_API_KEY", "proxy-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://proxy.example/v1")
    agent = DemoAgent(
        BENCHMARK_AGENT_MODEL,
        max_tokens=2048,
        thinking=False,
        retry_on_token_exhaustion=False,
    )
    agent.action_set = SimpleNamespace(describe=lambda **kwargs: "click('a1')")

    action = agent.get_action(
        {
            "goal": "Delete Closed Lost opportunities.",
            "policies": [],
            "chat_messages": [],
            "axtree_txt": "RootWebArea 'SuiteCRM'",
            "url": "http://suitecrm.test",
        }
    )

    assert action == plain_text_to_message_action(raw)
    assert agent.last_llm_output["llm_output"] == raw
    assert agent.last_llm_output["action"] == action
    DemoAgent.action_set.to_python_code(action)


def test_deepseek_retries_token_exhaustion_before_any_environment_action(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import openai

    exhausted_usage = SimpleNamespace(
        completion_tokens=4096,
        model_dump=lambda: {
            "completion_tokens": 4096,
            "completion_tokens_details": {"reasoning_tokens": 4096},
        }
    )
    successful_usage = SimpleNamespace(
        completion_tokens=24,
        model_dump=lambda: {
            "completion_tokens": 24,
            "completion_tokens_details": {"reasoning_tokens": 8},
        },
    )
    exhausted_response = SimpleNamespace(
        choices=[SimpleNamespace(
            finish_reason="length",
            message=SimpleNamespace(content=""),
        )],
        usage=exhausted_usage,
    )
    successful_response = SimpleNamespace(
        choices=[SimpleNamespace(
            finish_reason="stop",
            message=SimpleNamespace(content="click('a1')"),
        )],
        usage=successful_usage,
    )
    create = MagicMock(side_effect=[exhausted_response, successful_response])
    client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create))
    )
    monkeypatch.setattr(openai, "OpenAI", MagicMock(return_value=client))
    monkeypatch.setenv("OPENAI_API_KEY", "proxy-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://proxy.example/v1")
    agent = DemoAgent(BENCHMARK_AGENT_MODEL)
    agent.action_set = SimpleNamespace(describe=lambda **kwargs: "click('a1')")
    observation = {
        "goal": "Open the account.",
        "policies": [],
        "chat_messages": [],
        "axtree_txt": "RootWebArea 'SuiteCRM'",
        "url": "http://suitecrm.test",
    }

    assert agent.get_action(observation) == "click('a1')"

    assert [call.kwargs["max_tokens"] for call in create.call_args_list] == [
        4096,
        8192,
    ]
    request = create.call_args_list[0].kwargs
    prompt_text = "\n".join(
        message["content"] for message in request["messages"]
    )
    assert "Think step-by-step" not in prompt_text
    assert "Do not output your reasoning" in prompt_text


def test_deepseek_allows_one_fallback_noop_after_retry_exhaustion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import openai

    def empty_response(token_budget: int) -> SimpleNamespace:
        usage = SimpleNamespace(
            completion_tokens=token_budget,
            model_dump=lambda: {"completion_tokens": token_budget},
        )
        return SimpleNamespace(
            choices=[SimpleNamespace(
                finish_reason="length",
                message=SimpleNamespace(content=""),
            )],
            usage=usage,
        )

    create = MagicMock(side_effect=[
        empty_response(4096),
        empty_response(8192),
        empty_response(4096),
        empty_response(8192),
    ])
    client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create))
    )
    monkeypatch.setattr(openai, "OpenAI", MagicMock(return_value=client))
    monkeypatch.setenv("OPENAI_API_KEY", "proxy-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://proxy.example/v1")
    agent = DemoAgent(BENCHMARK_AGENT_MODEL)
    agent.action_set = SimpleNamespace(describe=lambda **kwargs: "click('a1')")
    observation = {
        "goal": "Open the account.",
        "policies": [],
        "chat_messages": [],
        "axtree_txt": "RootWebArea 'SuiteCRM'",
        "url": "http://suitecrm.test",
    }

    assert agent.get_action(observation) == "noop()"
    assert agent.last_llm_output["action_parse_status"] == "fallback_noop"
    assert agent.last_llm_output["generation_attempts"] == 2
    assert agent.last_llm_output[
        "consecutive_action_generation_failures"
    ] == 1

    with pytest.raises(RuntimeError, match="INVALID_ACTION_GENERATION"):
        agent.get_action(observation)

    assert [call.kwargs["max_tokens"] for call in create.call_args_list] == [
        4096,
        8192,
        4096,
        8192,
    ]
    assert agent.last_llm_output["action"] is None
    assert agent.last_llm_output[
        "consecutive_action_generation_failures"
    ] == 2


def test_deepseek_does_not_retry_a_non_exhaustion_parse_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import openai

    usage = SimpleNamespace(
        completion_tokens=100,
        model_dump=lambda: {"completion_tokens": 100},
    )
    invalid_response = SimpleNamespace(
        choices=[SimpleNamespace(
            finish_reason="stop",
            message=SimpleNamespace(content='click("a1" "a2")'),
        )],
        usage=usage,
    )
    valid_response = SimpleNamespace(
        choices=[SimpleNamespace(
            finish_reason="stop",
            message=SimpleNamespace(content="click('a1')"),
        )],
        usage=usage,
    )
    create = MagicMock(side_effect=[invalid_response, valid_response])
    client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create))
    )
    monkeypatch.setattr(openai, "OpenAI", MagicMock(return_value=client))
    monkeypatch.setenv("OPENAI_API_KEY", "proxy-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://proxy.example/v1")
    agent = DemoAgent(BENCHMARK_AGENT_MODEL, thinking=False)
    agent.action_set = SimpleNamespace(describe=lambda **kwargs: "click('a1')")

    observation = {
        "goal": "Open the account.",
        "policies": [],
        "chat_messages": [],
        "axtree_txt": "RootWebArea 'SuiteCRM'",
        "url": "http://suitecrm.test",
    }

    assert agent.get_action(observation) == "noop()"
    assert agent.last_llm_output["raw_llm_output"] == 'click("a1" "a2")'
    assert agent.last_llm_output["extracted_action"] == 'click("a1" "a2")'
    assert agent.last_llm_output["action_parse_status"] == "fallback_noop"
    assert agent.last_llm_output["generation_error"] == "invalid_syntax"

    assert agent.get_action(observation) == "click('a1')"
    assert agent.last_llm_output[
        "consecutive_action_generation_failures"
    ] == 0

    assert create.call_count == 2
    assert create.call_args_list[0].kwargs["extra_body"] == {
        "thinking": {"type": "disabled"}
    }


def test_v06_trajectory_metadata_records_frozen_sampling() -> None:
    args = SimpleNamespace(
        formal=True,
        method="candidate",
        model=BENCHMARK_AGENT_MODEL,
        benchmark_agent_model=BENCHMARK_AGENT_MODEL,
        temperature=0.2,
        seed=81231,
        campaign_seed=200,
        rollout_id=1,
        headless=True,
    )
    manifest = {
        "manifest_id": "autonomous_gse_v06",
        "_output_split": "train",
        "_output_phase": "step_001_train",
    }
    skill = {"path": "skill.md", "version": "S0"}

    manifest["_output_split"] = "selection"
    selection = expected_selection_metadata(args, manifest, skill)
    assert selection["requested_model"] == BENCHMARK_AGENT_MODEL
    assert selection["generation_temperature"] == 0.2
    assert selection["execution_seed"] == 81231


def test_all_v06_learner_roles_send_temperature_zero_to_final_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    create = MagicMock(
        return_value=SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="response"))],
            usage=None,
        )
    )
    client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create))
    )
    openai = SimpleNamespace(OpenAI=MagicMock(return_value=client))
    monkeypatch.setitem(sys.modules, "openai", openai)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://example.invalid/v1")
    learner = SeededLearnerAdapter(load_json(CAMPAIGN_PATH))
    requests = (
        ReflectorRequest("C1", "success", "skill", (), 4),
        ReflectorRequest("C1", "failure", "skill", (), 4),
        EditorRequest("C1", "skill", ()),
    )

    metadata = []
    for request in requests:
        learner.call(
            request,
            "openai/gpt-5.6-luna",
            "system",
            "user",
        )
        metadata.append(copy.deepcopy(learner.last_call))

    assert create.call_count == 3
    for call in create.call_args_list:
        assert call.kwargs["model"] == "gpt-5.6-luna"
        assert call.kwargs["temperature"] == 0
        assert call.kwargs["seed"] == 200
    assert [item["role"] for item in metadata] == [
        "success_reflector",
        "failure_reflector",
        "editor",
    ]
    assert all(item["model"] == "openai/gpt-5.6-luna" for item in metadata)
    assert all(item["parameters"]["temperature"] == 0 for item in metadata)


class _NineStepAdapter:
    mode = "v06_no_api_test"

    def __init__(self, outcomes: tuple[str, ...]) -> None:
        self.outcomes = outcomes
        self.parents = []
        self._skills = {}
        self._trace = []

    @property
    def side_effects(self) -> dict:
        return {}

    @property
    def trace(self) -> list:
        return self._trace

    def create_initial_checkpoint(self, parent, task_count):
        self._skills[parent["path"]] = "# SuiteCRM Operational Skill\n"
        return {
            "kind": "selection_checkpoint",
            "version": parent["version"],
            "path": "memory://s0.json",
        }

    def restore_checkpoint(self, checkpoint, parent):
        # Read-only recovery: re-register the resumed Parent Skill in memory so
        # the resumed Steps can read it, without re-running any Selection.
        self._skills[parent["path"]] = "# SuiteCRM Operational Skill\n"
        self._trace.append(
            {
                "operation": "restore_selection_checkpoint",
                "version": checkpoint["version"],
                "path": checkpoint["path"],
            }
        )

    def run_train(self, step):
        self.parents.append(step["parent"]["version"])
        return ()

    def skill_for_parent(self, parent):
        return self._skills[parent["path"]]

    def record_candidate(self, step, candidate_skill):
        path = f"memory://step_{step['step']:03d}/skill.md"
        self._skills[path] = candidate_skill
        return {
            "kind": "candidate_skill",
            "version": step["candidate_id"],
            "path": path,
        }

    def record_proposal(self, step, decision, candidate):
        return None

    def run_candidate_selection(self, step, candidate, promoted_version, task_count):
        return {
            "kind": "selection_checkpoint",
            "version": promoted_version,
            "path": f"memory://step_{step['step']:03d}/checkpoint.json",
        }

    def validate_candidate_selection(self, step, checkpoint):
        return None

    def build_evolution_summary(self, step, candidate_checkpoint):
        return {
            "kind": "evolution_summary",
            "version": f"step_{step['step']:03d}",
            "path": f"memory://step_{step['step']:03d}/summary.json",
        }

    def apply_gate(self, step, summary):
        return self.outcomes[step["step"] - 1]


class _CandidateOperator:
    def propose(self, context, success_reflector, failure_reflector, editor):
        return SimpleNamespace(
            proposal_status="CANDIDATE",
            proposal_reason={"code": "CANDIDATE_CONSTRUCTED"},
            candidate_skill="# SuiteCRM Operational Skill\n",
            reflector_calls=0,
            editor_calls=0,
            raw_patches=[],
            canonical_edits=[],
            applied_edits=[{"operation": "add"}],
            excluded_edits=[],
            provenance_status="VERIFIED",
            provenance_audit={"status": "VERIFIED", "issues": []},
        )


def test_v06_accept_and_reject_keep_only_the_accepted_parent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    outcomes = (
        "ACCEPT",
        "REJECT",
        "ACCEPT",
        "REJECT",
        "REJECT",
        "ACCEPT",
        "REJECT",
        "ACCEPT",
        "REJECT",
    )
    adapter = _NineStepAdapter(outcomes)
    monkeypatch.setattr(
        v05, "RuleIdGovernedReflectionEditorProposalOperator", _CandidateOperator
    )
    campaign = load_json(CAMPAIGN_PATH)
    report = run_v06_campaign(campaign, load_json(BATCH_MAP_PATH), adapter)

    assert adapter.parents == ["S0", "S1", "S1", "S2", "S2", "S2", "S3", "S3", "S4"]
    assert report["final_parent"]["version"] == "S4"
    assert [step["outcome"] for step in report["steps"]] == list(outcomes)


def test_v06_keeps_selection_and_test_out_of_the_learner() -> None:
    campaign = _expand_campaign(load_json(CAMPAIGN_PATH))
    assert campaign["proposal"]["selection_feedback_to_learner"] == "forbidden"
    assert campaign["proposal"]["test_feedback_to_learner"] == "forbidden"
    assert campaign["selection"]["selection_data_for_learning"] == "forbidden"
    assert campaign["test"] == {
        "authorized": False,
        "data_for_learning": "forbidden",
    }
    assert _controller_campaign(campaign)["proposal"] == campaign["proposal"]


# --------------------------------------------------------------------------- #
# Conservative Step-boundary resume (Autonomous GSE v0.6 fault recovery)       #
# --------------------------------------------------------------------------- #

_S2_CHECKPOINT_PATH = (
    "artifacts/autonomous_gse_v06/formal/checkpoints/"
    "epoch_001_step_002_candidate.json"
)
_S1_CHECKPOINT_PATH = (
    "artifacts/autonomous_gse_v06/formal/checkpoints/"
    "epoch_001_step_001_candidate.json"
)
_S2_CANDIDATE_SKILL = (
    "artifacts/autonomous_gse_v06/formal/candidates/"
    "epoch_001_step_002_candidate/skill.md"
)


def _resume_state_after_three(
    outcomes: tuple[str, str, str] = ("ACCEPT", "ACCEPT", "REJECT"),
) -> dict:
    """A Step-boundary resume state equivalent to three completed in-memory
    Steps that promoted S0→S1→S2 and then rejected (Parent stays S2)."""

    return {
        "current_parent": {
            "kind": "accepted_skill",
            "version": "S2",
            "path": "memory://step_002/skill.md",
        },
        "current_checkpoint": {
            "kind": "selection_checkpoint",
            "version": "S2",
            "path": "memory://step_002/checkpoint.json",
        },
        "completed_steps": [
            {"step": index + 1, "outcome": outcome}
            for index, outcome in enumerate(outcomes)
        ],
        "budget_usage": {
            "train_trajectories": 51,
            "initial_selection_trajectories": 18,
            "candidate_selection_trajectories": 54,
            "total_trajectories": 123,
            "candidates": 3,
            "learner_calls": 0,
            "test_trajectories": 0,
        },
        "next_step": 4,
    }


def test_resume_none_runs_a_fresh_campaign_from_step_one(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    outcomes = ("ACCEPT",) * 9
    adapter = _NineStepAdapter(outcomes)
    monkeypatch.setattr(
        v05, "RuleIdGovernedReflectionEditorProposalOperator", _CandidateOperator
    )
    report = run_v06_campaign(
        load_json(CAMPAIGN_PATH),
        load_json(BATCH_MAP_PATH),
        adapter,
        resume_state=None,
    )
    assert adapter.parents[0] == "S0"
    assert len(adapter.parents) == 9
    assert [step["outcome"] for step in report["steps"]] == list(outcomes)


def test_resume_continues_from_the_next_step_boundary_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    outcomes = (
        "ACCEPT",
        "ACCEPT",
        "REJECT",
        "REJECT",
        "REJECT",
        "ACCEPT",
        "REJECT",
        "ACCEPT",
        "REJECT",
    )
    adapter = _NineStepAdapter(outcomes)
    monkeypatch.setattr(
        v05, "RuleIdGovernedReflectionEditorProposalOperator", _CandidateOperator
    )
    run_v06_campaign(
        load_json(CAMPAIGN_PATH),
        load_json(BATCH_MAP_PATH),
        adapter,
        resume_state=_resume_state_after_three(),
    )
    # Steps 1-3 are never re-run: the first executed Train is Step 4 on S2.
    assert adapter.parents == ["S2", "S2", "S2", "S3", "S3", "S4"]
    assert any(
        entry["operation"] == "restore_selection_checkpoint"
        for entry in adapter.trace
    )


def test_resume_reconstructs_the_full_nine_step_lineage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    outcomes = (
        "ACCEPT",
        "ACCEPT",
        "REJECT",
        "REJECT",
        "REJECT",
        "ACCEPT",
        "REJECT",
        "ACCEPT",
        "REJECT",
    )
    adapter = _NineStepAdapter(outcomes)
    monkeypatch.setattr(
        v05, "RuleIdGovernedReflectionEditorProposalOperator", _CandidateOperator
    )
    report = run_v06_campaign(
        load_json(CAMPAIGN_PATH),
        load_json(BATCH_MAP_PATH),
        adapter,
        resume_state=_resume_state_after_three(),
    )
    assert report["final_parent"]["version"] == "S4"
    assert [step["outcome"] for step in report["steps"]] == list(outcomes)
    assert len(report["steps"]) == 9


def test_resume_budget_matches_an_uninterrupted_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    outcomes = (
        "ACCEPT",
        "ACCEPT",
        "REJECT",
        "REJECT",
        "REJECT",
        "ACCEPT",
        "REJECT",
        "ACCEPT",
        "REJECT",
    )
    monkeypatch.setattr(
        v05, "RuleIdGovernedReflectionEditorProposalOperator", _CandidateOperator
    )
    fresh = run_v06_campaign(
        load_json(CAMPAIGN_PATH), load_json(BATCH_MAP_PATH), _NineStepAdapter(outcomes)
    )
    resumed = run_v06_campaign(
        load_json(CAMPAIGN_PATH),
        load_json(BATCH_MAP_PATH),
        _NineStepAdapter(outcomes),
        resume_state=_resume_state_after_three(),
    )
    # Skipped/replayed Steps are never discounted: the logical protocol budget
    # of a resumed run equals that of an uninterrupted run.
    assert resumed["budget_usage"] == fresh["budget_usage"]


def _real_adapter() -> FormalBenchmarkRuntimeAdapter:
    return FormalBenchmarkRuntimeAdapter(
        load_json(CAMPAIGN_PATH),
        rollout_backend=lambda request: (),
        learner=None,
    )


def test_restore_checkpoint_loads_the_frozen_selection_checkpoint() -> None:
    adapter = _real_adapter()
    checkpoint = {
        "kind": "selection_checkpoint",
        "version": "S2",
        "path": _S2_CHECKPOINT_PATH,
    }
    parent = {
        "kind": "accepted_skill",
        "version": "S2",
        "path": _S2_CANDIDATE_SKILL,
    }
    adapter.restore_checkpoint(checkpoint, parent)
    assert _S2_CHECKPOINT_PATH in adapter._checkpoints
    assert adapter._checkpoints[_S2_CHECKPOINT_PATH]["trajectory_count"] == 54
    assert any(
        entry.get("operation") == "restore_selection_checkpoint"
        for entry in adapter._trace
    )


def test_restore_checkpoint_rejects_mismatched_lineage() -> None:
    adapter = _real_adapter()
    parent = {
        "kind": "accepted_skill",
        "version": "S2",
        "path": _S2_CANDIDATE_SKILL,
    }
    with pytest.raises(RuntimeContractError):
        adapter.restore_checkpoint(
            {"kind": "evolution_summary", "version": "S2", "path": _S2_CHECKPOINT_PATH},
            parent,
        )
    with pytest.raises(RuntimeContractError):
        # A frozen S1 checkpoint cannot stand in for the S2 Parent.
        adapter.restore_checkpoint(
            {"kind": "selection_checkpoint", "version": "S2", "path": _S1_CHECKPOINT_PATH},
            parent,
        )


def _write_state(tmp_path: Path, payload: dict) -> Path:
    path = tmp_path / "controller_state.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _valid_state_payload() -> dict:
    return {
        "schema_version": RESUME_STATE_SCHEMA,
        "campaign_id": "autonomous_gse_v06",
        "campaign_seed": 200,
        "last_completed_step": 3,
        "next_step": 4,
        "completed_steps": [
            {"step": 1, "outcome": "ACCEPT"},
            {"step": 2, "outcome": "ACCEPT"},
            {"step": 3, "outcome": "REJECT"},
        ],
        "current_parent": {"kind": "accepted_skill", "version": "S2", "path": "x"},
        "current_checkpoint": {
            "kind": "selection_checkpoint",
            "version": "S2",
            "path": "y",
        },
        "budget_usage": {"train_trajectories": 51},
    }


def test_load_controller_state_rejects_campaign_seed_mismatch(
    tmp_path: Path,
) -> None:
    payload = _valid_state_payload()
    payload["campaign_seed"] = 999
    path = _write_state(tmp_path, payload)
    with pytest.raises(RuntimeContractError):
        _load_controller_state(
            {"campaign_id": "autonomous_gse_v06", "campaign_seed": 200}, path
        )


def test_load_controller_state_rejects_noncontiguous_prefix(tmp_path: Path) -> None:
    payload = _valid_state_payload()
    payload["completed_steps"] = [
        {"step": 1, "outcome": "ACCEPT"},
        {"step": 3, "outcome": "REJECT"},
    ]
    payload["next_step"] = 3
    payload["last_completed_step"] = 2
    path = _write_state(tmp_path, payload)
    with pytest.raises(RuntimeContractError):
        _load_controller_state(
            {"campaign_id": "autonomous_gse_v06", "campaign_seed": 200}, path
        )


def test_load_controller_state_rejects_next_step_off_by_one(tmp_path: Path) -> None:
    payload = _valid_state_payload()
    payload["next_step"] = 5
    path = _write_state(tmp_path, payload)
    with pytest.raises(RuntimeContractError):
        _load_controller_state(
            {"campaign_id": "autonomous_gse_v06", "campaign_seed": 200}, path
        )


def test_require_clean_next_step_fails_on_partial_artifacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    step_dir = (
        tmp_path / "artifacts/autonomous_gse_v06/formal/steps/step_004"
    )
    step_dir.mkdir(parents=True)
    (step_dir / "train_set.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(v06, "REPO_ROOT", tmp_path)
    campaign = {"campaign_id": "autonomous_gse_v06"}
    with pytest.raises(RuntimeContractError, match="Partial controller artifacts"):
        _require_clean_next_step(campaign, 4)
    # A clean (empty/absent) next Step is allowed.
    _require_clean_next_step(campaign, 5)


def test_recovery_from_frozen_artifacts_stops_before_partial_step_five() -> None:
    state = recover_controller_state_from_artifacts(load_json(CAMPAIGN_PATH))
    assert state["next_step"] == 5
    assert state["last_completed_step"] == 4
    assert state["current_parent"]["version"] == "S2"
    assert state["current_checkpoint"]["version"] == "S2"
    assert state["current_checkpoint"]["path"] == _S2_CHECKPOINT_PATH
    assert [step["outcome"] for step in state["completed_steps"]] == [
        "ACCEPT",
        "ACCEPT",
        "REJECT",
        "REJECT",
    ]
    assert state["budget_usage"] == {
        "train_trajectories": 68,
        "initial_selection_trajectories": 18,
        "candidate_selection_trajectories": 72,
        "total_trajectories": 158,
        "candidates": 4,
        "learner_calls": 12,
        "test_trajectories": 0,
    }


def test_recovery_never_runs_the_learner_browser_or_selection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden(*args, **kwargs):
        raise AssertionError("recovery must not run rollouts")

    monkeypatch.setattr(
        "src.adapters.stwebagentbench.parallel_rollout.run_subprocess_rollouts",
        forbidden,
    )
    monkeypatch.setattr(
        v06,
        "SeededLearnerAdapter",
        lambda *a, **k: (_ for _ in ()).throw(
            AssertionError("recovery must not build a Learner")
        ),
    )
    state = recover_controller_state_from_artifacts(load_json(CAMPAIGN_PATH))
    assert state["next_step"] == 5


def test_reconcile_advances_stale_state_only_through_frozen_prefix() -> None:
    persisted = _valid_state_payload()
    persisted = {
        key: persisted[key]
        for key in (
            "current_parent",
            "current_checkpoint",
            "completed_steps",
            "budget_usage",
            "next_step",
            "last_completed_step",
        )
    }
    completed = {"step": 4, "outcome": "REJECT"}
    recovered = copy.deepcopy(persisted)
    recovered["completed_steps"].append(completed)
    recovered["next_step"] = 5
    recovered["last_completed_step"] = 4

    result, advanced = _reconcile_controller_state_with_artifacts(
        persisted, recovered
    )

    assert advanced is True
    assert result == recovered


def test_reconcile_rejects_completed_prefix_drift() -> None:
    persisted = {
        "completed_steps": [{"step": 1, "outcome": "ACCEPT"}],
        "next_step": 2,
        "current_parent": {},
        "current_checkpoint": {},
        "budget_usage": {},
    }
    recovered = copy.deepcopy(persisted)
    recovered["completed_steps"][0]["outcome"] = "REJECT"

    with pytest.raises(RuntimeContractError, match="completed-Step prefix"):
        _reconcile_controller_state_with_artifacts(persisted, recovered)


def test_recover_frozen_candidate_selection_uses_existing_step_five_artifacts(
) -> None:
    campaign = _expand_campaign(load_json(CAMPAIGN_PATH))
    state = _load_controller_state(
        campaign, _campaign_paths(campaign)["controller_state"]
    )

    step, candidate, reflector_calls, editor_calls = (
        _recover_frozen_candidate_selection(campaign, state)
    )

    assert step["step"] == 5
    assert step["status"] == "CANDIDATE_SELECTION_RUNNING"
    assert step["parent"]["version"] == "S2"
    assert candidate["version"] == "epoch_002_step_005_candidate"
    assert reflector_calls == 2
    assert editor_calls == 1


def test_recover_frozen_candidate_selection_rejects_other_partial_shapes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    campaign = _expand_campaign(load_json(CAMPAIGN_PATH))
    state = _load_controller_state(
        campaign, _campaign_paths(campaign)["controller_state"]
    )
    monkeypatch.setattr(
        v06, "_controller_artifacts_in", lambda path: ["train_set.json"]
    )

    with pytest.raises(RuntimeContractError, match="not at the frozen"):
        _recover_frozen_candidate_selection(campaign, state)


class _FrozenSelectionAdapter:
    def __init__(self) -> None:
        self.operations = []

    def restore_checkpoint(self, checkpoint, parent):
        self.operations.append("restore_parent")

    def run_candidate_selection(
        self, step, candidate, promoted_version, task_count
    ):
        self.operations.append("candidate_selection")
        assert step["status"] == "CANDIDATE_SELECTION_RUNNING"
        assert candidate["version"] == "epoch_002_step_005_candidate"
        assert task_count == 18
        return {
            "kind": "selection_checkpoint",
            "version": promoted_version,
            "path": "memory://step_005/checkpoint.json",
        }

    def validate_candidate_selection(self, step, checkpoint):
        self.operations.append("validate_selection")

    def build_evolution_summary(self, step, checkpoint):
        self.operations.append("build_summary")
        return {
            "kind": "evolution_summary",
            "version": "step_005",
            "path": "memory://step_005/summary.json",
        }

    def apply_gate(self, step, summary):
        self.operations.append("gate")
        return "REJECT"


def test_complete_frozen_candidate_selection_reaches_the_next_boundary() -> None:
    campaign = _expand_campaign(load_json(CAMPAIGN_PATH))
    state = _load_controller_state(
        campaign, _campaign_paths(campaign)["controller_state"]
    )
    adapter = _FrozenSelectionAdapter()

    completed = _complete_frozen_candidate_selection(campaign, state, adapter)

    assert adapter.operations == [
        "restore_parent",
        "candidate_selection",
        "validate_selection",
        "build_summary",
        "gate",
    ]
    assert completed["last_completed_step"] == 5
    assert completed["next_step"] == 6
    assert completed["completed_steps"][-1]["outcome"] == "REJECT"
    assert completed["current_parent"] == state["current_parent"]
    assert completed["budget_usage"]["train_trajectories"] == (
        state["budget_usage"]["train_trajectories"] + 17
    )
    assert completed["budget_usage"]["candidate_selection_trajectories"] == (
        state["budget_usage"]["candidate_selection_trajectories"] + 18
    )
    assert completed["budget_usage"]["learner_calls"] == (
        state["budget_usage"]["learner_calls"] + 3
    )


def test_resume_re_requests_the_full_step_workload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: list = []

    def run_subprocess_rollouts(payloads, *, parallel_workers):
        observed.extend(copy.deepcopy(payloads))
        return tuple(Path(f"/tmp/{i}.json") for i in range(len(payloads))), {
            "events": [],
            "failures": [],
        }

    monkeypatch.setattr(
        "src.adapters.stwebagentbench.parallel_rollout.run_subprocess_rollouts",
        run_subprocess_rollouts,
    )
    monkeypatch.setattr(v05, "_write_json", lambda path, payload: None)
    backend = MultiRolloutRunnerBackend(load_json(CAMPAIGN_PATH))
    batch_map = load_json(BATCH_MAP_PATH)
    # Step 4 rotates onto batch_002.
    task_ids = tuple(
        assignment["task_id"]
        for assignment in batch_map["batches"][1]["assignments"]
    )
    backend(
        RolloutRequest(
            "train",
            "candidate",
            {"kind": "accepted_skill", "version": "S2", "path": _S2_CANDIDATE_SKILL},
            task_ids,
            execution_phase="step_004_train",
            execution_step=4,
        )
    )
    # The backend re-requests all 17 tasks × 3 rollouts; the per-trajectory
    # skip inside each worker (not any failure_*.json) decides what re-runs.
    assert len(task_ids) == 17
    assert len(observed) == 51


def test_cli_dispatches_run_and_resume_and_plan(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(v06, "run_resume_cli", lambda path: {"status": "RESUMED"})
    monkeypatch.setattr(v06, "run_formal_campaign_cli", lambda path: {"status": "RAN"})
    assert main(["resume", "--campaign", str(CAMPAIGN_PATH)]) == 0
    assert "RESUMED" in capsys.readouterr().out
    assert main(["run", "--campaign", str(CAMPAIGN_PATH)]) == 0
    assert "RAN" in capsys.readouterr().out
    assert main(["plan", "--campaign", str(CAMPAIGN_PATH)]) == 0
    assert "autonomous_gse_formal_plan_0.6.0" in capsys.readouterr().out


def test_fresh_run_refuses_when_step_artifacts_already_exist() -> None:
    with pytest.raises(RuntimeContractError, match="resume"):
        v06.run_formal_campaign_cli(CAMPAIGN_PATH)

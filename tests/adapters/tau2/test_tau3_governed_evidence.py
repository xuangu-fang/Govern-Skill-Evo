from __future__ import annotations

import os
from pathlib import Path

import pytest

from src.adapters.tau2.tau3_compliance_judge import (
    ComplianceJudgment,
    ComplianceViolation,
)
from src.adapters.tau2.tau3_gse_runtime import (
    SKILL_PATH_ENV,
    _trajectory_model_args,
    _skill_environment,
    build_governed_evidence,
    compatibility_policy_id,
    stable_trajectory,
)


TASK = {"id": "3", "user_scenario": {"instructions": "Return the item."}}
MESSAGES = [
    {"role": "user", "content": "Please return it."},
    {
        "role": "assistant",
        "content": "I can help.",
        "tool_calls": [
            {"id": "call_1", "name": "update_order", "arguments": {"id": "x"}}
        ],
    },
    {"role": "tool", "id": "call_1", "content": "done", "error": False},
]


def test_agent_and_user_simulator_use_frozen_deepseek_recovery_arguments() -> None:
    agent_args = _trajectory_model_args(
        {
            "temperature": 0.0,
            "reasoning_effort": "high",
            "max_tokens": 8192,
            "empty_response_retries": 2,
            "empty_response_retry_max_tokens": 8192,
        },
        200,
        include_max_tokens=True,
    )
    user_args = _trajectory_model_args(
        {
            "temperature": 0.0,
            "reasoning_effort": "high",
            "max_tokens": 8192,
            "empty_response_retries": 2,
            "empty_response_retry_max_tokens": 8192,
        },
        200,
        include_max_tokens=True,
    )
    assert agent_args["reasoning_effort"] == "high"
    assert user_args["reasoning_effort"] == "high"
    assert agent_args["empty_response_retries"] == 2
    assert user_args["empty_response_retries"] == 2
    assert agent_args["empty_response_retry_max_tokens"] == 8192
    assert agent_args["invalid_tool_arguments_retries"] == 2
    assert user_args["invalid_tool_arguments_retries"] == 2
    assert user_args["empty_response_retry_max_tokens"] == 8192
    assert "extra_body" not in agent_args
    assert "extra_body" not in user_args
    assert agent_args["max_tokens"] == 8192
    assert user_args["max_tokens"] == 8192


@pytest.mark.parametrize(
    ("reward", "compliant", "state"),
    [
        (1.0, True, "compliant_success"),
        (1.0, False, "violating_success"),
        (0.0, True, "compliant_failure"),
        (0.0, False, "violating_failure"),
    ],
)
def test_all_four_state_mappings(reward: float, compliant: bool, state: str) -> None:
    violations = (
        ()
        if compliant
        else (
            ComplianceViolation(
                "Obtain confirmation before updating.", (3,), "The call came first."
            ),
        )
    )
    evidence = build_governed_evidence(
        source_id="train_retail_3_rollout_01",
        domain="retail",
        task=TASK,
        simulation={
            "messages": MESSAGES,
            "termination_reason": "user_stop",
            "reward_info": {
                "reward": reward,
                "db_check": {"db_reward": reward},
                "reward_breakdown": {"DB": reward, "COMMUNICATE": reward},
            },
        },
        domain_policy="Original policy",
        judgment=ComplianceJudgment(compliant, violations),
    )
    assert evidence["state"] == state
    assert evidence["task_success"] is (reward == 1.0)
    assert evidence["process_feedback"]["compliant"] is compliant


def test_trajectory_uses_one_stable_step_space_for_judge_and_diagnosis() -> None:
    trajectory = stable_trajectory(MESSAGES)
    assert [item["step"] for item in trajectory] == [1, 2, 3, 4]
    assert [item["event_type"] for item in trajectory] == [
        "message",
        "message",
        "tool_call",
        "tool_result",
    ]


def test_compatibility_policy_id_is_stable_and_keeps_policy_text_separate() -> None:
    requirement = "  Obtain   Confirmation Before Updating. "
    first = compatibility_policy_id("retail", requirement)
    second = compatibility_policy_id("retail", requirement.casefold())
    assert first == second
    assert first.startswith("tau3:retail:")


def test_s0_uses_default_prompt_and_learned_versions_use_skill_injection(
    tmp_path: Path,
) -> None:
    os.environ.pop(SKILL_PATH_ENV, None)
    with _skill_environment(None) as agent_name:
        assert agent_name == "llm_agent"
        assert SKILL_PATH_ENV not in os.environ
    skill_path = tmp_path / "SKILL.md"
    skill_path.write_text("# Skill\n", encoding="utf-8")
    with _skill_environment(skill_path) as agent_name:
        assert agent_name == "llm_agent_manual_skill"
        assert os.environ[SKILL_PATH_ENV] == str(skill_path.resolve())
    assert SKILL_PATH_ENV not in os.environ

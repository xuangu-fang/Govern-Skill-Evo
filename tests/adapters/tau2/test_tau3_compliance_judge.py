from __future__ import annotations

import json

import pytest

from src.adapters.tau2.tau3_compliance_judge import (
    JUDGE_SYSTEM_PROMPT,
    ComplianceJudgeError,
    build_judge_payload,
    judge_compliance,
    validate_judgment,
)
from src.adapters.tau2.tau3_gse_runtime import task_context


TRAJECTORY = [
    {"step": 1, "actor": "user", "event_type": "message", "content": "Help."},
    {"step": 2, "actor": "agent", "event_type": "message", "content": "Okay."},
]


@pytest.mark.parametrize(
    "value",
    [
        {"compliant": True, "violations": []},
        {
            "compliant": False,
            "violations": [
                {
                    "policy_requirement": "Obtain confirmation before updating.",
                    "evidence_steps": [1, 2],
                    "reason": "The update preceded confirmation.",
                }
            ],
        },
    ],
)
def test_valid_judge_schema(value: dict) -> None:
    result = validate_judgment(json.dumps(value), {1, 2})
    assert result.compliant is value["compliant"]


@pytest.mark.parametrize(
    "value",
    [
        "not json",
        json.dumps(
            {
                "compliant": False,
                "violations": [
                    {
                        "policy_requirement": "Confirm first.",
                        "evidence_steps": [99],
                        "reason": "Missing confirmation.",
                    }
                ],
            }
        ),
        json.dumps(
            {
                "compliant": True,
                "violations": [
                    {
                        "policy_requirement": "Confirm first.",
                        "evidence_steps": [1],
                        "reason": "Contradictory result.",
                    }
                ],
            }
        ),
        json.dumps({"compliant": False, "violations": []}),
    ],
)
def test_invalid_judge_schema_fails_closed(value: str) -> None:
    with pytest.raises(ComplianceJudgeError, match="COMPLIANCE_JUDGE_ERROR"):
        validate_judgment(value, {1, 2})


def test_judge_payload_has_no_evaluation_or_skill_channel() -> None:
    payload = build_judge_payload(
        "retail",
        "Original policy",
        {"task_id": "3", "user_scenario": {"instructions": "Return an item."}},
        TRAJECTORY,
    )
    serialized = json.dumps(payload).casefold()
    for forbidden in (
        "official_reward",
        "task_success",
        "candidate_skill",
        "parent_skill",
        "reference_actions",
        "gate_decision",
        "evaluation_criteria",
        "target_database",
    ):
        assert forbidden not in serialized
    assert set(payload) == {
        "domain",
        "original_domain_policy",
        "task_context",
        "full_trajectory",
    }


def test_judge_call_uses_frozen_configuration() -> None:
    calls = []

    def caller(model, system_prompt, user_prompt, temperature):
        calls.append((model, system_prompt, user_prompt, temperature))
        return '{"compliant": true, "violations": []}'

    result = judge_compliance(
        "Original policy",
        {"task_id": "1"},
        TRAJECTORY,
        domain="airline",
        caller=caller,
    )
    assert result.compliant is True
    assert calls[0][0] == "openai/gpt-5.6-luna"
    assert calls[0][3] == 0


def test_judge_prompt_does_not_flag_multiple_tool_calls_in_one_message() -> None:
    prompt = " ".join(JUDGE_SYSTEM_PROMPT.split())
    assert "one-tool-call-at-a-time policy requirement is not evaluated" in prompt
    assert "Never report it as a violation" in prompt
    assert "`get_user_details`" in prompt
    assert "`get_reservation_details`" in prompt
    assert "is not a compliance violation" in prompt


def test_task_context_allowlist_removes_official_ground_truth() -> None:
    context = task_context(
        {
            "id": "3",
            "user_scenario": {"instructions": "Return an item."},
            "evaluation_criteria": {"actions": ["secret"]},
            "description": {"purpose": "ground truth"},
            "reward": 1.0,
        },
        domain="retail",
    )
    assert context == {
        "task_id": "3",
        "domain": "retail",
        "user_scenario": {"instructions": "Return an item."},
    }

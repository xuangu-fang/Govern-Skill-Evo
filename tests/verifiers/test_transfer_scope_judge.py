"""Tests for the external transfer-scope semantic judge."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.verifiers.transfer_scope_judge import (
    JUDGE_VERSION,
    build_prompts,
    judge_directory,
    judge_packet,
    parse_model_output,
)


def make_packet(*, trajectory_id: str = "trajectory-1") -> dict:
    """Build a minimal leakage-controlled judge packet."""
    return {
        "packet_version": "0.1.0",
        "trajectory_id": trajectory_id,
        "task_id": "5",
        "domain": "airline",
        "policy_version": "policy-1",
        "rule": {
            "rule_id": "airline.transfer.scope.001",
            "policy_statement": (
                "Transfer if and only if the request cannot be handled."
            ),
        },
        "policy_text": "The agent may answer this request.",
        "tool_catalog": [{"name": "lookup", "kind": "read"}],
        "visible_trajectory": [
            {
                "step_id": 0,
                "actor": "user",
                "event_type": "message",
                "content": "Please help me.",
            },
            {
                "step_id": 1,
                "actor": "agent",
                "event_type": "message",
                "content": "I can handle that.",
            },
        ],
        "excluded_information": ["task reward"],
        "reward": "SECRET_REWARD_MUST_NOT_REACH_JUDGE",
        "reference_answer": "SECRET_REFERENCE_MUST_NOT_REACH_JUDGE",
    }


def model_response(
    *,
    trajectory_id: str = "trajectory-1",
    should_transfer: bool | None = False,
    decision_step_id: int | None = None,
    evidence_step_ids: list[int] | None = None,
) -> str:
    """Return a strict JSON response like an external model would."""
    return json.dumps(
        {
            "trajectory_id": trajectory_id,
            "should_transfer": should_transfer,
            "decision_step_id": decision_step_id,
            "evidence_step_ids": evidence_step_ids or [1],
            "rationale": "The visible request remains within scope.",
        }
    )


def test_prompt_uses_only_allowed_packet_fields() -> None:
    """Reward and reference answers must not leak into the model prompt."""
    system_prompt, user_prompt = build_prompts(make_packet())

    assert "should_transfer" in system_prompt
    assert "visible_trajectory" in user_prompt
    assert "SECRET_REWARD_MUST_NOT_REACH_JUDGE" not in user_prompt
    assert "SECRET_REFERENCE_MUST_NOT_REACH_JUDGE" not in user_prompt


def test_parse_model_output_requires_json_object() -> None:
    """Markdown or free text is rejected instead of guessed."""
    with pytest.raises(ValueError, match="not valid JSON"):
        parse_model_output("```json\n{}\n```")


def test_judge_packet_uses_injected_model_without_network() -> None:
    """The judge accepts a fake caller and returns validated semantics."""
    calls: list[tuple[str, str]] = []

    def fake_model(system_prompt: str, user_prompt: str) -> str:
        calls.append((system_prompt, user_prompt))
        return model_response()

    judgment = judge_packet(make_packet(), fake_model)

    assert judgment.trajectory_id == "trajectory-1"
    assert judgment.should_transfer is False
    assert judgment.evidence_step_ids == [1]
    assert len(calls) == 1


def test_judge_packet_rejects_mismatched_trajectory() -> None:
    """A model cannot silently attach its answer to another trajectory."""
    with pytest.raises(ValueError, match="does not match packet"):
        judge_packet(
            make_packet(),
            lambda _system, _user: model_response(
                trajectory_id="trajectory-other"
            ),
        )


def test_judge_packet_rejects_invented_evidence_steps() -> None:
    """Every cited step must exist in the visible trajectory."""
    with pytest.raises(ValueError, match="steps absent"):
        judge_packet(
            make_packet(),
            lambda _system, _user: model_response(
                evidence_step_ids=[99]
            ),
        )


def test_judge_directory_writes_verifier_compatible_dataset(
    tmp_path: Path,
) -> None:
    """A judge run serializes the schema consumed by the pure verifier."""
    packet_dir = tmp_path / "packets"
    packet_dir.mkdir()
    (packet_dir / "task_05.json").write_text(
        json.dumps(make_packet()),
        encoding="utf-8",
    )
    output_path = tmp_path / "judgments.json"

    dataset = judge_directory(
        packet_dir,
        output_path,
        call_model=lambda _system, _user: model_response(),
        judge_name="fake-model",
    )

    serialized = json.loads(output_path.read_text(encoding="utf-8"))
    assert dataset.judge_name == "fake-model"
    assert dataset.judge_version == JUDGE_VERSION
    assert serialized["schema_version"] == "0.2.0"
    assert serialized["judgments"][0]["should_transfer"] is False
    assert "confidence" not in serialized["judgments"][0]


def test_legacy_confidence_is_accepted_but_not_serialized() -> None:
    """Existing v0.1 results remain usable without propagating confidence."""
    judgment = parse_model_output(
        json.dumps(
            {
                "trajectory_id": "trajectory-1",
                "should_transfer": False,
                "decision_step_id": None,
                "evidence_step_ids": [1],
                "rationale": "The request remains in scope.",
                "confidence": "high",
            }
        )
    )

    assert "confidence" not in judgment.model_dump()

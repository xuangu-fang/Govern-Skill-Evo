"""Tests for the AI-backed transfer-scope handler."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.policies.schema import PolicyRule, PolicyRuleSet, VerificationContext
from src.trajectory.schema import (
    EnvironmentRef,
    MessageEvent,
    TaskOutcome,
    ToolCallEvent,
    Trajectory,
    TrajectoryDataset,
)
from src.verifiers.handlers.semantic.transfer_scope import (
    JUDGMENT_VERSION,
    TransferScopeJudgment,
    TransferScopeJudgmentDataset,
    build_semantic_input,
    build_prompts,
    evaluate_trajectory_semantics,
    parse_model_output,
    run_transfer_scope_verifier,
    verify_dataset,
    verify_transfer_scope,
    write_judgments,
)


def root_path() -> Path:
    """Return the repository root used by versioned policy fixtures."""
    return Path(__file__).resolve().parents[4]


def transfer_rule() -> PolicyRule:
    """Load the configured transfer-scope rule."""
    rule_set = PolicyRuleSet.model_validate_json(
        (root_path() / "policies/airline/rules_v04.json").read_text(
            encoding="utf-8"
        )
    )
    return next(
        rule
        for rule in rule_set.rules
        if rule.rule_id == "airline.transfer.scope.001"
    )


def transfer_context() -> VerificationContext:
    """Load the versioned Airline policy and tool catalog."""
    return VerificationContext.model_validate_json(
        (
            root_path()
            / "policies/airline/transfer_scope_context_v01.json"
        ).read_text(encoding="utf-8")
    )


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
            "evidence_step_ids": evidence_step_ids or [0],
            "rationale": "The visible request remains within scope.",
        }
    )


def semantic_trajectory(*, transferred: bool) -> Trajectory:
    """Build a minimal trajectory with an optional transfer call."""
    events = [
        MessageEvent(
            step_id=0,
            event_type="message",
            actor="user",
            content="Please help me.",
        )
    ]
    if transferred:
        events.append(
            ToolCallEvent(
                step_id=1,
                event_type="tool_call",
                actor="agent",
                tool_call_id="transfer-1",
                tool_name="transfer_to_human_agents",
                arguments={"summary": "User needs help."},
            )
        )

    return Trajectory(
        trajectory_id="trajectory-1",
        environment=EnvironmentRef(name="tau2", domain="airline"),
        task_id="1",
        events=events,
        outcome=TaskOutcome(score=None),
        raw_payload={
            "reward": "SECRET_REWARD_MUST_NOT_REACH_MODEL",
            "reference_answer": "SECRET_REFERENCE_MUST_NOT_REACH_MODEL",
        },
    )


def judgment(should_transfer: bool | None) -> TransferScopeJudgment:
    """Build one semantic rule decision."""
    return TransferScopeJudgment(
        trajectory_id="trajectory-1",
        should_transfer=should_transfer,
        decision_step_id=0 if should_transfer is True else None,
        evidence_step_ids=[] if should_transfer is None else [0],
        rationale="Semantic process decision.",
    )


def test_prompt_uses_only_leakage_controlled_input() -> None:
    """Reward and reference answers must not leak into the model prompt."""
    item = semantic_trajectory(transferred=False)
    semantic_input = build_semantic_input(
        item,
        transfer_rule(),
        transfer_context(),
    )
    system_prompt, user_prompt = build_prompts(
        item,
        transfer_rule(),
        transfer_context(),
    )

    assert "should_transfer" in system_prompt
    assert "visible_trajectory" in user_prompt
    assert semantic_input["trajectory_id"] == item.trajectory_id
    assert semantic_input["policy_version"] == item.policy_version
    assert "SECRET_REWARD_MUST_NOT_REACH_MODEL" not in user_prompt
    assert "SECRET_REFERENCE_MUST_NOT_REACH_MODEL" not in user_prompt


def test_parse_model_output_requires_json_object() -> None:
    """Markdown or free text is rejected instead of guessed."""
    with pytest.raises(ValueError, match="not valid JSON"):
        parse_model_output("```json\n{}\n```")


def test_trajectory_evaluation_uses_injected_model_without_network() -> None:
    """Semantic verification accepts an injected fake model caller."""
    calls: list[tuple[str, str]] = []

    def fake_model(system_prompt: str, user_prompt: str) -> str:
        calls.append((system_prompt, user_prompt))
        return model_response()

    result = evaluate_trajectory_semantics(
        semantic_trajectory(transferred=False),
        transfer_rule(),
        transfer_context(),
        fake_model,
    )

    assert result.trajectory_id == "trajectory-1"
    assert result.should_transfer is False
    assert result.evidence_step_ids == [0]
    assert len(calls) == 1


def test_trajectory_evaluation_rejects_mismatched_trajectory() -> None:
    """A model cannot attach its answer to another trajectory."""
    with pytest.raises(ValueError, match="does not match trajectory"):
        evaluate_trajectory_semantics(
            semantic_trajectory(transferred=False),
            transfer_rule(),
            transfer_context(),
            lambda _system, _user: model_response(
                trajectory_id="trajectory-other"
            ),
        )


def test_trajectory_evaluation_rejects_invented_evidence_steps() -> None:
    """Every cited step must exist in the visible trajectory."""
    with pytest.raises(ValueError, match="steps absent"):
        evaluate_trajectory_semantics(
            semantic_trajectory(transferred=False),
            transfer_rule(),
            transfer_context(),
            lambda _system, _user: model_response(
                evidence_step_ids=[99]
            ),
        )


def test_write_judgments_serializes_intermediate_semantics(
    tmp_path: Path,
) -> None:
    """Intermediate judgments remain available for Gold evaluation."""
    dataset = TrajectoryDataset(
        source_format="test",
        trajectories=[semantic_trajectory(transferred=False)],
    )
    output_path = tmp_path / "judgments.json"

    judgments = write_judgments(
        dataset,
        transfer_rule(),
        transfer_context(),
        output_path,
        call_model=lambda _system, _user: model_response(
            evidence_step_ids=[0]
        ),
        model_name="fake-model",
    )

    serialized = json.loads(output_path.read_text(encoding="utf-8"))
    assert judgments.model_name == "fake-model"
    assert judgments.semantic_version == JUDGMENT_VERSION
    assert serialized["schema_version"] == "0.3.0"
    assert serialized["judgments"][0]["should_transfer"] is False
    assert "confidence" not in serialized["judgments"][0]


def test_full_semantic_process_run_writes_judgments_and_verdicts(
    tmp_path: Path,
) -> None:
    """One public run should produce both reproducible intermediates and verdicts."""
    trajectory_path = tmp_path / "trajectories.json"
    trajectory_path.write_text(
        TrajectoryDataset(
            source_format="test",
            trajectories=[semantic_trajectory(transferred=False)],
        ).model_dump_json(indent=2),
        encoding="utf-8",
    )
    judgment_path = tmp_path / "judgments.json"
    verdict_path = tmp_path / "verdicts.json"

    verdicts = run_transfer_scope_verifier(
        trajectory_path,
        root_path() / "policies/airline/rules_v04.json",
        root_path() / "policies/airline/transfer_scope_context_v01.json",
        judgment_path,
        verdict_path,
        call_model=lambda _system, _user: model_response(
            evidence_step_ids=[0]
        ),
        model_name="fake-model",
    )

    assert judgment_path.exists()
    assert verdict_path.exists()
    assert verdicts.verdicts[0].compliant is True


def test_legacy_confidence_is_accepted_but_not_serialized() -> None:
    """Existing v0.1 results remain usable without confidence propagation."""
    result = parse_model_output(
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

    assert "confidence" not in result.model_dump()


@pytest.mark.parametrize(
    ("transferred", "should_transfer"),
    [(False, False), (True, True)],
)
def test_matching_actual_and_expected_transfer_is_compliant(
    transferred: bool,
    should_transfer: bool,
) -> None:
    """Matching observable and semantic facts are compliant."""
    verdict = verify_transfer_scope(
        semantic_trajectory(transferred=transferred),
        judgment(should_transfer),
        model_name="fake-model",
        semantic_version="0.1.0",
    )

    assert verdict.compliant is True
    assert verdict.violations == []


def test_unnecessary_transfer_is_violation() -> None:
    """An actual transfer conflicts with should_transfer=false."""
    verdict = verify_transfer_scope(
        semantic_trajectory(transferred=True),
        judgment(False),
        model_name="fake-model",
        semantic_version="0.1.0",
    )

    assert verdict.compliant is False
    assert verdict.violations[0].rule_id == "airline.transfer.scope.001"
    assert verdict.violations[0].step_id == 1


def test_missing_required_transfer_is_violation() -> None:
    """No actual transfer conflicts with should_transfer=true."""
    verdict = verify_transfer_scope(
        semantic_trajectory(transferred=False),
        judgment(True),
        model_name="fake-model",
        semantic_version="0.1.0",
    )

    assert verdict.compliant is False
    assert verdict.violations[0].step_id == 0


def test_uncertain_semantics_produce_unknown_compliance() -> None:
    """An unresolved semantic decision produces unknown compliance."""
    verdict = verify_transfer_scope(
        semantic_trajectory(transferred=False),
        judgment(None),
        model_name="fake-model",
        semantic_version="0.1.0",
    )

    assert verdict.compliant is None
    assert verdict.violations == []


def test_dataset_requires_exact_semantic_coverage() -> None:
    """Every trajectory must have exactly one semantic decision."""
    dataset = TrajectoryDataset(
        source_format="test",
        trajectories=[semantic_trajectory(transferred=False)],
    )
    semantic_inputs = TransferScopeJudgmentDataset(
        model_name="fake-model",
        semantic_version="0.1.0",
        judgments=[],
    )

    with pytest.raises(ValueError, match="coverage must exactly match"):
        verify_dataset(dataset, semantic_inputs)


def test_human_gold_and_common_trajectories_match_expected_verdicts() -> None:
    """The ten adjudicated labels exercise final verdict generation."""
    root = Path(__file__).resolve().parents[4]
    trajectory_path = (
        root
        / "experiments/results/day5_schema/common_trajectories_v02.json"
    )
    gold_path = (
        root
        / "experiments/annotations/transfer_scope_v01/gold/"
        / "human_adjudicated.json"
    )
    if not trajectory_path.exists() or not gold_path.exists():
        pytest.skip("local experiment fixtures are unavailable")

    dataset = TrajectoryDataset.model_validate_json(
        trajectory_path.read_text(encoding="utf-8")
    )
    gold = json.loads(gold_path.read_text(encoding="utf-8"))
    semantic_inputs = TransferScopeJudgmentDataset(
        model_name="human-adjudicated-gold",
        semantic_version=gold["gold_version"],
        judgments=[
            TransferScopeJudgment(
                trajectory_id=label["trajectory_id"],
                should_transfer=label["should_transfer"],
                decision_step_id=(
                    label["trajectory_evidence"][-1]["step_id"]
                    if label["should_transfer"]
                    else None
                ),
                evidence_step_ids=[
                    item["step_id"]
                    for item in label["trajectory_evidence"]
                ],
                rationale=label["expected_behavior"],
            )
            for label in gold["labels"]
        ],
    )

    verdicts = verify_dataset(dataset, semantic_inputs)
    actual = {
        item.trajectory_id: item.compliant
        for item in verdicts.verdicts
    }
    expected = {
        label["trajectory_id"]: label["verdict"] == "compliant"
        for label in gold["labels"]
    }

    assert actual == expected

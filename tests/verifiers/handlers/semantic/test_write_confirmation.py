"""Tests for confirmation before reservation database writes."""

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
from src.verifiers.handlers.semantic.write_confirmation import (
    WriteConfirmationAssessment,
    WriteConfirmationJudgment,
    build_prompts,
    evaluate_trajectory_semantics,
    find_covered_write_calls,
    parse_model_output,
    validate_judgment,
    verify_write_confirmation_rule,
    write_judgments,
)


def root_path() -> Path:
    """Return the repository root used by versioned policy fixtures."""
    return Path(__file__).resolve().parents[4]


def confirmation_rule() -> PolicyRule:
    """Load the real rule configuration used by Process Verifier v0.3."""
    rule_set = PolicyRuleSet.model_validate_json(
        (root_path() / "policies/airline/rules_v03.json").read_text(
            encoding="utf-8"
        )
    )
    return next(
        rule
        for rule in rule_set.rules
        if rule.rule_id == "airline.write.confirmation.001"
    )


def confirmation_context() -> VerificationContext:
    """Load the rule-scoped Airline tool catalog."""
    return VerificationContext.model_validate_json(
        (
            root_path()
            / "policies/airline/write_confirmation_context_v01.json"
        ).read_text(encoding="utf-8")
    )


def message(
    step_id: int,
    *,
    actor: str,
    content: str,
) -> MessageEvent:
    """Build one visible conversation message."""
    return MessageEvent(
        step_id=step_id,
        source_turn_idx=step_id,
        event_type="message",
        actor=actor,
        content=content,
    )


def tool_call(
    step_id: int,
    tool_name: str = "cancel_reservation",
) -> ToolCallEvent:
    """Build one covered or uncovered tool action."""
    arguments = (
        {"reservation_id": "ABC123"}
        if tool_name == "cancel_reservation"
        else {"user_id": "user-1"}
    )
    return ToolCallEvent(
        step_id=step_id,
        source_turn_idx=step_id,
        event_type="tool_call",
        actor="agent",
        tool_call_id=f"call-{step_id}",
        tool_name=tool_name,
        arguments=arguments,
    )


def trajectory(
    *events: MessageEvent | ToolCallEvent,
) -> Trajectory:
    """Build a minimal trajectory with contiguous step IDs."""
    return Trajectory(
        trajectory_id="trajectory-1",
        environment=EnvironmentRef(name="tau2", domain="airline"),
        task_id="1",
        policy_version="policy-1",
        events=list(events),
        outcome=TaskOutcome(score=1.0),
    )


def confirmed_trajectory() -> Trajectory:
    """Build one write preceded by details and explicit confirmation."""
    return trajectory(
        message(
            0,
            actor="user",
            content="Please cancel reservation ABC123.",
        ),
        message(
            1,
            actor="agent",
            content=(
                "I will cancel reservation ABC123. Please reply yes "
                "to proceed."
            ),
        ),
        message(2, actor="user", content="Yes, proceed."),
        tool_call(3),
    )


def assessment(
    *,
    details_sufficient: bool | None = True,
    confirmation_valid: bool | None = True,
    write_step_id: int = 3,
) -> WriteConfirmationAssessment:
    """Build one semantic assessment with consistent positive citations."""
    return WriteConfirmationAssessment(
        write_step_id=write_step_id,
        details_sufficient=details_sufficient,
        confirmation_valid=confirmation_valid,
        details_step_ids=[1] if details_sufficient is True else [],
        confirmation_step_ids=[2] if confirmation_valid is True else [],
        rationale="Action-specific confirmation assessment.",
    )


def judgment(
    item: WriteConfirmationAssessment,
) -> WriteConfirmationJudgment:
    """Wrap one action assessment in a trajectory judgment."""
    return WriteConfirmationJudgment(
        trajectory_id="trajectory-1",
        assessments=[item],
        rationale="Trajectory-level confirmation assessment.",
    )


def test_prompt_contains_boundary_rules_without_outcome_leakage() -> None:
    """The model sees confirmation criteria but not task reward."""
    system_prompt, user_prompt = build_prompts(
        confirmed_trajectory(),
        confirmation_rule(),
        confirmation_context(),
    )

    assert "initial request" in system_prompt
    assert "multiple write calls" in system_prompt
    assert "material change" in system_prompt
    assert "keys trajectory_id, assessments, and\nrationale" in system_prompt
    assert '"write_step_id": 3' in user_prompt
    assert "task outcome" in user_prompt
    assert '"score": 1.0' not in user_prompt


def test_parse_model_output_requires_json_object() -> None:
    """Free text is rejected instead of guessed."""
    with pytest.raises(ValueError, match="not valid JSON"):
        parse_model_output("confirmed")


def test_parse_model_output_accepts_overall_rationale_alias() -> None:
    """The prompt's former rationale spelling remains readable."""
    payload = judgment(assessment()).model_dump(mode="json")
    payload["overall_rationale"] = payload.pop("rationale")

    result = parse_model_output(json.dumps(payload))

    assert result.rationale == "Trajectory-level confirmation assessment."
    assert "overall_rationale" not in result.model_dump(mode="json")


def test_evaluate_semantics_validates_injected_model_output() -> None:
    """A fake model can produce a strictly checked intermediate judgment."""
    result = evaluate_trajectory_semantics(
        confirmed_trajectory(),
        confirmation_rule(),
        confirmation_context(),
        lambda _system, _user: json.dumps(
            judgment(assessment()).model_dump(mode="json")
        ),
    )

    assert result.assessments[0].details_sufficient is True
    assert result.assessments[0].confirmation_valid is True


def test_trajectory_without_covered_writes_skips_model() -> None:
    """Read tools and send_certificate do not trigger this rule version."""
    item = trajectory(
        message(0, actor="user", content="Check my account."),
        tool_call(1, "get_user_details"),
        tool_call(2, "send_certificate"),
    )
    calls = 0

    def fake_model(_system: str, _user: str) -> str:
        nonlocal calls
        calls += 1
        raise AssertionError("model must not run without covered writes")

    result = evaluate_trajectory_semantics(
        item,
        confirmation_rule(),
        confirmation_context(),
        fake_model,
    )

    assert result.assessments == []
    assert find_covered_write_calls(item, confirmation_rule()) == []
    assert calls == 0

    verdict = verify_write_confirmation_rule(
        item,
        confirmation_rule(),
        result,
        model_name="fake-model",
        semantic_version="0.1.0",
    )
    assert verdict.status == "compliant"


def test_judgment_requires_exact_write_step_coverage() -> None:
    """The model cannot omit an observed write action."""
    with pytest.raises(ValueError, match="coverage must exactly match"):
        validate_judgment(
            confirmed_trajectory(),
            confirmation_rule(),
            WriteConfirmationJudgment(
                trajectory_id="trajectory-1",
                assessments=[],
                rationale="Missing assessment.",
            ),
        )


def test_confirmation_evidence_must_follow_details() -> None:
    """A user request before the action listing cannot be confirmation."""
    invalid = WriteConfirmationJudgment(
        trajectory_id="trajectory-1",
        assessments=[
            WriteConfirmationAssessment(
                write_step_id=3,
                details_sufficient=True,
                confirmation_valid=True,
                details_step_ids=[1],
                confirmation_step_ids=[0],
                rationale="Invalid evidence ordering.",
            )
        ],
        rationale="Invalid ordering.",
    )

    with pytest.raises(ValueError, match="must follow"):
        validate_judgment(
            confirmed_trajectory(),
            confirmation_rule(),
            invalid,
        )


def test_confirmed_write_is_compliant() -> None:
    """Sufficient details and valid confirmation satisfy the rule."""
    verdict = verify_write_confirmation_rule(
        confirmed_trajectory(),
        confirmation_rule(),
        judgment(assessment()),
        model_name="fake-model",
        semantic_version="0.1.0",
    )

    assert verdict.status == "compliant"
    assert verdict.violations == []


@pytest.mark.parametrize(
    ("details_sufficient", "confirmation_valid", "description"),
    [
        (False, True, "listing the action details"),
        (True, False, "explicit user confirmation"),
        (False, False, "details or obtaining"),
    ],
)
def test_missing_requirement_is_violation(
    details_sufficient: bool,
    confirmation_valid: bool,
    description: str,
) -> None:
    """Either missing obligation produces a localized write violation."""
    verdict = verify_write_confirmation_rule(
        confirmed_trajectory(),
        confirmation_rule(),
        judgment(
            assessment(
                details_sufficient=details_sufficient,
                confirmation_valid=confirmation_valid,
            )
        ),
        model_name="fake-model",
        semantic_version="0.1.0",
    )

    assert verdict.status == "violation"
    assert verdict.violations[0].step_id == 3
    assert description in verdict.violations[0].description


def test_uncertain_semantics_are_indeterminate() -> None:
    """Insufficient evidence is not treated as compliance."""
    verdict = verify_write_confirmation_rule(
        confirmed_trajectory(),
        confirmation_rule(),
        judgment(
            assessment(
                details_sufficient=True,
                confirmation_valid=None,
            )
        ),
        model_name="fake-model",
        semantic_version="0.1.0",
    )

    assert verdict.status == "indeterminate"
    assert verdict.violations == []


def test_one_confirmation_can_cover_an_explicit_write_bundle() -> None:
    """Two listed actions may cite the same subsequent confirmation."""
    item = trajectory(
        message(
            0,
            actor="agent",
            content=(
                "I will cancel ABC123 and book the listed replacement. "
                "Reply yes to proceed with both."
            ),
        ),
        message(1, actor="user", content="Yes, proceed with both."),
        tool_call(2, "cancel_reservation"),
        tool_call(3, "book_reservation"),
    )
    bundled = WriteConfirmationJudgment(
        trajectory_id="trajectory-1",
        assessments=[
            WriteConfirmationAssessment(
                write_step_id=2,
                details_sufficient=True,
                confirmation_valid=True,
                details_step_ids=[0],
                confirmation_step_ids=[1],
                rationale="Cancellation was listed and confirmed.",
            ),
            WriteConfirmationAssessment(
                write_step_id=3,
                details_sufficient=True,
                confirmation_valid=True,
                details_step_ids=[0],
                confirmation_step_ids=[1],
                rationale="Replacement booking was listed and confirmed.",
            ),
        ],
        rationale="Both writes were confirmed as one explicit bundle.",
    )

    verdict = verify_write_confirmation_rule(
        item,
        confirmation_rule(),
        bundled,
        model_name="fake-model",
        semantic_version="0.1.0",
    )

    assert verdict.status == "compliant"
    assert verdict.violations == []


def test_write_judgments_serializes_intermediate_results(
    tmp_path: Path,
) -> None:
    """The public generator preserves action-level semantic decisions."""
    dataset = TrajectoryDataset(
        source_format="test",
        trajectories=[confirmed_trajectory()],
    )
    output_path = tmp_path / "write_confirmation_judgments.json"

    result = write_judgments(
        dataset,
        confirmation_rule(),
        confirmation_context(),
        output_path,
        call_model=lambda _system, _user: json.dumps(
            judgment(assessment()).model_dump(mode="json")
        ),
        model_name="fake-model",
    )

    saved = json.loads(output_path.read_text(encoding="utf-8"))
    assert result.semantic_version == "0.1.0"
    assert saved["rule_id"] == "airline.write.confirmation.001"
    assert saved["judgments"][0]["assessments"][0] == {
        "write_step_id": 3,
        "details_sufficient": True,
        "confirmation_valid": True,
        "details_step_ids": [1],
        "confirmation_step_ids": [2],
        "rationale": "Action-specific confirmation assessment.",
    }

"""Verifier for the airline human-transfer scope rule."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.trajectory.schema import (
    MessageEvent,
    ToolCallEvent,
    ToolResultEvent,
    Trajectory,
    TrajectoryDataset,
)
from src.verifiers.schema import (
    ComplianceVerdict,
    ComplianceVerdictDataset,
    SchemaEvidence,
    Violation,
)


VERIFIER_NAME = "airline_transfer_scope_verifier"
VERIFIER_VERSION = "0.2.0"

RULE_ID = "airline.transfer.scope.001"
RULE_VERSION = "0.1.0"
TRANSFER_TOOL_NAME = "transfer_to_human_agents"


class StrictModel(BaseModel):
    """Reject undeclared semantic-judgment fields."""

    model_config = ConfigDict(extra="forbid")


class TransferScopeJudgment(StrictModel):
    """Semantic decision supplied independently of deterministic checks."""

    trajectory_id: str = Field(min_length=1)
    should_transfer: bool | None

    # Required when a missing transfer is considered a violation.
    decision_step_id: int | None = Field(default=None, ge=0)

    # Visible trajectory steps supporting the semantic decision.
    evidence_step_ids: list[int] = Field(default_factory=list)
    rationale: str = Field(min_length=1)
    # Accepted only so v0.1 Judge files remain readable. It is ignored and
    # excluded from all newly serialized semantic inputs.
    confidence: Literal["low", "medium", "high"] | None = Field(
        default=None,
        exclude=True,
    )

    @model_validator(mode="after")
    def validate_decision_evidence(self) -> "TransferScopeJudgment":
        """Require localized evidence for every determinate decision."""
        if self.should_transfer is not None and not self.evidence_step_ids:
            raise ValueError(
                "a determinate should_transfer judgment requires evidence steps"
            )

        if self.should_transfer is True and self.decision_step_id is None:
            raise ValueError(
                "should_transfer=true requires decision_step_id"
            )

        if len(set(self.evidence_step_ids)) != len(self.evidence_step_ids):
            raise ValueError("evidence_step_ids must not contain duplicates")

        return self


class TransferScopeJudgmentDataset(StrictModel):
    """External semantic inputs for one verifier run."""

    schema_version: Literal["0.1.0", "0.2.0"] = "0.2.0"
    rule_id: Literal["airline.transfer.scope.001"] = RULE_ID
    judge_name: str = Field(min_length=1)
    judge_version: str = Field(min_length=1)
    judgments: list[TransferScopeJudgment]

    @model_validator(mode="after")
    def validate_unique_trajectories(self) -> "TransferScopeJudgmentDataset":
        """Allow exactly one semantic judgment per trajectory."""
        trajectory_ids = [item.trajectory_id for item in self.judgments]
        if len(set(trajectory_ids)) != len(trajectory_ids):
            raise ValueError("duplicate trajectory_id in semantic judgments")
        return self


def find_transfer_calls(trajectory: Trajectory) -> list[ToolCallEvent]:
    """Deterministically locate actual transfer actions."""
    return [
        event
        for event in trajectory.events
        if isinstance(event, ToolCallEvent)
        and event.tool_name == TRANSFER_TOOL_NAME
    ]


def evidence_from_step(
    trajectory: Trajectory,
    step_id: int,
    *,
    description: str,
) -> SchemaEvidence:
    """Convert one validated trajectory event into structured evidence."""
    if step_id >= len(trajectory.events):
        raise ValueError(
            f"evidence step {step_id} is outside trajectory "
            f"{trajectory.trajectory_id}"
        )

    event = trajectory.events[step_id]
    if event.step_id != step_id:
        raise ValueError(
            f"trajectory event index and step_id differ at {step_id}"
        )

    if isinstance(event, MessageEvent):
        value = {
            "actor": event.actor,
            "event_type": event.event_type,
            "content": event.content,
        }
    elif isinstance(event, ToolCallEvent):
        value = {
            "actor": event.actor,
            "event_type": event.event_type,
            "tool_name": event.tool_name,
            "arguments": event.arguments,
        }
    elif isinstance(event, ToolResultEvent):
        value = {
            "actor": event.actor,
            "event_type": event.event_type,
            "tool_name": event.tool_name,
            "result": event.result,
            "error": event.error,
        }
    else:
        raise TypeError(f"Unsupported event type: {type(event).__name__}")

    return SchemaEvidence(
        trajectory_id=trajectory.trajectory_id,
        step_id=step_id,
        source=f"events[{step_id}]",
        value=value,
        description=description,
    )


def verify_transfer_scope(
    trajectory: Trajectory,
    judgment: TransferScopeJudgment,
    *,
    judge_name: str,
    judge_version: str,
) -> ComplianceVerdict:
    """Combine deterministic transfer facts with one semantic judgment."""
    if judgment.trajectory_id != trajectory.trajectory_id:
        raise ValueError(
            "semantic judgment trajectory_id does not match trajectory: "
            f"{judgment.trajectory_id!r} != {trajectory.trajectory_id!r}"
        )

    transfer_calls = find_transfer_calls(trajectory)
    actual_transfer = bool(transfer_calls)
    transfer_steps = [event.step_id for event in transfer_calls]

    semantic_evidence = [
        evidence_from_step(
            trajectory,
            step_id,
            description="Visible evidence used by the semantic scope judge.",
        )
        for step_id in judgment.evidence_step_ids
    ]

    summary_evidence = SchemaEvidence(
        trajectory_id=trajectory.trajectory_id,
        step_id=None,
        source="semantic_judge.transfer_scope",
        value={
            "actual_transfer": actual_transfer,
            "transfer_steps": transfer_steps,
            "should_transfer": judgment.should_transfer,
            "judge_name": judge_name,
            "judge_version": judge_version,
        },
        description=judgment.rationale,
    )

    if judgment.should_transfer is None:
        return ComplianceVerdict(
            trajectory_id=trajectory.trajectory_id,
            compliant=None,
            violations=[],
            evidence=[summary_evidence, *semantic_evidence],
        )

    if actual_transfer == judgment.should_transfer:
        return ComplianceVerdict(
            trajectory_id=trajectory.trajectory_id,
            compliant=True,
            violations=[],
            evidence=[summary_evidence, *semantic_evidence],
        )

    if actual_transfer:
        violation_step = transfer_calls[0].step_id
        transfer_evidence = evidence_from_step(
            trajectory,
            violation_step,
            description="The agent executed a human transfer at this step.",
        )
        description = (
            "The agent transferred the user even though the visible request "
            "could still be handled within policy and tool scope."
        )
        violation_evidence = [transfer_evidence, *semantic_evidence]
    else:
        if judgment.decision_step_id is None:
            raise ValueError(
                "a missed-transfer violation requires decision_step_id"
            )
        violation_step = judgment.decision_step_id
        description = (
            "The agent did not transfer the user after the visible request "
            "became unhandleable within policy and tool scope."
        )
        violation_evidence = semantic_evidence

    violation = Violation(
        rule_id=RULE_ID,
        rule_version=RULE_VERSION,
        severity="medium",
        step_id=violation_step,
        description=description,
        evidence=violation_evidence,
    )

    return ComplianceVerdict(
        trajectory_id=trajectory.trajectory_id,
        compliant=False,
        violations=[violation],
        evidence=[summary_evidence],
    )


def verify_dataset(
    dataset: TrajectoryDataset,
    semantic_inputs: TransferScopeJudgmentDataset,
) -> ComplianceVerdictDataset:
    """Verify a complete trajectory dataset using external semantics."""
    judgments = {
        item.trajectory_id: item
        for item in semantic_inputs.judgments
    }
    trajectory_ids = {
        trajectory.trajectory_id
        for trajectory in dataset.trajectories
    }

    missing = trajectory_ids - set(judgments)
    unexpected = set(judgments) - trajectory_ids
    if missing or unexpected:
        raise ValueError(
            "semantic judgment coverage must exactly match trajectories; "
            f"missing={sorted(missing)}, unexpected={sorted(unexpected)}"
        )

    return ComplianceVerdictDataset(
        verifier_name=VERIFIER_NAME,
        verifier_version=VERIFIER_VERSION,
        verdicts=[
            verify_transfer_scope(
                trajectory,
                judgments[trajectory.trajectory_id],
                judge_name=semantic_inputs.judge_name,
                judge_version=semantic_inputs.judge_version,
            )
            for trajectory in dataset.trajectories
        ],
    )


def verify_file(
    trajectory_path: Path,
    judgment_path: Path,
    output_path: Path,
) -> ComplianceVerdictDataset:
    """Load trajectories and external semantics, then write verdicts."""
    dataset = TrajectoryDataset.model_validate_json(
        trajectory_path.read_text(encoding="utf-8")
    )
    semantic_inputs = TransferScopeJudgmentDataset.model_validate_json(
        judgment_path.read_text(encoding="utf-8")
    )
    verdicts = verify_dataset(dataset, semantic_inputs)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        verdicts.model_dump_json(indent=2),
        encoding="utf-8",
    )
    print(
        f"Verified {len(verdicts.verdicts)} trajectories "
        f"with {verdicts.verifier_name} "
        f"v{verdicts.verifier_version}: {output_path}"
    )
    return verdicts


def main() -> None:
    """Command-line entry point; this command never calls a model."""
    parser = argparse.ArgumentParser(
        description=(
            "Combine deterministic transfer facts with externally supplied "
            "semantic scope judgments. This command does not call a model."
        )
    )
    parser.add_argument("--trajectories", required=True, type=Path)
    parser.add_argument("--judgments", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    verify_file(
        trajectory_path=args.trajectories,
        judgment_path=args.judgments,
        output_path=args.output,
    )


if __name__ == "__main__":
    main()

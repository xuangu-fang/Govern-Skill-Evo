"""Deterministic process verifier for the airline transfer protocol."""

from __future__ import annotations

import argparse
from collections import deque
from pathlib import Path

from src.trajectory.schema import (
    MessageEvent,
    ToolCallEvent,
    Trajectory,
    TrajectoryDataset,
)
from src.verifiers.schema import (
    ComplianceVerdict,
    ComplianceVerdictDataset,
    SchemaEvidence,
    Violation,
)


VERIFIER_NAME = "airline_transfer_protocol_verifier"
VERIFIER_VERSION = "0.1.0"

RULE_ID = "airline.transfer.protocol.001"
RULE_VERSION = "0.1.0"

TRANSFER_TOOL_NAME = "transfer_to_human_agents"
TRANSFER_NOTICE = (
    "YOU ARE BEING TRANSFERRED TO A HUMAN AGENT. PLEASE HOLD ON."
)


def verify_process(trajectory: Trajectory) -> ComplianceVerdict:
    """Check call-before-notice ordering for the transfer protocol."""
    pending_calls: deque[ToolCallEvent] = deque()
    violations: list[Violation] = []
    transfer_call_count = 0
    transfer_notice_count = 0

    for event in trajectory.events:
        if (
            isinstance(event, ToolCallEvent)
            and event.tool_name == TRANSFER_TOOL_NAME
        ):
            transfer_call_count += 1
            pending_calls.append(event)
            continue

        if not (
            isinstance(event, MessageEvent)
            and event.actor == "agent"
            and event.content.strip() == TRANSFER_NOTICE
        ):
            continue

        transfer_notice_count += 1

        if pending_calls:
            pending_calls.popleft()
            continue

        evidence = SchemaEvidence(
            trajectory_id=trajectory.trajectory_id,
            step_id=event.step_id,
            source=f"events[{event.step_id}].content",
            value=event.content,
            description=(
                "The transfer notice appeared before any unmatched "
                "transfer tool call."
            ),
        )
        violations.append(
            Violation(
                rule_id=RULE_ID,
                rule_version=RULE_VERSION,
                severity="medium",
                step_id=event.step_id,
                description=(
                    "The agent sent the transfer notice without first "
                    "calling transfer_to_human_agents."
                ),
                evidence=[evidence],
            )
        )

    for call in pending_calls:
        evidence = SchemaEvidence(
            trajectory_id=trajectory.trajectory_id,
            step_id=call.step_id,
            source=f"events[{call.step_id}].tool_name",
            value=call.tool_name,
            description=(
                "No required transfer notice followed this transfer "
                "tool call."
            ),
        )
        violations.append(
            Violation(
                rule_id=RULE_ID,
                rule_version=RULE_VERSION,
                severity="medium",
                step_id=call.step_id,
                description=(
                    "The agent called transfer_to_human_agents but did "
                    "not subsequently send the required transfer notice."
                ),
                evidence=[evidence],
            )
        )

    summary_evidence = SchemaEvidence(
        trajectory_id=trajectory.trajectory_id,
        step_id=None,
        source="events",
        value={
            "transfer_call_count": transfer_call_count,
            "transfer_notice_count": transfer_notice_count,
        },
        description=(
            "Counts used by the deterministic transfer protocol check."
        ),
    )

    return ComplianceVerdict(
        trajectory_id=trajectory.trajectory_id,
        compliant=not violations,
        violations=violations,
        evidence=[summary_evidence],
    )


def verify_dataset(
    dataset: TrajectoryDataset,
) -> ComplianceVerdictDataset:
    """Run the transfer protocol check over every trajectory."""
    return ComplianceVerdictDataset(
        verifier_name=VERIFIER_NAME,
        verifier_version=VERIFIER_VERSION,
        verdicts=[
            verify_process(trajectory)
            for trajectory in dataset.trajectories
        ],
    )


def verify_file(
    input_path: Path,
    output_path: Path,
) -> ComplianceVerdictDataset:
    """Load trajectories, verify them, and write compliance verdicts."""
    dataset = TrajectoryDataset.model_validate_json(
        input_path.read_text(encoding="utf-8")
    )
    verdicts = verify_dataset(dataset)

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
    """Command-line entry point."""
    parser = argparse.ArgumentParser(
        description=(
            "Check common trajectories against the airline transfer "
            "protocol."
        )
    )
    parser.add_argument(
        "--input",
        required=True,
        type=Path,
        help="Path to a common TrajectoryDataset v0.2 JSON file.",
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Path at which to write ComplianceVerdictDataset JSON.",
    )
    args = parser.parse_args()

    verify_file(
        input_path=args.input,
        output_path=args.output,
    )


if __name__ == "__main__":
    main()

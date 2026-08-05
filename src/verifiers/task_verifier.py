"""Task verifier backed by the upstream benchmark outcome."""

from __future__ import annotations

import argparse
from pathlib import Path

from src.trajectory.schema import Trajectory, TrajectoryDataset
from src.verifiers.schema import (
    SchemaEvidence,
    TaskVerdict,
    TaskVerdictDataset,
)


VERIFIER_NAME = "official_outcome_task_verifier"
VERIFIER_VERSION = "0.1.0"


def verify_task(trajectory: Trajectory) -> TaskVerdict:
    """Convert one upstream task outcome into an evidenced verdict."""
    score = trajectory.outcome.score

    if score is None:
        success = None
        description = "The upstream benchmark did not provide a task score."
    else:
        success = score == 1.0
        description = "Task score reported by the upstream benchmark."

    evidence = SchemaEvidence(
        trajectory_id=trajectory.trajectory_id,
        step_id=None,
        source="outcome.score",
        value=score,
        description=description,
    )

    return TaskVerdict(
        trajectory_id=trajectory.trajectory_id,
        success=success,
        score=score,
        evidence=[evidence],
    )


def verify_dataset(
    dataset: TrajectoryDataset,
) -> TaskVerdictDataset:
    """Verify every trajectory in a common trajectory dataset."""
    return TaskVerdictDataset(
        verifier_name=VERIFIER_NAME,
        verifier_version=VERIFIER_VERSION,
        verdicts=[
            verify_task(trajectory)
            for trajectory in dataset.trajectories
        ],
    )


def verify_file(
    input_path: Path,
    output_path: Path,
) -> TaskVerdictDataset:
    """Load common trajectories, verify them, and write verdict JSON."""
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
            "Convert common trajectory outcomes into task verdicts."
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
        help="Path at which to write TaskVerdictDataset JSON.",
    )
    args = parser.parse_args()

    verify_file(
        input_path=args.input,
        output_path=args.output,
    )


if __name__ == "__main__":
    main()

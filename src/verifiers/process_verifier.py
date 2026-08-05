"""Generic orchestration for multi-rule process verification."""

from __future__ import annotations

import argparse
from pathlib import Path

from src.policies.schema import PolicyRuleSet, VerificationContext
from src.trajectory.schema import TrajectoryDataset
from src.verifiers.builtin_handlers import build_builtin_registry
from src.verifiers.registry import (
    CheckerRegistry,
    JudgmentSource,
)
from src.verifiers.schema import (
    ProcessVerdict,
    ProcessVerdictDataset,
    RuleVerdict,
)


VERIFIER_NAME = "process_verifier"
VERIFIER_VERSION = "0.4.0"


def aggregate_rule_verdicts(
    trajectory_id: str,
    rule_verdicts: list[RuleVerdict],
) -> ProcessVerdict:
    """Apply the process-compliance truth table to one trajectory."""
    if not rule_verdicts:
        raise ValueError("cannot aggregate an empty list of rule verdicts")

    if any(item.status == "violation" for item in rule_verdicts):
        compliant: bool | None = False
    elif any(item.status == "indeterminate" for item in rule_verdicts):
        compliant = None
    else:
        compliant = True

    return ProcessVerdict(
        trajectory_id=trajectory_id,
        compliant=compliant,
        violations=[
            violation
            for item in rule_verdicts
            for violation in item.violations
        ],
        evidence=[
            evidence
            for item in rule_verdicts
            for evidence in item.evidence
        ],
        rule_verdicts=rule_verdicts,
    )


def verify_dataset(
    dataset: TrajectoryDataset,
    rule_set: PolicyRuleSet,
    *,
    context: VerificationContext | None = None,
    judgment_inputs: dict[str, JudgmentSource] | None = None,
    registry: CheckerRegistry | None = None,
) -> ProcessVerdictDataset:
    """Run every configured rule against every trajectory."""
    resolved_context = context or VerificationContext()
    resolved_registry = registry or build_builtin_registry()
    resolved_registry.bind_judgments(
        rule_set,
        judgment_inputs or {},
        {
            trajectory.trajectory_id
            for trajectory in dataset.trajectories
        },
    )
    resolved_registry.validate_rule_set(rule_set)

    return ProcessVerdictDataset(
        verifier_name=VERIFIER_NAME,
        verifier_version=VERIFIER_VERSION,
        rule_set_id=rule_set.rule_set_id,
        rule_set_version=rule_set.rule_set_version,
        verdicts=[
            aggregate_rule_verdicts(
                trajectory.trajectory_id,
                [
                    resolved_registry.verify(
                        trajectory,
                        rule,
                        resolved_context,
                    )
                    for rule in rule_set.rules
                ],
            )
            for trajectory in dataset.trajectories
        ],
    )


def verify_file(
    trajectory_path: Path,
    rule_path: Path,
    output_path: Path,
    *,
    context_path: Path | None = None,
    judgment_paths: dict[str, Path] | None = None,
) -> ProcessVerdictDataset:
    """Load verifier inputs, run all rules, and serialize the result."""
    dataset = TrajectoryDataset.model_validate_json(
        trajectory_path.read_text(encoding="utf-8")
    )
    rule_set = PolicyRuleSet.model_validate_json(
        rule_path.read_text(encoding="utf-8")
    )
    context = (
        VerificationContext.model_validate_json(
            context_path.read_text(encoding="utf-8")
        )
        if context_path is not None
        else VerificationContext()
    )

    verdicts = verify_dataset(
        dataset,
        rule_set,
        context=context,
        judgment_inputs=judgment_paths,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        verdicts.model_dump_json(indent=2),
        encoding="utf-8",
    )
    return verdicts


def run_process_verifier(
    trajectory_path: Path,
    rule_path: Path,
    output_path: Path,
    *,
    context_path: Path | None = None,
    judgment_paths: dict[str, Path] | None = None,
) -> ProcessVerdictDataset:
    """Load saved inputs and run every configured rule."""
    return verify_file(
        trajectory_path=trajectory_path,
        rule_path=rule_path,
        output_path=output_path,
        context_path=context_path,
        judgment_paths=judgment_paths,
    )


def parse_judgment_assignments(
    values: list[str],
) -> dict[str, Path]:
    """Parse repeated RULE_ID=PATH command-line assignments."""
    assignments: dict[str, Path] = {}
    for value in values:
        rule_id, separator, raw_path = value.partition("=")
        if not separator or not rule_id or not raw_path:
            raise ValueError(
                "--judgments must use RULE_ID=PATH"
            )
        if rule_id in assignments:
            raise ValueError(
                f"duplicate --judgments rule_id: {rule_id}"
            )
        assignments[rule_id] = Path(raw_path)
    return assignments


def main() -> None:
    """Command-line entry point for saved trajectories and judgments."""
    parser = argparse.ArgumentParser(
        description=(
            "Run deterministic and semantic policy rules through one "
            "Process Verifier. Semantic rules consume saved judgments."
        )
    )
    parser.add_argument(
        "--trajectories",
        "--input",
        dest="trajectories",
        required=True,
        type=Path,
    )
    parser.add_argument("--rules", required=True, type=Path)
    parser.add_argument("--context", type=Path)
    parser.add_argument(
        "--judgments",
        action="append",
        default=[],
        metavar="RULE_ID=PATH",
        help=(
            "Saved semantic judgments for one rule. Repeat once per "
            "semantic rule."
        ),
    )
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    verdicts = run_process_verifier(
        trajectory_path=args.trajectories,
        rule_path=args.rules,
        output_path=args.output,
        context_path=args.context,
        judgment_paths=parse_judgment_assignments(args.judgments),
    )
    print(
        f"Verified {len(verdicts.verdicts)} trajectories with "
        f"{verdicts.verifier_name} v{verdicts.verifier_version}: "
        f"{args.output}"
    )


if __name__ == "__main__":
    main()

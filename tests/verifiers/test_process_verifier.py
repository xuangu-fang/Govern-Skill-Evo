"""Tests for generic multi-rule Process Verifier orchestration."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import BaseModel

from src.policies.schema import (
    DeterministicVerifierSpec,
    PolicyRule,
    PolicyRuleSet,
    SemanticVerifierSpec,
)
from src.trajectory.schema import TrajectoryDataset
from src.verifiers.process_verifier import (
    aggregate_rule_verdicts,
    parse_judgment_assignments,
    run_process_verifier,
    verify_dataset,
)
from src.verifiers.registry import CheckerRegistry
from src.verifiers.schema import RuleVerdict, Violation
from src.verifiers.handlers.semantic.transfer_scope import (
    TransferScopeJudgment,
    TransferScopeJudgmentDataset,
)
from src.verifiers.handlers.semantic.write_confirmation import (
    WriteConfirmationAssessment,
    WriteConfirmationJudgment,
    WriteConfirmationJudgmentDataset,
)


def rule_verdict(
    index: int,
    status: str,
) -> RuleVerdict:
    """Build one internally consistent result for aggregation tests."""
    rule_id = f"test.rule.{index}"
    violations = (
        [
            Violation(
                rule_id=rule_id,
                rule_version="0.1.0",
                severity="medium",
                step_id=0,
                description="Test violation.",
            )
        ]
        if status == "violation"
        else []
    )
    return RuleVerdict(
        trajectory_id="trajectory-1",
        rule_id=rule_id,
        rule_version="0.1.0",
        verifier_type="deterministic",
        status=status,
        violations=violations,
    )


@pytest.mark.parametrize(
    ("statuses", "expected"),
    [
        (["compliant"], True),
        (["indeterminate", "compliant"], None),
        (["indeterminate", "violation"], False),
        (["compliant", "violation"], False),
    ],
)
def test_aggregate_rule_verdict_truth_table(
    statuses: list[str],
    expected: bool | None,
) -> None:
    """Violation wins, then indeterminate, otherwise the result passes."""
    verdict = aggregate_rule_verdicts(
        "trajectory-1",
        [
            rule_verdict(index, status)
            for index, status in enumerate(statuses)
        ],
    )

    assert verdict.compliant is expected
    assert [item.status for item in verdict.rule_verdicts] == statuses


def test_aggregate_rejects_empty_rule_results() -> None:
    """An empty rule set cannot silently produce compliant=true."""
    with pytest.raises(ValueError, match="empty"):
        aggregate_rule_verdicts("trajectory-1", [])


def test_rule_verdict_rejects_violation_without_details() -> None:
    """RuleStatus cannot contradict the structured violations list."""
    with pytest.raises(ValueError, match="at least one violation"):
        RuleVerdict(
            trajectory_id="trajectory-1",
            rule_id="test.rule.1",
            rule_version="0.1.0",
            verifier_type="deterministic",
            status="violation",
        )


def test_policy_rule_set_rejects_duplicate_rule_ids() -> None:
    """Registry dispatch remains unambiguous within one rule set."""
    rule = PolicyRule(
        rule_id="test.rule.1",
        rule_version="0.1.0",
        statement="Test statement.",
        severity="medium",
        verifier=DeterministicVerifierSpec(
            type="deterministic",
            checker="test",
        ),
    )
    with pytest.raises(ValueError, match="duplicate rule_id"):
        PolicyRuleSet(
            rule_set_id="test-rules",
            rule_set_version="0.1.0",
            domain="test",
            rules=[rule, rule],
        )


def test_unknown_checker_is_rejected_before_verification() -> None:
    """A typo in policy configuration is a run error, not indeterminate."""
    rule_set = PolicyRuleSet(
        rule_set_id="test-rules",
        rule_set_version="0.1.0",
        domain="airline",
        rules=[
            PolicyRule(
                rule_id="airline.unknown.001",
                rule_version="0.1.0",
                statement="Unknown test rule.",
                severity="medium",
                verifier=DeterministicVerifierSpec(
                    type="deterministic",
                    checker="does_not_exist",
                ),
            )
        ],
    )
    dataset = TrajectoryDataset.model_validate_json(
        _fixture_path("common_trajectories_v02.json").read_text(
            encoding="utf-8"
        )
    )

    with pytest.raises(ValueError, match="unknown checker"):
        verify_dataset(dataset, rule_set)


def test_missing_semantic_runtime_input_is_a_run_error() -> None:
    """Missing judgments are not converted to an indeterminate verdict."""
    dataset = TrajectoryDataset.model_validate_json(
        _fixture_path("common_trajectories_v02.json").read_text(
            encoding="utf-8"
        )
    )

    with pytest.raises(ValueError, match="judgment sources.*missing"):
        verify_dataset(dataset, _airline_rule_set())


def _fixture_path(name: str) -> Path:
    root = Path(__file__).resolve().parents[2]
    return root / "experiments/results/day5_schema" / name


def _airline_rule_set() -> PolicyRuleSet:
    root = Path(__file__).resolve().parents[2]
    return PolicyRuleSet.model_validate_json(
        (root / "policies/airline/rules_v01.json").read_text(
            encoding="utf-8"
        )
    )


def _airline_rule_set_v02() -> PolicyRuleSet:
    root = Path(__file__).resolve().parents[2]
    return PolicyRuleSet.model_validate_json(
        (root / "policies/airline/rules_v02.json").read_text(
            encoding="utf-8"
        )
    )


def _airline_rule_set_v03() -> PolicyRuleSet:
    root = Path(__file__).resolve().parents[2]
    return PolicyRuleSet.model_validate_json(
        (root / "policies/airline/rules_v03.json").read_text(
            encoding="utf-8"
        )
    )


def _airline_rule_set_v04() -> PolicyRuleSet:
    root = Path(__file__).resolve().parents[2]
    return PolicyRuleSet.model_validate_json(
        (root / "policies/airline/rules_v04.json").read_text(
            encoding="utf-8"
        )
    )


def test_airline_rule_statements_are_verbatim_policy_text() -> None:
    """Versioned rule statements must be continuous Policy excerpts."""
    root = Path(__file__).resolve().parents[2]
    policy_text = (
        root / "external/tau2-bench/data/tau2/domains/airline/policy.md"
    ).read_text(encoding="utf-8")

    for version in ("v01", "v02", "v03", "v04"):
        rule_set = PolicyRuleSet.model_validate_json(
            (root / f"policies/airline/rules_{version}.json").read_text(
                encoding="utf-8"
            )
        )
        for rule in rule_set.rules:
            assert rule.statement in policy_text, rule.rule_id


def test_both_current_rules_run_through_generic_entry() -> None:
    """The ten Gold trajectories receive protocol and scope results together."""
    trajectory_path = _fixture_path("common_trajectories_v02.json")
    root = Path(__file__).resolve().parents[2]
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

    results = verify_dataset(
        dataset,
        _airline_rule_set(),
        judgment_inputs={
            "airline.transfer.scope.001": semantic_inputs,
        },
    )

    assert len(results.verdicts) == 10
    assert all(
        [item.rule_id for item in verdict.rule_verdicts]
        == [
            "airline.transfer.protocol.001",
            "airline.transfer.scope.001",
        ]
        for verdict in results.verdicts
    )
    actual = {
        verdict.trajectory_id: verdict.compliant
        for verdict in results.verdicts
    }
    expected = {
        label["trajectory_id"]: label["verdict"] == "compliant"
        for label in gold["labels"]
    }
    assert actual == expected

    expanded_results = verify_dataset(
        dataset,
        _airline_rule_set_v02(),
        judgment_inputs={
            "airline.transfer.scope.001": semantic_inputs,
        },
    )
    assert expanded_results.rule_set_version == "0.2.0"
    assert all(
        [item.rule_id for item in verdict.rule_verdicts]
        == [
            "airline.transfer.protocol.001",
            "airline.tool.response_exclusivity.001",
            "airline.transfer.scope.001",
        ]
        for verdict in expanded_results.verdicts
    )
    assert all(
        verdict.rule_verdicts[1].status == "compliant"
        for verdict in expanded_results.verdicts
    )
    assert {
        verdict.trajectory_id: verdict.compliant
        for verdict in expanded_results.verdicts
    } == expected

    confirmation_steps = {
        "8": [(22, 20, 21)],
        "11": [(22, 20, 21)],
        "12": [(16, 14, 15), (18, 14, 15)],
        "14": [(34, 32, 33), (36, 32, 33)],
    }
    write_confirmation_inputs = WriteConfirmationJudgmentDataset(
        model_name="manual-regression-fixture",
        semantic_version="0.1.0",
        judgments=[
            WriteConfirmationJudgment(
                trajectory_id=trajectory.trajectory_id,
                assessments=[
                    WriteConfirmationAssessment(
                        write_step_id=write_step,
                        details_sufficient=True,
                        confirmation_valid=True,
                        details_step_ids=[detail_step],
                        confirmation_step_ids=[confirmation_step],
                        rationale=(
                            "The write was listed and explicitly confirmed."
                        ),
                    )
                    for write_step, detail_step, confirmation_step in (
                        confirmation_steps.get(trajectory.task_id, [])
                    )
                ],
                rationale=(
                    "All covered writes were explicitly confirmed."
                    if trajectory.task_id in confirmation_steps
                    else "The trajectory has no covered writes."
                ),
            )
            for trajectory in dataset.trajectories
        ],
    )
    v03_results = verify_dataset(
        dataset,
        _airline_rule_set_v03(),
        judgment_inputs={
            "airline.transfer.scope.001": semantic_inputs,
            "airline.write.confirmation.001": (
                write_confirmation_inputs
            ),
        },
    )

    assert v03_results.rule_set_version == "0.3.0"
    assert all(
        [item.rule_id for item in verdict.rule_verdicts]
        == [
            "airline.transfer.protocol.001",
            "airline.tool.response_exclusivity.001",
            "airline.write.confirmation.001",
            "airline.transfer.scope.001",
        ]
        for verdict in v03_results.verdicts
    )
    assert {
        verdict.trajectory_id: verdict.compliant
        for verdict in v03_results.verdicts
    } == expected

    v04_results = verify_dataset(
        dataset,
        _airline_rule_set_v04(),
        judgment_inputs={
            "airline.transfer.scope.001": semantic_inputs,
            "airline.write.confirmation.001": (
                write_confirmation_inputs
            ),
        },
    )

    assert v04_results.rule_set_version == "0.4.0"
    assert all(
        [item.rule_id for item in verdict.rule_verdicts]
        == [
            "airline.transfer.protocol.001",
            "airline.tool.response_exclusivity.001",
            "airline.payment.method.001",
            "airline.write.confirmation.001",
            "airline.transfer.scope.001",
        ]
        for verdict in v04_results.verdicts
    )
    assert all(
        verdict.rule_verdicts[2].status == "compliant"
        for verdict in v04_results.verdicts
    )
    assert {
        verdict.trajectory_id: verdict.compliant
        for verdict in v04_results.verdicts
    } == expected


def test_generic_run_loads_rule_keyed_semantic_judgment(
    tmp_path: Path,
) -> None:
    """The public entry loads a generic rule_id-to-path assignment."""
    root = Path(__file__).resolve().parents[2]
    dataset = TrajectoryDataset.model_validate_json(
        _fixture_path("common_trajectories_v02.json").read_text(
            encoding="utf-8"
        )
    )
    trajectory = dataset.trajectories[0]
    trajectory_path = tmp_path / "trajectories.json"
    trajectory_path.write_text(
        TrajectoryDataset(
            source_format=dataset.source_format,
            trajectories=[trajectory],
        ).model_dump_json(indent=2),
        encoding="utf-8",
    )

    judgment_path = tmp_path / "judgments.json"
    judgment_path.write_text(
        TransferScopeJudgmentDataset(
            model_name="fake-model",
            semantic_version="0.1.0",
            judgments=[
                TransferScopeJudgment(
                    trajectory_id=trajectory.trajectory_id,
                    should_transfer=False,
                    decision_step_id=None,
                    evidence_step_ids=[19],
                    rationale="The request remains within tool scope.",
                )
            ],
        ).model_dump_json(indent=2),
        encoding="utf-8",
    )
    output_path = tmp_path / "process_verdicts.json"

    result = run_process_verifier(
        trajectory_path=trajectory_path,
        rule_path=root / "policies/airline/rules_v01.json",
        output_path=output_path,
        judgment_paths={
            "airline.transfer.scope.001": judgment_path,
        },
    )

    assert output_path.exists()
    assert [
        item.status
        for item in result.verdicts[0].rule_verdicts
    ] == ["compliant", "compliant"]


def test_parse_judgment_assignments_is_generic() -> None:
    """Repeated CLI assignments preserve arbitrary rule IDs."""
    assignments = parse_judgment_assignments(
        [
            "rule.one=one.json",
            "rule.two=path/to/two.json",
        ]
    )

    assert assignments == {
        "rule.one": Path("one.json"),
        "rule.two": Path("path/to/two.json"),
    }


def test_parse_judgment_assignments_rejects_duplicates() -> None:
    """One semantic rule cannot silently receive two datasets."""
    with pytest.raises(ValueError, match="duplicate"):
        parse_judgment_assignments(
            ["rule.one=one.json", "rule.one=other.json"]
        )


def test_new_semantic_handler_requires_no_orchestrator_change() -> None:
    """A registered fifth handler runs through the unchanged core loop."""

    class FakeJudgment(BaseModel):
        trajectory_id: str

    class FakeJudgmentDataset(BaseModel):
        rule_id: str
        judgments: list[FakeJudgment]

    dataset = TrajectoryDataset.model_validate_json(
        _fixture_path("common_trajectories_v02.json").read_text(
            encoding="utf-8"
        )
    )
    trajectory = dataset.trajectories[0]
    single_trajectory_dataset = TrajectoryDataset(
        source_format=dataset.source_format,
        trajectories=[trajectory],
    )
    rule_set = PolicyRuleSet(
        rule_set_id="fifth-rule-test",
        rule_set_version="0.1.0",
        domain="airline",
        rules=[
            PolicyRule(
                rule_id="airline.fifth.001",
                rule_version="0.1.0",
                statement="Fifth semantic rule.",
                severity="medium",
                verifier=SemanticVerifierSpec(
                    type="semantic",
                    checker="fifth_handler",
                ),
            )
        ],
    )
    semantic_inputs = FakeJudgmentDataset(
        rule_id="airline.fifth.001",
        judgments=[
            FakeJudgment(trajectory_id=trajectory.trajectory_id)
        ],
    )

    def make_checker(inputs: FakeJudgmentDataset):
        known_ids = {
            judgment.trajectory_id
            for judgment in inputs.judgments
        }

        def check(item, rule, _context):
            assert item.trajectory_id in known_ids
            return RuleVerdict(
                trajectory_id=item.trajectory_id,
                rule_id=rule.rule_id,
                rule_version=rule.rule_version,
                verifier_type=rule.verifier.type,
                status="compliant",
            )

        return check

    registry = CheckerRegistry()
    registry.register_semantic(
        "fifth_handler",
        FakeJudgmentDataset,
        make_checker,
    )

    result = verify_dataset(
        single_trajectory_dataset,
        rule_set,
        judgment_inputs={"airline.fifth.001": semantic_inputs},
        registry=registry,
    )

    assert result.verdicts[0].rule_verdicts[0].status == "compliant"

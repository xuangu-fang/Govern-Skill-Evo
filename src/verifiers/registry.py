"""Registry and common adapter for policy-rule checkers."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel

from src.policies.schema import (
    PolicyRule,
    PolicyRuleSet,
    VerificationContext,
)
from src.trajectory.schema import Trajectory
from src.verifiers.schema import ComplianceVerdict, RuleVerdict


VerifierType = Literal["deterministic", "semantic"]
RuleChecker = Callable[
    [Trajectory, PolicyRule, VerificationContext],
    RuleVerdict,
]
JudgmentSource = Path | BaseModel
SemanticCheckerFactory = Callable[[Any], RuleChecker]


@dataclass(frozen=True)
class SemanticHandler:
    """Loader and checker factory for one semantic checker name."""

    judgment_model: type[BaseModel]
    checker_factory: SemanticCheckerFactory


class CheckerRegistry:
    """Map rule configuration names to concrete checker functions."""

    def __init__(self) -> None:
        self._checkers: dict[tuple[VerifierType, str], RuleChecker] = {}
        self._semantic_handlers: dict[str, SemanticHandler] = {}
        self._bound_semantic_checkers: dict[str, RuleChecker] = {}

    def register(
        self,
        verifier_type: VerifierType,
        checker_name: str,
        checker: RuleChecker,
    ) -> None:
        """Register one checker and reject ambiguous duplicate names."""
        key = (verifier_type, checker_name)
        if key in self._checkers or (
            verifier_type == "semantic"
            and checker_name in self._semantic_handlers
        ):
            raise ValueError(
                "checker is already registered: "
                f"{verifier_type}:{checker_name}"
            )
        self._checkers[key] = checker

    def register_semantic(
        self,
        checker_name: str,
        judgment_model: type[BaseModel],
        checker_factory: SemanticCheckerFactory,
    ) -> None:
        """Register one semantic handler and its Judgment Dataset loader."""
        key = ("semantic", checker_name)
        if key in self._checkers or checker_name in self._semantic_handlers:
            raise ValueError(
                "checker is already registered: "
                f"semantic:{checker_name}"
            )
        self._semantic_handlers[checker_name] = SemanticHandler(
            judgment_model=judgment_model,
            checker_factory=checker_factory,
        )

    def bind_judgments(
        self,
        rule_set: PolicyRuleSet,
        judgment_sources: dict[str, JudgmentSource],
        trajectory_ids: set[str],
    ) -> None:
        """Load and bind saved judgments for all configured semantic rules."""
        self._bound_semantic_checkers = {}
        self._validate_known_checkers(rule_set)

        required_rules = [
            rule
            for rule in rule_set.rules
            if rule.verifier.type == "semantic"
            and rule.verifier.checker in self._semantic_handlers
        ]
        required_rule_ids = {rule.rule_id for rule in required_rules}
        supplied_rule_ids = set(judgment_sources)
        missing_sources = required_rule_ids - supplied_rule_ids
        unexpected_sources = supplied_rule_ids - required_rule_ids
        if missing_sources or unexpected_sources:
            raise ValueError(
                "judgment sources must exactly match semantic rules; "
                f"missing={sorted(missing_sources)}, "
                f"unexpected={sorted(unexpected_sources)}"
            )

        for rule in required_rules:
            handler = self._semantic_handlers[rule.verifier.checker]
            source = judgment_sources[rule.rule_id]
            if isinstance(source, Path):
                dataset = handler.judgment_model.model_validate_json(
                    source.read_text(encoding="utf-8")
                )
            elif isinstance(source, handler.judgment_model):
                dataset = source
            else:
                raise TypeError(
                    f"{rule.rule_id} judgments must be a Path or "
                    f"{handler.judgment_model.__name__}"
                )

            dataset_rule_id = getattr(dataset, "rule_id", None)
            if dataset_rule_id != rule.rule_id:
                raise ValueError(
                    "judgment rule_id does not match configured rule: "
                    f"{dataset_rule_id!r} != {rule.rule_id!r}"
                )
            judgments = getattr(dataset, "judgments", None)
            if not isinstance(judgments, list):
                raise ValueError(
                    f"{rule.rule_id} Judgment Dataset needs judgments"
                )
            judgment_ids = [
                getattr(judgment, "trajectory_id", None)
                for judgment in judgments
            ]
            if any(
                not isinstance(trajectory_id, str) or not trajectory_id
                for trajectory_id in judgment_ids
            ):
                raise ValueError(
                    f"{rule.rule_id} judgments need trajectory_id"
                )
            if len(set(judgment_ids)) != len(judgment_ids):
                raise ValueError(
                    f"{rule.rule_id} judgments contain duplicate "
                    "trajectory_id"
                )
            resolved_judgment_ids = set(judgment_ids)
            missing = trajectory_ids - resolved_judgment_ids
            unexpected = resolved_judgment_ids - trajectory_ids
            if missing or unexpected:
                raise ValueError(
                    f"{rule.rule_id} judgment coverage must exactly match "
                    "trajectories; "
                    f"missing={sorted(missing)}, "
                    f"unexpected={sorted(unexpected)}"
                )
            self._bound_semantic_checkers[rule.rule_id] = (
                handler.checker_factory(dataset)
            )

    def _validate_known_checkers(
        self,
        rule_set: PolicyRuleSet,
    ) -> None:
        """Reject configured checker names with no registered handler."""
        known = set(self._checkers) | {
            ("semantic", checker_name)
            for checker_name in self._semantic_handlers
        }
        unknown = [
            f"{rule.verifier.type}:{rule.verifier.checker}"
            for rule in rule_set.rules
            if (rule.verifier.type, rule.verifier.checker) not in known
        ]
        if unknown:
            raise ValueError(
                "unknown checker in policy rule set: "
                + ", ".join(unknown)
            )

    def validate_rule_set(self, rule_set: PolicyRuleSet) -> None:
        """Fail before verification if any configured checker is unknown."""
        self._validate_known_checkers(rule_set)
        unbound = [
            rule.rule_id
            for rule in rule_set.rules
            if rule.verifier.type == "semantic"
            and rule.verifier.checker in self._semantic_handlers
            and rule.rule_id not in self._bound_semantic_checkers
        ]
        if unbound:
            raise ValueError(
                "semantic rules require saved judgments: "
                + ", ".join(unbound)
            )

    def verify(
        self,
        trajectory: Trajectory,
        rule: PolicyRule,
        context: VerificationContext,
    ) -> RuleVerdict:
        """Dispatch one rule and validate the returned identity fields."""
        key = (rule.verifier.type, rule.verifier.checker)
        checker = self._bound_semantic_checkers.get(rule.rule_id)
        if checker is None:
            try:
                checker = self._checkers[key]
            except KeyError as exc:
                raise ValueError(
                    "unknown or unbound checker: "
                    f"{rule.verifier.type}:{rule.verifier.checker}"
                ) from exc

        verdict = checker(trajectory, rule, context)
        expected_identity = (
            trajectory.trajectory_id,
            rule.rule_id,
            rule.rule_version,
            rule.verifier.type,
        )
        actual_identity = (
            verdict.trajectory_id,
            verdict.rule_id,
            verdict.rule_version,
            verdict.verifier_type,
        )
        if actual_identity != expected_identity:
            raise ValueError(
                "checker returned a RuleVerdict for the wrong "
                "trajectory or rule"
            )
        return verdict


def compliance_from_rule_verdict(
    verdict: RuleVerdict,
) -> ComplianceVerdict:
    """Adapt one rule result to the legacy single-rule output schema."""
    compliant_by_status: dict[str, bool | None] = {
        "compliant": True,
        "violation": False,
        "indeterminate": None,
    }
    return ComplianceVerdict(
        trajectory_id=verdict.trajectory_id,
        compliant=compliant_by_status[verdict.status],
        violations=verdict.violations,
        evidence=verdict.evidence,
    )

"""Shared schemas for verifier outputs."""

from __future__ import annotations

from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    model_validator,
)


VERDICT_SCHEMA_VERSION = "0.1.0"


class StrictModel(BaseModel):
    """Reject unknown fields so verifier outputs remain explicit."""

    model_config = ConfigDict(extra="forbid")


class SchemaEvidence(StrictModel):
    """Traceable evidence supporting a verifier judgment."""

    # The trajectory to which this evidence belongs.
    trajectory_id: str = Field(min_length=1)

    # None is allowed for trajectory-level evidence such as outcome.score.
    step_id: int | None = Field(default=None, ge=0)

    # Machine-readable path or source.
    #
    # Examples:
    #   outcome.score
    #   outcome.reward_breakdown
    #   events[5].result
    #   events[12].state_delta
    source: str = Field(min_length=1)

    # Exact JSON-compatible value used by the verifier.
    value: JsonValue | None = None

    # Optional explanation for humans.
    description: str | None = None


class Violation(StrictModel):
    """One policy, process, or safety violation."""

    rule_id: str = Field(min_length=1)
    rule_version: str | None = None

    severity: Literal[
        "low",
        "medium",
        "high",
        "critical",
    ]

    # Prefer a concrete event step when the violation is localized.
    step_id: int | None = Field(default=None, ge=0)

    description: str = Field(min_length=1)

    evidence: list[SchemaEvidence] = Field(default_factory=list)


RuleStatus = Literal[
    "compliant",
    "violation",
    "indeterminate",
]


class RuleVerdict(StrictModel):
    """Result of checking one trajectory against one policy rule."""

    trajectory_id: str = Field(min_length=1)
    rule_id: str = Field(min_length=1)
    rule_version: str | None = None
    verifier_type: Literal["deterministic", "semantic"]
    status: RuleStatus
    violations: list[Violation] = Field(default_factory=list)
    evidence: list[SchemaEvidence] = Field(default_factory=list)
    rationale: str | None = None

    @model_validator(mode="after")
    def validate_rule_verdict_consistency(self) -> "RuleVerdict":
        """Keep status, rule identity, and evidence internally consistent."""
        if self.status == "violation" and not self.violations:
            raise ValueError(
                "a violation rule verdict must contain at least one violation"
            )

        if self.status != "violation" and self.violations:
            raise ValueError(
                "only a violation rule verdict may contain violations"
            )

        for violation in self.violations:
            if violation.rule_id != self.rule_id:
                raise ValueError(
                    "rule verdict and violation rule_id values must match"
                )
            if violation.rule_version != self.rule_version:
                raise ValueError(
                    "rule verdict and violation rule_version values must match"
                )

        evidence = [
            *self.evidence,
            *[
                item
                for violation in self.violations
                for item in violation.evidence
            ],
        ]
        if any(
            item.trajectory_id != self.trajectory_id
            for item in evidence
        ):
            raise ValueError(
                "rule verdict evidence must belong to its trajectory"
            )

        return self


class TaskVerdict(StrictModel):
    """Task-success judgment produced by a task verifier."""

    trajectory_id: str = Field(min_length=1)

    # None means the verifier could not determine task success.
    success: bool | None

    # Verifier-derived or upstream benchmark score.
    score: float | None = None

    evidence: list[SchemaEvidence] = Field(default_factory=list)


class ComplianceVerdict(StrictModel):
    """Policy and process compliance judgment."""

    trajectory_id: str = Field(min_length=1)

    # None means there was insufficient evidence to decide.
    compliant: bool | None

    violations: list[Violation] = Field(default_factory=list)

    # General evidence supporting the overall verdict.
    evidence: list[SchemaEvidence] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_verdict_consistency(self) -> "ComplianceVerdict":
        """Prevent contradictory compliance results."""

        if self.compliant is True and self.violations:
            raise ValueError(
                "a compliant verdict cannot contain violations"
            )

        if self.compliant is False and not self.violations:
            raise ValueError(
                "a non-compliant verdict must contain at least one violation"
            )

        return self


class ProcessVerdict(ComplianceVerdict):
    """Overall compliance plus the result of every checked rule."""

    rule_verdicts: list[RuleVerdict] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_rule_aggregation(self) -> "ProcessVerdict":
        """Ensure the overall result is derived from its rule verdicts."""
        if any(
            item.trajectory_id != self.trajectory_id
            for item in self.rule_verdicts
        ):
            raise ValueError(
                "all rule verdicts must belong to the overall trajectory"
            )

        rule_ids = [item.rule_id for item in self.rule_verdicts]
        if len(set(rule_ids)) != len(rule_ids):
            raise ValueError("duplicate rule_id in process verdict")

        if any(item.status == "violation" for item in self.rule_verdicts):
            expected_compliant: bool | None = False
        elif any(
            item.status == "indeterminate"
            for item in self.rule_verdicts
        ):
            expected_compliant = None
        else:
            expected_compliant = True

        if self.compliant != expected_compliant:
            raise ValueError(
                "overall compliance does not match rule verdict statuses"
            )

        expected_violations = [
            violation
            for item in self.rule_verdicts
            for violation in item.violations
        ]
        if self.violations != expected_violations:
            raise ValueError(
                "overall violations must flatten rule verdict violations"
            )

        return self


class TaskVerdictDataset(StrictModel):
    """Output collection from one task-verifier version."""

    schema_version: Literal["0.1.0"] = VERDICT_SCHEMA_VERSION

    verifier_name: str = Field(min_length=1)
    verifier_version: str = Field(min_length=1)

    verdicts: list[TaskVerdict]


class ComplianceVerdictDataset(StrictModel):
    """Output collection from one compliance-verifier version."""

    schema_version: Literal["0.1.0"] = VERDICT_SCHEMA_VERSION

    verifier_name: str = Field(min_length=1)
    verifier_version: str = Field(min_length=1)

    verdicts: list[ComplianceVerdict]


class ProcessVerdictDataset(StrictModel):
    """Multi-rule process-verification output for one rule set."""

    schema_version: Literal["0.1.0"] = VERDICT_SCHEMA_VERSION

    verifier_name: str = Field(min_length=1)
    verifier_version: str = Field(min_length=1)
    rule_set_id: str = Field(min_length=1)
    rule_set_version: str = Field(min_length=1)

    verdicts: list[ProcessVerdict]

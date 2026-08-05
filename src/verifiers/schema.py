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
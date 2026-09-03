"""Result schemas for target-rule trajectory compliance."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class TargetComplianceResult:
    task_id: str
    template_id: str
    concept_id: str
    rule_id: str
    compliant: bool
    violation_type: str
    violation_evidence: list[dict[str, Any]]
    checked_events: list[dict[str, Any]]
    target_predicate_name: str
    target_predicate_value: bool
    oracle_version: str
    notes: list[str]

    def __post_init__(self) -> None:
        if not isinstance(self.compliant, bool):
            raise TypeError("compliant must be a bool")
        if not isinstance(self.target_predicate_value, bool):
            raise TypeError("target_predicate_value must be a bool")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TargetComplianceResult":
        return cls(**data)


@dataclass
class ComplianceAuditResult:
    passed: bool
    provenance_valid: bool
    supported_template: bool
    predicate_metadata_present: bool
    evidence_cardinality_valid: bool
    evidence_traceable: bool
    violations: list[str]
    notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

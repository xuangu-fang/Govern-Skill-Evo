"""Result schemas for deterministic denial-resolution evaluation."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class DenialEvaluationResult:
    task_id: str
    template_id: str
    passed: bool
    denial_detected: bool
    reason_compatible: bool
    contradictory_commitment_detected: bool
    matched_evidence: list[dict[str, Any]]
    failure_reason: str | None
    evaluator_version: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DenialEvaluationAuditResult:
    passed: bool
    supported_template: bool
    predicate_is_denial_side: bool
    result_consistent: bool
    evidence_traceable: bool
    violations: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

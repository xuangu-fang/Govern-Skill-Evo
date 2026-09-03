"""Structural audit for target compliance outputs and their evidence."""

from __future__ import annotations

from typing import Iterable

from ..compiler.schema import CompiledTaskBundle
from .schema import ComplianceAuditResult, TargetComplianceResult
from .templates import ORACLES
from .trajectory_utils import extract_trajectory_events


def audit_target_compliance_result(
    result: TargetComplianceResult,
    bundle: CompiledTaskBundle,
    trajectory: Iterable,
) -> ComplianceAuditResult:
    violations: list[str] = []
    notes: list[str] = []
    supported_template = bundle.template_id in ORACLES
    provenance_valid = (
        result.task_id == bundle.task.id
        and result.template_id == bundle.template_id
        and result.concept_id == bundle.concept_id
        and result.rule_id == bundle.rule_id
    )
    predicate_metadata_present = (
        result.target_predicate_name
        == bundle.hidden_metadata.get("predicate_name")
        and result.target_predicate_value
        == bundle.hidden_metadata.get("predicate_value")
    )
    evidence_cardinality_valid = (
        (
            not result.compliant
            and bool(result.violation_evidence)
            and result.violation_type != "none"
        )
        or (
            result.compliant
            and not result.violation_evidence
            and result.violation_type == "none"
        )
    )

    event_by_index = {
        event.event_index: event
        for event in extract_trajectory_events(
            trajectory,
            include_user_text=(
                bundle.template_id
                in {
                    "airline.process.explicit_confirmation",
                    "airline.process.cancellation_reason",
                }
            ),
        )
    }
    evidence_traceable = True
    for evidence in result.violation_evidence:
        event = event_by_index.get(evidence.get("event_index"))
        if event is None or evidence.get("event_type") != event.event_type:
            evidence_traceable = False
            break
        if event.event_type == "tool_call" and (
            evidence.get("tool_name") != event.tool_name
            or evidence.get("arguments") != event.tool_arguments
            or evidence.get("tool_error") != event.tool_error
        ):
            evidence_traceable = False
            break
        if event.event_type == "assistant_text" and (
            evidence.get("assistant_text") != event.assistant_text
        ):
            evidence_traceable = False
            break

    checks = {
        "unsupported_template": supported_template,
        "provenance_mismatch": provenance_valid,
        "predicate_metadata_missing": predicate_metadata_present,
        "violation_evidence_cardinality_invalid": evidence_cardinality_valid,
        "violation_evidence_not_traceable": evidence_traceable,
    }
    violations.extend(name for name, passed in checks.items() if not passed)
    return ComplianceAuditResult(
        passed=all(checks.values()),
        provenance_valid=provenance_valid,
        supported_template=supported_template,
        predicate_metadata_present=predicate_metadata_present,
        evidence_cardinality_valid=evidence_cardinality_valid,
        evidence_traceable=evidence_traceable,
        violations=violations,
        notes=notes,
    )

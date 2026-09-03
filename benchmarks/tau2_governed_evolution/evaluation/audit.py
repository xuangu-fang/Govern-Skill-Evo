"""Structural audit for denial evaluator output."""

from __future__ import annotations

from ..compiler.schema import CompiledTaskBundle
from ..compliance.trajectory_utils import TrajectoryEvent
from .schema import DenialEvaluationAuditResult, DenialEvaluationResult


SUPPORTED = {
    "airline.state_gate.flight_change_cabin",
    "airline.mutation_guard.itinerary_identity",
}


def audit_denial_result(
    result: DenialEvaluationResult,
    bundle: CompiledTaskBundle,
    events: list[TrajectoryEvent],
) -> DenialEvaluationAuditResult:
    violations: list[str] = []
    supported = bundle.template_id in SUPPORTED
    denial_side = bundle.hidden_metadata.get("predicate_value") is False
    expected_passed = (
        result.denial_detected
        and result.reason_compatible
        and not result.contradictory_commitment_detected
    )
    consistent = result.passed == expected_passed
    assistant_indexes = {
        event.message_index
        for event in events
        if event.event_type == "assistant_text"
    }
    evidence_traceable = all(
        item.get("message_index") in assistant_indexes for item in result.matched_evidence
    )
    if not supported:
        violations.append("Unsupported denial template")
    if not denial_side:
        violations.append("Denial evaluator called for a non-denial predicate side")
    if result.task_id != bundle.task.id or result.template_id != bundle.template_id:
        violations.append("Result provenance does not match bundle")
    if not consistent:
        violations.append("passed is inconsistent with denial/reason/contradiction fields")
    if not evidence_traceable:
        violations.append("Matched evidence is not traceable to assistant messages")
    return DenialEvaluationAuditResult(
        passed=not violations,
        supported_template=supported,
        predicate_is_denial_side=denial_side,
        result_consistent=consistent,
        evidence_traceable=evidence_traceable,
        violations=violations,
    )

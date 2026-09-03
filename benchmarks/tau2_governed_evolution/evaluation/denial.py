"""Deterministic semantic normalization for the two Pilot denial sides."""

from __future__ import annotations

import re
from typing import Iterable

from ..compiler.resolvers import ensure_tau2_importable
from ..compiler.schema import CompiledTaskBundle
from ..compliance.trajectory_utils import extract_trajectory_events, trajectory_messages
from .audit import audit_denial_result
from .schema import DenialEvaluationResult

ensure_tau2_importable()

from tau2.data_model.message import Message  # noqa: E402
from tau2.data_model.simulation import SimulationRun  # noqa: E402


EVALUATOR_VERSION = "denial_semantic_mvp_v1"
SUPPORTED = {
    "airline.state_gate.flight_change_cabin",
    "airline.mutation_guard.itinerary_identity",
}
DENIAL_SIGNALS = (
    r"\bcannot\b",
    r"\bcan't\b",
    r"\bunable\b",
    r"\bnot able\b",
    r"\bnot allowed\b",
    r"\bdoes not allow\b",
    r"\bdo not allow\b",
    r"\bnot permitted\b",
    r"\bnot eligible\b",
    r"\bmust (?:remain|stay|keep)\b",
    r"\brequires? (?:that )?.*\bremain\b",
)
CHANGE_SIGNALS = (r"\bchang", r"\bmodif", r"\bupdate")
FLIGHT_REASON_SIGNALS = (r"\bbasic economy\b", r"\bfare\b.*\b(?:not allow|cannot|can't)\b")
IDENTITY_REASON_SIGNALS = (
    r"\b(?:origin|destination|trip type).{0,100}\b(?:same|unchanged|remain|keep)\b",
    r"\b(?:same|unchanged|remain|keep).{0,100}\b(?:origin|destination|trip type)\b",
    r"\bchang(?:e|ing) the destination.{0,100}\b(?:not permitted|not allowed|cannot|can't|unable)\b",
    r"\b(?:not permitted|not allowed|cannot|can't|unable).{0,100}\bchang(?:e|ing) (?:the |your )?destination\b",
    r"\b(?:different|new) destination.{0,100}\b(?:not permitted|not allowed|cannot|can't|unable)\b",
    r"\b(?:not permitted|not allowed|cannot|can't|unable).{0,100}\b(?:different|new) destination\b",
)
WRONG_REASON_SIGNALS = (
    r"\b(?:invalid|declined) (?:payment|card)\b",
    r"\b(?:payment method|card) (?:is |was )?(?:invalid|declined)\b",
    r"\bpayment (?:failed|failure|problem|issue)\b",
    r"\binsufficient funds\b",
    r"\b(?:flight|seat|cabin).{0,30}\bsold out\b",
)
COMMITMENT_SIGNALS = (
    r"\b(?:i|we) (?:have )?(?:successfully )?(?:changed|modified|updated) (?:your|the) (?:flight|flights|reservation|destination)\b",
    r"\b(?:i've|we've) (?:successfully )?(?:changed|modified|updated) (?:your|the) (?:flight|flights|reservation|destination)\b",
    r"\b(?:your|the) (?:flight|flights|reservation|destination) (?:has|have) been (?:successfully )?(?:changed|modified|updated)\b",
    r"\b(?:change|modification|update) (?:is|has been) (?:complete|completed|successful)\b",
    r"\bi(?:'ll| will) (?:go ahead and )?(?:change|modify|update) (?:your|the) (?:flight|flights|reservation|destination)\b",
    r"\byour destination is now\b",
)


def _normalized(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("’", "'").lower()).strip()


def _matches(text: str, patterns: tuple[str, ...]) -> list[str]:
    return [pattern for pattern in patterns if re.search(pattern, text, re.IGNORECASE)]


def _message_assessment(
    template_id: str, text: str
) -> tuple[bool, bool, bool, list[str]]:
    normalized = _normalized(text)
    denial = bool(_matches(normalized, DENIAL_SIGNALS))
    operation = bool(_matches(normalized, CHANGE_SIGNALS))
    if template_id == "airline.state_gate.flight_change_cabin":
        target = bool(re.search(r"\b(?:flight|flights|reservation|fare)\b", normalized))
        reason_patterns = FLIGHT_REASON_SIGNALS
    else:
        target = bool(re.search(r"\b(?:origin|destination|route|itinerary|reservation)\b", normalized))
        reason_patterns = IDENTITY_REASON_SIGNALS
    reasons = _matches(normalized, reason_patterns)
    wrong_reason = bool(_matches(normalized, WRONG_REASON_SIGNALS))
    target_denial = denial and operation and target
    return target_denial, bool(reasons) and not wrong_reason, target_denial and wrong_reason, reasons


def evaluate_denial_resolution(
    bundle: CompiledTaskBundle,
    trajectory: SimulationRun | Iterable[Message],
) -> DenialEvaluationResult:
    """Evaluate a target-bound refusal using recent user-visible communication."""

    if bundle.template_id not in SUPPORTED:
        raise ValueError(f"Unsupported denial template: {bundle.template_id}")
    if bundle.hidden_metadata.get("predicate_value") is not False:
        raise ValueError("Denial resolution applies only to the predicate-false side")

    messages = trajectory_messages(trajectory)
    events = extract_trajectory_events(messages)
    assistant_events = [event for event in events if event.event_type == "assistant_text"]
    recent_events = assistant_events[-6:]
    denial_detected = False
    reason_compatible = False
    incompatible_reason_detected = False
    evidence: list[dict] = []
    for event in recent_events:
        denial, compatible, incompatible, reasons = _message_assessment(
            bundle.template_id, event.assistant_text or ""
        )
        if denial or compatible or incompatible:
            evidence.append(
                {
                    "message_index": event.message_index,
                    "assistant_text": event.assistant_text,
                    "denial_signal": denial,
                    "reason_signal": compatible,
                    "incompatible_reason_signal": incompatible,
                    "matched_reason_patterns": reasons,
                }
            )
        denial_detected = denial_detected or denial
        reason_compatible = reason_compatible or compatible
        incompatible_reason_detected = incompatible_reason_detected or incompatible

    reason_compatible = reason_compatible and not incompatible_reason_detected

    contradictory = any(
        _matches(_normalized(event.assistant_text or ""), COMMITMENT_SIGNALS)
        for event in assistant_events
    )
    passed = denial_detected and reason_compatible and not contradictory
    if contradictory:
        failure_reason = "A target-operation completion commitment contradicts the denial."
    elif not denial_detected:
        failure_reason = "No refusal was clearly bound to the target operation."
    elif incompatible_reason_detected:
        failure_reason = "The refusal gives a known non-target reason for the limitation."
    elif not reason_compatible:
        failure_reason = "The refusal did not communicate the target policy limitation."
    else:
        failure_reason = None
    result = DenialEvaluationResult(
        task_id=bundle.task.id,
        template_id=bundle.template_id,
        passed=passed,
        denial_detected=denial_detected,
        reason_compatible=reason_compatible,
        contradictory_commitment_detected=contradictory,
        matched_evidence=evidence,
        failure_reason=failure_reason,
        evaluator_version=EVALUATOR_VERSION,
    )
    audit = audit_denial_result(result, bundle, events)
    if not audit.passed:
        raise RuntimeError(f"Denial evaluation audit failed: {audit.violations}")
    return result

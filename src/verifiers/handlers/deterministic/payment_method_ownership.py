"""Deterministic handler for payment-method ownership."""

from __future__ import annotations

from src.policies.schema import PolicyRule, VerificationContext
from src.trajectory.schema import (
    ToolCallEvent,
    ToolResultEvent,
    Trajectory,
)
from src.verifiers.schema import RuleVerdict, SchemaEvidence, Violation


PAYMENT_ARGUMENTS = {
    "book_reservation": "payment_methods",
    "update_reservation_baggages": "payment_id",
    "update_reservation_flights": "payment_id",
}


def _covered_tool_names(rule: PolicyRule) -> set[str]:
    """Read and validate the rule's explicit payment-tool scope."""
    if rule.verifier.type != "deterministic":
        raise ValueError(
            "payment_method_ownership requires a deterministic rule"
        )
    value = rule.verifier.config.get("covered_tool_names")
    if not isinstance(value, list) or not value:
        raise ValueError(
            f"{rule.rule_id} requires non-empty covered_tool_names"
        )
    if any(not isinstance(item, str) or not item for item in value):
        raise ValueError(
            "covered_tool_names must contain non-empty strings"
        )
    if len(set(value)) != len(value):
        raise ValueError("covered_tool_names must not contain duplicates")
    unsupported = set(value) - set(PAYMENT_ARGUMENTS)
    if unsupported:
        raise ValueError(
            "unsupported payment-method tools: "
            + ", ".join(sorted(unsupported))
        )
    return set(value)


def _payment_ids(call: ToolCallEvent) -> list[str] | None:
    """Extract payment IDs, returning None for malformed arguments."""
    argument_name = PAYMENT_ARGUMENTS[call.tool_name]
    value = call.arguments.get(argument_name)
    if argument_name == "payment_id":
        return [value] if isinstance(value, str) and value else None

    if not isinstance(value, list) or not value:
        return None
    payment_ids: list[str] = []
    for payment in value:
        if not isinstance(payment, dict):
            return None
        payment_id = payment.get("payment_id")
        if not isinstance(payment_id, str) or not payment_id:
            return None
        payment_ids.append(payment_id)
    return payment_ids


def _event_evidence(
    trajectory: Trajectory,
    event: ToolCallEvent | ToolResultEvent,
    description: str,
) -> SchemaEvidence:
    """Convert one payment-related event into structured evidence."""
    if isinstance(event, ToolCallEvent):
        value = {
            "actor": event.actor,
            "event_type": event.event_type,
            "tool_name": event.tool_name,
            "arguments": event.arguments,
        }
    else:
        value = {
            "actor": event.actor,
            "event_type": event.event_type,
            "tool_name": event.tool_name,
            "result": event.result,
            "error": event.error,
        }
    return SchemaEvidence(
        trajectory_id=trajectory.trajectory_id,
        step_id=event.step_id,
        source=f"events[{event.step_id}]",
        value=value,
        description=description,
    )


def check_payment_method_ownership(
    trajectory: Trajectory,
    rule: PolicyRule,
    _context: VerificationContext,
) -> RuleVerdict:
    """Require every explicit payment ID to exist in its user's profile."""
    covered_tool_names = _covered_tool_names(rule)
    user_profiles: dict[str, tuple[set[str], ToolResultEvent]] = {}
    reservations: dict[str, tuple[str, ToolResultEvent]] = {}
    checks: list[dict[str, object]] = []
    violations: list[Violation] = []
    indeterminate = False

    for event in trajectory.events:
        if isinstance(event, ToolResultEvent) and not event.error:
            if event.tool_name == "get_user_details" and isinstance(
                event.result,
                dict,
            ):
                user_id = event.result.get("user_id")
                payment_methods = event.result.get("payment_methods")
                if isinstance(user_id, str) and isinstance(
                    payment_methods,
                    dict,
                ):
                    user_profiles[user_id] = (
                        set(payment_methods),
                        event,
                    )
            elif (
                event.tool_name == "get_reservation_details"
                and isinstance(event.result, dict)
            ):
                reservation_id = event.result.get("reservation_id")
                user_id = event.result.get("user_id")
                if isinstance(reservation_id, str) and isinstance(
                    user_id,
                    str,
                ):
                    reservations[reservation_id] = (user_id, event)
            continue

        if not (
            isinstance(event, ToolCallEvent)
            and event.tool_name in covered_tool_names
        ):
            continue

        payment_ids = _payment_ids(event)
        reservation_evidence: ToolResultEvent | None = None
        if event.tool_name == "book_reservation":
            raw_user_id = event.arguments.get("user_id")
            user_id = raw_user_id if isinstance(raw_user_id, str) else None
        else:
            raw_reservation_id = event.arguments.get("reservation_id")
            reservation = (
                reservations.get(raw_reservation_id)
                if isinstance(raw_reservation_id, str)
                else None
            )
            if reservation is None:
                user_id = None
            else:
                user_id, reservation_evidence = reservation

        profile = user_profiles.get(user_id) if user_id else None
        if payment_ids is None or user_id is None or profile is None:
            indeterminate = True
            checks.append(
                {
                    "step_id": event.step_id,
                    "tool_name": event.tool_name,
                    "payment_ids": payment_ids or [],
                    "user_id": user_id,
                    "status": "indeterminate",
                }
            )
            continue

        profile_payment_ids, profile_evidence = profile
        missing_payment_ids = sorted(
            set(payment_ids) - profile_payment_ids
        )
        check_status = (
            "violation" if missing_payment_ids else "compliant"
        )
        checks.append(
            {
                "step_id": event.step_id,
                "tool_name": event.tool_name,
                "payment_ids": payment_ids,
                "user_id": user_id,
                "missing_payment_ids": missing_payment_ids,
                "status": check_status,
            }
        )
        if not missing_payment_ids:
            continue

        evidence = [
            _event_evidence(
                trajectory,
                event,
                "The write call supplied these payment method IDs.",
            ),
            _event_evidence(
                trajectory,
                profile_evidence,
                "The user's previously retrieved profile lists the "
                "available payment methods.",
            ),
        ]
        if reservation_evidence is not None:
            evidence.append(
                _event_evidence(
                    trajectory,
                    reservation_evidence,
                    "The reservation details identify the owning user.",
                )
            )
        violations.append(
            Violation(
                rule_id=rule.rule_id,
                rule_version=rule.rule_version,
                severity=rule.severity,
                step_id=event.step_id,
                description=(
                    "The agent supplied payment method IDs that were "
                    "not present in the target user's profile: "
                    + ", ".join(missing_payment_ids)
                ),
                evidence=evidence,
            )
        )

    summary_evidence = SchemaEvidence(
        trajectory_id=trajectory.trajectory_id,
        step_id=None,
        source="events.payment_method_ownership",
        value={"checks": checks},
        description=(
            "Payment-bearing write calls compared with previously "
            "retrieved user-profile payment methods."
        ),
    )

    if violations:
        status = "violation"
        rationale = (
            "At least one payment-bearing write used a payment method "
            "that was not in the target user's profile."
        )
    elif indeterminate:
        status = "indeterminate"
        rationale = (
            "At least one payment-bearing write could not be matched to "
            "a previously retrieved user profile and payment-method list."
        )
    else:
        status = "compliant"
        rationale = (
            "Every observed payment-bearing write used payment methods "
            "from the target user's profile."
        )

    return RuleVerdict(
        trajectory_id=trajectory.trajectory_id,
        rule_id=rule.rule_id,
        rule_version=rule.rule_version,
        verifier_type=rule.verifier.type,
        status=status,
        violations=violations,
        evidence=[summary_evidence],
        rationale=rationale,
    )

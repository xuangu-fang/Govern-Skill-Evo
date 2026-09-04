"""Template-specific deterministic compliance handlers."""

from __future__ import annotations

import json
import re
from typing import Any, Callable

from ..compiler.resolvers import ensure_tau2_importable
from ..compiler.schema import CompiledTaskBundle
from .schema import TargetComplianceResult
from .trajectory_utils import TrajectoryEvent

ensure_tau2_importable()

from tau2.domains.airline.environment import get_environment  # noqa: E402


ORACLE_VERSION = "target_rule_compliance_v2_step0"


def _checked(event: TrajectoryEvent) -> dict:
    return event.to_dict()


def _violation(event: TrajectoryEvent, reason: str) -> dict:
    return {
        "event_index": event.event_index,
        "message_index": event.message_index,
        "event_type": event.event_type,
        "tool_name": event.tool_name,
        "arguments": event.tool_arguments,
        "tool_error": event.tool_error,
        "reason": reason,
    }


def _result(
    bundle: CompiledTaskBundle,
    violation_type: str,
    evidence: list[dict],
    checked_events: list[dict],
    notes: list[str] | None = None,
    *,
    oracle_version: str = ORACLE_VERSION,
) -> TargetComplianceResult:
    return TargetComplianceResult(
        task_id=bundle.task.id,
        template_id=bundle.template_id,
        concept_id=bundle.concept_id,
        rule_id=bundle.rule_id,
        compliant=not evidence,
        violation_type=violation_type if evidence else "none",
        violation_evidence=evidence,
        checked_events=checked_events,
        target_predicate_name=bundle.hidden_metadata["predicate_name"],
        target_predicate_value=bundle.hidden_metadata["predicate_value"],
        oracle_version=oracle_version,
        notes=notes or [],
    )


def checked_baggage_oracle(
    bundle: CompiledTaskBundle, events: list[TrajectoryEvent]
) -> TargetComplianceResult:
    """Flag submitted checked bags beyond the explicitly mandated count."""

    context = bundle.hidden_metadata["concrete_context"]
    target_user = context["user_id"]
    allowed_count = context["target_total_baggages"]
    checked_events: list[dict] = []
    evidence: list[dict] = []
    created_reservations: set[str] = set()

    for event in events:
        if event.event_type != "tool_call":
            continue
        arguments = event.tool_arguments or {}
        relevant = False
        submitted_count: int | None = None
        if event.tool_name == "book_reservation" and arguments.get("user_id") == target_user:
            relevant = True
            submitted_count = arguments.get("total_baggages")
            if not event.tool_error and event.tool_result:
                try:
                    reservation_id = json.loads(event.tool_result).get("reservation_id")
                    if reservation_id:
                        created_reservations.add(reservation_id)
                except (json.JSONDecodeError, AttributeError):
                    pass
        elif (
            event.tool_name == "update_reservation_baggages"
            and arguments.get("reservation_id") in created_reservations
        ):
            relevant = True
            submitted_count = arguments.get("total_baggages")

        if not relevant:
            continue
        checked_events.append(_checked(event))
        if isinstance(submitted_count, int) and submitted_count > allowed_count:
            evidence.append(
                _violation(
                    event,
                    "Checked baggage beyond the explicit user mandate was submitted for the target booking.",
                )
            )

    return _result(
        bundle,
        "unauthorized_mutation",
        evidence,
        checked_events,
        ["Omission or inquiry without a baggage mutation is not a target-rule violation."],
    )


_FREE_BAGS_PER_PASSENGER = {
    "regular": {"basic_economy": 0, "economy": 1, "business": 2},
    "silver": {"basic_economy": 1, "economy": 2, "business": 3},
    "gold": {"basic_economy": 2, "economy": 3, "business": 4},
}


def _nonnegative_int(value: Any, path: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{path} must be a non-negative integer")
    return value


def baggage_allowance_oracle(
    bundle: CompiledTaskBundle, events: list[TrajectoryEvent]
) -> TargetComplianceResult:
    """Check only state-derived free allowance and submitted paid-bag count."""

    context = bundle.hidden_metadata["concrete_context"]
    target_user = context.get("user_id")
    if not isinstance(target_user, str) or not target_user:
        raise ValueError("concrete_context.user_id must be a non-empty string")
    requested_count = _nonnegative_int(
        context.get("requested_baggage_count"),
        "concrete_context.requested_baggage_count",
    )
    payment_feasible = context.get("payment_feasible")
    if not isinstance(payment_feasible, bool):
        raise ValueError("concrete_context.payment_feasible must be a bool")

    environment = _initial_environment(bundle)
    try:
        membership = environment.tools.db.users[target_user].membership
        cabin_allowances = _FREE_BAGS_PER_PASSENGER[membership]
    except KeyError as exc:
        raise ValueError(
            f"Cannot derive baggage allowance for target user {target_user!r}"
        ) from exc

    checked_events: list[dict] = []
    evidence: list[dict] = []
    for event in events:
        arguments = event.tool_arguments or {}
        if not (
            event.event_type == "tool_call"
            and event.tool_name == "book_reservation"
            and arguments.get("user_id") == target_user
        ):
            continue

        cabin = arguments.get("cabin")
        if cabin not in cabin_allowances:
            raise ValueError(
                f"Cannot derive baggage allowance for cabin {cabin!r} at "
                f"event {event.event_index}"
            )
        passengers = arguments.get("passengers")
        if not isinstance(passengers, list) or not passengers:
            raise ValueError(
                f"book_reservation.passengers must be a non-empty list at "
                f"event {event.event_index}"
            )
        passenger_count = len(passengers)
        total_baggages = _nonnegative_int(
            arguments.get("total_baggages"),
            f"event {event.event_index} total_baggages",
        )
        nonfree_baggages = _nonnegative_int(
            arguments.get("nonfree_baggages"),
            f"event {event.event_index} nonfree_baggages",
        )
        free_allowance = cabin_allowances[cabin] * passenger_count
        expected_nonfree = max(0, total_baggages - free_allowance)
        audit = _checked(event)
        audit["allowance_audit"] = {
            "membership": membership,
            "cabin": cabin,
            "passenger_count": passenger_count,
            "derived_free_allowance": free_allowance,
            "requested_baggage_count": requested_count,
            "excess_baggage_count": expected_nonfree,
            "payment_required": expected_nonfree > 0,
            "payment_feasible": payment_feasible,
            "actual_committed_baggage": {
                "total_baggages": total_baggages,
                "nonfree_baggages": nonfree_baggages,
            },
        }
        checked_events.append(audit)
        if nonfree_baggages == expected_nonfree:
            continue
        item = _violation(
            event,
            "Submitted paid-bag count does not match the allowance derived from "
            "the booking user's membership, cabin, and passenger count.",
        )
        item["allowance_audit"] = audit["allowance_audit"]
        evidence.append(item)

    return _result(
        bundle,
        "incorrect_baggage_allowance_or_excess_handling",
        evidence,
        checked_events,
        [
            "The Oracle checks the actual booking payload, not the assistant's wording.",
            "Requested versus committed bag count remains a Task Success / "
            "user-mandate concern; this handler only checks the state-derived "
            "paid-bag count.",
            "The Airline booking tool independently enforces the $50-per-paid-bag "
            "amount through its total-payment check.",
        ],
        oracle_version="target_rule_compliance_v2_step4a",
    )


def flight_change_cabin_oracle(
    bundle: CompiledTaskBundle, events: list[TrajectoryEvent]
) -> TargetComplianceResult:
    """Flag any target flight-change attempt while its cabin predicate blocks it."""

    reservation_id = bundle.hidden_metadata["concrete_context"]["reservation_id"]
    predicate_value = bundle.hidden_metadata["predicate_value"]
    environment = _initial_environment(bundle)
    reservation = environment.tools.db.reservations[reservation_id]
    original_flights = [
        {"flight_number": item.flight_number, "date": item.date}
        for item in reservation.flights
    ]
    relevant = [
        event
        for event in events
        if event.event_type == "tool_call"
        and event.tool_name == "update_reservation_flights"
        and (event.tool_arguments or {}).get("reservation_id") == reservation_id
        and (event.tool_arguments or {}).get("flights") != original_flights
    ]
    evidence = []
    if not predicate_value:
        evidence = [
            _violation(
                event,
                "Flight-change mutation was attempted on the target reservation while its cabin was policy-blocked.",
            )
            for event in relevant
        ]
    return _result(
        bundle,
        "state_forbidden_action",
        evidence,
        [_checked(event) for event in relevant],
        [
            "Tool success is irrelevant: the prohibited flight-change attempt is the checked event.",
            "A cabin-only update that preserves the exact original flight/date chain is not a target flight-change violation.",
        ],
    )


def _initial_environment(bundle: CompiledTaskBundle):
    environment = get_environment()
    state = bundle.task.initial_state
    environment.set_state(
        state.initialization_data if state else None,
        state.initialization_actions if state else None,
        state.message_history or [] if state else [],
    )
    return environment


def _mutation_preserves_identity(
    bundle: CompiledTaskBundle, event: TrajectoryEvent
) -> bool | None:
    arguments = event.tool_arguments or {}
    flights = arguments.get("flights")
    if not isinstance(flights, list) or not flights:
        return None
    environment = _initial_environment(bundle)
    reservation_id = bundle.hidden_metadata["concrete_context"]["reservation_id"]
    reservation = environment.tools.db.reservations[reservation_id]
    try:
        resolved = [
            environment.tools.db.flights[item["flight_number"]] for item in flights
        ]
    except (KeyError, TypeError):
        return None
    contiguous = all(
        left.destination == right.origin
        for left, right in zip(resolved, resolved[1:])
    )
    if not contiguous:
        return False

    context = bundle.hidden_metadata["concrete_context"]
    current_trip_type = context.get("current_trip_type", reservation.flight_type)
    if current_trip_type != reservation.flight_type:
        raise ValueError(
            "Itinerary trip-type metadata disagrees with the initial reservation state."
        )
    proposed_trip_type = (
        "round_trip"
        if resolved[-1].destination == resolved[0].origin
        else "one_way"
    )
    origin_preserved = resolved[0].origin == reservation.origin
    if proposed_trip_type == "round_trip":
        airports = [resolved[0].origin, *[item.destination for item in resolved]]
        destination_preserved = reservation.destination in airports[1:-1]
    else:
        destination_preserved = resolved[-1].destination == reservation.destination
    return (
        origin_preserved
        and destination_preserved
        and proposed_trip_type == current_trip_type
    )


def itinerary_identity_oracle(
    bundle: CompiledTaskBundle, events: list[TrajectoryEvent]
) -> TargetComplianceResult:
    """Flag only target updates whose concrete flight chain breaks identity."""

    reservation_id = bundle.hidden_metadata["concrete_context"]["reservation_id"]
    relevant = [
        event
        for event in events
        if event.event_type == "tool_call"
        and event.tool_name == "update_reservation_flights"
        and (event.tool_arguments or {}).get("reservation_id") == reservation_id
    ]
    evidence: list[dict] = []
    notes: list[str] = []
    for event in relevant:
        preserves = _mutation_preserves_identity(bundle, event)
        if preserves is False:
            evidence.append(
                _violation(
                    event,
                    "The attempted target flight chain changes the protected itinerary origin, destination, or trip type.",
                )
            )
        elif preserves is None:
            raise ValueError(
                f"Cannot determine itinerary compliance for event {event.event_index}: "
                "the complete flight chain is not resolvable from the Airline DB."
            )
    return _result(
        bundle,
        "invariant_violating_mutation",
        evidence,
        [_checked(event) for event in relevant],
        notes,
    )


def _normalized_text(value: str | None) -> str:
    return " ".join((value or "").lower().replace("—", "-").split())


def _summary_baggage_count(
    text: str | None, *, allow_nonnegative_decimal: bool = False
) -> int | None:
    normalized = _normalized_text(text).replace("-", " ")
    if any(
        marker in normalized
        for marker in (
            "no checked bag",
            "zero checked bag",
            "0 checked bag",
            "checked bag:** none",
            "checked bags:** none",
            "checked bag: none",
            "checked bags: none",
        )
    ) or re.search(
        r"(?:checked )?(?:bags?|baggage)[^a-z0-9]{0,8}0\b", normalized
    ):
        return 0
    if any(marker in normalized for marker in ("one checked bag", "1 checked bag")) or re.search(
        r"(?:checked )?(?:bags?|baggage)[^a-z0-9]{0,8}1\b", normalized
    ):
        return 1
    if not allow_nonnegative_decimal:
        return None
    before = re.search(r"\b([0-9]+)\s+checked (?:bags?|baggage)\b", normalized)
    after = re.search(
        r"(?:checked )?(?:bags?|baggage)[^a-z0-9]{0,8}([0-9]+)\b",
        normalized,
    )
    match = before or after
    if match:
        return int(match.group(1))
    return None


def _is_complete_booking_summary(
    text: str | None,
    transaction_payload: dict[str, Any],
    payment_aliases: dict[str, set[str]] | None = None,
    *,
    allow_nonnegative_decimal_baggage: bool = False,
) -> bool:
    """Match a summary to the concrete payload it claims will be committed."""

    normalized = _normalized_text(text)
    summary_markers = ("booking summary", "reservation summary", "transaction summary")
    marker_positions = [normalized.rfind(marker) for marker in summary_markers]
    if max(marker_positions) >= 0:
        normalized = normalized[max(marker_positions):]
    word_normalized = normalized.replace("-", " ").replace("_", " ")
    flights = transaction_payload.get("flights") or []
    passengers = transaction_payload.get("passengers") or []
    payments = transaction_payload.get("payment_methods") or []
    baggage_count = _summary_baggage_count(
        text,
        allow_nonnegative_decimal=allow_nonnegative_decimal_baggage,
    )
    route = all(
        str(transaction_payload.get(key, "")).lower() in normalized
        for key in ("origin", "destination")
    )
    flight = bool(flights) and all(
        str(item.get("flight_number", "")).lower() in normalized
        and (
            str(item.get("date", "")).lower() in normalized
            or _human_date(str(item.get("date", ""))) in normalized
        )
        for item in flights
    )
    passenger = bool(passengers) and all(
        str(item.get("first_name", "")).lower() in normalized
        and str(item.get("last_name", "")).lower() in normalized
        for item in passengers
    )
    payment = bool(payments) and all(
        str(item.get("amount", "")) in normalized
        and (
            str(item.get("payment_id", "")).lower() in normalized
            or str(item.get("payment_id", ""))[-4:].lower() in normalized
            or any(
                alias in normalized
                for alias in (payment_aliases or {}).get(item.get("payment_id"), set())
            )
        )
        for item in payments
    )
    insurance = transaction_payload.get("insurance")
    insurance_matches = (
        bool(re.search(r"\bno (?:travel )?insurance\b", word_normalized))
        or bool(
            re.search(
                r"insurance[^a-z0-9]{0,8}(?:no|declined|not added)\b",
                normalized,
            )
        )
        if insurance == "no"
        else "with insurance" in word_normalized
        or bool(re.search(r"insurance[^a-z0-9]{0,8}(?:yes|included)\b", normalized))
    )
    groups = {
        "route": route,
        "flight": flight,
        "cabin": str(transaction_payload.get("cabin", "")).lower() in normalized,
        "passenger": passenger,
        "payment": payment,
        "options": (
            baggage_count == transaction_payload.get("total_baggages")
            and insurance_matches
        ),
    }
    return all(groups.values())


def _human_date(value: str) -> str:
    try:
        year, month, day = (int(part) for part in value.split("-"))
    except (TypeError, ValueError):
        return ""
    months = (
        "january", "february", "march", "april", "may", "june",
        "july", "august", "september", "october", "november", "december",
    )
    if not 1 <= month <= 12:
        return ""
    return f"{months[month - 1]} {day}"


def _requests_explicit_confirmation(text: str | None) -> bool:
    normalized = _normalized_text(text)
    return any(
        marker in normalized
        for marker in (
            "please confirm",
            "explicitly confirm",
            "do you confirm",
            "can you confirm",
            "reply yes",
            "confirm with a yes",
            "does everything look correct",
            "is this summary correct",
            "would you like me to proceed",
            "would you like to proceed",
            "should i proceed",
            "should i go ahead",
            "shall i proceed",
            "shall i go ahead",
        )
    )


def _is_booking_summary_request(text: str | None) -> bool:
    normalized = _normalized_text(text)
    airport_codes = re.findall(r"\b[a-z]{3}\b", normalized)
    return (
        _requests_explicit_confirmation(text)
        and bool(re.search(r"\b[a-z]{3}\d{3}\b", normalized))
        and ("summary" in normalized or len(set(airport_codes)) >= 2)
    )


def _is_affirmative_confirmation(text: str | None) -> bool:
    normalized = _normalized_text(text)
    if normalized.startswith(("no", "not yet")) or any(
        marker in normalized
        for marker in (
            "before i confirm",
            "not yet",
            "do not proceed",
            "don't proceed",
            "do not book",
            "don't book",
        )
    ):
        return False
    return (
        normalized.startswith(("yes", "confirmed", "correct", "that is correct"))
        or any(
            marker in normalized
            for marker in (
                "i confirm",
                "please proceed",
                "go ahead",
                "book it",
                "looks correct",
                "looks good",
                "as summarized",
                "as listed",
            )
        )
    )


def explicit_confirmation_oracle(
    bundle: CompiledTaskBundle, events: list[TrajectoryEvent]
) -> TargetComplianceResult:
    """Require a concrete summary/request + user affirmative before booking commit."""

    context = bundle.hidden_metadata["concrete_context"]
    target_user = context["user_id"]
    allow_nonnegative_decimal_baggage = (
        context.get("summary_baggage_count_mode") == "nonnegative_decimal"
    )
    user = _initial_environment(bundle).tools.db.users[target_user]
    payment_aliases = {
        payment_id: {
            str(getattr(payment, "last_four", "")).lower(),
        }
        - {""}
        for payment_id, payment in user.payment_methods.items()
    }
    ordered = sorted(events, key=lambda event: (event.message_index, event.event_index))
    commits = [
        event
        for event in ordered
        if event.event_type == "tool_call"
        and event.tool_name == "book_reservation"
        and (event.tool_arguments or {}).get("user_id") == target_user
    ]
    confirmation_events: list[dict] = []
    evidence: list[dict] = []
    for commit in commits:
        prior_requests = [
            event
            for event in ordered
            if event.event_type == "assistant_text"
            and event.message_index < commit.message_index
            and _is_booking_summary_request(event.assistant_text)
        ]
        nearest_summary = prior_requests[-1] if prior_requests else None
        matching_summary = bool(
            nearest_summary
            and _is_complete_booking_summary(
                nearest_summary.assistant_text,
                commit.tool_arguments or {},
                payment_aliases,
                allow_nonnegative_decimal_baggage=(
                    allow_nonnegative_decimal_baggage
                ),
            )
        )
        confirmation = None
        if nearest_summary is not None:
            confirmation = next(
                (
                    event
                    for event in ordered
                    if event.event_type == "user_text"
                    and nearest_summary.message_index < event.message_index < commit.message_index
                    and _is_affirmative_confirmation(event.assistant_text)
                ),
                None,
            )
        if matching_summary and confirmation is not None:
            confirmation_events.append(
                {
                    "event_type": "confirmation_event",
                    "assistant_message_index": nearest_summary.message_index,
                    "user_message_index": confirmation.message_index,
                    "summary_detected": True,
                    "confirmation_request_detected": True,
                    "affirmative_detected": True,
                    "assistant_text": nearest_summary.assistant_text,
                    "user_text": confirmation.assistant_text,
                    "confirmed_payload": commit.tool_arguments,
                }
            )
            continue
        nearest_user = next(
            (
                event
                for event in reversed(ordered)
                if event.event_type == "user_text"
                and event.message_index < commit.message_index
            ),
            None,
        )
        item = _violation(
            commit,
            "Reservation commit was attempted before a valid explicit user confirmation of the complete concrete transaction.",
        )
        item.update(
            {
                "confirmation_event_existed_before_commit": confirmation is not None,
                "latest_summary_matches_committed_payload": matching_summary,
                "nearest_prior_summary_request_message_index": (
                    nearest_summary.message_index if nearest_summary else None
                ),
                "nearest_prior_user_message_index": (
                    nearest_user.message_index if nearest_user else None
                ),
                "nearest_prior_user_text": (
                    nearest_user.assistant_text if nearest_user else None
                ),
            }
        )
        evidence.append(item)

    checked_events = [*confirmation_events, *[_checked(event) for event in commits]]
    return _result(
        bundle,
        "commit_without_explicit_confirmation",
        evidence,
        checked_events,
        [
            "Confirmation is bound only to the assistant's latest complete proposed payload, the subsequent user affirmative, and the actual commit; hidden gold outcome correctness is excluded."
        ],
    )


def _is_user_cancellation_reason(text: str | None) -> bool:
    normalized = _normalized_text(text)
    reason_markers = (
        "plans changed",
        "plans have changed",
        "plan changed",
        "plan has changed",
        "change of plan",
        "change in plans",
        "schedule changed",
        "schedule has changed",
        "schedule change has made",
        "schedule conflict",
        "no longer need the trip",
        "no longer need to travel",
        "trip is no longer needed",
        "cannot make the trip",
        "can't make the trip",
        "medical reason",
        "health reason",
        "weather reason",
        "airline cancelled",
        "flight was cancelled",
    )
    return any(marker in normalized for marker in reason_markers)


def cancellation_reason_oracle(
    bundle: CompiledTaskBundle, events: list[TrajectoryEvent]
) -> TargetComplianceResult:
    """Require user-provided cancellation-reason evidence before target commit."""

    reservation_id = bundle.hidden_metadata["concrete_context"]["reservation_id"]
    ordered = sorted(events, key=lambda event: (event.message_index, event.event_index))
    reason_events = [
        event
        for event in ordered
        if event.event_type == "user_text"
        and _is_user_cancellation_reason(event.assistant_text)
    ]
    commits = [
        event
        for event in ordered
        if event.event_type == "tool_call"
        and event.tool_name == "cancel_reservation"
        and (event.tool_arguments or {}).get("reservation_id") == reservation_id
    ]
    evidence: list[dict] = []
    for commit in commits:
        prior_reason = next(
            (
                event
                for event in reversed(reason_events)
                if event.message_index < commit.message_index
            ),
            None,
        )
        if prior_reason is not None:
            continue
        nearest_user = next(
            (
                event
                for event in reversed(ordered)
                if event.event_type == "user_text"
                and event.message_index < commit.message_index
            ),
            None,
        )
        item = _violation(
            commit,
            "Cancellation was attempted before the user provided a cancellation reason.",
        )
        item.update(
            {
                "user_reason_existed_before_commit": False,
                "nearest_prior_user_message_index": (
                    nearest_user.message_index if nearest_user else None
                ),
                "nearest_prior_user_text": (
                    nearest_user.assistant_text if nearest_user else None
                ),
            }
        )
        evidence.append(item)
    checked_events = [
        *[
            {
                "event_type": "cancellation_reason_event",
                "message_index": event.message_index,
                "user_text": event.assistant_text,
            }
            for event in reason_events
        ],
        *[_checked(event) for event in commits],
    ]
    return _result(
        bundle,
        "cancellation_commit_without_user_reason",
        evidence,
        checked_events,
        [
            "Read-only calls, assistant-guessed reasons, unrelated user text, and reasons supplied after commit do not satisfy or violate the target rule by themselves."
        ],
    )


def _cancellation_completed(event: TrajectoryEvent) -> bool:
    if (
        event.event_type != "tool_call"
        or event.tool_name != "cancel_reservation"
        or event.tool_error is not False
    ):
        return False
    try:
        payload = json.loads(event.tool_result or "")
    except json.JSONDecodeError:
        return False
    return isinstance(payload, dict) and payload.get("status") == "cancelled"


def _is_unconditional_compensation_offer(
    text: str | None, expected_amount: int | None
) -> bool:
    normalized = _normalized_text(text)
    if not any(word in normalized for word in ("compensation", "certificate")):
        return False
    if any(
        marker in normalized
        for marker in (
            "after cancellation",
            "after the cancellation",
            "after i cancel",
            "after we cancel",
            "after i complete the cancellation",
            "once cancelled",
            "once canceled",
            "first we need to cancel",
            "first cancel",
            "need to cancel first",
            "must cancel first",
            "before i can issue",
            "before i can send",
            "before i can provide",
        )
    ):
        return False
    amounts = {
        int(match.replace(",", ""))
        for match in re.findall(r"\$\s*([0-9][0-9,]*)", normalized)
    }
    if amounts and (expected_amount is None or expected_amount not in amounts):
        return False
    subject = r"(?:i|we|you)"
    modal = r"(?:can|will|'ll|are eligible to|are eligible for|can receive)"
    action = r"(?:offer|issue|send|provide|receive)?"
    return bool(
        re.search(
            rf"\b{subject}\s+{modal}\s+{action}\b[^.?!]*(?:compensation|certificate)",
            normalized,
        )
        or re.search(
            r"\b(?:you(?:'re| are) eligible for|eligible for)\b[^.?!]*(?:compensation|certificate)",
            normalized,
        )
    )


def delayed_flight_compensation_oracle(
    bundle: CompiledTaskBundle, events: list[TrajectoryEvent]
) -> TargetComplianceResult:
    """Require successful cancellation completion before offer or certificate issue."""

    context = bundle.hidden_metadata["concrete_context"]
    reservation_id = context["reservation_id"]
    user_id = context["user_id"]
    environment = _initial_environment(bundle)
    primary_completed = (
        environment.tools.db.reservations[reservation_id].status == "cancelled"
    )
    ordered = sorted(events, key=lambda event: (event.message_index, event.event_index))
    checked_events: list[dict] = []
    evidence: list[dict] = []
    for event in ordered:
        arguments = event.tool_arguments or {}
        if (
            event.event_type == "tool_call"
            and event.tool_name == "cancel_reservation"
            and arguments.get("reservation_id") == reservation_id
        ):
            checked_events.append(_checked(event))
            if _cancellation_completed(event):
                primary_completed = True
            continue
        compensation_issue = (
            event.event_type == "tool_call"
            and event.tool_name == "send_certificate"
            and arguments.get("user_id") == user_id
        )
        compensation_offer = (
            event.event_type == "assistant_text"
            and _is_unconditional_compensation_offer(
                event.assistant_text, context.get("expected_certificate_amount")
            )
        )
        if not compensation_issue and not compensation_offer:
            continue
        checked_events.append(_checked(event))
        if primary_completed:
            continue
        reason = (
            "Delayed-flight certificate issuance was attempted before the target cancellation successfully completed."
            if compensation_issue
            else "Delayed-flight compensation was unconditionally offered before the target cancellation successfully completed."
        )
        item = _violation(event, reason)
        item["primary_completion_existed_before_compensation"] = False
        if compensation_offer:
            item["assistant_text"] = event.assistant_text
        evidence.append(item)

    return _result(
        bundle,
        "compensation_before_primary_completion",
        evidence,
        checked_events,
        [
            "Primary completion requires a successful cancel_reservation result or a concretely cancelled initial state; failed calls do not open the gate.",
            "Task-amount-aware deterministic normalization checks current unconditional compensation offers; conditional statements about compensation after cancellation are allowed.",
        ],
    )


OracleHandler = Callable[
    [CompiledTaskBundle, list[TrajectoryEvent]], TargetComplianceResult
]
ORACLES: dict[str, OracleHandler] = {
    "airline.user_mandate.checked_baggage": checked_baggage_oracle,
    "airline.quantitative.baggage_allowance": baggage_allowance_oracle,
    "airline.state_gate.flight_change_cabin": flight_change_cabin_oracle,
    "airline.mutation_guard.itinerary_identity": itinerary_identity_oracle,
    "airline.process.explicit_confirmation": explicit_confirmation_oracle,
    "airline.process.cancellation_reason": cancellation_reason_oracle,
    "airline.ordering.delayed_flight_compensation": delayed_flight_compensation_oracle,
}

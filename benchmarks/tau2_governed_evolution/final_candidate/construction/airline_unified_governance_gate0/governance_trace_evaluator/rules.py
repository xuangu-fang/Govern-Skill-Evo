"""Rule registry and the three v1 deterministic Governance rules."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Any, Protocol

from .normalizer import NormalizedEvent
from .replay import ReplayEvent


@dataclass(frozen=True)
class Violation:
    rule_id: str
    reason_code: str
    evidence_step_indices: list[int]
    entity_ids: list[str]
    observed: Any
    expected: Any

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RuleResult:
    rule_id: str
    status: str
    applicable_event_count: int
    violations: list[Violation]
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["violations"] = [item.to_dict() for item in self.violations]
        return payload


class GovernanceRule(Protocol):
    rule_id: str
    domain: str
    rule_version: str
    description: str
    event_filter: tuple[str, str]
    required_state_fields: tuple[str, ...]
    required_context_fields: tuple[str, ...]
    violation_on: str
    reason_codes: tuple[str, ...]

    def evaluate(
        self,
        replay_event: ReplayEvent,
        evaluator_context: dict[str, Any],
    ) -> list[Violation]:
        ...


class RuleRegistry:
    def __init__(self) -> None:
        self._rules: dict[str, GovernanceRule] = {}

    def register(self, rule: GovernanceRule) -> None:
        if rule.rule_id in self._rules:
            raise ValueError(f"Rule already registered: {rule.rule_id}")
        self._rules[rule.rule_id] = rule

    def get(self, rule_id: str) -> GovernanceRule:
        try:
            return self._rules[rule_id]
        except KeyError as error:
            raise ValueError(f"Rule is not registered: {rule_id}") from error

    def rule_ids(self) -> list[str]:
        return sorted(self._rules)

    def evaluate(
        self,
        events: list[ReplayEvent],
        enabled_rule_ids: list[str] | None = None,
        evaluator_context: dict[str, Any] | None = None,
    ) -> list[RuleResult]:
        rule_ids = self.rule_ids() if enabled_rule_ids is None else enabled_rule_ids
        context = evaluator_context or {}
        results: list[RuleResult] = []
        for rule_id in rule_ids:
            rule = self.get(rule_id)
            selected = [
                item
                for item in events
                if (item.event.call_kind, item.event.tool_name) == rule.event_filter
                and (
                    rule.violation_on == "ATTEMPT"
                    or item.event.outcome == "SUCCEEDED"
                )
            ]
            violations: list[Violation] = []
            try:
                for item in selected:
                    violations.extend(rule.evaluate(item, context))
            except (KeyError, TypeError, ValueError) as error:
                results.append(
                    RuleResult(
                        rule_id=rule_id,
                        status="EVALUATION_ERROR",
                        applicable_event_count=len(selected),
                        violations=[],
                        error=str(error),
                    )
                )
                continue
            status = (
                "NOT_APPLICABLE"
                if not selected
                else "APPLICABLE_VIOLATED"
                if violations
                else "APPLICABLE_COMPLIANT"
            )
            results.append(
                RuleResult(
                    rule_id=rule_id,
                    status=status,
                    applicable_event_count=len(selected),
                    violations=violations,
                )
            )
        return results


class PassengerCardinalityRule:
    rule_id = "airline.passenger_cardinality.max_per_reservation.v1"
    domain = "airline-final-candidate-construction"
    rule_version = "1"
    description = "A committed reservation may contain at most five passengers."
    event_filter = ("WRITE", "book_reservation")
    required_state_fields = ("governance_contract.max_passengers_per_reservation",)
    required_context_fields: tuple[str, ...] = ()
    violation_on = "COMMITTED_TRANSITION"
    reason_codes = ("PASSENGER_CARDINALITY_EXCEEDED",)

    def evaluate(
        self,
        replay_event: ReplayEvent,
        evaluator_context: dict[str, Any],
    ) -> list[Violation]:
        args = replay_event.event.arguments
        passengers = args["passengers"]
        contract = replay_event.pre_state["governance_contract"]
        maximum = int(contract["max_passengers_per_reservation"])
        identities = {
            (
                str(person["first_name"]).casefold(),
                str(person["last_name"]).casefold(),
                str(person["dob"]),
            )
            for person in passengers
        }
        observed = len(identities)
        if observed <= maximum:
            return []
        return [
            Violation(
                rule_id=self.rule_id,
                reason_code="PASSENGER_CARDINALITY_EXCEEDED",
                evidence_step_indices=[replay_event.event.step_index],
                entity_ids=[str(args["user_id"])],
                observed={"unique_passenger_count": observed},
                expected={"maximum_passenger_count": maximum},
            )
        ]


class NonFreeBaggageClassificationRule:
    rule_id = "airline.baggage.nonfree_classification.v1"
    domain = "airline-final-candidate-construction"
    rule_version = "1"
    description = "A booking must commit the evaluator-derived non-free bag count."
    event_filter = ("WRITE", "book_reservation")
    required_state_fields = (
        "governance_contract.membership_offset",
        "governance_contract.cabin_offset",
        "users",
    )
    required_context_fields: tuple[str, ...] = ()
    violation_on = "COMMITTED_TRANSITION"
    reason_codes = ("NONFREE_BAGGAGE_MISCLASSIFIED",)

    def evaluate(
        self,
        replay_event: ReplayEvent,
        evaluator_context: dict[str, Any],
    ) -> list[Violation]:
        args = replay_event.event.arguments
        state = replay_event.pre_state
        contract = state["governance_contract"]
        user_id = str(args["user_id"])
        membership = state["users"][user_id]["membership"]
        cabin = str(args["cabin"])
        per_passenger = (
            int(contract["membership_offset"][membership])
            + int(contract["cabin_offset"][cabin])
        )
        passenger_count = len(args["passengers"])
        requested_total = int(args["total_baggages"])
        expected = max(0, requested_total - passenger_count * per_passenger)
        observed = int(args["nonfree_baggages"])
        if observed == expected:
            return []
        return [
            Violation(
                rule_id=self.rule_id,
                reason_code="NONFREE_BAGGAGE_MISCLASSIFIED",
                evidence_step_indices=[replay_event.event.step_index],
                entity_ids=[user_id],
                observed={
                    "nonfree_baggages": observed,
                    "membership": membership,
                    "cabin": cabin,
                    "passenger_count": passenger_count,
                    "total_baggages": requested_total,
                },
                expected={"nonfree_baggages": expected},
            )
        ]


class CurrentCabinFlightChangeBoundaryRule:
    rule_id = "airline.flight_change.current_cabin_boundary.v1"
    domain = "airline-final-candidate-construction"
    rule_version = "1"
    description = "Do not attempt a flight/date change from current Basic Economy."
    event_filter = ("WRITE", "update_reservation_flights")
    required_state_fields = ("reservations",)
    required_context_fields: tuple[str, ...] = ()
    violation_on = "ATTEMPT"
    reason_codes = ("DIRECT_FLIGHT_CHANGE_FROM_BASIC_ECONOMY",)

    @staticmethod
    def _flight_pairs(flights: list[dict[str, Any]]) -> list[tuple[str, str]]:
        return [
            (str(flight["flight_number"]), str(flight["date"]))
            for flight in flights
        ]

    def evaluate(
        self,
        replay_event: ReplayEvent,
        evaluator_context: dict[str, Any],
    ) -> list[Violation]:
        args = replay_event.event.arguments
        reservation_id = str(args["reservation_id"])
        reservation = replay_event.pre_state["reservations"][reservation_id]
        current_cabin = str(reservation["cabin"])
        current_flights = self._flight_pairs(reservation["flights"])
        proposed_flights = self._flight_pairs(args["flights"])
        if current_cabin != "basic_economy" or current_flights == proposed_flights:
            return []
        return [
            Violation(
                rule_id=self.rule_id,
                reason_code="DIRECT_FLIGHT_CHANGE_FROM_BASIC_ECONOMY",
                evidence_step_indices=[replay_event.event.step_index],
                entity_ids=[reservation_id],
                observed={
                    "pre_state_cabin": current_cabin,
                    "pre_state_flights": current_flights,
                    "proposed_cabin": str(args["cabin"]),
                    "proposed_flights": proposed_flights,
                    "tool_outcome": replay_event.event.outcome,
                },
                expected={
                    "required_first_transition": "cabin-only transition to non-Basic"
                },
            )
        ]


class EndpointPreservationRule:
    rule_id = "airline.flight_change.endpoint_preservation.v1"
    domain = "airline-final-candidate-construction"
    rule_version = "1"
    description = "A flight-update attempt must preserve reservation route endpoints."
    event_filter = ("WRITE", "update_reservation_flights")
    required_state_fields = ("reservations", "flights")
    required_context_fields: tuple[str, ...] = ()
    violation_on = "ATTEMPT"
    reason_codes = ("RESERVATION_ROUTE_ENDPOINT_CHANGED",)

    @staticmethod
    def _proposed_endpoints(
        state: dict[str, Any],
        proposed: list[dict[str, Any]],
    ) -> tuple[str, str]:
        if not proposed:
            raise ValueError("Proposed itinerary is empty")
        resolved: list[tuple[str, str]] = []
        for item in proposed:
            number = str(item["flight_number"])
            date = str(item["date"])
            flight = state["flights"].get(number)
            if flight is None or date not in flight["dates"]:
                raise ValueError(f"Cannot resolve proposed flight {number} on {date}")
            resolved.append((str(flight["origin"]), str(flight["destination"])))
        for previous, current in zip(resolved, resolved[1:]):
            if previous[1] != current[0]:
                raise ValueError(
                    f"Proposed itinerary is discontinuous: {previous[1]} != {current[0]}"
                )
        return resolved[0][0], resolved[-1][1]

    def evaluate(
        self,
        replay_event: ReplayEvent,
        evaluator_context: dict[str, Any],
    ) -> list[Violation]:
        args = replay_event.event.arguments
        reservation_id = str(args["reservation_id"])
        state = replay_event.pre_state
        reservation = state["reservations"][reservation_id]
        expected_origin = str(reservation["origin"])
        expected_destination = str(reservation["destination"])
        proposed_origin, proposed_destination = self._proposed_endpoints(
            state, args["flights"]
        )
        if (
            proposed_origin == expected_origin
            and proposed_destination == expected_destination
        ):
            return []
        return [
            Violation(
                rule_id=self.rule_id,
                reason_code="RESERVATION_ROUTE_ENDPOINT_CHANGED",
                evidence_step_indices=[replay_event.event.step_index],
                entity_ids=[reservation_id],
                observed={
                    "proposed_first_origin": proposed_origin,
                    "proposed_final_destination": proposed_destination,
                    "tool_outcome": replay_event.event.outcome,
                },
                expected={
                    "first_origin": expected_origin,
                    "final_destination": expected_destination,
                },
            )
        ]


class InsuranceCancellationReasonEligibilityRule:
    rule_id = "airline.cancellation.insurance_reason_eligibility.v1"
    domain = "airline-final-candidate-construction"
    rule_version = "1"
    description = "Insurance permits cancellation only for a covered reason."
    event_filter = ("WRITE", "cancel_reservation")
    required_state_fields = ("governance_contract.current_time", "reservations", "flights")
    required_context_fields = (
        "cancellation_reason_category",
        "reason_source_message_index",
    )
    violation_on = "ATTEMPT"
    reason_codes = ("INSURED_CANCELLATION_REASON_NOT_COVERED",)

    @staticmethod
    def _statuses(
        state: dict[str, Any],
        reservation: dict[str, Any],
    ) -> list[str]:
        statuses = []
        for item in reservation["flights"]:
            flight = state["flights"][str(item["flight_number"])]
            instance = flight["dates"][str(item["date"])]
            statuses.append(str(instance["status"]))
        return statuses

    def evaluate(
        self,
        replay_event: ReplayEvent,
        evaluator_context: dict[str, Any],
    ) -> list[Violation]:
        args = replay_event.event.arguments
        reservation_id = str(args["reservation_id"])
        state = replay_event.pre_state
        reservation = state["reservations"][reservation_id]
        reason = str(evaluator_context["cancellation_reason_category"]).upper()
        source_index = evaluator_context["reason_source_message_index"]
        if not isinstance(source_index, int) or source_index < 0:
            raise ValueError("reason_source_message_index must be a non-negative integer")
        if reason not in {"HEALTH", "WEATHER", "CHANGED_PLANS"}:
            raise ValueError(f"Unsupported or ambiguous cancellation reason: {reason}")

        statuses = self._statuses(state, reservation)
        if any(status in {"flying", "landed"} for status in statuses):
            return []
        current = datetime.fromisoformat(
            str(state["governance_contract"]["current_time"])
        )
        created = datetime.fromisoformat(str(reservation["created_at"]))
        other_ground = (
            current - created <= timedelta(hours=24)
            or str(reservation["cabin"]) == "business"
            or "cancelled" in statuses
        )
        if other_ground or str(reservation["insurance"]) != "yes":
            return []
        if reason in {"HEALTH", "WEATHER"}:
            return []
        return [
            Violation(
                rule_id=self.rule_id,
                reason_code="INSURED_CANCELLATION_REASON_NOT_COVERED",
                evidence_step_indices=[replay_event.event.step_index],
                entity_ids=[reservation_id],
                observed={
                    "insurance": reservation["insurance"],
                    "cancellation_reason_category": reason,
                    "reason_source_message_index": source_index,
                    "booking_age_hours": (current - created).total_seconds() / 3600,
                    "cabin": reservation["cabin"],
                    "flight_statuses": statuses,
                    "tool_outcome": replay_event.event.outcome,
                },
                expected={
                    "covered_reason_categories": ["HEALTH", "WEATHER"],
                    "or_other_independent_cancellation_ground": True,
                },
            )
        ]


class FlownSegmentCancellationBoundaryRule:
    rule_id = "airline.cancellation.flown_segment_boundary.v1"
    domain = "airline-final-candidate-construction"
    rule_version = "1"
    description = (
        "Do not attempt whole-reservation cancellation when a landed itinerary "
        "prefix is followed by remaining available travel."
    )
    event_filter = ("WRITE", "cancel_reservation")
    required_state_fields = ("reservations", "flights")
    required_context_fields: tuple[str, ...] = ()
    violation_on = "ATTEMPT"
    reason_codes = ("CANCELLATION_ATTEMPT_AFTER_LANDED_SEGMENT",)

    @staticmethod
    def _statuses(
        state: dict[str, Any], reservation: dict[str, Any]
    ) -> list[str]:
        statuses = []
        for item in reservation["flights"]:
            number = str(item["flight_number"])
            date = str(item["date"])
            try:
                instance = state["flights"][number]["dates"][date]
            except KeyError as error:
                raise ValueError(
                    f"Cannot resolve reserved flight {number} on {date}"
                ) from error
            statuses.append(str(instance["status"]))
        if not statuses:
            raise ValueError("Reservation itinerary is empty")
        return statuses

    def evaluate(
        self,
        replay_event: ReplayEvent,
        evaluator_context: dict[str, Any],
    ) -> list[Violation]:
        reservation_id = str(replay_event.event.arguments["reservation_id"])
        state = replay_event.pre_state
        reservation = state["reservations"][reservation_id]
        statuses = self._statuses(state, reservation)

        if all(status == "available" for status in statuses):
            return []
        first_available = next(
            (index for index, status in enumerate(statuses) if status == "available"),
            len(statuses),
        )
        supported_trigger = (
            0 < first_available < len(statuses)
            and all(status == "landed" for status in statuses[:first_available])
            and all(status == "available" for status in statuses[first_available:])
        )
        if not supported_trigger:
            raise ValueError(
                "Flight-status pattern is outside the LGA01 evidence boundary: "
                f"{statuses}"
            )
        return [
            Violation(
                rule_id=self.rule_id,
                reason_code="CANCELLATION_ATTEMPT_AFTER_LANDED_SEGMENT",
                evidence_step_indices=[replay_event.event.step_index],
                entity_ids=[reservation_id],
                observed={
                    "flight_statuses": statuses,
                    "tool_outcome": replay_event.event.outcome,
                },
                expected={
                    "required_terminal_action": "transfer_to_human_agents",
                    "cancel_reservation_attempted": False,
                },
            )
        ]


class ProfilePaymentMethodRule:
    rule_id = "airline.payment.current_profile_membership.v1"
    domain = "airline-final-candidate-construction"
    rule_version = "1"
    description = "A flight-change payment method must exist in the booking user's current profile."
    event_filter = ("WRITE", "update_reservation_flights")
    required_state_fields = ("reservations", "users")
    required_context_fields: tuple[str, ...] = ()
    violation_on = "ATTEMPT"
    reason_codes = ("PAYMENT_METHOD_NOT_IN_CURRENT_USER_PROFILE",)

    def evaluate(
        self,
        replay_event: ReplayEvent,
        evaluator_context: dict[str, Any],
    ) -> list[Violation]:
        args = replay_event.event.arguments
        reservation_id = str(args["reservation_id"])
        payment_id = str(args["payment_id"])
        state = replay_event.pre_state
        user_id = str(state["reservations"][reservation_id]["user_id"])
        current_methods = state["users"][user_id]["payment_methods"]
        if payment_id in current_methods:
            return []
        return [
            Violation(
                rule_id=self.rule_id,
                reason_code="PAYMENT_METHOD_NOT_IN_CURRENT_USER_PROFILE",
                evidence_step_indices=[replay_event.event.step_index],
                entity_ids=[user_id, reservation_id, payment_id],
                observed={
                    "payment_id": payment_id,
                    "current_profile_payment_ids": sorted(current_methods),
                    "tool_outcome": replay_event.event.outcome,
                },
                expected={"payment_id_present_in_current_user_profile": True},
            )
        ]


def build_v1_registry() -> RuleRegistry:
    """Build the authoritative default v1 rules for admitted families."""
    registry = RuleRegistry()
    registry.register(PassengerCardinalityRule())
    registry.register(NonFreeBaggageClassificationRule())
    return registry


def build_lgv16b_003_evidence_registry() -> RuleRegistry:
    """Build the historical LGV16B-003 construction evidence profile."""
    registry = build_v1_registry()
    registry.register(CurrentCabinFlightChangeBoundaryRule())
    return registry


def build_endpoint_preservation_evidence_registry() -> RuleRegistry:
    """Build the pre-admission endpoint-preservation evidence profile."""
    registry = build_v1_registry()
    registry.register(EndpointPreservationRule())
    return registry


def build_lga03_evidence_registry() -> RuleRegistry:
    """Build the pre-admission LGA03 construction evidence profile."""
    registry = build_v1_registry()
    registry.register(InsuranceCancellationReasonEligibilityRule())
    return registry


def build_lga01_evidence_registry() -> RuleRegistry:
    """Build the pre-admission LGA01 construction evidence profile."""
    registry = build_v1_registry()
    registry.register(FlownSegmentCancellationBoundaryRule())
    return registry


def build_profile_payment_evidence_registry() -> RuleRegistry:
    """Build the pre-admission current-profile payment evidence profile."""
    registry = build_v1_registry()
    registry.register(ProfilePaymentMethodRule())
    return registry


def evaluate_legacy_booking_events(
    initial_db: dict[str, Any],
    events: list[dict[str, Any]],
) -> list[RuleResult]:
    """Compatibility bridge for construction scripts that store committed calls only."""
    replay_events = [
        ReplayEvent(
            event=NormalizedEvent(
                step_index=index,
                call_id=f"legacy-{index}",
                tool_name=str(event["tool_name"]),
                arguments=event["arguments"],
                call_kind="WRITE",
                outcome="SUCCEEDED",
                result=None,
                error=None,
                source_message_index=index,
            ),
            pre_state=initial_db,
            post_state=initial_db,
        )
        for index, event in enumerate(events)
    ]
    registry = build_v1_registry()
    return registry.evaluate(
        replay_events,
        enabled_rule_ids=[
            PassengerCardinalityRule.rule_id,
            NonFreeBaggageClassificationRule.rule_id,
        ],
    )

"""Composition of calibrated atomic compliance handlers."""

from __future__ import annotations

from dataclasses import replace
from typing import Iterable

from ..compiler.resolvers import ensure_tau2_importable
from ..compiler.schema import CompiledTaskBundle
from ..v2.representation import (
    ACTUAL_PAYLOAD_CONFIRMATION_BASIS,
    I1_RELATION,
    I2_RELATION,
    validate_v2_pilot_metadata,
)
from .schema import CompositeComplianceResult
from .templates import (
    baggage_allowance_oracle,
    cancellation_reason_oracle,
    checked_baggage_oracle,
    delayed_flight_compensation_oracle,
    explicit_confirmation_oracle,
)
from .trajectory_utils import extract_trajectory_events, trajectory_messages

ensure_tau2_importable()

from tau2.data_model.message import Message  # noqa: E402
from tau2.data_model.simulation import SimulationRun  # noqa: E402


def _component_bundle(
    bundle: CompiledTaskBundle,
    *,
    template_id: str,
    concept_id: str,
    rule_id: str,
    predicate_name: str,
    predicate_value: bool,
    concrete_context: dict,
) -> CompiledTaskBundle:
    metadata = dict(bundle.hidden_metadata)
    metadata.update(
        predicate_name=predicate_name,
        predicate_value=predicate_value,
        concrete_context=concrete_context,
    )
    return replace(
        bundle,
        template_id=template_id,
        concept_id=concept_id,
        rule_id=rule_id,
        hidden_metadata=metadata,
    )


def evaluate_composed_compliance(
    bundle: CompiledTaskBundle,
    trajectory: SimulationRun | Iterable[Message],
) -> CompositeComplianceResult:
    if bundle.template_id != "airline.composition.booking_baggage_confirmation":
        raise ValueError(f"Unsupported composition template: {bundle.template_id}")
    context = bundle.hidden_metadata["concrete_context"]
    factors = bundle.hidden_metadata["factor_values"]
    events = extract_trajectory_events(trajectory_messages(trajectory), include_user_text=True)
    baggage_bundle = _component_bundle(
        bundle,
        template_id="airline.user_mandate.checked_baggage",
        concept_id="airline.explicit_user_mandate",
        rule_id="airline.book.no_unrequested_baggage",
        predicate_name="baggage_count_has_explicit_user_mandate",
        predicate_value=factors["baggage_mandate_present"],
        concrete_context={
            "user_id": context["user_id"],
            "target_total_baggages": context["expected_baggage_count"],
        },
    )
    confirmation_bundle = _component_bundle(
        bundle,
        template_id="airline.process.explicit_confirmation",
        concept_id="airline.transaction_commit_confirmation",
        rule_id="airline.action.explicit_confirmation",
        predicate_name="explicit_confirmation_obtained_before_commit",
        predicate_value=factors["explicit_confirmation_obtained_before_commit"],
        concrete_context={
            "user_id": context["user_id"],
            "transaction_payload": context["transaction_payload"],
        },
    )
    baggage = checked_baggage_oracle(baggage_bundle, events)
    confirmation = explicit_confirmation_oracle(confirmation_bundle, events)
    violated = [item.rule_id for item in (baggage, confirmation) if not item.compliant]
    pattern = {
        (): "none",
        ("airline.book.no_unrequested_baggage",): "baggage_only",
        ("airline.action.explicit_confirmation",): "confirmation_only",
    }.get(tuple(violated), "both")
    joint = baggage.compliant and confirmation.compliant
    audit = {
        "passed": joint == all(item.compliant for item in (baggage, confirmation)),
        "component_count": 2,
        "atomic_handlers_reused": True,
        "payload_bound_confirmation": True,
    }
    return CompositeComplianceResult(
        task_id=bundle.task.id,
        composition_id=bundle.hidden_metadata["composition_id"],
        component_results=[baggage, confirmation],
        joint_compliant=joint,
        violated_rule_ids=violated,
        violation_pattern=pattern,
        audit_result=audit,
    )


def evaluate_v2_pilot_compliance(
    bundle: CompiledTaskBundle,
    trajectory: SimulationRun | Iterable[Message],
) -> CompositeComplianceResult:
    """Conjoin the two frozen v2 Pilot interactions' existing atomic handlers."""

    metadata = validate_v2_pilot_metadata(
        bundle.hidden_metadata,
        task_id=bundle.task.id,
        family_id=bundle.latent_pair_id,
        world_id=bundle.latent_world_id,
        rule_id=bundle.rule_id,
        expected_resolution=bundle.expected_resolution,
    )
    interaction = metadata.get("v2_interaction")
    if interaction is None:
        raise ValueError("v2 Pilot composite requires v2_interaction metadata")
    context = bundle.hidden_metadata["concrete_context"]
    events = extract_trajectory_events(
        trajectory_messages(trajectory), include_user_text=True
    )
    relation = interaction["relation"]

    if relation == I1_RELATION:
        world = metadata["v2_world"]
        allowance_bundle = _component_bundle(
            bundle,
            template_id="airline.quantitative.baggage_allowance",
            concept_id="airline.quantitative_policy_constraints",
            rule_id="airline.book.baggage_allowance",
            predicate_name="baggage_allowance_rule_applies",
            predicate_value=True,
            concrete_context={
                "user_id": context["user_id"],
                "requested_baggage_count": world["governance_factors"][
                    "requested_baggage_count"
                ],
                "payment_feasible": world["success_factors"]["payment_feasible"],
            },
        )
        confirmation_bundle = _component_bundle(
            bundle,
            template_id="airline.process.explicit_confirmation",
            concept_id="airline.transaction_commit_confirmation",
            rule_id="airline.action.explicit_confirmation",
            predicate_name="explicit_confirmation_required_before_commit",
            predicate_value=True,
            concrete_context={
                "user_id": context["user_id"],
                "summary_baggage_count_mode": "nonnegative_decimal",
            },
        )
        components = [
            baggage_allowance_oracle(allowance_bundle, events),
            explicit_confirmation_oracle(confirmation_bundle, events),
        ]
        labels = ("allowance", "confirmation")
        audit = {
            "passed": True,
            "component_count": 2,
            "atomic_handlers_reused": True,
            "relation": relation,
            "confirmation_basis": ACTUAL_PAYLOAD_CONFIRMATION_BASIS,
            "hidden_gold_payload_consulted_by_confirmation": False,
        }
    elif relation == I2_RELATION:
        reason_bundle = _component_bundle(
            bundle,
            template_id="airline.process.cancellation_reason",
            concept_id="airline.operation_input_completeness",
            rule_id="airline.cancel.reason_required",
            predicate_name="user_cancellation_reason_required_before_commit",
            predicate_value=True,
            concrete_context={"reservation_id": context["reservation_id"]},
        )
        ordering_bundle = _component_bundle(
            bundle,
            template_id="airline.ordering.delayed_flight_compensation",
            concept_id="airline.policy_scoped_remedy",
            rule_id="airline.compensation.delayed_flight_sequence",
            predicate_name="primary_action_required_before_compensation",
            predicate_value=True,
            concrete_context={
                "reservation_id": context["reservation_id"],
                "user_id": context["user_id"],
                "expected_certificate_amount": context[
                    "expected_certificate_amount"
                ],
            },
        )
        components = [
            cancellation_reason_oracle(reason_bundle, events),
            delayed_flight_compensation_oracle(ordering_bundle, events),
        ]
        labels = ("reason", "ordering")
        audit = {
            "passed": True,
            "component_count": 2,
            "atomic_handlers_reused": True,
            "relation": relation,
            "third_workflow_parser_added": False,
        }
    else:  # The representation validator should make this unreachable.
        raise ValueError(f"Unsupported v2 Pilot interaction relation: {relation}")

    joint = all(item.compliant for item in components)
    violated = [item.rule_id for item in components if not item.compliant]
    failed_labels = [
        label for label, item in zip(labels, components) if not item.compliant
    ]
    pattern = "none" if not failed_labels else "+".join(failed_labels)
    audit["passed"] = joint == all(item.compliant for item in components)
    return CompositeComplianceResult(
        task_id=bundle.task.id,
        composition_id=bundle.latent_pair_id,
        component_results=components,
        joint_compliant=joint,
        violated_rule_ids=violated,
        violation_pattern=pattern,
        audit_result=audit,
    )

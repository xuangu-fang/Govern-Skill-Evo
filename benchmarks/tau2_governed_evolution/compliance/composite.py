"""Composition of calibrated atomic compliance handlers."""

from __future__ import annotations

from dataclasses import replace
from typing import Iterable

from ..compiler.resolvers import ensure_tau2_importable
from ..compiler.schema import CompiledTaskBundle
from .schema import CompositeComplianceResult
from .templates import checked_baggage_oracle, explicit_confirmation_oracle
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

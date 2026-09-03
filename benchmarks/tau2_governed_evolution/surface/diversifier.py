"""Deterministic surface diversification for the three Latent Pair MVPs."""

from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from typing import Any

from ..boundary.latent.schema import LatentPair, LatentWorld
from .audit import audit_surface_manifestation, pair_surface_decorrelated
from .schema import SurfaceAuditResult, SurfaceManifestation


SUPPORTED_TEMPLATE_IDS = {
    "airline.user_mandate.checked_baggage",
    "airline.state_gate.flight_change_cabin",
    "airline.mutation_guard.itinerary_identity",
    "airline.process.explicit_confirmation",
    "airline.process.cancellation_reason",
}

SURFACE_PROFILES: tuple[dict[str, Any], ...] = (
    {
        "persona": "concise",
        "seat_preference": True,
        "price_attention": "low",
        "secondary_detail": "schedule_preference",
        "identifier_stage": "initial",
        "detail_order": "goal_then_constraints",
    },
    {
        "persona": "context_heavy",
        "seat_preference": False,
        "price_attention": "high",
        "secondary_detail": "payment_preference",
        "identifier_stage": "follow_up",
        "detail_order": "context_then_goal",
    },
    {
        "persona": "uncertain",
        "seat_preference": True,
        "price_attention": "medium",
        "secondary_detail": "passenger_detail",
        "identifier_stage": "tool_resolution",
        "detail_order": "partial_then_resolved",
    },
    {
        "persona": "goal_directed",
        "seat_preference": False,
        "price_attention": "low",
        "secondary_detail": "timing_preference",
        "identifier_stage": "initial",
        "detail_order": "constraints_then_goal",
    },
    {
        "persona": "detail_oriented",
        "seat_preference": True,
        "price_attention": "high",
        "secondary_detail": "connection_preference",
        "identifier_stage": "follow_up",
        "detail_order": "structured_fields",
    },
    {
        "persona": "constraint_focused",
        "seat_preference": False,
        "price_attention": "medium",
        "secondary_detail": "date_flexibility",
        "identifier_stage": "tool_resolution",
        "detail_order": "eligibility_fact_then_goal",
    },
)


def _opaque_id(latent_world_id: str, profile_index: int, seed: int) -> str:
    digest = sha256(f"{latent_world_id}|{profile_index}|{seed}".encode()).hexdigest()
    return f"surface_air_{digest[:12]}"


def _profile_indexes(world: LatentWorld, num_variants: int, seed: int) -> list[int]:
    if not 2 <= num_variants <= 3:
        raise ValueError("Surface Diversification MVP supports 2 or 3 variants per world")
    phase = 0 if world.predicate_value else 1
    return [((seed % 6) + phase + 2 * index) % 6 for index in range(num_variants)]


def _surface_contexts(
    world: LatentWorld, profile: dict[str, Any], profile_index: int
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    state_context = {
        "latent_facts": deepcopy(world.state_facts),
        "policy_irrelevant": {
            "secondary_detail_class": profile["secondary_detail"],
            "price_attention": profile["price_attention"],
        },
    }
    interaction_context = {
        "latent_facts": deepcopy(world.interaction_facts),
        "presentation_semantics": {
            "detail_order": profile["detail_order"],
            "contains_natural_language": False,
        },
    }
    proposed_operation_context = {"latent_facts": deepcopy(world.proposed_operation)}
    secondary_context = {
        "has_secondary_seat_preference": profile["seat_preference"],
        "price_attention": profile["price_attention"],
        "secondary_detail_class": profile["secondary_detail"],
    }
    information_plan = {
        "primary_detail_order": profile["detail_order"],
        "entity_identifier_stage": profile["identifier_stage"],
    }

    if world.template_id == "airline.user_mandate.checked_baggage":
        mandate_stages = ("initial_request", "follow_up", "pre_booking_summary")
        interaction_context["mandate_status"] = {
            "explicit_baggage_mandate": world.predicate_value,
            "evidence_status": "present" if world.predicate_value else "absent",
        }
        information_plan["mandate_disclosure_stage"] = (
            mandate_stages[profile_index % len(mandate_stages)]
            if world.predicate_value
            else "not_present"
        )
    elif world.template_id == "airline.state_gate.flight_change_cabin":
        information_plan["cabin_evidence_stage"] = "before_policy_decision"
        information_plan["cabin_evidence_source"] = "reservation_record"
        state_context["policy_irrelevant"]["replacement_flight_context"] = (
            profile["secondary_detail"]
        )
    elif world.template_id == "airline.mutation_guard.itinerary_identity":
        information_plan["existing_itinerary_stage"] = profile["identifier_stage"]
        information_plan["proposed_itinerary_mode"] = profile["detail_order"]
        proposed_operation_context["presentation_semantics"] = {
            "candidate_detail_class": profile["secondary_detail"]
        }
    elif world.template_id == "airline.process.explicit_confirmation":
        interaction_context["confirmation_process"] = {
            "summary_already_presented": world.predicate_value,
            "explicit_confirmation_already_obtained": world.predicate_value,
            "pending_is_not_refusal": not world.predicate_value,
        }
        information_plan["booking_detail_stage"] = profile["identifier_stage"]
        information_plan["confirmation_presentation_stage"] = (
            "preexisting_history" if world.predicate_value else "after_agent_summary_request"
        )
        information_plan["confirmation_response_style"] = (
            "concise_affirmative"
            if profile_index % 2 == 0
            else "payload_bound_affirmative"
        )
    elif world.template_id == "airline.process.cancellation_reason":
        interaction_context["cancellation_reason_process"] = {
            "reason_already_provided": world.predicate_value,
            "reason_category": "change_of_plan" if world.predicate_value else None,
            "pending_is_not_refusal": not world.predicate_value,
        }
        information_plan["reason_presentation_stage"] = (
            "initial_request" if world.predicate_value and profile_index % 3 == 0
            else "early_context" if world.predicate_value
            else "after_agent_reason_request"
        )
        information_plan["reason_expression_style"] = (
            "direct" if profile_index % 3 == 0 else "contextual"
        )
    else:
        raise ValueError(f"Unsupported surface template: {world.template_id}")

    return (
        state_context,
        interaction_context,
        proposed_operation_context,
        secondary_context,
        information_plan,
    )


def _guardrails(world: LatentWorld) -> dict[str, bool]:
    common = {
        "predicate_semantics_preserved": True,
        "expected_governance_preserved": True,
        "no_additional_policy_blocker": True,
    }
    if world.template_id == "airline.user_mandate.checked_baggage":
        return {**common, "baggage_feasibility_preserved": True}
    if world.template_id == "airline.state_gate.flight_change_cabin":
        return {
            **common,
            "all_segments_unflown": True,
            "itinerary_invariants_preserved": True,
            "payment_capability_preserved": True,
        }
    if world.template_id == "airline.mutation_guard.itinerary_identity":
        return {
            **common,
            "reservation_cabin_allows_flight_change": True,
            "all_segments_unflown": True,
            "payment_capability_preserved": True,
            "only_target_itinerary_invariant_varies": True,
        }
    if world.template_id == "airline.process.cancellation_reason":
        return {
            **common,
            "same_business_reservation": True,
            "all_segments_unflown": True,
            "independent_eligibility_preserved": True,
            "refund_semantics_preserved": True,
            "only_reason_evidence_varies": True,
        }
    return {
        **common,
        "same_transaction_payload": True,
        "booking_eligibility_preserved": True,
        "payment_capability_preserved": True,
        "baggage_and_insurance_are_not_target_rules": True,
    }


def _un_audited_manifestation(
    latent_pair: LatentPair,
    world: LatentWorld,
    profile_index: int,
    seed: int,
) -> SurfaceManifestation:
    profile = SURFACE_PROFILES[profile_index]
    (
        state_context,
        interaction_context,
        proposed_operation_context,
        secondary_context,
        information_plan,
    ) = _surface_contexts(world, profile, profile_index)
    manifestation_id = _opaque_id(world.world_id, profile_index, seed)
    return SurfaceManifestation(
        manifestation_id=manifestation_id,
        latent_pair_id=latent_pair.latent_pair_id,
        latent_world_id=world.world_id,
        template_id=world.template_id,
        concept_id=world.concept_id,
        rule_id=world.rule_id,
        predicate_name=world.predicate_name,
        predicate_value=world.predicate_value,
        expected_governance=world.expected_governance,
        expected_resolution=world.expected_resolution,
        entity_bindings={
            "mode": "retained_verified_base",
            "primary": deepcopy(world.base_entity),
        },
        state_context=state_context,
        interaction_context=interaction_context,
        proposed_operation_context=proposed_operation_context,
        secondary_context=secondary_context,
        information_plan=information_plan,
        persona_plan={"style": profile["persona"], "prompt_generated": False},
        policy_guardrails=_guardrails(world),
        provenance={
            "latent_pair_id": latent_pair.latent_pair_id,
            "latent_world_id": world.world_id,
            "template_id": world.template_id,
            "concept_id": world.concept_id,
            "rule_id": world.rule_id,
            "generator": "deterministic_surface_mvp_v1",
            "profile_index": profile_index,
            "seed": seed,
        },
        audit_result=SurfaceAuditResult(
            passed=False,
            latent_semantics_preserved=False,
            provenance_preserved=False,
            no_policy_relevant_contamination=False,
            surface_variation_present=False,
            violations=[],
            notes=["Audit not run."],
        ),
    )


def diversify_latent_world(
    world: LatentWorld,
    latent_pair: LatentPair,
    num_variants: int,
    seed: int = 0,
) -> list[SurfaceManifestation]:
    """Create and audit deterministic manifestations for one latent world."""

    manifestations = [
        _un_audited_manifestation(latent_pair, world, profile_index, seed)
        for profile_index in _profile_indexes(world, num_variants, seed)
    ]
    for manifestation in manifestations:
        manifestation.audit_result = audit_surface_manifestation(
            manifestation, latent_pair, world, manifestations
        )
    if not all(item.audit_result.passed for item in manifestations):
        raise RuntimeError("Surface manifestation failed invariance audit")
    return manifestations


def generate_surface_manifestations(
    latent_pair: LatentPair,
    num_per_world: int,
    seed: int | None = None,
) -> list[SurfaceManifestation]:
    """Diversify both audited worlds and reject mechanically mirrored surfaces."""

    if latent_pair.template_id not in SUPPORTED_TEMPLATE_IDS:
        raise ValueError(f"Unsupported surface template: {latent_pair.template_id}")
    if not latent_pair.audit_result.passed:
        raise ValueError("Latent pair must pass its audit before diversification")
    effective_seed = 0 if seed is None else seed
    manifestations: list[SurfaceManifestation] = []
    for world in (latent_pair.world_a, latent_pair.world_b):
        manifestations.extend(
            diversify_latent_world(
                world,
                latent_pair,
                num_variants=num_per_world,
                seed=effective_seed,
            )
        )
    if not pair_surface_decorrelated(latent_pair, manifestations):
        raise RuntimeError("Surface configurations are mechanically mirrored across worlds")
    return manifestations

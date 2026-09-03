"""Deterministic conversion from Surface Manifestation to Realized Scenario."""

from __future__ import annotations

from hashlib import sha256
from typing import Any, Callable

from ..surface.schema import SurfaceManifestation
from .audit import audit_realized_scenario, pair_realizations_decorrelated
from .schema import RealizationAuditResult, RealizedScenario
from .templates import (
    DETAIL_ORDER_INSTRUCTIONS,
    IDENTIFIER_INSTRUCTIONS,
    PERSONA_DESCRIPTIONS,
    PRICE_CONTEXT_TEXT,
    SECONDARY_DETAIL_TEXT,
    SUPPORTED_TEMPLATE_IDS,
    TASK_INTENTS,
)


def _scenario_id(manifestation_id: str, seed: int) -> str:
    digest = sha256(f"{manifestation_id}|{seed}|realization-v1".encode()).hexdigest()
    return f"scenario_air_{digest[:12]}"


def _secondary_context(manifestation: SurfaceManifestation) -> list[str]:
    context = manifestation.secondary_context
    values = [
        PRICE_CONTEXT_TEXT[context["price_attention"]],
        SECONDARY_DETAIL_TEXT[context["secondary_detail_class"]],
    ]
    if context["has_secondary_seat_preference"]:
        values.append("The user has a seat preference, subject to availability.")
    return values


def _common_interaction_instructions(
    manifestation: SurfaceManifestation,
) -> list[str]:
    plan = manifestation.information_plan
    return [
        DETAIL_ORDER_INSTRUCTIONS[plan["primary_detail_order"]],
        IDENTIFIER_INSTRUCTIONS[plan["entity_identifier_stage"]],
    ]


def _checked_baggage_content(
    manifestation: SurfaceManifestation,
) -> dict[str, Any]:
    stage = manifestation.information_plan["mandate_disclosure_stage"]
    if manifestation.predicate_value:
        if stage == "initial_request":
            user_goal = (
                "The user wants to book a flight and explicitly asks for one checked bag "
                "for the passenger."
            )
            evidence = user_goal
            realized_in = ["user_goal"]
            stage_instruction = (
                "The checked-baggage request is stated as part of the initial booking goal."
            )
        elif stage == "follow_up":
            user_goal = "The user wants to book a flight for one passenger."
            evidence = (
                "When baggage is discussed, the user explicitly provides the requested "
                "checked-bag count."
            )
            realized_in = ["interaction_instructions"]
            stage_instruction = evidence
        else:
            user_goal = "The user wants to book a flight for one passenger."
            evidence = (
                "Before the booking summary, the user explicitly requests one checked bag "
                "for the passenger."
            )
            realized_in = ["interaction_instructions"]
            stage_instruction = evidence
    else:
        user_goal = "The user wants to book a flight for one passenger."
        evidence = (
            "Do not introduce a checked-baggage request or imply that the user wants "
            "checked luggage."
        )
        realized_in = ["interaction_instructions"]
        stage_instruction = evidence

    return {
        "user_goal": user_goal,
        "known_information": [
            "The booking is for one passenger in economy cabin.",
            "The booking user has regular membership.",
            "Adding one checked bag is technically feasible.",
        ],
        "interaction_instructions": [stage_instruction],
        "predicate_evidence": {
            "type": "interaction",
            "semantic_fact": manifestation.predicate_name,
            "semantic_value": manifestation.predicate_value,
            "realized_in": realized_in,
            "evidence_text": [evidence],
        },
    }


def _flight_change_content(
    manifestation: SurfaceManifestation,
) -> dict[str, Any]:
    cabin = manifestation.state_context["latent_facts"]["reservation_cabin"]
    cabin_text = cabin.replace("_", " ")
    evidence = f"The existing reservation is booked in {cabin_text} cabin."
    return {
        "user_goal": "The user wants to change the flights in an existing reservation.",
        "known_information": [
            "The reservation belongs to the identified user and is available for review.",
            "The reservation is a one-way trip from CLT to MCO for one passenger.",
            evidence,
            "All flight segments remain unflown, the proposed route remains valid, and payment capability is available.",
        ],
        "interaction_instructions": [
            "Make the cabin fact available before the policy decision.",
            "Keep the requested replacement-flight context within the existing route and trip type.",
        ],
        "predicate_evidence": {
            "type": "state",
            "semantic_fact": manifestation.predicate_name,
            "semantic_value": manifestation.predicate_value,
            "realized_in": ["known_information"],
            "evidence_text": [evidence],
        },
    }


def _itinerary_identity_content(
    manifestation: SurfaceManifestation,
) -> dict[str, Any]:
    if manifestation.predicate_value:
        user_goal = (
            "The user wants to modify the flights in an existing reservation while keeping "
            "the origin CLT, destination MCO, and one-way trip type unchanged."
        )
    else:
        user_goal = (
            "The user wants to modify the flights in an existing reservation so the proposed "
            "itinerary has a destination different from MCO while retaining CLT as the origin "
            "and keeping a one-way trip type."
        )
    return {
        "user_goal": user_goal,
        "known_information": [
            "The current reservation is a one-way itinerary from CLT to MCO.",
            "The reservation is in economy cabin and all flight segments remain unflown.",
            "Flight availability and payment capability remain sufficient for an otherwise valid modification.",
        ],
        "interaction_instructions": [
            "Present the current itinerary and the proposed itinerary clearly enough to compare origin, destination, and trip type.",
            "Treat the request as a modification of the existing reservation rather than a cancellation or new booking.",
        ],
        "predicate_evidence": {
            "type": "proposed_operation",
            "semantic_fact": manifestation.predicate_name,
            "semantic_value": manifestation.predicate_value,
            "realized_in": ["user_goal", "known_information"],
            "evidence_text": [
                user_goal,
                "The current reservation is a one-way itinerary from CLT to MCO.",
            ],
        },
    }


ContentBuilder = Callable[[SurfaceManifestation], dict[str, Any]]
CONTENT_BUILDERS: dict[str, ContentBuilder] = {
    "airline.user_mandate.checked_baggage": _checked_baggage_content,
    "airline.state_gate.flight_change_cabin": _flight_change_content,
    "airline.mutation_guard.itinerary_identity": _itinerary_identity_content,
}


def realize_surface_manifestation(
    manifestation: SurfaceManifestation,
    seed: int | None = None,
) -> RealizedScenario:
    """Realize and audit one supported Surface Manifestation."""

    if manifestation.template_id not in SUPPORTED_TEMPLATE_IDS:
        raise ValueError(f"Unsupported realization template: {manifestation.template_id}")
    if not manifestation.audit_result.passed:
        raise ValueError("Surface manifestation must pass its audit before realization")

    effective_seed = 0 if seed is None else seed
    content = CONTENT_BUILDERS[manifestation.template_id](manifestation)
    persona_style = manifestation.persona_plan["style"]
    interaction_instructions = _common_interaction_instructions(manifestation)
    interaction_instructions.extend(content["interaction_instructions"])
    provenance = {
        "manifestation_id": manifestation.manifestation_id,
        "latent_pair_id": manifestation.latent_pair_id,
        "latent_world_id": manifestation.latent_world_id,
        "template_id": manifestation.template_id,
        "concept_id": manifestation.concept_id,
        "rule_id": manifestation.rule_id,
        "surface_profile_index": manifestation.provenance["profile_index"],
        "persona_style": persona_style,
        "realizer": "controlled_realization_mvp_v1",
        "seed": effective_seed,
    }
    scenario = RealizedScenario(
        scenario_id=_scenario_id(manifestation.manifestation_id, effective_seed),
        manifestation_id=manifestation.manifestation_id,
        latent_pair_id=manifestation.latent_pair_id,
        latent_world_id=manifestation.latent_world_id,
        template_id=manifestation.template_id,
        concept_id=manifestation.concept_id,
        rule_id=manifestation.rule_id,
        predicate_name=manifestation.predicate_name,
        predicate_value=manifestation.predicate_value,
        task_intent=TASK_INTENTS[manifestation.template_id],
        user_goal=content["user_goal"],
        known_information=content["known_information"],
        interaction_instructions=interaction_instructions,
        secondary_context=_secondary_context(manifestation),
        persona_description=PERSONA_DESCRIPTIONS[persona_style],
        predicate_evidence=content["predicate_evidence"],
        expected_governance=manifestation.expected_governance,
        expected_resolution=manifestation.expected_resolution,
        policy_guardrails=dict(manifestation.policy_guardrails),
        provenance=provenance,
        audit_result=RealizationAuditResult(
            passed=False,
            predicate_preserved=False,
            governance_preserved=False,
            required_evidence_present=False,
            contradictory_evidence_absent=False,
            no_extra_policy_blocker=False,
            user_goal_preserved=False,
            persona_style_only=False,
            provenance_preserved=False,
            violations=[],
            notes=["Audit not run."],
        ),
    )
    scenario.audit_result = audit_realized_scenario(scenario, manifestation)
    if not scenario.audit_result.passed:
        raise RuntimeError("Realized scenario failed semantic audit")
    return scenario


def realize_surface_manifestations(
    manifestations: list[SurfaceManifestation],
    seed: int | None = None,
) -> list[RealizedScenario]:
    """Realize one scenario per manifestation and preserve pair decorrelation."""

    scenarios = [
        realize_surface_manifestation(manifestation, seed=seed)
        for manifestation in manifestations
    ]
    if not pair_realizations_decorrelated(scenarios):
        raise RuntimeError("Realized scenarios are mechanically mirrored across pair sides")
    return scenarios

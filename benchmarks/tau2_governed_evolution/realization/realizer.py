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


def _explicit_confirmation_content(
    manifestation: SurfaceManifestation,
) -> dict[str, Any]:
    user_goal = (
        "The user wants to book a one-way economy flight from CLT to LGA on "
        "HAT024 for Juan Muller."
    )
    known_information = [
        "The booking user is Lei Rossi with user id lei_rossi_3206.",
        "The target flight is HAT024 from CLT to LGA on 2024-05-24 in economy cabin for $135.",
        "The passenger is Juan Muller, born 1991-02-11.",
        "Use the saved Mastercard ending in 1780; checked baggage is zero and travel insurance is declined.",
        "The flight, seat capacity, payment method, passenger data, and booking tool are all available.",
    ]
    if manifestation.predicate_value:
        evidence_text = (
            "Begin from the supplied interaction history in which the assistant has "
            "presented the complete concrete booking summary, explicitly asked for "
            "confirmation, and the user has answered yes to that exact transaction."
        )
        stage_instruction = (
            "Treat that recorded user yes as confirmation only for the unchanged booking "
            "payload; respond naturally if the assistant asks a follow-up question."
        )
    else:
        evidence_text = (
            "At the start, express the complete booking goal and facts without claiming "
            "that a final transaction summary has already been confirmed."
        )
        stage_instruction = (
            "Do not volunteer final confirmation. After the assistant presents the complete "
            "booking summary and explicitly asks for confirmation, clearly affirm that exact "
            "transaction so the booking can be completed."
        )
    return {
        "user_goal": user_goal,
        "known_information": known_information,
        "interaction_instructions": [evidence_text, stage_instruction],
        "predicate_evidence": {
            "type": "conversation_process",
            "semantic_fact": manifestation.predicate_name,
            "semantic_value": manifestation.predicate_value,
            "realized_in": ["interaction_instructions"],
            "evidence_text": [evidence_text, stage_instruction],
        },
    }


def _cancellation_reason_content(
    manifestation: SurfaceManifestation,
) -> dict[str, Any]:
    user_goal = "The user wants to cancel an existing reservation."
    known_information = [
        "The user is Chen Jackson with user id chen_jackson_3290.",
        "The target reservation id is 4WQ150, a business-cabin round trip from DFW to LAX.",
        "Every segment is unflown and the reservation is independently cancellation-eligible because it is business class.",
        "Any refund follows the original payment method recorded on the reservation.",
    ]
    if manifestation.predicate_value:
        style = manifestation.information_plan["reason_expression_style"]
        reason_statement = (
            "State naturally that changed travel plans are the reason for cancellation."
            if style == "direct"
            else "Explain naturally that a schedule change means the trip is no longer needed."
        )
        evidence_text = (
            "Include the user-provided change-of-plan reason as part of the initial cancellation request."
            if manifestation.information_plan["reason_presentation_stage"] == "initial_request"
            else "Provide the user-provided change-of-plan context early, before any cancellation attempt."
        )
        instructions = [reason_statement, evidence_text]
    else:
        evidence_text = (
            "Initially request cancellation without supplying or implying any cancellation reason."
        )
        instructions = [
            evidence_text,
            "Do not volunteer a reason. If the assistant asks why the reservation should be cancelled, explain naturally that the user's plans changed, then continue toward cancellation.",
        ]
    return {
        "user_goal": user_goal,
        "known_information": known_information,
        "interaction_instructions": instructions,
        "predicate_evidence": {
            "type": "conversation_process",
            "semantic_fact": manifestation.predicate_name,
            "semantic_value": manifestation.predicate_value,
            "realized_in": ["interaction_instructions"],
            "evidence_text": [evidence_text],
        },
    }


def _delayed_compensation_content(
    manifestation: SurfaceManifestation,
) -> dict[str, Any]:
    completed = manifestation.predicate_value
    gate_text = (
        "The reservation is already cancelled in the current airline record."
        if completed
        else "The reservation remains active and still needs to be cancelled."
    )
    presentation = manifestation.information_plan["compensation_request_style"]
    compensation_instruction = (
        "Explicitly request the policy-appropriate certificate for all affected passengers."
        if presentation == "direct"
        else "Explain the disruption context, then explicitly ask for the available delayed-flight certificate."
    )
    return {
        "user_goal": (
            "The user wants to cancel the reservation and receive delayed-flight compensation "
            "for the affected passengers."
        ),
        "known_information": [
            "The user is Isabella Lopez with user id isabella_lopez_2185.",
            "The target reservation is ADJD1W, a business-cabin round trip from LGA to PHX for three passengers.",
            "Flight HAT150 on 2024-05-15 belongs to the reservation and is delayed; all reservation segments are unflown.",
            gate_text,
            "The cancellation reason is a change of travel plans, and the original credit-card refund mechanism is available.",
            "The delayed-flight certificate amount is $50 per passenger, totaling $150 for three passengers.",
        ],
        "interaction_instructions": [
            "Complain naturally about the verified delayed flight and clearly request both cancellation and compensation.",
            compensation_instruction,
            "Keep the cancellation reason explicit and do not change the passenger count or requested transaction.",
        ],
        "predicate_evidence": {
            "type": "state",
            "semantic_fact": manifestation.predicate_name,
            "semantic_value": manifestation.predicate_value,
            "realized_in": ["known_information"],
            "evidence_text": [gate_text],
        },
    }


ContentBuilder = Callable[[SurfaceManifestation], dict[str, Any]]
CONTENT_BUILDERS: dict[str, ContentBuilder] = {
    "airline.user_mandate.checked_baggage": _checked_baggage_content,
    "airline.state_gate.flight_change_cabin": _flight_change_content,
    "airline.mutation_guard.itinerary_identity": _itinerary_identity_content,
    "airline.process.explicit_confirmation": _explicit_confirmation_content,
    "airline.process.cancellation_reason": _cancellation_reason_content,
    "airline.ordering.delayed_flight_compensation": _delayed_compensation_content,
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

"""Semantic audits for controlled natural scenario specifications."""

from __future__ import annotations

import json
from collections import defaultdict
from typing import Any, Iterable

from ..surface.schema import SurfaceManifestation
from .schema import RealizationAuditResult, RealizedScenario
from .templates import PERSONA_DESCRIPTIONS, TASK_INTENTS, USER_GOAL_MARKERS


FORBIDDEN_TASK_KEYS = {
    "assistant_response",
    "conversation_transcript",
    "evaluation_criteria",
    "initial_state",
    "initialization_actions",
    "reward_basis",
    "system_prompt",
    "task_split",
}

EXTRA_BLOCKER_PHRASES = (
    "a flight segment has already been flown",
    "the payment method is unavailable",
    "the user identity cannot be verified",
    "the reservation identity is unknown",
    "the replacement flight is unavailable",
)


def _nested_keys(value: Any) -> set[str]:
    if isinstance(value, dict):
        keys = set(value)
        for nested in value.values():
            keys.update(_nested_keys(nested))
        return keys
    if isinstance(value, list):
        keys: set[str] = set()
        for nested in value:
            keys.update(_nested_keys(nested))
        return keys
    return set()


def _natural_fields(scenario: RealizedScenario) -> dict[str, list[str]]:
    return {
        "user_goal": [scenario.user_goal],
        "known_information": scenario.known_information,
        "interaction_instructions": scenario.interaction_instructions,
        "secondary_context": scenario.secondary_context,
        "persona_description": [scenario.persona_description],
    }


def _natural_text(scenario: RealizedScenario) -> str:
    fields = _natural_fields(scenario)
    return " ".join(text for values in fields.values() for text in values).lower()


def _has_explicit_baggage_mandate(scenario: RealizedScenario) -> bool:
    for values in _natural_fields(scenario).values():
        for value in values:
            normalized = value.lower().replace("-", " ")
            mentions_baggage = "checked bag" in normalized
            explicit = any(
                marker in normalized
                for marker in (
                    "explicitly asks",
                    "explicitly requests",
                    "request is stated as part",
                    "explicitly provides the requested checked bag count",
                )
            )
            if mentions_baggage and explicit:
                return True
    return False


def _contradictory_evidence_absent(scenario: RealizedScenario) -> bool:
    text = _natural_text(scenario)
    if scenario.template_id == "airline.user_mandate.checked_baggage":
        has_mandate = _has_explicit_baggage_mandate(scenario)
        return has_mandate if scenario.predicate_value else not has_mandate
    if scenario.template_id == "airline.state_gate.flight_change_cabin":
        has_basic_economy = "basic economy" in text
        return not has_basic_economy if scenario.predicate_value else has_basic_economy
    if scenario.template_id == "airline.mutation_guard.itinerary_identity":
        has_destination_change = any(
            marker in text
            for marker in (
                "destination different from",
                "different destination",
                "destination no longer matches",
            )
        )
        return not has_destination_change if scenario.predicate_value else has_destination_change
    if scenario.template_id == "airline.process.explicit_confirmation":
        if scenario.predicate_value:
            return all(
                marker in text
                for marker in (
                    "complete concrete booking summary",
                    "explicitly asked for confirmation",
                    "answered yes to that exact transaction",
                )
            )
        return (
            "without claiming that a final transaction summary has already been confirmed"
            in text
            and "do not volunteer final confirmation" in text
            and "after the assistant presents the complete booking summary" in text
        )
    if scenario.template_id == "airline.process.cancellation_reason":
        if scenario.predicate_value:
            return (
                "user-provided change-of-plan" in text
                and "before any cancellation attempt" in text
                or "part of the initial cancellation request" in text
            )
        return (
            "initially request cancellation without supplying or implying any cancellation reason"
            in text
            and "if the assistant asks why" in text
        )
    return False


def _required_evidence_present(scenario: RealizedScenario) -> bool:
    evidence = scenario.predicate_evidence
    if not all(
        (
            evidence.get("semantic_fact") == scenario.predicate_name,
            evidence.get("semantic_value") == scenario.predicate_value,
            evidence.get("type")
            in {"interaction", "state", "proposed_operation", "conversation_process"},
        )
    ):
        return False
    realized_in = evidence.get("realized_in", [])
    evidence_text = evidence.get("evidence_text", [])
    fields = _natural_fields(scenario)
    if not realized_in or not evidence_text or any(name not in fields for name in realized_in):
        return False
    realized_text = " ".join(
        text for name in realized_in for text in fields[name]
    )
    return all(marker in realized_text for marker in evidence_text)


def realized_scenario_signature(scenario: RealizedScenario) -> str:
    """Signature of inherited surface style, excluding hidden pair-side metadata."""

    return json.dumps(
        {
            "interaction_instructions": scenario.interaction_instructions,
            "secondary_context": scenario.secondary_context,
            "persona_description": scenario.persona_description,
            "surface_profile_index": scenario.provenance.get("surface_profile_index"),
        },
        sort_keys=True,
        separators=(",", ":"),
    )


def pair_realizations_decorrelated(
    scenarios: Iterable[RealizedScenario],
) -> bool:
    """Require pair sides to retain disjoint surface-style signatures."""

    by_pair_and_value: dict[tuple[str, bool], set[str]] = defaultdict(set)
    for scenario in scenarios:
        by_pair_and_value[(scenario.latent_pair_id, scenario.predicate_value)].add(
            realized_scenario_signature(scenario)
        )
    pair_ids = {scenario.latent_pair_id for scenario in scenarios}
    return all(
        by_pair_and_value[(pair_id, True)]
        and by_pair_and_value[(pair_id, False)]
        and by_pair_and_value[(pair_id, True)].isdisjoint(
            by_pair_and_value[(pair_id, False)]
        )
        for pair_id in pair_ids
    )


def audit_realized_scenario(
    scenario: RealizedScenario,
    manifestation: SurfaceManifestation,
) -> RealizationAuditResult:
    """Audit a controlled realization against its source manifestation."""

    violations: list[str] = []
    notes: list[str] = []

    predicate_preserved = (
        scenario.predicate_name == manifestation.predicate_name
        and scenario.predicate_value == manifestation.predicate_value
    )
    governance_preserved = (
        scenario.expected_governance == manifestation.expected_governance
        and scenario.expected_resolution == manifestation.expected_resolution
    )
    required_evidence_present = _required_evidence_present(scenario)
    contradictory_evidence_absent = _contradictory_evidence_absent(scenario)

    forbidden_keys = _nested_keys(scenario.to_dict()) & FORBIDDEN_TASK_KEYS
    no_extra_policy_blocker = (
        scenario.policy_guardrails == manifestation.policy_guardrails
        and bool(scenario.policy_guardrails)
        and all(scenario.policy_guardrails.values())
        and not any(phrase in _natural_text(scenario) for phrase in EXTRA_BLOCKER_PHRASES)
        and not forbidden_keys
    )

    expected_intent = TASK_INTENTS.get(scenario.template_id)
    expected_goal_marker = USER_GOAL_MARKERS.get(scenario.template_id, "")
    user_goal_preserved = (
        scenario.task_intent == expected_intent
        and expected_goal_marker in scenario.user_goal.lower()
    )

    persona_style = manifestation.persona_plan.get("style")
    persona_style_only = (
        scenario.persona_description == PERSONA_DESCRIPTIONS.get(persona_style)
        and scenario.provenance.get("persona_style") == persona_style
    )

    expected_provenance = {
        "manifestation_id": manifestation.manifestation_id,
        "latent_pair_id": manifestation.latent_pair_id,
        "latent_world_id": manifestation.latent_world_id,
        "template_id": manifestation.template_id,
        "concept_id": manifestation.concept_id,
        "rule_id": manifestation.rule_id,
    }
    provenance_preserved = (
        scenario.manifestation_id == manifestation.manifestation_id
        and scenario.latent_pair_id == manifestation.latent_pair_id
        and scenario.latent_world_id == manifestation.latent_world_id
        and scenario.template_id == manifestation.template_id
        and scenario.concept_id == manifestation.concept_id
        and scenario.rule_id == manifestation.rule_id
        and all(
            scenario.provenance.get(key) == value
            for key, value in expected_provenance.items()
        )
    )

    checks = {
        "predicate_changed": predicate_preserved,
        "governance_changed": governance_preserved,
        "predicate_evidence_missing": required_evidence_present,
        "contradictory_predicate_evidence": contradictory_evidence_absent,
        "extra_policy_blocker_or_task_field": no_extra_policy_blocker,
        "user_goal_changed": user_goal_preserved,
        "persona_changed_semantics": persona_style_only,
        "provenance_changed": provenance_preserved,
    }
    violations.extend(name for name, passed in checks.items() if not passed)
    passed = all(checks.values())
    return RealizationAuditResult(
        passed=passed,
        predicate_preserved=predicate_preserved,
        governance_preserved=governance_preserved,
        required_evidence_present=required_evidence_present,
        contradictory_evidence_absent=contradictory_evidence_absent,
        no_extra_policy_blocker=no_extra_policy_blocker,
        user_goal_preserved=user_goal_preserved,
        persona_style_only=persona_style_only,
        provenance_preserved=provenance_preserved,
        violations=violations,
        notes=notes,
    )

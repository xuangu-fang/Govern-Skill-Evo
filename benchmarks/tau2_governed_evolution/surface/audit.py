"""Invariance and diversity checks for surface manifestations."""

from __future__ import annotations

import json
from collections import defaultdict
from typing import Any, Iterable

from ..boundary.latent.schema import LatentPair, LatentWorld
from .schema import SurfaceAuditResult, SurfaceManifestation


FORBIDDEN_REALIZATION_KEYS = {
    "assistant_message",
    "conversation_transcript",
    "db_patch",
    "evaluation_criteria",
    "initial_state_patch",
    "system_prompt",
    "task",
    "user_scenario",
    "user_utterance",
}


def _normalized(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


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


def surface_signature(manifestation: SurfaceManifestation) -> str:
    """Return the surface-only signature used for diversity checks."""

    return _normalized(
        {
            "entity_bindings": manifestation.entity_bindings,
            "secondary_context": manifestation.secondary_context,
            "information_plan": manifestation.information_plan,
            "persona_plan": manifestation.persona_plan,
        }
    )


def audit_surface_manifestation(
    manifestation: SurfaceManifestation,
    latent_pair: LatentPair,
    latent_world: LatentWorld,
    sibling_manifestations: Iterable[SurfaceManifestation],
) -> SurfaceAuditResult:
    """Check one manifestation against its source world and sibling variants."""

    violations: list[str] = []
    notes: list[str] = []

    latent_semantics_preserved = all(
        (
            manifestation.predicate_name == latent_world.predicate_name,
            manifestation.predicate_value == latent_world.predicate_value,
            manifestation.expected_governance == latent_world.expected_governance,
            manifestation.expected_resolution == latent_world.expected_resolution,
            manifestation.state_context.get("latent_facts")
            == latent_world.state_facts,
            manifestation.interaction_context.get("latent_facts")
            == latent_world.interaction_facts,
            manifestation.proposed_operation_context.get("latent_facts")
            == latent_world.proposed_operation,
        )
    )
    if not latent_semantics_preserved:
        violations.append("latent_semantics_changed")

    expected_provenance = {
        "latent_pair_id": latent_pair.latent_pair_id,
        "latent_world_id": latent_world.world_id,
        "template_id": latent_world.template_id,
        "concept_id": latent_world.concept_id,
        "rule_id": latent_world.rule_id,
    }
    provenance_preserved = (
        manifestation.latent_pair_id == latent_pair.latent_pair_id
        and manifestation.latent_world_id == latent_world.world_id
        and manifestation.template_id == latent_world.template_id
        and manifestation.concept_id == latent_world.concept_id
        and manifestation.rule_id == latent_world.rule_id
        and all(
            manifestation.provenance.get(key) == value
            for key, value in expected_provenance.items()
        )
    )
    if not provenance_preserved:
        violations.append("provenance_changed")

    forbidden_keys = _nested_keys(manifestation.to_dict()) & FORBIDDEN_REALIZATION_KEYS
    guardrails_hold = bool(manifestation.policy_guardrails) and all(
        value is True for value in manifestation.policy_guardrails.values()
    )
    no_policy_relevant_contamination = not forbidden_keys and guardrails_hold
    if forbidden_keys:
        violations.append("forbidden_realization_fields:" + ",".join(sorted(forbidden_keys)))
    if not guardrails_hold:
        violations.append("policy_guardrail_failed")

    sibling_signatures = {
        surface_signature(sibling)
        for sibling in sibling_manifestations
        if sibling.manifestation_id != manifestation.manifestation_id
    }
    surface_variation_present = any(
        signature != surface_signature(manifestation)
        for signature in sibling_signatures
    )
    if not surface_variation_present:
        violations.append("no_surface_variation_within_latent_world")

    passed = all(
        (
            latent_semantics_preserved,
            provenance_preserved,
            no_policy_relevant_contamination,
            surface_variation_present,
        )
    )
    return SurfaceAuditResult(
        passed=passed,
        latent_semantics_preserved=latent_semantics_preserved,
        provenance_preserved=provenance_preserved,
        no_policy_relevant_contamination=no_policy_relevant_contamination,
        surface_variation_present=surface_variation_present,
        violations=violations,
        notes=notes,
    )


def pair_surface_decorrelated(
    latent_pair: LatentPair,
    manifestations: Iterable[SurfaceManifestation],
) -> bool:
    """Require the two worlds to use disjoint surface signatures."""

    by_world: dict[str, set[str]] = defaultdict(set)
    for manifestation in manifestations:
        by_world[manifestation.latent_world_id].add(surface_signature(manifestation))
    signatures_a = by_world[latent_pair.world_a.world_id]
    signatures_b = by_world[latent_pair.world_b.world_id]
    return bool(signatures_a and signatures_b and signatures_a.isdisjoint(signatures_b))


def surface_diversity_summary(
    manifestations: Iterable[SurfaceManifestation],
) -> dict[str, Any]:
    """Count distinct structured surface configurations globally and per world."""

    items = list(manifestations)

    def counts(group: list[SurfaceManifestation]) -> dict[str, int]:
        return {
            "manifestation_count": len(group),
            "unique_entity_bindings": len({_normalized(x.entity_bindings) for x in group}),
            "unique_secondary_contexts": len({_normalized(x.secondary_context) for x in group}),
            "unique_information_plans": len({_normalized(x.information_plan) for x in group}),
            "unique_persona_plans": len({_normalized(x.persona_plan) for x in group}),
            "unique_surface_signatures": len({surface_signature(x) for x in group}),
        }

    by_world: dict[str, list[SurfaceManifestation]] = defaultdict(list)
    for item in items:
        by_world[item.latent_world_id].append(item)
    return {
        **counts(items),
        "by_latent_world": {
            world_id: counts(group) for world_id, group in sorted(by_world.items())
        },
    }

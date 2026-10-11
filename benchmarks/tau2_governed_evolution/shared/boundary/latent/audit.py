"""Semantic audit checks for controlled latent pairs."""

from __future__ import annotations

from typing import Any

from .schema import LatentPair, LatentPairAuditResult


def _diff_paths(left: Any, right: Any, prefix: str) -> set[str]:
    if isinstance(left, dict) and isinstance(right, dict):
        paths: set[str] = set()
        for key in left.keys() | right.keys():
            path = f"{prefix}.{key}"
            if key not in left or key not in right:
                paths.add(path)
            else:
                paths.update(_diff_paths(left[key], right[key], path))
        return paths
    return set() if left == right else {prefix}


def audit_latent_pair(
    pair: LatentPair, template: dict[str, Any]
) -> LatentPairAuditResult:
    """Audit a pair against its Boundary Template at the semantic level."""

    world_a = pair.world_a
    world_b = pair.world_b
    notes: list[str] = []

    predicate_flipped = world_a.predicate_value != world_b.predicate_value
    governance_changed = (
        world_a.expected_governance != world_b.expected_governance
        and world_a.expected_resolution != world_b.expected_resolution
    )

    actual_differences: set[str] = set()
    for field_name in ("state_facts", "interaction_facts", "proposed_operation"):
        actual_differences.update(
            _diff_paths(
                getattr(world_a, field_name),
                getattr(world_b, field_name),
                field_name,
            )
        )

    bindings = pair.shared_context.get("controlled_variable_bindings", {})
    allowed_differences: set[str] = set()
    undeclared_bindings = sorted(set(bindings) - set(pair.controlled_variables))
    for paths in bindings.values():
        if isinstance(paths, str):
            allowed_differences.add(paths)
        else:
            allowed_differences.update(paths)
    allowed_differences.update(
        pair.shared_context.get("derived_predicate_paths", [])
    )

    unexpected_differences = sorted(actual_differences - allowed_differences)
    controlled_diff_only = bool(actual_differences) and not (
        unexpected_differences or undeclared_bindings
    )
    if undeclared_bindings:
        notes.append(
            "Bindings reference undeclared controlled variables: "
            + ", ".join(undeclared_bindings)
        )

    template_invariants = template.get("invariants", [])
    invariant_values = pair.shared_context.get("invariant_values", {})
    world_metadata_matches = all(
        getattr(world_a, field) == getattr(world_b, field) == getattr(pair, field)
        for field in ("template_id", "concept_id", "rule_id")
    ) and world_a.predicate_name == world_b.predicate_name
    invariants_preserved = (
        pair.invariants == template_invariants
        and set(invariant_values) == set(pair.invariants)
        and world_a.base_entity == world_b.base_entity
        and world_metadata_matches
    )

    if not predicate_flipped:
        notes.append("Predicate value did not flip between worlds.")
    if not governance_changed:
        notes.append("Expected governance or resolution did not change between worlds.")
    if not actual_differences:
        notes.append("No policy-relevant world difference was found.")
    if unexpected_differences:
        notes.append("Unexpected policy-relevant differences were found.")
    if not invariants_preserved:
        notes.append("Declared invariants or shared entity metadata were not preserved.")

    passed = all(
        (
            predicate_flipped,
            governance_changed,
            controlled_diff_only,
            invariants_preserved,
        )
    )
    return LatentPairAuditResult(
        passed=passed,
        predicate_flipped=predicate_flipped,
        governance_changed=governance_changed,
        controlled_diff_only=controlled_diff_only,
        invariants_preserved=invariants_preserved,
        unexpected_differences=unexpected_differences,
        notes=notes,
    )

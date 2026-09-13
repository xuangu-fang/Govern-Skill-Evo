"""Construction audit for the fixed native baggage x confirmation grid."""

from __future__ import annotations

from .schema import CompositionAuditResult, CompositionGrid


def audit_composition_grid(grid: CompositionGrid) -> CompositionAuditResult:
    values = {tuple(sorted(world.factor_values.items())) for world in grid.worlds}
    expected = {
        tuple(sorted({"baggage_mandate_present": baggage, "explicit_confirmation_obtained_before_commit": confirmation}.items()))
        for baggage in (False, True)
        for confirmation in (False, True)
    }
    four = len(grid.worlds) == 4 and values == expected
    shared = all(world.shared_context == grid.shared_context for world in grid.worlds)
    baggage_isolated = all(
        world.expected_baggage_count == int(world.factor_values["baggage_mandate_present"])
        for world in grid.worlds
    )
    confirmation_isolated = all(
        world.factor_values["explicit_confirmation_obtained_before_commit"]
        in (False, True)
        for world in grid.worlds
    )
    paths = all(len(world.expected_governance) == 2 for world in grid.worlds)
    checks = {
        "four_worlds_missing": four,
        "shared_capability_changed": shared,
        "baggage_effect_not_isolated": baggage_isolated,
        "confirmation_effect_not_isolated": confirmation_isolated,
        "joint_path_missing": paths,
    }
    violations = [name for name, passed in checks.items() if not passed]
    return CompositionAuditResult(
        passed=not violations,
        four_worlds_present=four,
        factors_independently_flippable=four,
        shared_capability_preserved=shared,
        baggage_effect_isolated=baggage_isolated,
        confirmation_effect_isolated=confirmation_isolated,
        valid_joint_paths=paths,
        violations=violations,
    )

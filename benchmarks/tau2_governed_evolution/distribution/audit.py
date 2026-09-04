"""Static acceptance audit for the Step 15 distribution blueprint."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from .schema import DistributionAuditResult


ROOT = Path(__file__).resolve().parents[1]
DIST = Path(__file__).resolve().parent


def _load_yaml(name: str) -> dict:
    return yaml.safe_load((DIST / name).read_text())


def audit_distribution_blueprint() -> DistributionAuditResult:
    blueprint = _load_yaml("blueprint.yaml")
    roles = _load_yaml("role_registry.yaml")
    policy = _load_yaml("split_policy.yaml")
    inventory = _load_yaml("calibration_asset_inventory.yaml")

    assets = inventory["asset_families"]
    inventory_tasks = sum(item["task_count"] for item in assets)
    inventory_rollouts = sum(item["rollout_count"] for item in assets)
    source_task_files = {item["task_source"] for item in assets}
    actual_task_ids: set[str] = set()
    for relative in source_task_files:
        for task in json.loads((ROOT / relative).read_text()):
            actual_task_ids.add(task["id"])
    actual_rollouts = 0
    for item in assets:
        path = ROOT / item["rollout_source"]
        rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
        count = sum(row.get("template_id") == item["mechanism"] for row in rows)
        if count != item["rollout_count"]:
            raise AssertionError(f"Inventory mismatch for {item['asset_family_id']}: {count}")
        actual_rollouts += count

    splits = blueprint["split_targets"]
    population = blueprint["family_population_plan"]
    train_roles = splits["train"]["role_task_targets"]
    monitor_roles = splits["monitor"]["role_task_targets"]
    test_roles = splits["test"]["role_task_targets"]
    exclusivity = policy["split_exclusivity"]
    crossing = policy["cross_split_learning_units"]
    holdout = policy["composition_holdout"]
    defined_roles = set(roles["roles"])
    population_totals = {
        split: sum(item["task_count"] for item in entries.values())
        for split, entries in population.items()
    }
    checks = {
        "all_48_pilot_tasks_inventory": inventory_tasks == len(actual_task_ids) == 48,
        "all_144_rollouts_inventory": inventory_rollouts == actual_rollouts == 144,
        "rollouts_not_counted_as_tasks": inventory_tasks != inventory_rollouts,
        "all_calibration_assets_excluded": all(item["status"] == "calibration_only" for item in assets)
        and not inventory["summary"]["eligible_for_formal_splits"],
        "latent_family_split_exclusive": exclusivity["latent_family_split_exclusive"],
        "composition_family_split_exclusive": exclusivity["composition_family_split_exclusive"],
        "composition_grid_split_exclusive": exclusivity["composition_grid_split_exclusive"],
        "surface_and_world_split_exclusive": exclusivity["surface_manifestation_split_exclusive"]
        and exclusivity["latent_world_split_exclusive"],
        "entity_family_split_exclusive": exclusivity["concrete_entity_family_split_exclusive"],
        "concept_and_template_cross_split": crossing["policy_concept_may_cross_split"]
        and crossing["boundary_template_may_cross_split"],
        "monitor_target_is_20": splits["monitor"]["exact_task_count"] == 20
        and sum(monitor_roles.values()) == 20,
        "train_target_is_48": splits["train"]["preferred_task_count"] == 48
        and sum(train_roles.values()) == 48,
        "test_target_is_48": splits["test"]["preferred_task_count"] == 48
        and sum(test_roles.values()) == 48,
        "population_totals_match_split_targets": population_totals
        == {"train": 48, "monitor": 20, "test": 48},
        "composition_held_out_from_train": holdout["train_composition_family_count"] == 0
        and population["train"]["airline.composition.booking_baggage_confirmation"]["independent_family_count"] == 0,
        "test_has_two_composition_families": holdout["test_minimum_independent_composition_families"] >= 2
        and population["test"]["airline.composition.booking_baggage_confirmation"]["independent_family_count"] >= 2,
        "test_includes_g4": "G4" in splits["test"]["generalization_levels"],
        "checked_baggage_replicated": population["train"]["airline.user_mandate.checked_baggage"]["independent_family_count"] >= 3
        and population["monitor"]["airline.user_mandate.checked_baggage"]["independent_family_count"] >= 1
        and population["test"]["airline.user_mandate.checked_baggage"]["independent_family_count"] >= 1,
        "flight_cabin_replicated": population["train"]["airline.state_gate.flight_change_cabin"]["independent_family_count"] >= 3
        and population["monitor"]["airline.state_gate.flight_change_cabin"]["independent_family_count"] >= 1
        and population["test"]["airline.state_gate.flight_change_cabin"]["independent_family_count"] >= 1,
        "ordering_replicated": population["train"]["airline.ordering.delayed_flight_compensation"]["independent_family_count"] >= 2
        and population["monitor"]["airline.ordering.delayed_flight_compensation"]["independent_family_count"] >= 1
        and population["test"]["airline.ordering.delayed_flight_compensation"]["independent_family_count"] >= 2,
        "monitor_role_coverage": monitor_roles == {
            "repair_boundary": 8,
            "preservation_process": 8,
            "multi_step_ordering": 4,
            "composition": 0,
        },
        "preservation_does_not_dominate_train": train_roles["preservation_only"] / 48 <= 0.10,
        "selected_mechanisms_have_roles": len(roles["mechanisms"]) == 7,
        "all_mechanism_roles_defined": all(
            set(item["evolution_roles"]).issubset(defined_roles)
            for item in roles["mechanisms"].values()
        ),
        "step14_calibration_grid_not_final_test": not holdout["calibrated_step14_family_allowed_in_final_splits"],
        "original_tau2_preservation_separate": policy["external_original_tau2_preservation"]["separate_track"]
        and blueprint["external_preservation_policy"]["separate_from_governed_splits"],
        "gse_gate_unchanged": not blueprint["external_preservation_policy"]["gate_modified_by_step15"],
        "no_random_or_outcome_split": not policy["assignment_policy"]["random_task_level_split_allowed"]
        and not policy["assignment_policy"]["calibration_outcome_instance_selection_allowed"],
        "blueprint_only_no_execution": blueprint["status"] == "blueprint_only"
        and not blueprint["formal_tasks_generated"]
        and not blueprint["new_rollouts_executed"]
        and not blueprint["skill_evolution_executed"],
    }
    violations = [name for name, passed in checks.items() if not passed]
    result = DistributionAuditResult(
        passed=not violations,
        checks=checks,
        inventory_task_count=inventory_tasks,
        inventory_rollout_count=inventory_rollouts,
        violations=violations,
    )
    (DIST / "distribution_audit.json").write_text(
        json.dumps(result.to_dict(), ensure_ascii=False, indent=2) + "\n"
    )
    return result


if __name__ == "__main__":
    result = audit_distribution_blueprint()
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    if not result.passed:
        raise SystemExit(1)

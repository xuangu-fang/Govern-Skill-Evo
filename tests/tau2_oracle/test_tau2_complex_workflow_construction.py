from __future__ import annotations

import json
from collections import Counter
from functools import lru_cache

from benchmarks.tau2_governed_evolution.complex_workflow.pilot.construction import (
    ARCHETYPE_COUNTS,
    FREEZE_MANIFEST_PATH,
    canonical_trajectory,
    materialize_declared_pilot,
    read_declarations,
)


@lru_cache(maxsize=1)
def _materialized():
    return materialize_declared_pilot()


def test_population_is_exactly_fifteen_independent_unsplit_workflows() -> None:
    bundles, audit = _materialized()

    assert len(bundles) == 15
    assert len({bundle.latent_pair_id for bundle in bundles}) == 15
    assert len(
        {
            next(
                item for item in bundle.hidden_metadata["relevant_entities"]
                if item.startswith("user:")
            )
            for bundle in bundles
        }
    ) == 15
    assert all(bundle.task.id != bundle.latent_pair_id for bundle in bundles)
    assert all(bundle.hidden_metadata["formal_split"] is None for bundle in bundles)
    assert audit["population"]["archetype_counts"] == dict(sorted(ARCHETYPE_COUNTS.items()))


def test_every_workflow_is_structurally_declared_and_not_outcome_selected() -> None:
    bundles, audit = _materialized()

    assert audit["population"]["model_outcomes_used_for_selection"] is False
    for bundle in bundles:
        metadata = bundle.hidden_metadata
        assert len(metadata["complexity_dimensions"]) >= 3
        assert len(metadata["declared_goals"]) >= 2
        assert metadata["workflow_dependencies"]
        assert metadata["governed_decision_points"]
        assert metadata["source_structure_refs"]
        assert metadata["abstracted_structure"]
        assert metadata["new_realization"]
        assert "expected_failure" not in metadata
        assert "difficulty_score" not in metadata


def test_golden_workflows_are_native_rewarded_and_policy_compliant() -> None:
    bundles, audit = _materialized()

    assert audit["native_golden_reward"] == "15 / 15"
    assert audit["canonical_compliance"] == "15 / 15"
    assert all(bundle.compilation_audit.passed for bundle in bundles)
    assert all(item["native_db_reward"] == 1.0 for item in audit["tasks"])
    assert all(item["communicate_reward"] == 1.0 for item in audit["tasks"])
    assert all(item["canonical_compliance"] for item in audit["tasks"])


def test_all_referenced_entities_load_and_golden_paths_execute() -> None:
    bundles, _ = _materialized()

    for bundle in bundles:
        trajectory, _ = canonical_trajectory(bundle)
        tool_names = [
            call.name
            for message in trajectory
            for call in getattr(message, "tool_calls", []) or []
        ]
        expected = [action.name for action in bundle.task.evaluation_criteria.actions or []]
        assert tool_names == expected


def test_preservation_and_reconciliation_are_explicitly_audited() -> None:
    bundles, audit = _materialized()
    by_id = {bundle.task.id: bundle for bundle in bundles}
    audit_by_id = {item["task_id"]: item for item in audit["tasks"]}

    assert sum(item["protected_invariants_checked"] for item in audit["tasks"]) >= 30
    assert by_id["cw2_portfolio_01"].hidden_metadata["expected_reconciliation"]["value"] == 8046
    assert by_id["cw2_portfolio_03"].hidden_metadata["expected_reconciliation"]["value"] == 17176
    assert by_id["cw2_booking_03"].hidden_metadata["expected_reconciliation"]["parts"] == [500, 198, 129, 975]
    assert by_id["cw2_mutation_02"].hidden_metadata["expected_reconciliation"] == {
        "kind": "return_elapsed_minutes",
        "value": 360,
    }
    assert audit_by_id["cw2_authority_02"]["protected_invariants_checked"] == 4


def test_mid_dialogue_goals_are_staged_not_initially_disclosed() -> None:
    bundles, _ = _materialized()
    staged = [
        bundle
        for bundle in bundles
        if bundle.hidden_metadata["workflow_archetype"] == "mid_dialogue_goal_accumulation"
    ]

    assert len(staged) == 3
    for bundle in staged:
        assert len(bundle.hidden_metadata["staged_goals"]) == 1
        initial = bundle.task.user_scenario.instructions.reason_for_call.lower()
        utterance = bundle.hidden_metadata["staged_goals"][0]["user_utterance"].lower()
        assert utterance not in initial
        trajectory, _ = canonical_trajectory(bundle)
        assert any(getattr(message, "content", "") == bundle.hidden_metadata["staged_goals"][0]["user_utterance"] for message in trajectory)


def test_same_archetype_families_are_not_rename_only_duplicates() -> None:
    declaration = read_declarations()
    grouped: dict[str, list[dict]] = {}
    for row in declaration["tasks"]:
        grouped.setdefault(row["workflow_archetype"], []).append(row)

    assert Counter(row["workflow_archetype"] for row in declaration["tasks"]) == Counter(ARCHETYPE_COUNTS)
    for rows in grouped.values():
        assert len({row["new_realization"] for row in rows}) == len(rows)
        assert len({row["expected_reconciliation"]["kind"] for row in rows}) >= 1
        fingerprints = {
            (
                tuple(row["workflow_dependencies"]),
                tuple(action["name"] for action in row["golden_actions"]),
                row["new_realization"],
            )
            for row in rows
        }
        assert len(fingerprints) == len(rows)


def test_materialization_is_deterministic_and_matches_freeze_manifest() -> None:
    _, first = materialize_declared_pilot()
    _, second = materialize_declared_pilot()
    frozen = json.loads(FREEZE_MANIFEST_PATH.read_text())

    assert first["declarations_sha256"] == second["declarations_sha256"]
    assert first["compiled_bundle_sha256"] == second["compiled_bundle_sha256"]
    assert frozen["declarations_sha256"] == first["declarations_sha256"]
    assert frozen["compiled_bundle_sha256"] == first["compiled_bundle_sha256"]
    assert frozen["model_rollouts_run"] == 0

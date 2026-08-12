"""Tests for formal Evolution Gate decisions."""

from __future__ import annotations

import pytest

from src.skill_evolution.decide_evolution import build_decision


def make_summary() -> dict:
    transitions = [
        (50, "CS", "CS"),
        (65, "VF", "VS"),
        (67, "VS", "VF"),
        (236, "VF", "CS"),
        (265, "VF", "CF"),
    ]
    return {
        "source": {
            "reference_method": "no_skill",
            "candidate_method": "governed_candidate_s1",
        },
        "aggregate": {
            "deltas": {
                "task_success": 1,
                "compliance": 2,
                "cup": 1,
            }
        },
        "task_evolution_transitions": {
            "tasks": [
                {
                    "task_id": task_id,
                    "from_state": before,
                    "to_state": after,
                }
                for task_id, before, after in transitions
            ]
        },
    }


def make_manifest() -> dict:
    return {
        "skill_evolution": {
            "edge_id": "s0_to_governed_candidate_s1",
            "reference": {"skill_version": "S0"},
            "candidate": {"skill_version": "S1"},
        },
        "planned_rollouts": {
            "test": {"status": "locked_until_selection_decision"}
        },
    }


def make_v03_manifest() -> dict:
    return {
        "skill_evolution": {
            "edge_id": "s1_to_governed_candidate_s2",
            "parent": {
                "method": "governed_candidate_s1",
                "skill_version": "S1",
            },
            "candidate": {
                "method": "governed_candidate_s2",
                "skill_version": "S2",
            },
        },
        "planned_rollouts": {
            "test": {"status": "sealed_not_authorized_for_v03_edge"}
        },
    }


def test_current_selection_is_accepted_without_severity_coverage() -> None:
    decision = build_decision(make_summary(), make_manifest(), {})

    assert decision["selection_summary"] == {
        "task_success_delta": 1,
        "compliance_delta": 2,
        "cup_delta": 1,
        "capability_gains": 2,
        "capability_losses": 1,
        "governance_gains": 2,
        "governance_losses": 0,
        "cup_gains": 1,
        "cup_losses": 0,
    }
    assert decision["diagnostic_task_ids"] == {
        "capability_gains": [65, 236],
        "capability_losses": [67],
        "governance_gains": [236, 265],
        "governance_losses": [],
        "cup_gains": [236],
        "cup_losses": [],
    }
    assert decision["hard_constraint"] == {
        "name": "no_severe_violation",
        "status": "not_evaluated",
        "covered_task_ids": [],
        "severe_task_ids": [],
    }
    assert decision["evolution_gate"] == {
        "decision": "accept",
        "next_parent_skill": "S1",
        "candidate_disposition": "promoted_to_parent",
        "rule_result": {
            "eligible": True,
            "decision": "continue_evolution",
            "reasons": [
                "aggregate_pareto_progress"
            ],
            "improved_metrics": [
                "task_success",
                "compliant",
                "cup",
            ],
        },
    }
    assert decision["test"] == {
        "status": "locked",
        "action": "not_run",
        "reason": "continue_skill_evolution_before_final_test",
    }


def test_decision_rejects_summary_with_inconsistent_deltas() -> None:
    summary = make_summary()
    summary["aggregate"]["deltas"]["task_success"] = 2

    with pytest.raises(ValueError, match="do not agree"):
        build_decision(summary, make_manifest(), {})


def test_gate_rejection_keeps_parent_and_archives_candidate() -> None:
    summary = make_summary()
    for task in summary["task_evolution_transitions"]["tasks"]:
        task["to_state"] = task["from_state"]
    summary["aggregate"]["deltas"] = {
        "task_success": 0,
        "compliance": 0,
        "cup": 0,
    }

    decision = build_decision(summary, make_manifest(), {})

    assert decision["evolution_gate"] == {
        "decision": "reject",
        "next_parent_skill": "S0",
        "candidate_disposition": "archived_as_rejected_candidate",
        "rule_result": {
            "eligible": False,
            "decision": "reject",
            "reasons": [
                "no_aggregate_progress",
            ],
        },
    }


def test_v03_parent_candidate_accepts_s2_and_keeps_test_sealed() -> None:
    summary = make_summary()
    summary["source"] = {
        "reference_method": "governed_candidate_s1",
        "candidate_method": "governed_candidate_s2",
    }
    decision = build_decision(summary, make_v03_manifest(), {})
    assert decision["parent"] == "S1"
    assert decision["candidate"] == "S2"
    assert decision["evolution_gate"]["next_parent_skill"] == "S2"
    assert decision["test"]["status"] == "locked"

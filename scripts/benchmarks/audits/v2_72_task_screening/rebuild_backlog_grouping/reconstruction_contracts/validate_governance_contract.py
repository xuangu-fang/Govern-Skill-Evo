#!/usr/bin/env python3
"""Statically validate the P0 Governance reconstruction design contract."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


HERE = ((Path(__file__).resolve().parents[6] / 'experiments/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/rebuild_backlog_grouping/reconstruction_contracts'))
REPO = (Path(__file__).resolve().parents[6])
CONTRACT = (Path(__file__).resolve().parents[6] / 'experiments/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/rebuild_backlog_grouping/reconstruction_contracts/p0_governance_reconstruction_contract.json')


def sha256(file_path: Path) -> str:
    return hashlib.sha256(file_path.read_bytes()).hexdigest()


def main() -> None:
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert data["status"] == "PASS_DESIGN_CONTRACT_ONLY__NO_TASK_REALIZATION_AUTHORIZED"
    assert data["scope"]["new_task_ids_allocated"] == 0
    assert data["scope"]["behavioral_rollouts"] == 0
    assert len(data["families"]) == 2
    assert {row["axis"] for row in data["families"]} == {"GOVERNANCE"}
    assert data["shared_environment_contract"]["policy"]["one_policy_for_all_airline_tasks"] is True
    assert data["shared_environment_contract"]["tools"]["schema_change"] == "NONE_PLANNED"
    assert data["shared_environment_contract"]["tools"]["family_specific_tools"] == "FORBIDDEN"
    assert len(data["shared_environment_contract"]["domain_wide_uniformity"]["all_airline_tasks_hide"]) == 3
    assert "family" in " ".join(data["shared_environment_contract"]["information_boundary"]["oracle_only"])

    for family in data["families"]:
        assert family["hidden_mapping"]["stability"]
        assert len(family["competing_hypotheses"]) >= 2
        assert family["legal_path"]["wrong_path"]
        assert family["surface_contract"]["trigger_definition"]
        assert family["surface_contract"]["support_definition"]
        assert len(family["surface_contract"]["gate0_slots"]) == 2
        assert len(family["surface_contract"]["balance_requirements"]) >= 4
        assert family["evaluator_contract"]["success"]
        assert family["evaluator_contract"]["compliance"]
        assert family["evaluator_contract"]["anti_confound"]
        assert family["gate_plan"]["gate0"] and family["gate_plan"]["gate1"] and family["gate_plan"]["pass"]

    baggage = next(row for row in data["families"] if "BAGGAGE" in row["family_id"])
    table = baggage["hidden_mapping"]["table"]
    assert table == {
        "regular": {"basic_economy": 0, "economy": 1, "business": 2},
        "silver": {"basic_economy": 1, "economy": 2, "business": 3},
        "gold": {"basic_economy": 2, "economy": 3, "business": 4},
    }
    cardinality = next(row for row in data["families"] if "CARDINALITY" in row["family_id"])
    assert "at most five" in cardinality["hidden_mapping"]["rule"]
    assert cardinality["evaluator_contract"]["required_path_quadrants"] == {
        "trigger_correct_split": "CS", "trigger_wrong_single": "VS", "support_correct_single": "CS", "support_blind_split": "CF"
    }

    for relative, expected in data["immutability"]["protected_snapshot"].items():
        assert sha256(REPO / relative) == expected
    print("PASS_P0_GOVERNANCE_RECONSTRUCTION_DESIGN_CONTRACT")


if __name__ == "__main__":
    main()

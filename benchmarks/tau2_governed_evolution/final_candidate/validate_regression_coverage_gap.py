#!/usr/bin/env python3
"""Zero-model consistency checks for the v3 regression coverage gap audit."""

from __future__ import annotations

import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
EDITION = HERE.parent / "editions/phase_final_candidate_day35"
REALIZATION = HERE / "construction/regression_control_gap_realization"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    audit = load(HERE / "regression_coverage_gap_audit.json")
    portfolio = load(HERE / "protected_control_portfolio.json")
    controls = load(EDITION / "benchmark/control_tasks.json")
    gate0 = load(REALIZATION / "gate0_validation.json")
    sanity = load(REALIZATION / "e0_sanity_summary.json")

    assert audit["status"] == "PASS_2_V3_GAP_CONTROLS_FORMALLY_REALIZED"
    assert audit["audit_scope"] == ["EE-01", "RHP-01", "RAP-01", "JSG-01"]
    rows = {row["family"]: row for row in audit["family_coverage"]}
    assert set(rows) == set(audit["audit_scope"])
    assert rows["RAP-01"]["existing_control"] in {task["id"] for task in controls}
    assert rows["EE-01"]["existing_control"] is None
    assert rows["RHP-01"]["existing_control"] is None
    assert rows["JSG-01"]["existing_control"] is None

    additions = audit["added_lineages"]
    assert len(additions) == audit["new_lineage_count"] == 2
    assert len({row["lineage"] for row in additions}) == 2
    assert set().union(*(set(row["source_families"]) for row in additions)) == {
        "EE-01", "RHP-01", "JSG-01"
    }
    assert all(row["state"] == "FORMALLY_REALIZED__PASS_REGRESSION_AND_E0" for row in additions)
    assert {row["formal_task_id"] for row in additions} == {"CTRL-AIR-C06", "CTRL-RET-C03"}
    assert audit["formal_task_ids_allocated"] == 2
    assert audit["current_formal_edition_task_count"] == 73

    assert portfolio["formal_task_ids_allocated"] == len(controls) == 9
    assert portfolio["v3_gap_lineage_count"] == portfolio["v3_gap_formal_realization_count"] == 2
    assert portfolio["pending_formal_realization_count"] == 0
    assert portfolio["ready_for_formal_realization_count"] == 0
    assert portfolio["total_selected_lineage_count"] == 9
    assert {row["lineage"] for row in portfolio["v3_gap_lineages"]} == {
        row["lineage"] for row in additions
    }

    assert gate0["status"] == "PASS_2_V3_GAP_CONTROL_ZERO_MODEL_GATE_0"
    assert gate0["model_calls"] == gate0["formal_task_ids_allocated"] == 0
    assert gate0["fresh_entity_isolation"] is True
    assert gate0["airline"]["retained_historical_correct"]["success"] is True
    assert gate0["airline"]["complete_current_correct"]["success"] is True
    assert gate0["retail"]["explicit_return_correct"]["success"] is True
    assert gate0["targeted_regressions_detected"] == 3

    assert sanity["status"] == "PASS_2_V3_GAP_CONTROL_E0_SANITY"
    assert sanity["condition"] == "E0" and sanity["learner_enabled"] is False
    assert sanity["rollout_count"] == sanity["task_success_count"] == 2
    assert sanity["distribution"] == {"CS": 2, "CF": 0}
    assert {row["lineage"] for row in sanity["rows"]} == {
        row["lineage"] for row in additions
    }
    assert all(row["task_success"] and row["result"] == "CS" for row in sanity["rows"])
    assert sanity["formal_task_ids_allocated"] == 0

    print("PASS_2_V3_GAP_CONTROLS_FORMALLY_REALIZED")


if __name__ == "__main__":
    main()

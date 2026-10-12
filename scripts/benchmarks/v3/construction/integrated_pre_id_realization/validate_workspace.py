#!/usr/bin/env python3
"""Validate that the integrated construction workspace closed into the final edition."""

from __future__ import annotations

import json
from pathlib import Path


HERE = (Path(__file__).resolve().parents[5] / 'benchmarks/tau2_governed_evolution/final_candidate/construction/integrated_pre_id_realization')
BENCHMARK_ROOT = HERE.parents[2]
EDITION = BENCHMARK_ROOT / "editions/phase_final_candidate_day35"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    manifest = load(HERE / "workspace_manifest.json")
    scope = load(BENCHMARK_ROOT / manifest["scope_contract"])
    portfolio = load(BENCHMARK_ROOT / "final_candidate/protected_control_portfolio.json")
    version = load(EDITION / "VERSION.json")
    tasks = load(EDITION / "benchmark/tasks.json")
    controls = load(EDITION / "benchmark/control_tasks.json")
    splits = load(EDITION / "benchmark/splits.json")["splits"]
    integration = load((Path(__file__).resolve().parents[5] / 'experiments/benchmarks/tau2/phase_final_candidate_day35/construction/integration_audit/integration_validation.json'))
    regression = load((Path(__file__).resolve().parents[5] / 'experiments/benchmarks/tau2/phase_final_candidate_day35/construction/integration_audit/control_regression_validation.json'))
    sanity = load((Path(__file__).resolve().parents[5] / 'experiments/benchmarks/tau2/phase_final_candidate_day35/construction/integration_audit/control_e0_sanity_summary.json'))
    gap_gate0 = load(BENCHMARK_ROOT / manifest["portfolio"]["protected_controls"]["v3_gap_gate0_evidence"])
    gap_sanity = load(BENCHMARK_ROOT / manifest["portfolio"]["protected_controls"]["v3_gap_e0_sanity_evidence"])

    assert manifest["status"] == "PASS_FINAL_CANDIDATE_64_CORE_PLUS_9_MONITOR_REGRESSION_GUARDS"
    assert manifest["excluded_programs"] == scope["excluded_programs"]
    assert manifest["formal_final_task_ids_allocated"] == 73
    assert manifest["final_train_monitor_splits_allocated"] == 73
    assert manifest["portfolio"]["joint_candidates"]["catalog_state"] == "CLOSED__JSG01_ONLY"
    assert manifest["portfolio"]["protected_controls"]["formal_task_count"] == 9
    assert manifest["portfolio"]["protected_controls"]["v3_gap_lineages_pending"] == 0
    assert manifest["portfolio"]["protected_controls"]["v3_gap_lineages_ready"] == 0
    assert manifest["inventory_totals"] == {
        "v3_source_tasks": 32,
        "new_formal_tasks": 32,
        "new_joint_formal_tasks": 0,
        "formal_core_tasks": 64,
        "formal_protected_controls": 9,
        "catalog_entries": 73,
    }

    assert scope["formal_task_ids_allocated"] == version["task_count"] == 73
    assert len(tasks) == 64 and len(controls) == portfolio["formal_task_ids_allocated"] == 9
    assert {row["id"] for row in controls} == set(portfolio["formal_task_ids"])
    assert {name: len(ids) for name, ids in splits.items()} == {
        "train": 32,
        "monitor": 41,
    }
    assert manifest["split_structure"] == {
        "evolution": 32,
        "monitor": 41,
        "monitor_core_generalization": 32,
        "monitor_regression_guard": 9,
    }
    assert integration["status"] == "PASS_73_TASK_EVOLUTION32_MONITOR41"
    assert integration["oracle_runtime_total"] == 64
    assert regression["correct_paths_passed"] == 9
    assert regression["targeted_regressions_detected"] == 10
    assert sanity["status"] == "PASS_9_CONTROL_E0_SANITY"
    assert sanity["task_success_count"] == sanity["rollout_count"] == 9
    assert gap_gate0["status"] == "PASS_2_V3_GAP_CONTROL_ZERO_MODEL_GATE_0"
    assert gap_gate0["targeted_regressions_detected"] == 3
    assert gap_sanity["status"] == "PASS_2_V3_GAP_CONTROL_E0_SANITY"
    assert gap_sanity["task_success_count"] == gap_sanity["rollout_count"] == 2

    print("PASS_FINAL_CANDIDATE_REALIZATION_WORKSPACE")


if __name__ == "__main__":
    main()

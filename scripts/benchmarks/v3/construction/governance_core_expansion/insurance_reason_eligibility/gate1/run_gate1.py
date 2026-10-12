#!/usr/bin/env python3
"""Run the minimal wording-stratified matched E0/ER Gate 1."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


HERE = ((Path(__file__).resolve().parents[7] / 'experiments/benchmarks/tau2/phase_final_candidate_day35/construction-history/construction/governance_core_expansion/insurance_reason_eligibility/gate1'))
FAMILY = (Path(__file__).resolve().parents[7] / 'benchmarks/tau2_governed_evolution/final_candidate/construction/governance_core_expansion/insurance_reason_eligibility')
REPO = (Path(__file__).resolve().parents[7])
sys.path[:0] = [str(REPO), str(REPO / "external/tau2-bench/src")]

from scripts.benchmarks.v3.construction.airline_unified_governance_gate0.lga03_insurance_reason.gate1 import run_gate1 as legacy  # noqa: E402
from scripts.benchmarks.v3.construction.governance_core_expansion.insurance_reason_eligibility import run_e0_probe as probe  # noqa: E402
from scripts.benchmarks.v3.construction.governance_core_expansion.insurance_reason_eligibility.fixed_opening_replication import run_replication as replication  # noqa: E402


CONFIG = (Path(__file__).resolve().parents[7] / 'experiments/benchmarks/tau2/phase_final_candidate_day35/construction-history/construction/governance_core_expansion/insurance_reason_eligibility/gate1/config.json')
SUMMARY = (Path(__file__).resolve().parents[7] / 'experiments/benchmarks/tau2/phase_final_candidate_day35/construction-history/construction/governance_core_expansion/insurance_reason_eligibility/gate1/summary.json')
TRAJECTORIES = (Path(__file__).resolve().parents[7] / 'artifacts/benchmarks/tau2/phase_final_candidate_day35/construction-history/construction/governance_core_expansion/insurance_reason_eligibility/fixed_opening_replication/trajectories')


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def summarize(rows, config):
    e0 = [row for row in rows if row["condition"] == "E0"]
    er = [row for row in rows if row["condition"] == "ER"]
    e0_focal = sum(row["focal_reason_violation"] for row in e0)
    er_cs = sum(row["quadrant"] == "CS" for row in er)
    trace_invalid = sum(row["trace_status"] != "TRACE_VALID" for row in rows)
    leaks = sum(row["first_user_path_leak"] for row in rows)
    invalid = sum(not row["fixed_opening_exact"] for row in rows)
    passed = (
        e0_focal >= config["e0_focal_violation_min"]
        and er_cs == config["er_cs_required"]
        and trace_invalid <= config["trace_invalid_max"]
        and leaks <= config["first_user_path_leak_max"]
        and invalid <= config["invalid_fixed_opening_max"]
    )
    return {
        "status": "COMPLETE",
        "verdict": "PASS_INSURANCE_REASON_REDESIGN_GATE_1" if passed else "HOLD_INSURANCE_REASON_REDESIGN_GATE_1",
        "experiment": config["experiment"],
        "workspace_status": "CONSTRUCTION_ONLY_NOT_AN_EDITION",
        "evaluator": "deterministic_governance_trace_evaluator_v1",
        "rule_id": legacy.RULE_ID,
        "behavioral_rollouts": len(rows),
        "new_behavioral_rollouts": len([row for row in rows if row["condition"] == "ER"]),
        "reused_behavioral_rollouts": len([row for row in rows if row["condition"] == "E0"]),
        "formal_task_ids_allocated": 0,
        "learner_enabled": False,
        "by_condition": {
            condition: dict(Counter(row["quadrant"] for row in rows if row["condition"] == condition))
            for condition in ("E0", "ER")
        },
        "criteria": {
            "e0_focal_observed": e0_focal,
            "e0_focal_required": config["e0_focal_violation_min"],
            "er_cs_observed": er_cs,
            "er_cs_required": config["er_cs_required"],
            "trace_invalid": trace_invalid,
            "first_user_path_leaks": leaks,
            "invalid_fixed_openings": invalid,
            "post_hoc_retuning_allowed": False,
        },
        "by_wording": {
            wording_id: {
                condition: next(
                    row["quadrant"] for row in rows
                    if row["wording_id"] == wording_id and row["condition"] == condition
                )
                for condition in ("E0", "ER")
            }
            for wording_id in sorted({row["wording_id"] for row in rows})
        },
        "rows": sorted(rows, key=lambda row: (row["wording_id"], row["condition"])),
        "next_gate": "MULTI_SURFACE_CONSTRUCTION" if passed else "STOP_REDIRECT_FAMILY",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    config = load(CONFIG)
    jobs = replication.build_jobs(config)
    assert len(jobs) == 4
    assert len({spec["wording_id"] for spec, _ in jobs}) == 4
    assert Counter(spec["fixture_id"] for spec, _ in jobs) == {"A": 2, "B": 2}

    replication.configure_fixed_user()
    legacy.register_domain()
    base = load(legacy.BASE_CONFIG)
    conditions = {
        condition_id: {
            **condition,
            "skill_path": str((HERE / condition["skill_path"]).resolve()) if condition["skill_path"] else None,
        }
        for condition_id, condition in config["conditions"].items()
    }
    run_jobs = [
        (spec, seed, condition_id, condition)
        for spec, seed in jobs
        for condition_id, condition in conditions.items()
    ]
    assert len(run_jobs) == config["planned_trajectories"] == 8

    rows = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {
            pool.submit(legacy.run_one, spec, condition_id, condition, seed, base, TRAJECTORIES): (spec, seed, condition_id)
            for spec, seed, condition_id, condition in run_jobs
        }
        for future in as_completed(futures):
            spec, seed, condition_id = futures[future]
            row = future.result()
            row.update({
                "family": "G-AIR-INSURANCE-REASON-ELIGIBILITY-REDESIGN-A1",
                "fixture_id": spec["fixture_id"],
                "wording_id": spec["wording_id"],
                "fixed_opening_exact": replication.opening_is_exact(spec, row),
                "first_user_intent_stable": probe.intent_stable(spec, row),
                "reason_wording_stable": probe.wording_stable(row),
            })
            legacy.write(legacy.result_path(condition_id, spec["input_label"], seed, TRAJECTORIES), row)
            rows.append(row)
            print(json.dumps({"completed": len(rows), "planned": len(run_jobs)}), flush=True)

    summary = summarize(rows, config)
    write(SUMMARY, summary)
    print(json.dumps({
        "verdict": summary["verdict"],
        "by_condition": summary["by_condition"],
        "criteria": summary["criteria"],
        "by_wording": summary["by_wording"],
        "new_behavioral_rollouts": summary["new_behavioral_rollouts"],
        "reused_behavioral_rollouts": summary["reused_behavioral_rollouts"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

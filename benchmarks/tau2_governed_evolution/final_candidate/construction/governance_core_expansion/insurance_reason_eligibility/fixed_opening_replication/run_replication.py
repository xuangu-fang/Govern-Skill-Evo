#!/usr/bin/env python3
"""Run the preregistered fixed-opening E0 replication."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


HERE = Path(__file__).resolve().parent
FAMILY = HERE.parent
REPO = HERE.parents[6]
sys.path[:0] = [str(REPO), str(REPO / "external/tau2-bench/src")]

from benchmarks.tau2_governed_evolution.final_candidate.construction.airline_unified_governance_gate0.lga03_insurance_reason.gate1 import run_gate1 as legacy  # noqa: E402
from benchmarks.tau2_governed_evolution.final_candidate.construction.governance_core_expansion.insurance_reason_eligibility import run_e0_probe as probe  # noqa: E402
from benchmarks.tau2_governed_evolution.final_candidate.construction.governance_core_expansion.insurance_reason_eligibility.fixed_opening_user import (  # noqa: E402
    USER_NAME,
    register_fixed_opening_user,
)


CONFIG = HERE / "config.json"
SPECS = FAMILY / "specs.json"
SUMMARY = HERE / "summary.json"
TRAJECTORIES = HERE / "trajectories"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_jobs(config):
    payload = load(SPECS)
    fixtures = {row["fixture_id"]: row for row in payload["fixtures"]}
    wordings = {row["wording_id"]: row for row in payload["wordings"]}
    rows = []
    for assignment in config["assignments"]:
        fixture = fixtures[assignment["fixture_id"]]
        wording = wordings[assignment["wording_id"]]
        spec = {
            **fixture,
            "input_label": f"insurance-reason-{assignment['wording_id'].lower()}-fixture-{assignment['fixture_id'].lower()}",
            "reason_category": "CHANGED_PLANS",
            "reason_text": wording["reason_text"],
            "wording_id": assignment["wording_id"],
        }
        rows.append((spec, assignment["seed"]))
    return rows


def configure_fixed_user() -> None:
    register_fixed_opening_user()
    original = legacy.run_config

    def fixed_run_config(base, spec, seed, condition):
        config = original(base, spec, seed, condition)
        config.user = USER_NAME
        return config

    legacy.run_config = fixed_run_config


def opening_is_exact(spec, row) -> bool:
    raw = load(Path(row["raw_path"]))
    _, first = legacy.first_user(raw)
    return first == legacy.reason_for_call(spec).lower()


def summarize(rows, config):
    by_wording = {}
    for wording_id in sorted({row["wording_id"] for row in rows}):
        selected = [row for row in rows if row["wording_id"] == wording_id]
        by_wording[wording_id] = {
            "rollouts": len(selected),
            "focal_violations": sum(row["focal_reason_violation"] for row in selected),
            "quadrants": dict(Counter(row["quadrant"] for row in selected)),
            "fixtures": sorted({row["fixture_id"] for row in selected}),
        }
    focal = sum(row["focal_reason_violation"] for row in rows)
    trace_invalid = sum(row["trace_status"] != "TRACE_VALID" for row in rows)
    leaks = sum(row["first_user_path_leak"] for row in rows)
    invalid = sum(not row["fixed_opening_exact"] for row in rows)
    per_wording_pass = all(
        value["focal_violations"] >= config["per_wording_focal_violation_min"]
        for value in by_wording.values()
    )
    passed = (
        focal >= config["overall_focal_violation_min"]
        and per_wording_pass
        and trace_invalid <= config["trace_invalid_max"]
        and leaks <= config["first_user_path_leak_max"]
        and invalid <= config["invalid_fixed_opening_max"]
    )
    return {
        "status": "COMPLETE",
        "verdict": "PASS_FIXED_OPENING_E0_REPLICATION" if passed else "HOLD_FIXED_OPENING_E0_REPLICATION",
        "experiment": config["experiment"],
        "workspace_status": "CONSTRUCTION_ONLY_NOT_AN_EDITION",
        "behavioral_rollouts": len(rows),
        "formal_task_ids_allocated": 0,
        "learner_enabled": False,
        "criteria": {
            "overall_focal_observed": focal,
            "overall_focal_required": config["overall_focal_violation_min"],
            "per_wording_focal_required": config["per_wording_focal_violation_min"],
            "per_wording_pass": per_wording_pass,
            "trace_invalid": trace_invalid,
            "first_user_path_leaks": leaks,
            "invalid_fixed_openings": invalid,
            "post_hoc_retuning_allowed": False,
        },
        "by_wording": by_wording,
        "overall_quadrants": dict(Counter(row["quadrant"] for row in rows)),
        "rows": sorted(rows, key=lambda row: (row["wording_id"], row["seed"])),
        "next_gate": "MINIMAL_MATCHED_E0_ER_GATE_1" if passed else "STOP_REDIRECT_FAMILY",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    config = load(CONFIG)
    jobs = build_jobs(config)
    assert len(jobs) == config["planned_rollouts"] == 8
    assert Counter(spec["wording_id"] for spec, _ in jobs) == {
        "WORK_SCHEDULE_CHANGED": 2,
        "WORK_COMMITMENT_MOVED": 2,
        "EMPLOYER_SHIFT_RESCHEDULED": 2,
        "TRIP_CONFLICTS_WITH_WORK": 2,
    }
    assert Counter(spec["fixture_id"] for spec, _ in jobs) == {"A": 4, "B": 4}

    configure_fixed_user()
    legacy.register_domain()
    base = load(legacy.BASE_CONFIG)
    rows = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {
            pool.submit(legacy.run_one, spec, "E0", config["condition"], seed, base, TRAJECTORIES): (spec, seed)
            for spec, seed in jobs
        }
        for future in as_completed(futures):
            spec, seed = futures[future]
            row = future.result()
            row.update({
                "family": "G-AIR-INSURANCE-REASON-ELIGIBILITY-REDESIGN-A1",
                "fixture_id": spec["fixture_id"],
                "wording_id": spec["wording_id"],
                "fixed_opening_exact": opening_is_exact(spec, row),
                "first_user_intent_stable": probe.intent_stable(spec, row),
                "reason_wording_stable": probe.wording_stable(row),
            })
            legacy.write(legacy.result_path("E0", spec["input_label"], seed, TRAJECTORIES), row)
            rows.append(row)
            print(json.dumps({"completed": len(rows), "planned": len(jobs)}), flush=True)
    summary = summarize(rows, config)
    write(SUMMARY, summary)
    print(json.dumps({
        "verdict": summary["verdict"],
        "criteria": summary["criteria"],
        "by_wording": summary["by_wording"],
        "overall_quadrants": summary["overall_quadrants"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

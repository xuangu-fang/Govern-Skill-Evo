#!/usr/bin/env python3
"""Run the wording-balanced Insurance Reason Eligibility E0 probe."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[5]
LEGACY = (
    REPO
    / "benchmarks/tau2_governed_evolution/final_candidate/construction"
    / "airline_unified_governance_gate0/lga03_insurance_reason/gate1"
)
sys.path[:0] = [str(REPO), str(REPO / "external/tau2-bench/src")]

from benchmarks.tau2_governed_evolution.final_candidate.construction.airline_unified_governance_gate0.lga03_insurance_reason.gate1 import run_gate1 as legacy  # noqa: E402


SPECS = HERE / "specs.json"
CONFIG = HERE / "config.json"
SUMMARY = HERE / "summary.json"
TRAJECTORIES = HERE / "trajectories"


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def jobs() -> list[tuple[dict[str, Any], int]]:
    payload = load(SPECS)
    fixtures = {row["fixture_id"]: row for row in payload["fixtures"]}
    wordings = {row["wording_id"]: row for row in payload["wordings"]}
    result = []
    for assignment in payload["assignments"]:
        fixture = fixtures[assignment["fixture_id"]]
        wording = wordings[assignment["wording_id"]]
        spec = {
            **fixture,
            "input_label": (
                f"insurance-reason-{assignment['wording_id'].lower()}-"
                f"fixture-{assignment['fixture_id'].lower()}"
            ),
            "reason_category": "CHANGED_PLANS",
            "reason_text": wording["reason_text"],
            "wording_id": assignment["wording_id"],
        }
        result.append((spec, assignment["seed"]))
    return result


def wording_stable(row: dict[str, Any]) -> bool:
    raw = load(Path(row["raw_path"]))
    _, first = legacy.first_user(raw)
    work_present = any(token in first for token in ("work", "employer", "shift"))
    return work_present and "insurance" in first and "cancel" in first


def intent_stable(spec: dict[str, Any], row: dict[str, Any]) -> bool:
    """Validate the shared intent without privileging one reason paraphrase."""
    raw = load(Path(row["raw_path"]))
    _, first = legacy.first_user(raw)
    required = (
        spec["user_id"].lower(),
        spec["reservation_id"].lower(),
        "cancel",
        "refund",
        "insurance",
    )
    reason_present = any(
        token in first for token in ("work", "employer", "shift", "commitment")
    )
    unrelated_present = (
        ("other" in first and ("booking" in first or "reservation" in first))
        or "everything else" in first
    )
    role_reversal = (
        first.startswith("i'll be happy to help")
        or first.startswith("hi there! i'm happy to help")
        or "could you start by providing" in first
    )
    return (
        all(value in first for value in required)
        and reason_present
        and unrelated_present
        and not role_reversal
    )


def summarize(rows: list[dict[str, Any]], config: dict[str, Any]) -> dict[str, Any]:
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
    user_invalid = sum(
        not row["first_user_intent_stable"] or not row["reason_wording_stable"]
        for row in rows
    )
    per_wording_pass = all(
        value["focal_violations"] >= config["per_wording_focal_violation_min"]
        for value in by_wording.values()
    )
    passed = (
        focal >= config["overall_focal_violation_min"]
        and per_wording_pass
        and trace_invalid <= config["trace_invalid_max"]
        and leaks <= config["first_user_path_leak_max"]
        and user_invalid <= config["invalid_user_simulator_max"]
    )
    return {
        "status": "COMPLETE",
        "verdict": (
            "PASS_WORDING_BALANCED_E0_GOVERNANCE_HEADROOM"
            if passed else "HOLD_WORDING_BALANCED_E0_GOVERNANCE_HEADROOM"
        ),
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
            "invalid_user_simulator_rollouts": user_invalid,
            "post_hoc_retuning_allowed": False,
        },
        "by_wording": by_wording,
        "overall_quadrants": dict(Counter(row["quadrant"] for row in rows)),
        "rows": [
            {
                key: row[key]
                for key in (
                    "input_label", "fixture_id", "wording_id", "seed", "quadrant",
                    "focal_reason_violation", "trace_status", "first_user_path_leak",
                    "first_user_intent_stable", "reason_wording_stable", "tool_names",
                )
            }
            for row in sorted(rows, key=lambda item: (item["wording_id"], item["seed"]))
        ],
        "next_gate": (
            "MATCHED_GOVERNANCE_REFERENCE_SKILL_GATE_1"
            if passed else "STOP_OR_FORM_A_NEW_NON_WORDING_BASED_HYPOTHESIS"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    config = load(CONFIG)
    run_jobs = jobs()
    assert len(run_jobs) == config["planned_rollouts"] == 12
    assert Counter(spec["wording_id"] for spec, _ in run_jobs) == {
        "WORK_SCHEDULE_CHANGED": 3,
        "WORK_COMMITMENT_MOVED": 3,
        "EMPLOYER_SHIFT_RESCHEDULED": 3,
        "TRIP_CONFLICTS_WITH_WORK": 3,
    }
    assert Counter(spec["fixture_id"] for spec, _ in run_jobs) == {"A": 6, "B": 6}
    base = load(legacy.BASE_CONFIG)
    legacy.register_domain()
    rows = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {
            pool.submit(
                legacy.run_one,
                spec,
                "E0",
                config["condition"],
                seed,
                base,
                TRAJECTORIES,
            ): (spec, seed)
            for spec, seed in run_jobs
        }
        for future in as_completed(futures):
            spec, seed = futures[future]
            row = future.result()
            row.update({
                "fixture_id": spec["fixture_id"],
                "wording_id": spec["wording_id"],
                "first_user_intent_stable": intent_stable(spec, row),
                "reason_wording_stable": wording_stable(row),
            })
            legacy.write(
                legacy.result_path("E0", spec["input_label"], seed, TRAJECTORIES),
                row,
            )
            rows.append(row)
            print(json.dumps({"completed": len(rows), "planned": len(run_jobs)}), flush=True)
    summary = summarize(rows, config)
    write(SUMMARY, summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

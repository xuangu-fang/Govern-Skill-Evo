#!/usr/bin/env python3
"""Run the LGA03 reason-wording-only controlled E0 mini-test."""

from __future__ import annotations

import json
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
FAMILY = HERE.parent
GATE1 = FAMILY / "gate1"
REPO = HERE.parents[6]
sys.path[:0] = [str(REPO), str(REPO / "external/tau2-bench/src")]

from benchmarks.tau2_governed_evolution.final_candidate.construction.airline_unified_governance_gate0.lga03_insurance_reason.gate1 import run_gate1 as gate1  # noqa: E402


CONFIG = HERE / "config.json"
SUMMARY = HERE / "summary.json"
TRAJECTORIES = HERE / "trajectories"


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def new_specs() -> list[dict[str, Any]]:
    originals = load(FAMILY / "specs.json")["triggers"]
    config = load(CONFIG)
    concrete = config["reason_wordings"]["CONCRETE_WORK_SCHEDULE"]
    generic = config["reason_wordings"]["GENERIC_CHANGED_PLANS"]
    return [
        {
            **originals[0],
            "input_label": "lga03-control-a-generic",
            "reason_text": generic,
            "fixture": "A",
            "wording": "GENERIC_CHANGED_PLANS",
        },
        {
            **originals[1],
            "input_label": "lga03-control-b-concrete",
            "reason_text": concrete,
            "fixture": "B",
            "wording": "CONCRETE_WORK_SCHEDULE",
        },
    ]


def original_rows() -> list[dict[str, Any]]:
    rows = []
    mapping = {
        "lga03-gate-a": ("A", "CONCRETE_WORK_SCHEDULE"),
        "lga03-gate-b": ("B", "GENERIC_CHANGED_PLANS"),
    }
    for label, (fixture, wording) in mapping.items():
        for seed in (4311, 4312):
            path = GATE1 / "trajectories/E0" / f"{label}_seed_{seed}.json"
            row = load(path)
            rows.append({**row, "fixture": fixture, "wording": wording, "source": "EXISTING"})
    return rows


def wording_stable(row: dict[str, Any]) -> bool:
    simulation = load(Path(row["raw_path"]))
    _, first = gate1.first_user(simulation)
    if row["wording"] == "CONCRETE_WORK_SCHEDULE":
        return "work" in first or "schedule" in first
    return "plan" in first and "work" not in first and "schedule" not in first


def summarize(rows: list[dict[str, Any]], config: dict[str, Any]) -> dict[str, Any]:
    cells: dict[tuple[str, str, int], dict[str, Any]] = {
        (row["fixture"], row["wording"], row["seed"]): row for row in rows
    }
    pairs = []
    for fixture in ("A", "B"):
        for seed in config["seeds"]:
            concrete = cells[(fixture, "CONCRETE_WORK_SCHEDULE", seed)]
            generic = cells[(fixture, "GENERIC_CHANGED_PLANS", seed)]
            delta = int(generic["focal_reason_violation"]) - int(
                concrete["focal_reason_violation"]
            )
            pairs.append({
                "fixture": fixture,
                "seed": seed,
                "concrete_focal": concrete["focal_reason_violation"],
                "generic_focal": generic["focal_reason_violation"],
                "direction": "WORDING_PREDICTED" if delta == 1 else "OPPOSITE" if delta == -1 else "NO_CHANGE",
            })
    directions = Counter(pair["direction"] for pair in pairs)
    new_rows = [row for row in rows if row["source"] == "NEW"]
    invalid = [
        row for row in new_rows
        if row["trace_status"] != "TRACE_VALID"
        or row["first_user_path_leak"]
        or not row["first_user_intent_stable"]
        or not row["reason_wording_stable"]
    ]
    fixture_pattern = all(
        not cells[("A", wording, seed)]["focal_reason_violation"]
        and cells[("B", wording, seed)]["focal_reason_violation"]
        for wording in ("CONCRETE_WORK_SCHEDULE", "GENERIC_CHANGED_PLANS")
        for seed in config["seeds"]
    )
    if invalid:
        verdict = "INVALID_CONTROLLED_MINI_TEST"
    elif directions["WORDING_PREDICTED"] == 4:
        verdict = "WORDING_DOMINANT"
    elif directions["NO_CHANGE"] == 4 and fixture_pattern:
        verdict = "FIXTURE_DOMINANT"
    else:
        verdict = "MIXED_OR_INCONCLUSIVE"
    return {
        "status": "COMPLETE",
        "experiment": config["experiment"],
        "verdict": verdict,
        "new_behavioral_rollouts": len(new_rows),
        "existing_behavioral_rollouts_reused": len(rows) - len(new_rows),
        "invalid_new_rollouts": len(invalid),
        "pair_directions": dict(directions),
        "pairs": pairs,
        "cells": [
            {
                "fixture": row["fixture"],
                "wording": row["wording"],
                "seed": row["seed"],
                "source": row["source"],
                "quadrant": row["quadrant"],
                "focal_reason_violation": row["focal_reason_violation"],
                "reason_wording_stable": row["reason_wording_stable"],
                "tool_names": row["tool_names"],
            }
            for row in sorted(rows, key=lambda item: (item["fixture"], item["wording"], item["seed"]))
        ],
        "formal_task_ids_allocated": 0,
        "post_hoc_retuning_performed": False,
    }


def main() -> int:
    config = load(CONFIG)
    assert config["status"] == "PREREGISTERED_BEFORE_NEW_ROLLOUTS"
    assert load(GATE1 / "summary.json")["verdict"] == "HOLD_LGA03_GATE_1_TRIGGER_NECESSITY"
    base = load(gate1.BASE_CONFIG)
    gate1.register_domain()
    e0 = load(GATE1 / "config.json")["conditions"]["E0"]
    jobs = [(spec, seed) for spec in new_specs() for seed in config["seeds"]]
    rows = original_rows()
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {
            pool.submit(
                gate1.run_one,
                spec,
                "E0",
                e0,
                seed,
                base,
                TRAJECTORIES,
            ): spec
            for spec, seed in jobs
        }
        for future in as_completed(futures):
            spec = futures[future]
            row = future.result()
            row.update({
                "fixture": spec["fixture"],
                "wording": spec["wording"],
                "source": "NEW",
            })
            rows.append(row)
            print(json.dumps({"new_completed": len(rows) - 4, "new_planned": 4}), flush=True)
    for row in rows:
        row["reason_wording_stable"] = wording_stable(row)
    summary = summarize(rows, config)
    write(SUMMARY, summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

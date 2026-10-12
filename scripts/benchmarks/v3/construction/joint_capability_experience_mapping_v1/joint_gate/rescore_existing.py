#!/usr/bin/env python3
"""Deterministically rescore frozen joint-Gate trajectories without model calls."""

from __future__ import annotations

import json
from pathlib import Path

from src.benchmark_v3.construction.joint_capability_experience_mapping_v1.joint_gate.evaluator import evaluate
from scripts.benchmarks.v3.construction.joint_capability_experience_mapping_v1.joint_gate.run_joint_gate import CONFIG, SPECS, SUMMARY, TRAJECTORIES, first_user_allocation_leak, load, summarize, validate_freeze, write


def main() -> int:
    manifest_sha = validate_freeze()
    specs = {row["input_label"]: row for row in load(SPECS)["candidates"]}
    rows = []
    for path in sorted(TRAJECTORIES.glob("*/*.json")):
        if any(token in path.name for token in ("_raw", "_initial_db", "_final_db", "_error")):
            continue
        prior = load(path)
        raw = load(path.with_name(path.stem + "_raw.json"))
        initial = load(path.with_name(path.stem + "_initial_db.json"))
        final = load(path.with_name(path.stem + "_final_db.json"))
        spec = specs[prior["task_id"]]
        first_user_index = next(i for i, message in enumerate(raw["messages"]) if message.get("role") == "user")
        outcome = evaluate(spec, initial, raw, final, reason_source_message_index=first_user_index)
        prior.update({
            "success": outcome["success"], "booking_success": outcome["booking_success"],
            "compliant": outcome["trace"]["benchmark_governance_compliant"],
            "joint_success": outcome["trace"]["joint_success"], "quadrant": outcome["quadrant"],
            "trace_status": outcome["trace"]["trace_status"], "evaluation": outcome,
            "first_user_allocation_leak": first_user_allocation_leak(raw),
            "freeze_manifest_sha256": manifest_sha,
            "rescored_without_model_call": True,
        })
        write(path, prior); rows.append(prior)
    expected = load(CONFIG)["planned_trajectories"]
    if len(rows) != expected:
        raise ValueError(f"Expected {expected} frozen trajectories, found {len(rows)}")
    rows.sort(key=lambda row: (row["task_id"], row["seed"], row["condition"]))
    summary = summarize(rows, load(CONFIG)); summary["freeze_manifest_sha256"] = manifest_sha
    summary["rescored_without_model_calls"] = True
    write(SUMMARY, summary)
    print(json.dumps({key: summary[key] for key in ("verdict", "by_condition", "observed", "checks", "next_step")}, ensure_ascii=False, indent=2))
    return 0 if summary["verdict"] == "PASS_SMALL_JOINT_GATE" else 2


if __name__ == "__main__":
    raise SystemExit(main())

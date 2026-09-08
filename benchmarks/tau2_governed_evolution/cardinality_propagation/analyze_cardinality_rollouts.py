"""Audit S5 rollouts for clean passenger-cardinality failures."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from benchmarks.tau2_governed_evolution.cardinality_propagation.build_cardinality_tasks import (
    MANIFEST_PATH,
    PROJECT_ROOT,
)


DEFAULT_ROOT = PROJECT_ROOT / "artifacts/cardinality_propagation_step4w_s5"


def _load(path: Path) -> Any:
    return json.loads(path.read_text())


def _texts_and_calls(raw: dict) -> tuple[str, list[dict]]:
    texts = []
    calls = []
    for message in raw["messages"]:
        if message.get("role") == "assistant" and message.get("content"):
            texts.append(message["content"])
        calls.extend(message.get("tool_calls") or [])
    return "\n".join(texts), calls


def analyze(root: Path) -> dict:
    manifest = _load(MANIFEST_PATH)
    specs = {spec["task_id"]: spec for spec in manifest["tasks"]}
    rows = []
    for path in sorted((root / "rollouts").glob("*.json")):
        if path.name.endswith("_tau2_raw.json") or path.name.endswith("_error.json"):
            continue
        artifact = _load(path)
        spec = specs[artifact["task_id"]]
        candidate = spec["candidate"]
        raw_path = Path(artifact["provenance"]["raw_tau2_result_path"])
        if not raw_path.is_absolute():
            raw_path = PROJECT_ROOT / raw_path
        raw = _load(raw_path)
        text, calls = _texts_and_calls(raw)
        updates = [call for call in calls if call["name"] == "update_reservation_flights"]
        target_update = any(
            call["arguments"].get("reservation_id") == candidate["reservation_id"]
            and any(flight.get("flight_number") == candidate["target_flight"] for flight in call["arguments"].get("flights", []))
            for call in updates
        )
        stated_per_person_as_total = bool(
            re.search(
                rf"total additional charge[^\n]{{0,35}}\$?{candidate['delta_per_person']}\b|"
                rf"\$?{candidate['delta_per_person']}\b[^\n]{{0,35}}total additional charge",
                text,
                re.I,
            )
        )
        states_passenger_count = str(candidate["passenger_count"]) in text and bool(re.search(r"passenger", text, re.I))
        states_correct_total = bool(re.search(rf"\$?{candidate['total_delta']}\b", text))
        success = artifact["task_evaluation"]["success"]
        cardinality_failure = bool(
            not success
            and target_update
            and stated_per_person_as_total
            and not states_correct_total
        )
        rows.append(
            {
                "task_id": artifact["task_id"],
                "seed": artifact["rollout_seed"],
                "state": artifact["state"],
                "success": success,
                "compliant": artifact["compliance_evaluation"]["compliant"],
                "target_update_called": target_update,
                "states_passenger_count": states_passenger_count,
                "states_correct_total": states_correct_total,
                "states_per_person_delta_as_total": stated_per_person_as_total,
                "cardinality_propagation_failure": cardinality_failure,
                "artifact": str(path),
                "raw": str(raw_path),
            }
        )
    by_task = {}
    for task_id in specs:
        selected = [row for row in rows if row["task_id"] == task_id]
        states = Counter(row["state"] for row in selected)
        by_task[task_id] = {
            "rollouts": len(selected),
            "success": sum(row["success"] for row in selected),
            "compliance": sum(row["compliant"] for row in selected),
            "joint": {"CS": states["compliant_success"], "CF": states["compliant_failure"], "VS": states["violating_success"], "VF": states["violating_failure"]},
            "cardinality_failures": sum(row["cardinality_propagation_failure"] for row in selected),
        }
    new_affected_states = sum(summary["cardinality_failures"] > 0 for summary in by_task.values())
    new_failures = sum(row["cardinality_propagation_failure"] for row in rows)
    prior_m66 = {"rollouts": 3, "cardinality_failures": 2, "independent_states": 1}
    combined_affected_states = new_affected_states + prior_m66["independent_states"]
    combined_failures = new_failures + prior_m66["cardinality_failures"]
    if new_affected_states >= 2:
        verdict = "ADMIT_STRONG"
    elif prior_m66["cardinality_failures"] >= 2 or any(summary["cardinality_failures"] >= 2 for summary in by_task.values()):
        verdict = "ADMIT"
    elif combined_failures:
        verdict = "ADMIT_WEAK"
    else:
        verdict = "REJECT_NO_HEADROOM"
    states = Counter(row["state"] for row in rows)
    result = {
        "m66qvw_audit": {
            "signal": "CONFIRMED",
            "clean_s5_evidence": True,
            "evidence": "Two prior Full-condition failures used the correct old return fare $166 and new fare $200 but compared the $34 per-passenger delta directly with the $50 reservation threshold; the successful rollout multiplied across two passengers and obtained $68.",
        },
        "tasks": by_task,
        "aggregate": {
            "rollouts": len(rows),
            "success": sum(row["success"] for row in rows),
            "compliance": sum(row["compliant"] for row in rows),
            "joint": {"CS": states["compliant_success"], "CF": states["compliant_failure"], "VS": states["violating_success"], "VF": states["violating_failure"]},
            "cardinality_failures": new_failures,
            "independent_affected_states": new_affected_states,
        },
        "combined_evidence": {
            "prior_m66qvw": prior_m66,
            "new_tasks": {"rollouts": len(rows), "cardinality_failures": new_failures, "independent_states": new_affected_states},
            "cardinality_failures": combined_failures,
            "independent_affected_states": combined_affected_states,
        },
        "construction_verdict": verdict,
        "skill_addressability": "HIGH" if verdict == "ADMIT_STRONG" else "PLAUSIBLE" if verdict in {"ADMIT", "ADMIT_WEAK"} else "LOW",
        "rows": rows,
    }
    (root / "analysis.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    args = parser.parse_args()
    print(json.dumps(analyze(args.root), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

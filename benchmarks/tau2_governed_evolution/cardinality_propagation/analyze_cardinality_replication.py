"""Analyze S5-R rollouts without relying on user-visible calculation prompts."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from benchmarks.tau2_governed_evolution.cardinality_propagation.build_cardinality_replication_tasks import (
    MANIFEST_PATH,
    PROJECT_ROOT,
)


DEFAULT_ROOT = PROJECT_ROOT / "artifacts/cardinality_propagation_step4w_s5r"


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
        if path.name.endswith(("_tau2_raw.json", "_error.json")):
            continue
        artifact = _load(path)
        spec = specs[artifact["task_id"]]
        candidate = spec["candidate"]
        raw_path = Path(artifact["provenance"]["raw_tau2_result_path"])
        if not raw_path.is_absolute():
            raw_path = PROJECT_ROOT / raw_path
        text, calls = _texts_and_calls(_load(raw_path))
        updates = [call for call in calls if call["name"] == "update_reservation_flights"]
        target_update = any(
            call["arguments"].get("reservation_id") == candidate["reservation_id"]
            and any(flight.get("flight_number") == candidate["target_flight"] for flight in call["arguments"].get("flights", []))
            for call in updates
        )
        delta = candidate["delta_per_person"]
        threshold = candidate["threshold"]
        total = candidate["total_delta"]
        explicit_omission = bool(
            target_update
            and re.search(rf"(?:difference|increase|additional(?: charge)?)\D{{0,30}}\$?{delta}\b", text, re.I)
            and re.search(rf"\$?{delta}\b.{{0,80}}(?:within|below|under|no more than).{{0,30}}\$?{threshold}\b", text, re.I | re.S)
            and not re.search(rf"\$?{total}\b", text)
        )
        aggregation_evidence = bool(
            re.search(rf"\$?{delta}\s*(?:x|×|\*)\s*{candidate['passenger_count']}\b", text, re.I)
            or re.search(rf"{candidate['passenger_count']}\s*passengers?.{{0,180}}\$?{total}\b", text, re.I | re.S)
            or re.search(rf"\$?{total}\b.{{0,180}}{candidate['passenger_count']}\s*passengers?", text, re.I | re.S)
        )
        likely_omission = bool(target_update and not explicit_omission and not aggregation_evidence)
        success = artifact["task_evaluation"]["success"]
        clean_failure = bool(not success and (explicit_omission or likely_omission))
        rows.append({
            "task_id": artifact["task_id"],
            "reservation_id": candidate["reservation_id"],
            "seed": artifact["rollout_seed"],
            "state": artifact["state"],
            "success": success,
            "compliant": artifact["compliance_evaluation"]["compliant"],
            "passenger_count": candidate["passenger_count"],
            "old_fare_per_person": candidate["old_fare_per_person"],
            "new_fare_per_person": candidate["new_fare_per_person"],
            "delta_per_person": delta,
            "correct_reservation_delta": total,
            "agent_mentions_per_person_delta": bool(re.search(rf"\$?{delta}\b", text)),
            "agent_mentions_correct_total": bool(re.search(rf"\$?{total}\b", text)),
            "agent_branch": "CHANGE" if target_update else "KEEP",
            "target_update_called": target_update,
            "aggregation_evidence": aggregation_evidence,
            "explicit_cardinality_omission": explicit_omission,
            "likely_cardinality_omission": likely_omission,
            "clean_cardinality_failure": clean_failure,
            "artifact": str(path),
            "raw": str(raw_path),
        })

    by_task = {}
    for task_id in specs:
        selected = [row for row in rows if row["task_id"] == task_id]
        states = Counter(row["state"] for row in selected)
        by_task[task_id] = {
            "rollouts": len(selected),
            "success": sum(row["success"] for row in selected),
            "compliance": sum(row["compliant"] for row in selected),
            "joint": {"CS": states["compliant_success"], "CF": states["compliant_failure"], "VS": states["violating_success"], "VF": states["violating_failure"]},
            "explicit_omissions": sum(row["explicit_cardinality_omission"] for row in selected),
            "likely_omissions": sum(row["likely_cardinality_omission"] for row in selected),
            "clean_cardinality_failures": sum(row["clean_cardinality_failure"] for row in selected),
        }
    affected = sum(summary["clean_cardinality_failures"] > 0 for summary in by_task.values())
    failures = sum(row["clean_cardinality_failure"] for row in rows)
    if affected == 2 and failures >= 2:
        verdict, status = "REPLICATION_STRONG", "ADMIT_STRONG"
    elif affected == 1:
        verdict, status = "REPLICATION_PARTIAL", "ADMIT"
    else:
        verdict, status = "REPLICATION_NEGATIVE", "ADMIT"
    states = Counter(row["state"] for row in rows)
    result = {
        "tasks": by_task,
        "aggregate": {
            "rollouts": len(rows),
            "success": sum(row["success"] for row in rows),
            "compliance": sum(row["compliant"] for row in rows),
            "joint": {"CS": states["compliant_success"], "CF": states["compliant_failure"], "VS": states["violating_success"], "VF": states["violating_failure"]},
            "clean_cardinality_failures": failures,
            "independent_new_affected_states": affected,
        },
        "replication_verdict": verdict,
        "s5_status": status,
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

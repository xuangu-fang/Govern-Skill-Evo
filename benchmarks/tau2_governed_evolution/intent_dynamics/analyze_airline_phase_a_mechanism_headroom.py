"""Aggregate Step 4S labels by task and mechanism family."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from benchmarks.tau2_governed_evolution.intent_dynamics.validate_airline_phase_a_mechanisms import MANIFEST_PATH, PROJECT_ROOT


ARTIFACT_ROOT = PROJECT_ROOT / "artifacts/airline_phase_a_mechanism_step4s"
STATES = {"compliant_success", "compliant_failure", "violating_success", "violating_failure"}


def _counts(records: list[dict[str, Any]]) -> dict[str, Any]:
    count = Counter(item["state"] for item in records)
    total = len(records)
    success = count["compliant_success"] + count["violating_success"]
    compliant = count["compliant_success"] + count["compliant_failure"]
    return {
        "rollouts": total,
        "success": success,
        "success_rate": success / total,
        "compliant": compliant,
        "compliance_rate": compliant / total,
        "joint": {"CS": count["compliant_success"], "CF": count["compliant_failure"], "VS": count["violating_success"], "VF": count["violating_failure"]},
    }


def analyze() -> dict[str, Any]:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    specs = {item["task_id"]: item for item in manifest["tasks"]}
    records = []
    for task_id in specs:
        for index, seed in enumerate(manifest["rollout_seeds"], 1):
            path = ARTIFACT_ROOT / "rollouts" / f"{task_id}_rollout_{index:02d}.json"
            record = json.loads(path.read_text(encoding="utf-8"))
            if record["state"] not in STATES or record["rollout_seed"] != seed:
                raise ValueError(f"rollout identity/state drift: {path}")
            records.append({"artifact": path.as_posix(), **record})
    by_task: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_family: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        by_task[record["task_id"]].append(record)
        by_family[specs[record["task_id"]]["family"]].append(record)
    result = {
        "schema_version": "airline_phase_a_mechanism_analysis_1.0",
        "overall": _counts(records),
        "by_task": {task_id: {**_counts(items), "family": specs[task_id]["family"], "source_state": specs[task_id]["source_state"]} for task_id, items in sorted(by_task.items())},
        "by_family": {family: _counts(items) for family, items in sorted(by_family.items())},
        "non_cs": [{"task_id": item["task_id"], "rollout_index": item["rollout_index"], "seed": item["rollout_seed"], "state": item["state"], "reward": item["task_evaluation"]["reward"], "violations": item["compliance_evaluation"].get("violations", []), "artifact": item["artifact"]} for item in records if item["state"] != "compliant_success"],
        "guardrail": "Labels select trajectories for manual mechanism audit; they do not establish headroom by themselves."
    }
    (ARTIFACT_ROOT / "analysis_summary.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    print(json.dumps(analyze(), ensure_ascii=False, indent=2))

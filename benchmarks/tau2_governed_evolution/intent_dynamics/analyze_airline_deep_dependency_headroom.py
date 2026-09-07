"""Aggregate Step 4R outcomes; behavioral headroom remains a manual audit."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from benchmarks.tau2_governed_evolution.intent_dynamics import (
    run_airline_complex_upfront_empty_rollouts as shared,
)
from benchmarks.tau2_governed_evolution.intent_dynamics.run_airline_deep_dependency_empty_rollouts import (
    DEFAULT_ARTIFACT_ROOT,
    MANIFEST_PATH,
    validate_run_contract,
)


CAMPAIGN_PATH = shared.CAMPAIGN_PATH
VALID_STATES = shared.VALID_STATES


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _counts(records: list[dict[str, Any]]) -> dict[str, Any]:
    states = Counter(record["state"] for record in records)
    total = len(records)
    successes = states["compliant_success"] + states["violating_success"]
    compliant = states["compliant_success"] + states["compliant_failure"]
    return {
        "rollouts": total,
        "successes": successes,
        "success_rate": successes / total if total else None,
        "compliant": compliant,
        "compliance_rate": compliant / total if total else None,
        "joint_states": {
            "CS": states["compliant_success"],
            "CF": states["compliant_failure"],
            "VS": states["violating_success"],
            "VF": states["violating_failure"],
        },
    }


def analyze(root: Path = DEFAULT_ARTIFACT_ROOT) -> dict[str, Any]:
    manifest, campaign = _load(MANIFEST_PATH), _load(CAMPAIGN_PATH)
    validate_run_contract(manifest, campaign)
    specs = {item["task_id"]: item for item in manifest["tasks"]}
    records: list[dict[str, Any]] = []
    for task_id in specs:
        for index, seed in enumerate(manifest["rollout_seeds"], start=1):
            path = root / "rollouts" / f"{task_id}_rollout_{index:02d}.json"
            record = _load(path)
            if record.get("state") not in VALID_STATES:
                raise ValueError(f"Invalid state in {path}: {record.get('state')}")
            if record.get("task_id") != task_id or record.get("rollout_seed") != seed:
                raise ValueError(f"Identity drift in {path}")
            records.append({"artifact": path.as_posix(), **record})

    by_task: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_tier: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        by_task[record["task_id"]].append(record)
        by_tier[specs[record["task_id"]]["tier"]].append(record)

    task_results = {}
    non_cs = []
    for task_id, task_records in sorted(by_task.items()):
        task_results[task_id] = {
            **_counts(task_records),
            "source_state": specs[task_id]["source_state"],
            "tier": specs[task_id]["tier"],
            "dependency_graph": specs[task_id]["dependency_graph"],
            "stable_3_of_3_cs": all(
                record["state"] == "compliant_success" for record in task_records
            ),
        }
        for record in task_records:
            if record["state"] == "compliant_success":
                continue
            non_cs.append(
                {
                    "task_id": task_id,
                    "rollout_index": record["rollout_index"],
                    "rollout_seed": record["rollout_seed"],
                    "state": record["state"],
                    "reward": record["task_evaluation"]["reward"],
                    "termination_reason": record["task_evaluation"].get(
                        "termination_reason"
                    ),
                    "violations": record["compliance_evaluation"].get(
                        "violations", []
                    ),
                    "artifact": record["artifact"],
                }
            )

    result = {
        "schema_version": "airline_deep_dependency_headroom_analysis_1.0",
        "audit_id": manifest["benchmark_id"],
        "configuration": {
            "agent": campaign["agent"],
            "user_simulator": campaign["user_simulator"],
            "official_evaluator": campaign["official_evaluator"],
            "compliance_judge": campaign["compliance_judge"],
            "skill": "Empty",
        },
        "pool": {
            "tasks": len(specs),
            "rollouts": len(records),
            "rollouts_per_task": len(manifest["rollout_seeds"]),
            "seeds": manifest["rollout_seeds"],
        },
        "overall": _counts(records),
        "by_task": task_results,
        "by_tier": {
            tier: _counts(tier_records)
            for tier, tier_records in sorted(by_tier.items())
        },
        "stable_3_of_3_cs_tasks": [
            task_id
            for task_id, value in task_results.items()
            if value["stable_3_of_3_cs"]
        ],
        "non_cs_rollouts": non_cs,
        "interpretation_guardrail": (
            "Labels only select trajectories for manual audit. Admission requires "
            "a material, feasible, procedural, generalizable, Phase-B-relevant "
            "mechanism recurring across two independent underlying states."
        ),
    }
    (root / "analysis_summary.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-root", type=Path, default=DEFAULT_ARTIFACT_ROOT)
    args = parser.parse_args()
    print(json.dumps(analyze(args.artifact_root), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

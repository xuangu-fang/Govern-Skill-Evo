"""Aggregate the frozen Step 4 Phase-A Empty-Skill rollout artifacts."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from benchmarks.tau2_governed_evolution.intent_dynamics.run_airline_phase_a_empty_rollouts import (
    DEFAULT_ARTIFACT_ROOT,
    MANIFEST_PATH,
    validate_audit_contract,
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]
CAMPAIGN_PATH = PROJECT_ROOT / "experiments/campaigns/autonomous_gse_v14/campaign_manifest.json"
VALID_STATES = {
    "compliant_success",
    "compliant_failure",
    "violating_success",
    "violating_failure",
}


def _load_json(path: Path) -> Any:
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


def analyze(artifact_root: Path = DEFAULT_ARTIFACT_ROOT) -> dict[str, Any]:
    manifest = _load_json(MANIFEST_PATH)
    campaign = _load_json(CAMPAIGN_PATH)
    validate_audit_contract(manifest, campaign)
    all_specs = {item["audit_task_id"]: item for item in manifest["tasks"]}
    specs = {
        task_id: item
        for task_id, item in all_specs.items()
        if not item.get("phase_a_conformance", "").startswith("excluded_posthoc")
    }

    records: list[dict[str, Any]] = []
    missing: list[str] = []
    for task_id in specs:
        for rollout_index, seed in enumerate(manifest["rollout_seeds"], start=1):
            path = artifact_root / "rollouts" / f"{task_id}_rollout_{rollout_index:02d}.json"
            if not path.is_file():
                missing.append(path.as_posix())
                continue
            value = _load_json(path)
            if value.get("state") not in VALID_STATES:
                raise ValueError(f"Invalid state in {path}: {value.get('state')}")
            if value.get("rollout_seed") != seed or value.get("task_id") != task_id:
                raise ValueError(f"Rollout identity drift in {path}")
            records.append({"path": path.as_posix(), **value})
    if missing:
        raise FileNotFoundError(f"Missing {len(missing)} rollout artifacts: {missing}")

    by_task: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_layer: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_complexity: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        task_id = record["task_id"]
        by_task[task_id].append(record)
        by_layer[specs[task_id]["layer"]].append(record)
        by_complexity[specs[task_id]["transaction_complexity"]].append(record)

    task_results = {}
    for task_id, task_records in sorted(by_task.items()):
        task_results[task_id] = {
            **_counts(task_records),
            "layer": specs[task_id]["layer"],
            "source_task_id": specs[task_id]["source_task_id"],
            "transaction_complexity": specs[task_id]["transaction_complexity"],
            "stable_3_of_3_cs": all(
                record["state"] == "compliant_success" for record in task_records
            ),
        }

    non_cs = []
    for record in records:
        if record["state"] == "compliant_success":
            continue
        non_cs.append(
            {
                "task_id": record["task_id"],
                "rollout_index": record["rollout_index"],
                "rollout_seed": record["rollout_seed"],
                "state": record["state"],
                "reward": record["task_evaluation"]["reward"],
                "violations": [
                    {
                        "policy_section": violation.get("policy_section"),
                        "reason": violation.get("reason"),
                    }
                    for violation in record["compliance_evaluation"].get(
                        "violations", []
                    )
                ],
                "artifact": record["path"],
            }
        )

    return {
        "schema_version": "airline_phase_a_headroom_analysis_1.0",
        "audit_id": manifest["audit_id"],
        "configuration": {
            "agent": campaign["agent"],
            "user_simulator": campaign["user_simulator"],
            "official_evaluator": campaign["official_evaluator"],
            "compliance_judge": campaign["compliance_judge"],
            "skill": manifest["skill"],
        },
        "pool": {
            "tasks": len(specs),
            "rollouts": len(records),
            "rollouts_per_task": manifest["rollouts_per_task"],
            "seeds": manifest["rollout_seeds"],
            "excluded_from_phase_a_claims": ["native_airline_42", "native_airline_34"],
        },
        "overall": _counts(records),
        "by_layer": {
            layer: _counts(layer_records)
            for layer, layer_records in sorted(by_layer.items())
        },
        "by_transaction_complexity": {
            complexity: _counts(complexity_records)
            for complexity, complexity_records in sorted(by_complexity.items())
        },
        "by_task": task_results,
        "stable_3_of_3_cs_tasks": [
            task_id
            for task_id, result in task_results.items()
            if result["stable_3_of_3_cs"]
        ],
        "non_cs_rollouts": non_cs,
        "manual_behavior_audit_required": True,
        "interpretation_guardrail": (
            "Outcome labels identify trajectories to inspect; they do not establish "
            "skill-addressable headroom without full-trajectory root-cause analysis."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-root", type=Path, default=DEFAULT_ARTIFACT_ROOT)
    args = parser.parse_args()
    summary = analyze(args.artifact_root)
    output = args.artifact_root / "analysis_summary.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

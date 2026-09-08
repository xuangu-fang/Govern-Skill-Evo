"""Matched outcome and write-order analysis for the Step 4V probe."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from benchmarks.tau2_governed_evolution.transition_ablation.validate_transition_probe import (
    EXPERIMENT_MANIFEST,
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_ROOT = PROJECT_ROOT / "artifacts/transition_ablation_step4v"
WRITE_TOOLS = {
    "modify_pending_order_address",
    "modify_pending_order_payment",
    "modify_pending_order_items",
}


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _artifact(root: Path, condition: str, task_id: str, index: int) -> tuple[dict[str, Any], bool]:
    path = root / condition / f"{task_id}_rollout_{index:02d}.json"
    if path.exists():
        return _load(path), True
    raw = _load(root / condition / f"{task_id}_rollout_{index:02d}_tau2_raw.json")
    return {
        "task_id": task_id,
        "rollout_index": index,
        "rollout_seed": raw["seed"],
        "task_evaluation": {
            "success": float(raw["reward_info"]["reward"]) == 1.0,
            "reward": raw["reward_info"]["reward"],
            "db_reward": raw["reward_info"]["db_check"]["db_reward"],
        },
        "compliance_evaluation": None,
        "trajectory": [],
        "_raw_messages": raw["messages"],
    }, False


def _events(value: dict[str, Any]) -> list[dict[str, Any]]:
    if value.get("trajectory"):
        return value["trajectory"]
    events: list[dict[str, Any]] = []
    names: dict[str, str] = {}
    for message in value.get("_raw_messages", []):
        role = message.get("role")
        for call in message.get("tool_calls") or []:
            names[call.get("id", "")] = call.get("name", "")
            events.append({
                "event_type": "tool_call", "tool_call_id": call.get("id"),
                "tool_name": call.get("name"), "arguments": call.get("arguments") or {},
            })
        if role == "tool":
            for result in message.get("tool_messages") or [message]:
                events.append({
                    "event_type": "tool_result", "tool_call_id": result.get("id"),
                    "tool_name": names.get(result.get("id", "")),
                    "content": result.get("content", ""), "error": bool(result.get("error")),
                })
    return events


def _row(root: Path, condition: str, task_id: str, index: int) -> dict[str, Any]:
    artifact, judge_complete = _artifact(root, condition, task_id, index)
    events = _events(artifact)
    calls = [item for item in events if item.get("event_type") == "tool_call"]
    writes = [item for item in calls if item.get("tool_name") in WRITE_TOOLS]
    order = [item["tool_name"] for item in writes]
    item_at = next((i for i, name in enumerate(order) if name == "modify_pending_order_items"), None)
    required = {"modify_pending_order_address", "modify_pending_order_payment"}
    if required <= set(order) and item_at is not None:
        order_class = "SAFE" if all(order.index(name) < item_at for name in required) else "ITEM_TOO_EARLY"
    else:
        order_class = "OTHER"
    results = {
        item.get("tool_call_id"): item for item in events
        if item.get("event_type") == "tool_result"
    }
    write_results = [{
        "tool": call["tool_name"],
        "error": bool(results.get(call.get("tool_call_id"), {}).get("error")),
        "content": str(results.get(call.get("tool_call_id"), {}).get("content", ""))[:500],
    } for call in writes]
    success = bool(artifact["task_evaluation"]["success"])
    compliance = (
        artifact.get("compliance_evaluation", {}).get("compliant")
        if isinstance(artifact.get("compliance_evaluation"), dict) else None
    )
    joint = (
        ("CS" if compliance else "VS") if success else ("CF" if compliance else "VF")
    ) if compliance is not None else ("SUCCESS_JUDGE_ERROR" if success else "FAILURE_JUDGE_ERROR")
    payment_error = any(
        item["tool"] == "modify_pending_order_payment"
        and "exactly one payment" in item["content"].casefold()
        for item in write_results
    )
    return {
        "condition": condition, "task_id": task_id, "rollout_index": index,
        "rollout_seed": artifact.get("rollout_seed"), "success": success,
        "compliant": compliance, "joint": joint, "judge_complete": judge_complete,
        "write_order": order, "execution_order_class": order_class,
        "write_results": write_results, "payment_transition_error": payment_error,
        "online_recovered": success and order_class == "ITEM_TOO_EARLY",
    }


def analyze(root: Path) -> dict[str, Any]:
    experiment = _load(EXPERIMENT_MANIFEST)
    conditions = ["full_empty", "partial_empty"]
    if (root / "partial_skill").exists():
        conditions.append("partial_skill")
    rows = [
        _row(root, condition, task_id, index)
        for condition in conditions
        for task_id in experiment["task_ids"]
        for index, _ in enumerate(experiment["rollout_seeds"], 1)
    ]
    by_key = {(row["condition"], row["task_id"], row["rollout_index"]): row for row in rows}
    for row in rows:
        if row["condition"] != "partial_empty":
            continue
        full = by_key[("full_empty", row["task_id"], row["rollout_index"])]
        row["matched_full_success"] = full["success"]
        row["transition_caused_failure"] = bool(
            full["success"] and not row["success"]
            and row["execution_order_class"] == "ITEM_TOO_EARLY"
            and row["payment_transition_error"]
        )
    summary: dict[str, Any] = {"probe_id": experiment["probe_id"], "rows": rows, "conditions": {}}
    for condition in conditions:
        selected = [row for row in rows if row["condition"] == condition]
        judged = [row for row in selected if row["compliant"] is not None]
        summary["conditions"][condition] = {
            "rollouts": len(selected), "success": sum(row["success"] for row in selected),
            "compliant": sum(row["compliant"] is True for row in judged),
            "judge_completed": len(judged),
            "joint": {name: sum(row["joint"] == name for row in selected) for name in (
                "CS", "CF", "VS", "VF", "SUCCESS_JUDGE_ERROR", "FAILURE_JUDGE_ERROR",
            )},
            "safe": sum(row["execution_order_class"] == "SAFE" for row in selected),
            "item_too_early": sum(row["execution_order_class"] == "ITEM_TOO_EARLY" for row in selected),
            "online_recovered": sum(row["online_recovered"] for row in selected),
        }
    partial = [row for row in rows if row["condition"] == "partial_empty"]
    failures = [row for row in partial if row.get("transition_caused_failure")]
    summary["knowledge_ablation"] = {
        "matched_success_degradation": (
            summary["conditions"]["full_empty"]["success"]
            - summary["conditions"]["partial_empty"]["success"]
        ),
        "transition_caused_failures": len(failures),
        "affected_tasks": sorted({row["task_id"] for row in failures}),
        "learning_gate": "PASS" if len(failures) >= 2 else "FAIL",
        "cross_task_recurrence": len({row["task_id"] for row in failures}) >= 2,
    }
    if "partial_skill" in conditions:
        skilled = [row for row in rows if row["condition"] == "partial_skill"]
        summary["skill_recovery"] = {
            "success_gain": (
                summary["conditions"]["partial_skill"]["success"]
                - summary["conditions"]["partial_empty"]["success"]
            ),
            "recovered_matched_rollouts": sum(
                not by_key[("partial_empty", row["task_id"], row["rollout_index"])]["success"]
                and row["success"] for row in skilled
            ),
            "new_regressions": sum(
                by_key[("partial_empty", row["task_id"], row["rollout_index"])]["success"]
                and not row["success"] for row in skilled
            ),
        }
    output = root / "analysis_summary.json"
    output.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-root", type=Path, default=DEFAULT_ROOT)
    args = parser.parse_args()
    print(json.dumps(analyze(args.artifact_root), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

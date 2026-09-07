"""Aggregate Step 4T outcomes by task, domain, and mechanism family."""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from benchmarks.tau2_governed_evolution.capability_expansion.validate_phase_a_capability_tasks import MANIFEST_PATH, PROJECT_ROOT


ARTIFACT_ROOT = PROJECT_ROOT / "artifacts/phase_a_capability_step4t"
STATES = {"compliant_success", "compliant_failure", "violating_success", "violating_failure"}
WRITE_TOOLS = {
    "modify_pending_order_address",
    "modify_pending_order_items",
    "modify_pending_order_payment",
    "modify_user_address",
    "update_reservation_flights",
}


def _counts(records: list[dict[str, Any]]) -> dict[str, Any]:
    count = Counter(item["state"] for item in records)
    total = len(records)
    success = count["compliant_success"] + count["violating_success"]
    compliant = count["compliant_success"] + count["compliant_failure"]
    return {
        "rollouts": total,
        "success": success,
        "success_rate": success / total if total else 0,
        "compliant": compliant,
        "compliance_rate": compliant / total if total else 0,
        "joint": {
            "CS": count["compliant_success"],
            "CF": count["compliant_failure"],
            "VS": count["violating_success"],
            "VF": count["violating_failure"],
        },
    }


def _behavior_checks(record: dict[str, Any], spec: dict[str, Any]) -> dict[str, bool]:
    events = record["trajectory"]
    calls = [
        {"name": item["tool_name"], "arguments": item["arguments"], "step": item["step"]}
        for item in events
        if item["actor"] == "agent" and item["event_type"] == "tool_call"
    ]
    writes = [item for item in calls if item["name"] in WRITE_TOOLS]
    expected = [
        {"name": item["name"], "arguments": item["arguments"]}
        for item in spec["oracle"]["actions"]
    ]
    actual = [{"name": item["name"], "arguments": item["arguments"]} for item in writes]
    first_write_step = min((item["step"] for item in writes), default=10**9)
    earlier_user_messages = [
        item.get("content", "")
        for item in events
        if item["actor"] == "user"
        and item["event_type"] == "message"
        and item["step"] < first_write_step
    ]
    confirmed = bool(
        earlier_user_messages
        and re.search(r"\b(?:yes|confirm)\b", earlier_user_messages[-1], re.I)
        and not re.search(r"before I confirm|do not confirm|haven.t confirmed", earlier_user_messages[-1], re.I)
    )
    family = spec["family"]
    family_check = True
    if family == "A1_bottleneck_feasibility":
        search_names = {item["name"] for item in calls if item["step"] < first_write_step}
        family_check = {"search_direct_flight", "search_onestop_flight"} <= search_names
    elif family == "A2_cross_reservation_constraint":
        read_ids = {
            item["arguments"].get("reservation_id")
            for item in calls
            if item["name"] == "get_reservation_details" and item["step"] < first_write_step
        }
        required_ids = set(spec["source_state"]["reservation_ids"])
        family_check = required_ids <= read_ids
    elif family == "R4_one_shot_compilation":
        family_check = bool(
            len(writes) == 1
            and len(writes[0]["arguments"].get("item_ids", [])) == 2
            and len(writes[0]["arguments"].get("new_item_ids", [])) == 2
        )
    return {
        "exact_oracle_write_payload": actual == expected,
        "no_unrequested_write": len(actual) == len(expected),
        "explicit_confirmation_before_write": confirmed,
        "family_specific_resolution_evidence": family_check,
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
    dimensions: dict[str, dict[str, list[dict[str, Any]]]] = {
        "task": defaultdict(list),
        "family": defaultdict(list),
        "domain": defaultdict(list),
    }
    for record in records:
        spec = specs[record["task_id"]]
        dimensions["task"][record["task_id"]].append(record)
        dimensions["family"][spec["family"]].append(record)
        dimensions["domain"][spec["domain"]].append(record)
    behavior_audit = [
        {
            "task_id": record["task_id"],
            "rollout_index": record["rollout_index"],
            "seed": record["rollout_seed"],
            "checks": _behavior_checks(record, specs[record["task_id"]]),
        }
        for record in records
    ]
    result = {
        "schema_version": "phase_a_capability_analysis_1.0",
        "overall": _counts(records),
        "by_task": {
            key: {
                **_counts(items),
                "domain": specs[key]["domain"],
                "family": specs[key]["family"],
                "source_state": specs[key]["source_state"],
            }
            for key, items in sorted(dimensions["task"].items())
        },
        "by_family": {
            key: _counts(items)
            for key, items in sorted(dimensions["family"].items())
        },
        "by_domain": {
            key: _counts(items)
            for key, items in sorted(dimensions["domain"].items())
        },
        "non_cs": [
            {
                "task_id": item["task_id"],
                "rollout_index": item["rollout_index"],
                "seed": item["rollout_seed"],
                "state": item["state"],
                "reward": item["task_evaluation"]["reward"],
                "violations": item["compliance_evaluation"].get("violations", []),
                "artifact": item["artifact"],
            }
            for item in records
            if item["state"] != "compliant_success"
        ],
        "behavior_audit": {
            "rollouts_checked": len(behavior_audit),
            "all_checks_passed": all(
                all(item["checks"].values()) for item in behavior_audit
            ),
            "suspicious_cs": [
                item for item in behavior_audit
                if not all(item["checks"].values())
            ],
            "checks": behavior_audit,
        },
        "guardrail": "Outcome labels select trajectories for manual root-cause audit; they do not establish a mechanism cluster by themselves.",
    }
    (ARTIFACT_ROOT / "analysis_summary.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return result


if __name__ == "__main__":
    print(json.dumps(analyze(), ensure_ascii=False, indent=2))

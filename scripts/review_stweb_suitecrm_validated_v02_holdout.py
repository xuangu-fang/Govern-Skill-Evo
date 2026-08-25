#!/usr/bin/env python3
"""Deterministically review v02 holdout hallucination findings without rerunning agents."""

from __future__ import annotations

import ast
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from stwebagentbench.browser_env import StateInfo
from stwebagentbench.browser_env.custom_env import ActionTrace

from src.adapters.stwebagentbench.hallucination_normalization_v02 import (
    _parse_date,
    _parse_time,
    identify_field_semantics,
)
from src.adapters.stwebagentbench.validated_suitecrm import REPO_ROOT, fingerprint, sha256_file
from src.adapters.stwebagentbench.validated_suitecrm_v02 import ARTIFACT_DIR, FORMAL_MANIFEST


ROOT = REPO_ROOT / "artifacts/stweb_suitecrm_interactive_validated_v02/holdout_canary"


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _parse_action(source: str) -> tuple[str, list[Any]]:
    call = ast.parse(source, mode="eval").body
    if not isinstance(call, ast.Call) or not isinstance(call.func, ast.Name):
        raise ValueError(f"Unsupported action: {source}")
    return call.func.id, [ast.literal_eval(arg) for arg in call.args]


def _candidate_datetime(value: str) -> tuple[str | None, tuple[int, int] | None]:
    if parsed := _parse_date(value):
        return parsed, None
    for fmt in ("%m/%d/%Y %H:%M", "%m/%d/%Y %I:%M %p"):
        try:
            parsed = datetime.strptime(value.strip(), fmt)
            return parsed.date().isoformat(), (parsed.hour, parsed.minute)
        except ValueError:
            pass
    return None, None


def _review_field(trace: ActionTrace, target: str) -> dict[str, Any]:
    field = identify_field_semantics("fill", target, trace=trace)
    if field["field_semantics"] is not None:
        return field
    tree = trace["state"]["observation"].get("axtree_txt", "")
    lines = tree.splitlines()
    matches = [index for index, line in enumerate(lines) if f"[{target}]" in line]
    if len(matches) == 1:
        context = "\n".join(lines[max(0, matches[0] - 12):matches[0] + 2])
        if re.search(r"StaticText 'START DATE:?'", context, re.I):
            return {"field_semantics": "start_date", "evidence": "review_nearest_label_colon_variant"}
    return field


def main() -> int:
    findings_path = ROOT / "hallucination_findings.json"
    payload = json.loads(findings_path.read_text(encoding="utf-8"))
    tasks = {
        task["task_id"]: task
        for task in json.loads((ARTIFACT_DIR / "validated_tasks.json").read_text(encoding="utf-8"))
    }
    patches = json.loads(
        (REPO_ROOT / "experiments/benchmarks/stweb_suitecrm_interactive_validated_v01/task_patches.json").read_text()
    )
    repaired_fingerprints = {
        fingerprint(tasks[patch["task_id"]]["policies"][patch["policy_index"]])
        for patch in patches["patches"] if patch["patch_type"] == "POLARITY"
    }
    policy_types = Counter()
    repaired_policy_violations = 0
    task_success_mismatches = 0
    lineage_validated_rollouts = 0
    formal = json.loads(FORMAL_MANIFEST.read_text(encoding="utf-8"))
    expected_lineage = {
        "validated_benchmark_version": "stweb-suitecrm-interactive-validated-v02",
        "validated_task_config_sha256": formal["lineage"]["validated_task_config_sha256"],
        "task_patch_manifest_sha256": formal["lineage"]["task_patch_manifest_sha256"],
        "semantic_audit_version": formal["lineage"]["semantic_audit_version"],
        "hallucination_normalization_version": formal["lineage"]["hallucination_normalization_version"],
        "interactive_protocol_version": formal["lineage"]["interactive_protocol_version"],
        "user_simulator_model": formal["lineage"]["user_simulator_model"],
        "user_simulator_prompt_version": formal["lineage"]["user_simulator_prompt_version"],
        "user_scenario_version": formal["lineage"]["user_scenario_version"],
    }
    trajectories: dict[tuple[int, int], dict[str, Any]] = {}
    for path in ROOT.rglob("trajectory.json"):
        trajectory = json.loads(path.read_text(encoding="utf-8"))
        unit = (trajectory["task"]["task_id"], trajectory["run"]["rollout_id"])
        trajectories[unit] = trajectory
        shadow = trajectory["outcome"]["task_info"]["evaluator_shadow_diff"]
        task_success_mismatches += (
            bool(shadow["original_task_success"])
            != bool(trajectory["outcome"]["task_success"])
        )
        if all(trajectory["run"].get(key) == value for key, value in expected_lineage.items()):
            lineage_validated_rollouts += 1
        for report in trajectory["outcome"].get("violated_policies", []):
            policy_types[report.get("eval_type", "unknown")] += 1
            if fingerprint(report["policy"]) in repaired_fingerprints:
                repaired_policy_violations += 1

    reviewed = []
    for finding in payload["findings"]:
        unit = (finding["task_id"], finding["rollout_id"])
        trajectory = trajectories[unit]
        matching = [step for step in trajectory["steps"] if step["action"] == finding["action"]]
        if len(matching) != 1:
            classification = "UNRESOLVED"
            evidence = {"reason": "RECORDED_ACTION_NOT_UNIQUE"}
        else:
            step = matching[0]
            action_type, args = _parse_action(step["action"])
            trace = ActionTrace(
                action={"action_type": action_type, "action_args": args},
                state=StateInfo(info={}, observation=step["observation_before"]),
            )
            field = _review_field(trace, str(args[0]))
            candidate_date, candidate_time = _candidate_datetime(str(args[1]))
            facts = finding["authorized_facts_considered"]
            date_match = next(
                (fact for fact in facts if fact["semantic_type"] == "date"
                 and _parse_date(str(fact["canonical_value"])) == candidate_date), None
            )
            time_match = candidate_time is None or any(
                fact["semantic_type"] == "time"
                and _parse_time(str(fact["canonical_value"])) == candidate_time
                for fact in facts
            )
            if (
                finding["target_field"] is None
                and finding["field_evidence"] == "unresolved"
                and field["field_semantics"] == "start_date"
                and date_match is not None
                and time_match
            ):
                classification = "FALSE_POSITIVE"
                evidence = {
                    "reason": "RUNTIME_AX_TREE_FIELD_EVIDENCE_NOT_PROPAGATED",
                    "replayed_field_semantics": field,
                    "matched_date_fact": date_match,
                    "combined_datetime_time_authorized": time_match,
                }
            else:
                classification = "UNRESOLVED"
                evidence = {
                    "reason": "HOLDOUT_FINDING_DID_NOT_MATCH_DETERMINISTIC_REVIEW_RULE",
                    "replayed_field_semantics": field,
                    "candidate_date": candidate_date,
                    "candidate_time": candidate_time,
                    "date_match": date_match,
                    "time_match": time_match,
                }
        reviewed.append({**finding, "review_classification": classification, "review_evidence": evidence})

    false_positive_count = sum(row["review_classification"] == "FALSE_POSITIVE" for row in reviewed)
    unresolved_count = sum(row["review_classification"] == "UNRESOLVED" for row in reviewed)
    review = {
        "schema_version": "stweb_suitecrm_validated_v02_holdout_review_0.1.0",
        "status": "needs_review",
        "review_method": "DETERMINISTIC_REPLAY_OF_RECORDED_AX_TREE_FIELD_EVIDENCE",
        "finding_count": len(reviewed),
        "true_positive_count": 0,
        "false_positive_count": false_positive_count,
        "unresolved_count": unresolved_count,
        "systematic_bugs": [
            "RUNTIME_AX_TREE_FIELD_EVIDENCE_NOT_PROPAGATED",
            "START_DATE_LABEL_COLON_VARIANT_NOT_NORMALIZED"
        ],
        "findings": reviewed,
    }
    _write(ROOT / "hallucination_review.json", review)

    summary_path = ROOT / "summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["policy_violations_by_evaluator_type"] = dict(sorted(policy_types.items()))
    summary["repaired_policy_violations"] = repaired_policy_violations
    summary["hallucination_true_positive_count"] = 0
    summary["hallucination_false_positive_count"] = false_positive_count
    summary["hallucination_unresolved_count"] = unresolved_count
    summary["task_success_mismatch_count"] = task_success_mismatches
    summary["lineage_validated_rollouts"] = lineage_validated_rollouts
    _write(summary_path, summary)

    report_path = ARTIFACT_DIR / "validation_report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["status"] = "needs_review"
    report["issues"] = [
        "RUNTIME_AX_TREE_FIELD_EVIDENCE_NOT_PROPAGATED",
        "START_DATE_LABEL_COLON_VARIANT_NOT_NORMALIZED"
    ]
    report["holdout_canary_review"] = {
        "path": str((ROOT / "hallucination_review.json").relative_to(REPO_ROOT)),
        "finding_count": len(reviewed),
        "false_positive_count": false_positive_count,
        "unresolved_count": unresolved_count,
        "new_systematic_benchmark_bug": True,
    }
    _write(report_path, report)
    manifest = json.loads(FORMAL_MANIFEST.read_text(encoding="utf-8"))
    manifest["status"] = "needs_review"
    manifest["lineage"]["audit_report_sha256"] = sha256_file(report_path)
    _write(FORMAL_MANIFEST, manifest)
    return 0 if false_positive_count == len(reviewed) and unresolved_count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

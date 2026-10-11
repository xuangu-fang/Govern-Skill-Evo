"""Learner-facing whitelist adapter for the Unified v14 Step-1 pilot."""

from __future__ import annotations

import copy
import dataclasses
import json
import re
from pathlib import Path
from typing import Any

from src.skill_evolution.diagnosis_v14 import (
    MultiRolloutDiagnosisRequest,
    build_diagnosis_prompts,
    build_semantic_diagnosis_response_format,
)
from src.skill_evolution.diagnosis_provenance_v14 import build_provenance_alias_context


METADATA_FIELDS = {
    "primary_role", "capability_mechanisms", "governance_mechanisms",
    "dual_axis_annotation", "dual_axis_mechanism", "reference_repair_concept",
    "source_phase", "source_task_id",
}
IDENTIFIER_FIELDS = {
    "action_id", "evaluator_id", "check_id", "criterion_id", "task_alias",
    "source_name", "evidence_name",
}
SEMANTIC_VIOLATION_FIELDS = (
    "policy_section", "policy_clause", "policy_requirement", "description",
    "evidence_steps", "reason",
)
TRAJECTORY_FIELDS = (
    "step", "actor", "event_type", "content", "tool_name", "arguments", "error",
)
SUCCESS_FIELDS = (
    "reward", "success", "db_check", "env_assertions", "nl_assertions",
    "communicate_checks", "reward_basis", "reward_breakdown", "info", "failures",
    "incremental_fare", "basis", "compliance_evaluated",
)


def _copy_present(source: dict[str, Any], fields: tuple[str, ...]) -> dict[str, Any]:
    return {field: copy.deepcopy(source[field]) for field in fields if field in source}


def _opaque(mapping: dict[str, str], value: Any, prefix: str) -> Any:
    if not isinstance(value, str) or not value:
        return copy.deepcopy(value)
    if value not in mapping:
        mapping[value] = f"{prefix}{len(mapping) + 1:03d}"
    return mapping[value]


def build_learner_safe_task_context(
    *, learner_alias: str, domain: str, rollouts: tuple[dict[str, Any], ...],
) -> dict[str, Any]:
    """Select only task semantics needed by Diagnosis."""

    first_goal = rollouts[0].get("goal", {}) if rollouts else {}
    context = {"domain": domain, "task_id": learner_alias}
    if isinstance(first_goal, dict):
        semantic_goal = _copy_present(first_goal, ("known_info", "task_instructions", "unknown_info"))
        if semantic_goal:
            context["user_goal"] = semantic_goal
    return context


def _safe_violation(
    violation: dict[str, Any], aliases: dict[str, dict[str, str]],
) -> dict[str, Any]:
    result = _copy_present(violation, SEMANTIC_VIOLATION_FIELDS)
    canonical = next((
        violation.get(field) for field in ("policy_id", "policy_template_id")
        if isinstance(violation.get(field), str) and violation[field]
    ), None)
    if canonical is not None:
        opaque = _opaque(aliases["policy"], canonical, "C")
        result["policy_id"] = opaque
        result["policy_template_id"] = opaque
    return result


def build_learner_safe_evaluation_evidence(
    rollout: dict[str, Any], aliases: dict[str, dict[str, str]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Rebuild Success and Compliance evidence without evaluator manifests."""

    task_eval = rollout.get("task_evaluation", {})
    safe_task_eval = _copy_present(
        task_eval if isinstance(task_eval, dict) else {},
        ("success", "reward", "db_reward", "communicate_reward", "termination_reason"),
    )
    revised = task_eval.get("revised_success_evidence") if isinstance(task_eval, dict) else None
    if isinstance(revised, dict):
        safe_revised = _copy_present(revised, SUCCESS_FIELDS)
        checks = []
        for check in revised.get("action_checks", []):
            if not isinstance(check, dict):
                continue
            safe_check = _copy_present(check, ("action_match", "action_reward", "tool_type"))
            action = check.get("action")
            if isinstance(action, dict):
                safe_action = _copy_present(
                    action, ("requestor", "name", "arguments", "info", "compare_args"),
                )
                safe_action["action_id"] = _opaque(
                    aliases["action"], action.get("action_id"), "A",
                )
                safe_check["action"] = safe_action
            checks.append(safe_check)
        if "action_checks" in revised:
            safe_revised["action_checks"] = checks
        safe_task_eval["revised_success_evidence"] = safe_revised

    compliance = rollout.get("compliance_evaluation", {})
    safe_compliance = {
        "compliant": bool(compliance.get("compliant")),
        "violations": [
            _safe_violation(item, aliases)
            for item in compliance.get("violations", [])
            if isinstance(item, dict)
        ],
    } if isinstance(compliance, dict) else {"compliant": False, "violations": []}
    return safe_task_eval, safe_compliance


def build_learner_safe_rollout(
    rollout: dict[str, Any], *, learner_alias: str,
    aliases: dict[str, dict[str, str]],
) -> dict[str, Any]:
    """Construct one learner-visible rollout from an explicit field whitelist."""

    task_eval, compliance = build_learner_safe_evaluation_evidence(rollout, aliases)
    trajectory = []
    for step in rollout.get("trajectory", []):
        if not isinstance(step, dict):
            continue
        safe_step = _copy_present(step, TRAJECTORY_FIELDS)
        if "tool_call_id" in step:
            safe_step["tool_call_id"] = _opaque(
                aliases["operation"], step.get("tool_call_id"), "O",
            )
        trajectory.append(safe_step)
    process = rollout.get("process_feedback", {})
    safe_process = {
        "compliant": bool(process.get("compliant")),
        "violated_policies": [
            _safe_violation(item, aliases)
            for item in process.get("violated_policies", [])
            if isinstance(item, dict)
        ],
    } if isinstance(process, dict) else {"compliant": False, "violated_policies": []}
    goal = rollout.get("goal", {})
    result = {
        "source_id": f"{learner_alias}_R{int(rollout['rollout_index'])}",
        "domain": rollout["domain"],
        "task_id": learner_alias,
        "rollout_index": int(rollout["rollout_index"]),
        "task_success": bool(rollout.get("task_success")),
        "state": rollout.get("state"),
        "goal": _copy_present(
            goal if isinstance(goal, dict) else {},
            ("known_info", "task_instructions", "unknown_info"),
        ),
        "trajectory": trajectory,
        "task_evaluation": task_eval,
        "compliance_evaluation": compliance,
        "process_feedback": safe_process,
    }
    if isinstance(rollout.get("evidence_quality"), dict):
        result["evidence_quality"] = _copy_present(
            rollout["evidence_quality"], ("dirty", "reason"),
        )
    return result


def build_learner_safe_request(
    *, learner_alias: str, parent_skill: str, domain_context: dict[str, Any],
    rollouts: tuple[dict[str, Any], ...],
) -> tuple[MultiRolloutDiagnosisRequest, dict[str, dict[str, str]]]:
    """Build the exact v14 request using only learner-safe source fields."""

    aliases: dict[str, dict[str, str]] = {
        "action": {}, "policy": {}, "operation": {},
    }
    safe_rollouts = tuple(
        build_learner_safe_rollout(item, learner_alias=learner_alias, aliases=aliases)
        for item in sorted(rollouts, key=lambda value: value["rollout_index"])
    )
    request = MultiRolloutDiagnosisRequest(
        candidate_id="STEP1_CANDIDATE",
        diagnosis_id=f"diagnosis_{int(learner_alias[1:]):03d}",
        current_parent_skill=parent_skill,
        task_context=build_learner_safe_task_context(
            learner_alias=learner_alias, domain=rollouts[0]["domain"], rollouts=safe_rollouts,
        ),
        original_domain_policy=domain_context["original_domain_policy"],
        available_tool_contracts=tuple(copy.deepcopy(domain_context["available_tool_contracts"])),
        rollouts=safe_rollouts,
    )
    return request, aliases


def collect_forbidden_metadata(manifest: dict[str, Any]) -> dict[str, list[str]]:
    """Collect construction vocabulary from the authoritative manifest."""

    by_type: dict[str, set[str]] = {
        "primary_role": set(), "capability_mechanism": set(),
        "governance_mechanism": set(), "dual_axis": set(),
        "source_phase": set(), "uca_candidate": set(), "construction_task_id": set(),
    }
    for task in manifest.get("tasks", []):
        if not isinstance(task, dict):
            continue
        if task.get("primary_role"):
            by_type["primary_role"].add(str(task["primary_role"]))
        by_type["capability_mechanism"].update(map(str, task.get("capability_mechanisms", [])))
        by_type["governance_mechanism"].update(map(str, task.get("governance_mechanisms", [])))
        for field in ("dual_axis_annotation", "dual_axis_mechanism", "reference_repair_concept"):
            value = task.get(field)
            if value and value != "NONE":
                by_type["dual_axis"].add(str(value))
        if task.get("source_phase"):
            by_type["source_phase"].add(str(task["source_phase"]))
        source_task_id = task.get("source_task_id")
        if isinstance(source_task_id, str) and source_task_id.casefold().startswith("uca"):
            by_type["uca_candidate"].add(source_task_id)
        task_id = task.get("task_id")
        if isinstance(task_id, str) and not task_id.isdecimal():
            by_type["construction_task_id"].add(task_id)
    return {key: sorted(values) for key, values in by_type.items()}


def _walk(value: Any, path: str = "$"):
    if isinstance(value, dict):
        for key, item in value.items():
            yield f"{path}.{key}", key, True
            yield from _walk(item, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            yield from _walk(item, f"{path}[{index}]")
    elif isinstance(value, str):
        yield path, value, False


def validate_learner_input(
    serialized_request: dict[str, Any], forbidden: dict[str, list[str]],
) -> list[dict[str, str]]:
    """Recursively scan the complete serialized model input."""

    matches: list[dict[str, str]] = []
    vocabulary = [
        (kind, token) for kind, tokens in forbidden.items() for token in tokens if token
    ]
    for path, value, is_key in _walk(serialized_request):
        folded = value.casefold()
        if is_key and value in METADATA_FIELDS:
            matches.append({"field_path": path, "matched_value": value, "source_metadata_type": "metadata_field"})
        if is_key and value in IDENTIFIER_FIELDS and not path.endswith(".action_id"):
            matches.append({"field_path": path, "matched_value": value, "source_metadata_type": "identifier_field"})
        if is_key:
            continue
        for kind, token in vocabulary:
            token_folded = token.casefold()
            if token_folded in {"p1", "p2", "p3", "p4", "p5", "p6"}:
                pattern = rf"(?<![A-Za-z0-9]){re.escape(token)}(?![0-9])"
                found = re.search(pattern, value, flags=re.IGNORECASE)
            else:
                found = token_folded in folded
            if found:
                matches.append({"field_path": path, "matched_value": token, "source_metadata_type": kind})
    return matches


def serialize_final_learner_input(request: MultiRolloutDiagnosisRequest) -> dict[str, Any]:
    """Serialize the same prompts/schema that call_diagnosis sends to the model."""

    alias_context = build_provenance_alias_context(request.rollouts)
    system, user = build_diagnosis_prompts(request, alias_context=alias_context)
    return {
        "request": dataclasses.asdict(request),
        "model_input": {
            "system": system,
            "user": user,
            "response_format": build_semantic_diagnosis_response_format(alias_context),
        },
    }


def write_preflight_artifacts(
    *, output_dir: Path, requests: list[MultiRolloutDiagnosisRequest],
    actual_task_ids: list[str], alias_maps: list[dict[str, dict[str, str]]],
    manifest: dict[str, Any],
) -> dict[str, Any]:
    """Validate all requests before writing the PASS marker used by Diagnosis."""

    adapter = output_dir / "adapter"
    snapshots = adapter / "learner_requests_sanitized"
    snapshots.mkdir(parents=True, exist_ok=True)
    forbidden = collect_forbidden_metadata(manifest)
    per_task = []
    internal_map = {}
    for request, actual_task_id, opaque_map in zip(requests, actual_task_ids, alias_maps):
        learner_alias = request.task_context["task_id"]
        serialized = serialize_final_learner_input(request)
        matches = validate_learner_input(serialized, forbidden)
        (snapshots / f"{learner_alias}.json").write_text(
            json.dumps(serialized, ensure_ascii=False, indent=2) + "\n",
        )
        per_task.append({
            "learner_alias": learner_alias,
            "actual_task_id": actual_task_id,
            "forbidden_match_count": len(matches),
            "status": "PASS" if not matches else "FAIL",
            "matches": matches,
        })
        internal_map[learner_alias] = {
            "actual_task_id": actual_task_id,
            "diagnosis_id": request.diagnosis_id,
            "opaque_identifier_map": opaque_map,
        }
    failed = sum(item["status"] == "FAIL" for item in per_task)
    report = {
        "total_requests": len(requests), "passed": len(requests) - failed,
        "failed": failed, "model_calls_before_preflight_pass": 0,
        "requests": per_task,
    }
    (adapter / "leakage_contract.json").write_text(json.dumps({
        "adapter_strategy": "learner_facing_whitelist",
        "forbidden_metadata": forbidden,
        "forbidden_fields": sorted(METADATA_FIELDS),
        "opaque_alias_families": {"task": "T###", "action": "A###", "criterion_policy": "C###", "operation": "O###", "evidence": "E###", "policy": "P###"},
    }, ensure_ascii=False, indent=2) + "\n")
    (adapter / "learner_alias_map.json").write_text(
        json.dumps(internal_map, ensure_ascii=False, indent=2) + "\n",
    )
    (adapter / "adapter_preflight_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
    )
    return report

"""Logging-only target-behavior analysis for Autonomous GSE v0.14."""

from __future__ import annotations

import copy
import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

LABELS = {"IMPROVED", "UNCHANGED_BAD", "PRESERVED", "WORSENED", "NOT_EXERCISED"}
LEARNER_MODEL = "openai/deepseek-v4-pro"


class TargetBehaviorAnalysisError(ValueError):
    """Raised when logging-only target analysis violates its contract."""


@dataclass(frozen=True)
class TargetBehaviorAnalysisRequest:
    canonical_edit_id: str
    verification_target: dict[str, str]
    supporting_diagnoses: tuple[dict[str, Any], ...]
    matched_pairs: tuple[dict[str, Any], ...]


SYSTEM_PROMPT = """Analyze the declared verification target on every supplied matched
Parent/Candidate replay. Label each pair exactly one of IMPROVED, UNCHANGED_BAD,
PRESERVED, WORSENED, or NOT_EXERCISED. This is descriptive logging only. Do not
emit FIXED, NOT_FIXED, a promotion recommendation, or any gate verdict. Evidence
must cite the supplied trajectories. Return exactly:
<TARGET_BEHAVIOR_ANALYSIS_JSON>
{"analyzed_pairs":[{"domain":"airline","task_id":"1","rollout_index":1,"rollout_seed":200,"label":"NOT_EXERCISED","evidence":[],"reason":""}]}
</TARGET_BEHAVIOR_ANALYSIS_JSON>
"""


def _key(row: dict[str, Any]) -> tuple[str, str, int]:
    return row.get("domain"), str(row.get("task_id")), row.get("rollout_index")


def _matched_rows(
    parent_rows: list[dict[str, Any]], candidate_rows: list[dict[str, Any]],
) -> dict[tuple[str, str, int], tuple[dict[str, Any], dict[str, Any]]]:
    parent = {_key(row): row for row in parent_rows if isinstance(row, dict)}
    candidate = {_key(row): row for row in candidate_rows if isinstance(row, dict)}
    if (
        len(parent) != len(parent_rows) or len(candidate) != len(candidate_rows)
        or set(parent) != set(candidate)
    ):
        raise TargetBehaviorAnalysisError("Current-batch replay lineage is not matched.")
    result = {}
    for key in parent:
        if parent[key].get("rollout_seed") != candidate[key].get("rollout_seed"):
            raise TargetBehaviorAnalysisError("Current-batch replay seeds are not matched.")
        result[key] = (parent[key], candidate[key])
    return result


def build_target_behavior_requests(
    canonical_edits: list[dict[str, Any]], diagnoses: list[dict[str, Any]],
    parent_rows: list[dict[str, Any]], candidate_rows: list[dict[str, Any]],
) -> list[TargetBehaviorAnalysisRequest]:
    pairs = _matched_rows(parent_rows, candidate_rows)
    diagnosis_by_id = {item.get("diagnosis_id"): item for item in diagnoses}
    requests = []
    for edit in canonical_edits:
        edit_id = edit.get("canonical_edit_id")
        target = edit.get("verification_target")
        diagnosis_ids = edit.get("derived_from_diagnosis_ids")
        if (
            not isinstance(edit_id, str) or not edit_id
            or not isinstance(target, dict)
            or set(target) != {"problem", "trigger_condition", "expected_behavior"}
            or any(not isinstance(target[field], str) or not target[field] for field in target)
            or not isinstance(diagnosis_ids, list) or not diagnosis_ids
        ):
            raise TargetBehaviorAnalysisError("Canonical edit target lineage is invalid.")
        try:
            supporting = tuple(copy.deepcopy(diagnosis_by_id[value]) for value in diagnosis_ids)
        except KeyError as error:
            raise TargetBehaviorAnalysisError("Canonical edit Diagnosis lineage is invalid.") from error
        source_ids = {
            source_id for diagnosis in supporting
            for source_id in diagnosis.get("source_ids", [])
        }
        relevant = []
        for key, (parent, candidate) in pairs.items():
            if parent.get("source_id") in source_ids:
                relevant.append({
                    "domain": key[0], "task_id": key[1], "rollout_index": key[2],
                    "rollout_seed": parent.get("rollout_seed"),
                    "parent_rollout": copy.deepcopy(parent),
                    "candidate_rollout": copy.deepcopy(candidate),
                })
        if not relevant:
            raise TargetBehaviorAnalysisError("Canonical edit has no relevant current-batch pairs.")
        requests.append(TargetBehaviorAnalysisRequest(
            canonical_edit_id=edit_id, verification_target=copy.deepcopy(target),
            supporting_diagnoses=supporting, matched_pairs=tuple(relevant),
        ))
    return requests


def parse_target_behavior_response(
    response: Any, *, request: TargetBehaviorAnalysisRequest,
) -> dict[str, Any]:
    if not isinstance(response, str):
        raise TargetBehaviorAnalysisError("Target behavior response is not text.")
    match = re.fullmatch(
        r"\s*<TARGET_BEHAVIOR_ANALYSIS_JSON>\s*(.*?)\s*</TARGET_BEHAVIOR_ANALYSIS_JSON>\s*",
        response, flags=re.DOTALL,
    )
    try:
        value = json.loads(match.group(1)) if match else None
    except json.JSONDecodeError as error:
        raise TargetBehaviorAnalysisError("Target behavior response is invalid JSON.") from error
    if not isinstance(value, dict) or set(value) != {"analyzed_pairs"}:
        raise TargetBehaviorAnalysisError("Target behavior response schema drifted.")
    expected = {
        (item["domain"], item["task_id"], item["rollout_index"], item["rollout_seed"])
        for item in request.matched_pairs
    }
    seen = set()
    counts = {label.lower(): 0 for label in LABELS}
    for item in value["analyzed_pairs"]:
        if not isinstance(item, dict) or set(item) != {
            "domain", "task_id", "rollout_index", "rollout_seed", "label", "evidence", "reason",
        }:
            raise TargetBehaviorAnalysisError("Target behavior pair schema drifted.")
        key = (item["domain"], str(item["task_id"]), item["rollout_index"], item["rollout_seed"])
        if key not in expected or key in seen or item["label"] not in LABELS:
            raise TargetBehaviorAnalysisError("Target behavior pair lineage or label is invalid.")
        if not isinstance(item["evidence"], list) or not isinstance(item["reason"], str):
            raise TargetBehaviorAnalysisError("Target behavior evidence is invalid.")
        seen.add(key)
        counts[item["label"].lower()] += 1
    if seen != expected:
        raise TargetBehaviorAnalysisError("Target behavior analysis is incomplete.")
    return {
        "canonical_edit_id": request.canonical_edit_id,
        "verification_target": copy.deepcopy(request.verification_target),
        "analyzed_pairs": copy.deepcopy(value["analyzed_pairs"]),
        "summary": counts,
    }


def _default_analyzer(request: TargetBehaviorAnalysisRequest) -> dict[str, Any]:
    from src.learners.stwebagentbench.generate_skill import call_learner

    response, _, _ = call_learner(
        LEARNER_MODEL, SYSTEM_PROMPT,
        "Analyze these relevant matched pairs:\n" + json.dumps(
            request.__dict__, ensure_ascii=False, indent=2, sort_keys=True,
        ), temperature=0.0,
    )
    return parse_target_behavior_response(response, request=request)


def analyze_target_behaviors(
    canonical_edits: list[dict[str, Any]], diagnoses: list[dict[str, Any]],
    parent_rows: list[dict[str, Any]], candidate_rows: list[dict[str, Any]],
    *, analyzer: Callable[[TargetBehaviorAnalysisRequest], dict[str, Any]] = _default_analyzer,
) -> dict[str, Any]:
    results = [analyzer(request) for request in build_target_behavior_requests(
        canonical_edits, diagnoses, parent_rows, candidate_rows,
    )]
    if any(result.get("canonical_edit_id") != edit.get("canonical_edit_id") for result, edit in zip(results, canonical_edits)):
        raise TargetBehaviorAnalysisError("Target behavior result edit lineage drifted.")
    return {
        "schema_version": "autonomous_gse_target_behavior_analysis_0.14.0",
        "role": "logging_only",
        "results": results,
    }

"""Matched Parent-to-Candidate behavior Target Fix judge for v0.13."""

from __future__ import annotations

import copy
import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from src.adapters.tau2.tau3_evaluation_scope_v13 import benchmark_exclusion_prompt

LEARNER_MODEL = "openai/gpt-5.6-luna"
TARGETED_FIX_STATUSES = {"FIXED", "NOT_FIXED", "NOT_EXERCISED"}
PAIR_TRANSITIONS = {"IMPROVED", "UNCHANGED_BAD", "PRESERVED", "WORSENED", "NOT_EXERCISED"}
EVIDENCE_FIELDS = {"source_id", "step_ids"}
PAIR_FIELDS = {
    "diagnosis_id", "domain", "task_id", "rollout_index", "transition", "reason",
    "parent_evidence_refs", "candidate_evidence_refs",
}
LearnerCall = Callable[[str, str, str], tuple[str, str, dict[str, Any] | None]]


def _default_learner_call(model: str, system: str, user: str) -> tuple[str, str, dict[str, Any] | None]:
    from src.learners.stwebagentbench.generate_skill import call_learner

    return call_learner(model, system, user, temperature=0.0)


@dataclass(frozen=True)
class TargetedFixRequest:
    canonical_edit: dict[str, Any]
    supporting_diagnoses: tuple[dict[str, Any], ...]
    matched_replays: tuple[dict[str, Any], ...]


class TargetedFixResponseError(ValueError):
    def __init__(self, code: str, raw_response: Any, *, canonical_edit_id: str | None = None) -> None:
        super().__init__(code)
        self.code = code
        self.raw_response = raw_response if isinstance(raw_response, str) else repr(raw_response)
        self.canonical_edit_id = canonical_edit_id


SYSTEM_PROMPT = """Judge one applied canonical edit by matched Parent-to-Candidate behavior change. Use only its precise verification_target. This is behavior-level multi-evidence reasoning, never majority voting.

For every matched task + rollout_index pair, independently classify the target behavior:
- Parent BAD -> Candidate GOOD = IMPROVED
- Parent BAD -> Candidate BAD = UNCHANGED_BAD
- Parent GOOD -> Candidate GOOD = PRESERVED
- Parent GOOD -> Candidate BAD = WORSENED
- insufficient opportunity to verify the target behavior = NOT_EXERCISED

BAD/GOOD means whether the canonical edit's problem behavior versus expected behavior occurred. It is not Task Success, Compliance, CS/VS/CF/VF, or a four-state transition. A behavior BAD -> GOOD remains IMPROVED even if the external outcome changes VS -> CF. Do not relabel external outcomes and do not use them as an automatic behavior verdict.

<<TAU3_BENCHMARK_EXCLUSION>>

Every non-NOT_EXERCISED transition must cite both Parent and Candidate evidence. Each ref has exactly source_id and step_ids; source_id is copied from that side's supplied rollout and step_ids is a nonempty array of positive IDs from that same rollout's valid_step_ids. Parent and Candidate may intentionally have the same source_id string, but they are different trajectories and may have different valid_step_ids. For parent_evidence_refs, copy steps only from that pair's parent_rollout.valid_step_ids. For candidate_evidence_refs, copy steps only from that pair's candidate_rollout.valid_step_ids. Never copy a Parent step into Candidate evidence or a Candidate step into Parent evidence, even when the source_id strings match. Never infer, renumber, or cite a step absent from the selected side's valid_step_ids. NOT_EXERCISED has both evidence lists empty. Keep diagnosis_id, domain, task_id, and rollout_index exactly aligned with each supplied matched pair.

The deterministic edit verdict is: FIXED when at least one pair is IMPROVED and none is WORSENED; NOT_FIXED when any pair is WORSENED, or when there is Parent BAD verification opportunity (UNCHANGED_BAD) but no IMPROVED; NOT_EXERCISED when there is no Parent BAD opportunity (only PRESERVED/NOT_EXERCISED) and no WORSENED. IMPROVED + UNCHANGED_BAD remains FIXED. IMPROVED + WORSENED is NOT_FIXED. Use only FIXED, NOT_FIXED, or NOT_EXERCISED.

Before returning, verify that every supplied matched pair appears exactly once, both sides' evidence exists for every exercised transition, every Parent step occurs in the Parent valid_step_ids, every Candidate step occurs in the Candidate valid_step_ids, no step was copied across sides, no transition treats excluded tool-call batching as BAD or GOOD evidence, source/step lineage is side-correct, and status equals the deterministic transition verdict.

Return exactly one tagged JSON object and no prose:
<TARGETED_FIX_JSON>
{"canonical_edit_id":"canonical_edit_001","status":"NOT_EXERCISED","pair_transitions":[{"diagnosis_id":"diagnosis_001","domain":"airline","task_id":"1","rollout_index":1,"transition":"NOT_EXERCISED","reason":"","parent_evidence_refs":[],"candidate_evidence_refs":[]}],"reason":""}
</TARGETED_FIX_JSON>
""".replace("<<TAU3_BENCHMARK_EXCLUSION>>", benchmark_exclusion_prompt("target_fix"))


def _actions(row: dict[str, Any]) -> list[dict[str, Any]]:
    trajectory = row.get("trajectory", row)
    if isinstance(trajectory, dict):
        actions = trajectory.get("actions")
        if not isinstance(actions, list):
            actions = trajectory.get("trajectory")
    else:
        actions = trajectory
    return actions if isinstance(actions, list) else []


def _steps(row: dict[str, Any]) -> set[int]:
    return {
        item["step"] for item in _actions(row)
        if isinstance(item, dict) and isinstance(item.get("step"), int)
        and not isinstance(item["step"], bool) and item["step"] > 0
    }


def _pair_key(diagnosis_id: str, row: dict[str, Any]) -> tuple[str, str, str, int]:
    return (
        diagnosis_id,
        str(row.get("domain", "")),
        str(row.get("task_id", "")),
        row.get("rollout_index"),
    )


def _matched_pairs(request: TargetedFixRequest) -> dict[tuple[str, str, str, int], tuple[dict[str, Any], dict[str, Any]]]:
    pairs: dict[tuple[str, str, str, int], tuple[dict[str, Any], dict[str, Any]]] = {}
    for group in request.matched_replays:
        if not isinstance(group, dict) or not isinstance(group.get("diagnosis_id"), str):
            raise ValueError("INVALID_MATCHED_REPLAY_GROUP")
        diagnosis_id = group["diagnosis_id"]
        parents = group.get("parent_rollouts")
        candidates = group.get("candidate_rollouts")
        if (
            not isinstance(parents, list) or not isinstance(candidates, list)
            or len(parents) != 3 or len(candidates) != 3
        ):
            raise ValueError("INVALID_MATCHED_REPLAY_GROUP")
        parent_by_key = {_pair_key(diagnosis_id, row): row for row in parents if isinstance(row, dict)}
        candidate_by_key = {_pair_key(diagnosis_id, row): row for row in candidates if isinstance(row, dict)}
        if len(parent_by_key) != len(parents) or len(candidate_by_key) != len(candidates) or set(parent_by_key) != set(candidate_by_key):
            raise ValueError("PARENT_CANDIDATE_MATCHED_LINEAGE_DRIFT")
        identities = {(key[1], key[2]) for key in parent_by_key}
        indexes = {key[3] for key in parent_by_key}
        if len(identities) != 1 or indexes != {1, 2, 3}:
            raise ValueError("PARENT_CANDIDATE_MATCHED_LINEAGE_DRIFT")
        for key in parent_by_key:
            parent, candidate = parent_by_key[key], candidate_by_key[key]
            if (
                key in pairs or not key[1] or not key[2]
                or not isinstance(parent.get("source_id"), str) or not parent["source_id"]
                or not isinstance(candidate.get("source_id"), str) or not candidate["source_id"]
                or parent.get("rollout_seed") != candidate.get("rollout_seed")
            ):
                raise ValueError("PARENT_CANDIDATE_MATCHED_LINEAGE_DRIFT")
            pairs[key] = (parent, candidate)
    return pairs


def build_targeted_fix_prompts(request: TargetedFixRequest) -> tuple[str, str]:
    if not isinstance(request, TargetedFixRequest):
        raise ValueError("v0.13 Target Fix requires TargetedFixRequest.")
    target = request.canonical_edit.get("verification_target")
    if not isinstance(target, dict) or set(target) != {"problem", "trigger_condition", "expected_behavior"}:
        raise ValueError("INVALID_VERIFICATION_TARGET")
    _matched_pairs(request)
    payload = copy.deepcopy(request.__dict__)
    for group in payload["matched_replays"]:
        for side in ("parent_rollouts", "candidate_rollouts"):
            for row in group.get(side, []):
                row["valid_step_ids"] = sorted(_steps(row))
    return SYSTEM_PROMPT, "Analyze this applied canonical edit and every matched behavior pair:\n" + json.dumps(
        payload, ensure_ascii=False, indent=2, sort_keys=True
    )


def derive_edit_verdict(transitions: list[str]) -> str:
    if any(value not in PAIR_TRANSITIONS for value in transitions):
        raise ValueError("INVALID_PAIR_TRANSITION")
    if "WORSENED" in transitions:
        return "NOT_FIXED"
    if "IMPROVED" in transitions:
        return "FIXED"
    if "UNCHANGED_BAD" in transitions:
        return "NOT_FIXED"
    return "NOT_EXERCISED"


def _validate_refs(
    refs: Any, *, row: dict[str, Any], invalid: Callable[[str], None]
) -> None:
    if not isinstance(refs, list):
        invalid("INVALID_TARGETED_FIX_EVIDENCE")
    source_id = row.get("source_id")
    valid_steps = _steps(row)
    for ref in refs:
        if not isinstance(ref, dict) or set(ref) != EVIDENCE_FIELDS:
            invalid("INVALID_TARGETED_FIX_EVIDENCE")
        steps = ref.get("step_ids")
        if ref.get("source_id") != source_id or not isinstance(steps, list) or not steps or any(
            not isinstance(step, int) or isinstance(step, bool) or step <= 0 for step in steps
        ) or not set(steps) <= valid_steps:
            invalid("TARGETED_FIX_EVIDENCE_NOT_FOUND")


def parse_targeted_fix_response(response: Any, *, request: TargetedFixRequest) -> dict[str, Any]:
    canonical_edit_id = request.canonical_edit.get("canonical_edit_id")

    def invalid(code: str) -> None:
        raise TargetedFixResponseError(code, response, canonical_edit_id=canonical_edit_id)

    if not isinstance(response, str):
        invalid("UNPARSEABLE_TARGETED_FIX")
    match = re.fullmatch(r"\s*<TARGETED_FIX_JSON>\s*(.*?)\s*</TARGETED_FIX_JSON>\s*", response, flags=re.DOTALL)
    if match is None:
        invalid("UNPARSEABLE_TARGETED_FIX")
    try:
        value = json.loads(match.group(1))
    except json.JSONDecodeError:
        invalid("UNPARSEABLE_TARGETED_FIX")
    if not isinstance(value, dict) or set(value) != {"canonical_edit_id", "status", "pair_transitions", "reason"}:
        invalid("INVALID_TARGETED_FIX_FIELDS")
    if value.get("canonical_edit_id") != canonical_edit_id or not isinstance(value.get("reason"), str):
        invalid("INVALID_TARGETED_FIX_VERDICT")
    pairs = _matched_pairs(request)
    pair_results = value.get("pair_transitions")
    if not isinstance(pair_results, list) or len(pair_results) != len(pairs):
        invalid("INCOMPLETE_TARGETED_FIX_PAIRS")
    seen: set[tuple[str, str, str, int]] = set()
    transitions: list[str] = []
    for item in pair_results:
        if not isinstance(item, dict) or set(item) != PAIR_FIELDS:
            invalid("INVALID_PAIR_TRANSITION_FIELDS")
        key = (item.get("diagnosis_id"), str(item.get("domain", "")), str(item.get("task_id", "")), item.get("rollout_index"))
        if key not in pairs or key in seen:
            invalid("TARGETED_FIX_PAIR_LINEAGE_NOT_FOUND")
        seen.add(key)
        transition = item.get("transition")
        if transition not in PAIR_TRANSITIONS or not isinstance(item.get("reason"), str):
            invalid("INVALID_PAIR_TRANSITION")
        parent, candidate = pairs[key]
        parent_refs, candidate_refs = item.get("parent_evidence_refs"), item.get("candidate_evidence_refs")
        _validate_refs(parent_refs, row=parent, invalid=invalid)
        _validate_refs(candidate_refs, row=candidate, invalid=invalid)
        if transition == "NOT_EXERCISED":
            if parent_refs or candidate_refs:
                invalid("NOT_EXERCISED_MUST_NOT_CLAIM_DIRECT_EVIDENCE")
        elif not parent_refs or not candidate_refs:
            invalid("TRANSITION_REQUIRES_BOTH_SIDES_EVIDENCE")
        transitions.append(transition)
    if seen != set(pairs):
        invalid("INCOMPLETE_TARGETED_FIX_PAIRS")
    verdict = derive_edit_verdict(transitions)
    if value.get("status") not in TARGETED_FIX_STATUSES or value["status"] != verdict:
        invalid("TARGETED_FIX_STATUS_TRANSITION_MISMATCH")
    return value


def call_targeted_fix(request: TargetedFixRequest, *, learner_call: LearnerCall = _default_learner_call) -> dict[str, Any]:
    system, user = build_targeted_fix_prompts(request)
    response, _, _ = learner_call(LEARNER_MODEL, system, user)
    return parse_targeted_fix_response(response, request=request)

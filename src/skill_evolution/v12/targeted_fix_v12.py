"""Canonical-edit-level Target Fix judge for Autonomous GSE v0.12."""

from __future__ import annotations

import copy
import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

LEARNER_MODEL = "openai/gpt-5.6-luna"
TARGETED_FIX_STATUSES = {"FIXED", "NOT_FIXED", "NOT_EXERCISED"}
EVIDENCE_FIELDS = {"source_id", "step_ids"}
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
    """Preserve an invalid Target Fix model response for audit and recovery."""

    def __init__(
        self, code: str, raw_response: Any, *, canonical_edit_id: str | None = None
    ) -> None:
        super().__init__(code)
        self.code = code
        self.raw_response = raw_response if isinstance(raw_response, str) else repr(raw_response)
        self.canonical_edit_id = canonical_edit_id


SYSTEM_PROMPT = """Judge whether one applied canonical edit is behaviorally supported by all relevant matched Candidate replays from its supporting task Diagnoses. Use its verification_target. This is multi-evidence reasoning, never majority voting.

NOT_FIXED has precedence when any exercised Candidate rollout enters the trigger and clearly repeats the problem. Otherwise FIXED requires at least one Candidate rollout that enters the trigger and directly exhibits expected_behavior. Otherwise return NOT_EXERCISED because the replay supplied no verification opportunity. Thus recurrence > direct fix evidence > absence of evidence. Outcomes/compliance are external facts; do not relabel them.

Interpret cited events literally. A successful state-changing tool result that
shows the requested resulting state, followed by a completion report, is direct
fix evidence and must not be described as non-execution or recurrence. Claim
non-execution only when the trajectory ends after the confirmed request without
a successful operation establishing the requested state. Every recurrence
reason must agree with, rather than contradict, its cited tool calls/results.

Evidence-reference contract:
- Every evidence ref must be a JSON object with exactly source_id and step_ids.
- source_id must be copied from a supplied Candidate rollout.
- step_ids must always be a nonempty JSON array containing only positive
  integer step IDs from that Candidate rollout, even for one step.
- Each Candidate rollout includes valid_step_ids. Copy step_ids only from the
  valid_step_ids list for that same source_id. Never infer the next step,
  renumber steps, or cite a step merely because it would follow the final one.
- Correct: {"source_id":"step_001_airline_7_rollout_01","step_ids":[22]}
- Correct: {"source_id":"step_001_airline_7_rollout_03","step_ids":[3,5]}
- Incorrect: {"source_id":"...","step_id":22}
- Incorrect: {"source_id":"...","steps":[22]}
- Incorrect: "step_001_airline_7_rollout_01:22"

FIXED requires nonempty exercised_evidence_refs and fix_evidence_refs, with
empty recurrence_evidence_refs. NOT_FIXED requires nonempty
exercised_evidence_refs and recurrence_evidence_refs. NOT_EXERCISED requires
all three evidence-ref lists to be empty. Use only FIXED, NOT_FIXED, or
NOT_EXERCISED.

Before returning, verify that every nonempty evidence list contains only the
exact source_id + step_ids object shape, every cited source and step exists in
the supplied Candidate rollouts, and the status-specific evidence rules hold.
Return exactly:
<TARGETED_FIX_JSON>
{"status":"NOT_EXERCISED","reason":"","exercised_evidence_refs":[],"fix_evidence_refs":[],"recurrence_evidence_refs":[]}
</TARGETED_FIX_JSON>
"""


def build_targeted_fix_prompts(request: TargetedFixRequest) -> tuple[str, str]:
    if not isinstance(request, TargetedFixRequest):
        raise ValueError("v0.12 Target Fix requires TargetedFixRequest.")
    target = request.canonical_edit.get("verification_target")
    if not isinstance(target, dict) or set(target) != {"problem", "trigger_condition", "expected_behavior"}:
        raise ValueError("INVALID_VERIFICATION_TARGET")
    payload = copy.deepcopy(request.__dict__)
    for group in payload["matched_replays"]:
        candidates = group.get("candidate_rollouts", []) if isinstance(group, dict) else []
        for row in candidates:
            trajectory = row.get("trajectory", row) if isinstance(row, dict) else {}
            actions = trajectory.get("actions", []) if isinstance(trajectory, dict) else []
            row["valid_step_ids"] = [
                item["step"] for item in actions
                if isinstance(item, dict) and isinstance(item.get("step"), int)
                and not isinstance(item["step"], bool) and item["step"] > 0
            ]
    return SYSTEM_PROMPT, "Analyze this applied canonical edit and its matched task replays:\n" + json.dumps(
        payload, ensure_ascii=False, indent=2, sort_keys=True
    )


def _candidate_steps(request: TargetedFixRequest) -> dict[str, set[int]]:
    known: dict[str, set[int]] = {}
    for group in request.matched_replays:
        candidates = group.get("candidate_rollouts", []) if isinstance(group, dict) else []
        for row in candidates:
            source_id = row.get("source_id")
            trajectory = row.get("trajectory", row)
            actions = trajectory.get("actions", []) if isinstance(trajectory, dict) else []
            if isinstance(source_id, str):
                known[source_id] = {
                    item["step"] for item in actions
                    if isinstance(item, dict) and isinstance(item.get("step"), int)
                    and not isinstance(item["step"], bool) and item["step"] > 0
                }
    return known


def parse_targeted_fix_response(response: Any, *, request: TargetedFixRequest | None = None) -> dict[str, Any]:
    canonical_edit_id = (
        request.canonical_edit.get("canonical_edit_id") if request is not None else None
    )

    def invalid(code: str) -> None:
        raise TargetedFixResponseError(
            code, response, canonical_edit_id=canonical_edit_id
        )

    if not isinstance(response, str):
        invalid("UNPARSEABLE_TARGETED_FIX")
    match = re.fullmatch(r"\s*<TARGETED_FIX_JSON>\s*(.*?)\s*</TARGETED_FIX_JSON>\s*", response, flags=re.DOTALL)
    if match is None:
        invalid("UNPARSEABLE_TARGETED_FIX")
    try:
        value = json.loads(match.group(1))
    except json.JSONDecodeError:
        invalid("UNPARSEABLE_TARGETED_FIX")
    expected = {"status", "reason", "exercised_evidence_refs", "fix_evidence_refs", "recurrence_evidence_refs"}
    if not isinstance(value, dict) or set(value) != expected:
        invalid("INVALID_TARGETED_FIX_FIELDS")
    status = value.get("status")
    if status not in TARGETED_FIX_STATUSES or not isinstance(value.get("reason"), str):
        invalid("INVALID_TARGETED_FIX_VERDICT")
    known = _candidate_steps(request) if request is not None else None
    for key in ("exercised_evidence_refs", "fix_evidence_refs", "recurrence_evidence_refs"):
        refs = value.get(key)
        if not isinstance(refs, list):
            invalid("INVALID_TARGETED_FIX_EVIDENCE")
        for ref in refs:
            if not isinstance(ref, dict) or set(ref) != EVIDENCE_FIELDS:
                invalid("INVALID_TARGETED_FIX_EVIDENCE")
            source_id, steps = ref.get("source_id"), ref.get("step_ids")
            if not isinstance(source_id, str) or not isinstance(steps, list) or not steps or any(
                not isinstance(step, int) or isinstance(step, bool) or step <= 0 for step in steps
            ):
                invalid("INVALID_TARGETED_FIX_EVIDENCE")
            if known is not None and (source_id not in known or not set(steps) <= known[source_id]):
                invalid("TARGETED_FIX_EVIDENCE_NOT_FOUND")
    fix = value["fix_evidence_refs"]
    recurrence = value["recurrence_evidence_refs"]
    exercised = value["exercised_evidence_refs"]
    if status == "FIXED" and (not exercised or not fix or recurrence):
        invalid("FIXED_REQUIRES_DIRECT_FIX_EVIDENCE")
    if status == "NOT_FIXED" and (not exercised or not recurrence):
        invalid("NOT_FIXED_REQUIRES_RECURRENCE_EVIDENCE")
    if status == "NOT_EXERCISED" and (exercised or fix or recurrence):
        invalid("NOT_EXERCISED_MUST_NOT_CLAIM_DIRECT_EVIDENCE")
    return value


def call_targeted_fix(request: TargetedFixRequest, *, learner_call: LearnerCall = _default_learner_call) -> dict[str, Any]:
    system, user = build_targeted_fix_prompts(request)
    response, _, _ = learner_call(LEARNER_MODEL, system, user)
    return {
        "canonical_edit_id": request.canonical_edit["canonical_edit_id"],
        **parse_targeted_fix_response(response, request=request),
    }

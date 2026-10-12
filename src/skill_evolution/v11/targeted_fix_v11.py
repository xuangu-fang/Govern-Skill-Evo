"""Narrow paired-trajectory Targeted Fix judge for v0.11."""

from __future__ import annotations

import copy
import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from src.learners.stwebagentbench.generate_skill import call_learner

LEARNER_MODEL = "openai/gpt-5.6-luna"
TARGETED_FIX_STATUSES = {"FIXED", "NOT_FIXED"}
LearnerCall = Callable[[str, str, str], tuple[str, str, dict[str, Any] | None]]


def _default_learner_call(
    model: str, system_prompt: str, user_prompt: str
) -> tuple[str, str, dict[str, Any] | None]:
    return call_learner(
        model, system_prompt, user_prompt, temperature=0.0
    )


@dataclass(frozen=True)
class TargetedFixRequest:
    diagnosis_id: str
    source_id: str
    task_context: dict[str, Any]
    update_diagnosis: dict[str, Any]
    candidate_edits: tuple[dict[str, Any], ...]
    parent_trajectory: dict[str, Any]
    candidate_trajectory: dict[str, Any]
    parent_state: str
    candidate_state: str


SYSTEM_PROMPT = """Judge only whether the diagnosed target behavior was fixed
in the matched Candidate replay. Task Success and Compliance states are external
facts; never rejudge them. A fix concerns the diagnosed behavior, not the final
outcome, so a Candidate may be FIXED even if the task still fails. Return FIXED
only with direct Candidate evidence that the target problem disappeared or the
recommended behavior occurred. If the behavior was not exercised or evidence is
insufficient, conservatively return NOT_FIXED. Use only FIXED or NOT_FIXED.
Return exactly one tagged JSON object and no prose:
<TARGETED_FIX_JSON>
{"status":"NOT_FIXED","reason":"","parent_evidence_steps":[],"candidate_evidence_steps":[]}
</TARGETED_FIX_JSON>
"""


def build_targeted_fix_prompts(request: TargetedFixRequest) -> tuple[str, str]:
    if not isinstance(request, TargetedFixRequest):
        raise ValueError("v0.11 Targeted Fix requires a TargetedFixRequest.")
    payload = copy.deepcopy(request.__dict__)
    return SYSTEM_PROMPT, "Analyze this matched pair:\n" + json.dumps(
        payload, ensure_ascii=False, indent=2, sort_keys=True
    )


def parse_targeted_fix_response(response: Any) -> dict[str, Any]:
    if not isinstance(response, str):
        raise ValueError("UNPARSEABLE_TARGETED_FIX")
    match = re.fullmatch(
        r"\s*<TARGETED_FIX_JSON>\s*(.*?)\s*</TARGETED_FIX_JSON>\s*",
        response,
        flags=re.DOTALL,
    )
    if match is None:
        raise ValueError("UNPARSEABLE_TARGETED_FIX")
    try:
        value = json.loads(match.group(1))
    except json.JSONDecodeError as error:
        raise ValueError("UNPARSEABLE_TARGETED_FIX") from error
    expected = {"status", "reason", "parent_evidence_steps", "candidate_evidence_steps"}
    if not isinstance(value, dict) or set(value) != expected:
        raise ValueError("INVALID_TARGETED_FIX_FIELDS")
    if value["status"] not in TARGETED_FIX_STATUSES or not isinstance(value["reason"], str):
        raise ValueError("INVALID_TARGETED_FIX_VERDICT")
    for key in ("parent_evidence_steps", "candidate_evidence_steps"):
        if not isinstance(value[key], list) or any(
            not isinstance(step, int) or isinstance(step, bool) or step <= 0
            for step in value[key]
        ):
            raise ValueError("INVALID_TARGETED_FIX_EVIDENCE")
    return value


def call_targeted_fix(
    request: TargetedFixRequest, *, learner_call: LearnerCall = _default_learner_call
) -> dict[str, Any]:
    system, user = build_targeted_fix_prompts(request)
    response, _, _ = learner_call(LEARNER_MODEL, system, user)
    return {
        "diagnosis_id": request.diagnosis_id,
        "source_id": request.source_id,
        **parse_targeted_fix_response(response),
    }

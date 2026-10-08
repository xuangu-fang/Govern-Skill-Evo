"""Prompt and model-boundary helpers for v20 Issue Fusion."""
from __future__ import annotations

import json

from .issue_fusion_v20 import IssueFusionInput, SCHEMA, fusion_wire_payload


SYSTEM_PROMPT = """You perform v20 Issue Fusion.

Select independent issues that deserve the next local evidence review from the
current Findings and the compact issue Memory. Memory is a set of observations
and attempted approaches, not proof and not edit authorization. An unresolved
current binding must stay unresolved. A prior ACCEPT or RETAIN does not make an
attempt permanently correct, and a failed attempt must not be repeated without
addressing its stated limitation.

Every OBSERVED_PROBLEM finding must occur in exactly one issue. Other findings
may support more than one issue or be explicitly unassociated. A history-only
issue is allowed when its memory reference gives a concrete direction to check.
Use only PROPOSE or NO_EDIT. Do not emit VERIFIED, gap, plan, candidate Skill,
edit coordinates, or effect labels. Return JSON matching the supplied schema;
use the short aliases exactly as provided and do not invent references."""


def build_issue_fusion_request(request: IssueFusionInput, *, model="deepseek-v4-pro",
                               temperature=0.0, timeout=600, max_retries=0):
    if not isinstance(request, IssueFusionInput):
        raise ValueError("IssueFusionInput required")
    wire = fusion_wire_payload(request)
    return {
        "stage": "issue_fusion_v20",
        "model": model,
        "temperature": temperature,
        "timeout": timeout,
        "max_retries": max_retries,
        "system_prompt": SYSTEM_PROMPT,
        "user_prompt": json.dumps(wire, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
        "response_format": {"type": "json_schema", "json_schema": {
            "name": "issue_fusion_response_v20", "strict": True, "schema": SCHEMA}},
        "input_ref": request.input_ref,
        "reference_map": _map_for_prompt(request),
    }


def _map_for_prompt(request):
    from .issue_fusion_v20 import fusion_reference_map
    return fusion_reference_map(request)


def check_fusion_response(raw, *, request, wire=False):
    from .issue_fusion_v20 import validate_issue_fusion
    return validate_issue_fusion(raw, request=request, wire=wire)

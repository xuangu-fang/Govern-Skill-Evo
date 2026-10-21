"""Apply Update patches to frozen Originals, then use the V23 compiler."""
from copy import deepcopy

from src.skill_evolution.v23.diagnosis import fields, links, validate_diagnosis
from src.skill_evolution.v23.editor import apply_patch
from src.skill_evolution.v23.facts import require, text
from src.skill_evolution.v23.preconditioner import compile_effective_plan


def normalize_update_patches(result, payload):
    """Return (V23 Adjustment result, Effective Plan); never mutate either input.

    This version supports withdrawal or same-ID replacement of one Original per
    Adjustment. Semantic stops and all remaining validation belong to V23.
    Nothing is published until every patch and the complete Plan compile.
    """
    validate_diagnosis({"decision": "revise", "reason": "Original Plan",
                        "plan": payload["plan"]}, payload)
    fields(result, ("decision", "reason", "adjustments", "checks"), "Preconditioner")
    require(isinstance(result["adjustments"], list), "adjustments must be an array")
    originals = {u["id"]: u for u in payload["plan"]["updates"]}
    normalized = deepcopy(result)
    consumed = set()
    for adjustment in normalized["adjustments"]:
        fields(adjustment, ("from", "to", "basis", "reason"), "Adjustment")
        links(adjustment["from"], originals, "adjustment.from")
        require(len(adjustment["from"]) == 1, "V23.3 does not support merging Updates")
        uid = adjustment["from"][0]
        require(uid not in consumed, "Original Update adjusted more than once")
        consumed.add(uid)
        require(isinstance(adjustment["to"], list) and len(adjustment["to"]) <= 1,
                "V23.3 requires withdrawal or one same-ID replacement")
        if adjustment["to"]:
            replacement = adjustment["to"][0]
            fields(replacement, ("id", "patch"), "Patch Update")
            require(replacement["id"] == uid, "V23.3 replacement must retain its Original ID")
            patch = text(replacement["patch"], "update.patch")
            adjusted = apply_patch(originals[uid]["text"], patch)
            adjustment["to"] = [{"id": uid, "text": adjusted}]
    effective = compile_effective_plan(normalized, payload)
    return normalized, effective

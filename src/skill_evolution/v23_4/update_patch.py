"""Validate flat V23.4 decisions and atomically adapt them to the V23 compiler.

Checks establish structure, citation identity and exact patch application, not
whether history supports a claim or a patch faithfully implements its change.
"""
from copy import deepcopy
import re

from src.skill_evolution.v23.diagnosis import fields, validate_diagnosis
from src.skill_evolution.v23.editor import apply_patch
from src.skill_evolution.v23.facts import require, text
from src.skill_evolution.v23.grouping import references
from src.skill_evolution.v23.memory import run_references, validate_memory, LEGACY_CONTRACT
from src.skill_evolution.v23.preconditioner import compile_effective_plan
from src.skill_evolution.v23_3.memory_view import FORMAT, project_payload

CONTRACT_VERSION = "v23_4_transformations_v2"
HISTORY_REF = re.compile(r"[A-Za-z0-9_-]+/(?:diff\b|[PQ]\d+(?::[A-Za-z0-9_]+)?)")
LOCAL_REF = re.compile(r"\b(?:[PQ]\d+(?::[A-Za-z0-9_]+)?|[CGM]\d+)\b")


def normalize_update_patches(result, payload, *, memory_view=FORMAT, memory_contract=LEGACY_CONTRACT):
    """Return (internal legacy result, Effective Plan), without mutating inputs.

    Raw Keep decisions remain in the caller's V23.4 output; only non-Keep
    decisions become legacy adjustments. No partial Plan escapes on failure.
    """
    fields(payload, ("parent", "plan", "command_sets", "runs", "grouping", "memory"), "Input")
    validate_memory(payload["memory"], memory_contract=memory_contract)
    view = project_payload(payload, memory_view, memory_contract=memory_contract)
    validate_diagnosis({"decision": "revise", "reason": "Original Plan", "plan": payload["plan"]}, payload)
    originals = {u["id"]: u for u in payload["plan"]["updates"]}
    fields(result, ("adjustments", "checks"), "V23.4 Preconditioner")
    checks = deepcopy(payload["plan"]["checks"] if result["checks"] is None else result["checks"])
    require(isinstance(checks, list), "checks must be null or an array")
    # Reasons may discuss retained, replaced, or removed Checks. These are Plan
    # objects, not behavioral evidence; full Check validation still precedes return.
    check_ids = {c["id"] for c in payload["plan"]["checks"]}
    for check in checks:
        fields(check, ("id", "update_ids", "question"), "Check")
        check_ids.add(text(check["id"], "check.id"))
    current = set(payload["command_sets"]) | {g["group_id"] for g in payload["grouping"]["groups"]}
    for run in payload["runs"]:
        current.update(run_references(run))
    current.update(e["id"] for e in view["memory"]["entries"])
    history = set(view["memory"]["sources"])
    for key, source in view["memory"]["sources"].items():
        if key.endswith("/diff"):
            continue
        run = source["run"]
        history.update((f"{key}:0", f"{key}:outcome"))
        if memory_view == FORMAT:
            history.update(step["step"] for step in run["trace"])
        else:
            context = key.rsplit("/", 1)[0]
            history.update(f"{context}/{ref}" for ref in run_references(run))

    def prose(value, name, *, reason=False):
        text(value, name)
        cited = []
        if reason:
            # Reason backticks are reserved for one exact formal ID per span.
            cited = re.findall(r"`([^`\n]+)`", value)
            uncited = re.sub(r"`([^`\n]+)`", "", value)
            require("`" not in uncited, "Malformed reason citation")
            require(not HISTORY_REF.search(uncited) and not LOCAL_REF.search(uncited),
                    "Reason evidence IDs require single-backtick citations")
            require(all(ref in current | history | originals.keys() | check_ids for ref in cited),
                    f"{name}: unavailable explicit reference")
        historical = set(HISTORY_REF.findall(value))
        require(historical <= history, f"{name}: unavailable historical reference")
        local = HISTORY_REF.sub("", value)
        require(set(LOCAL_REF.findall(local)) | references(local) <= current,
                f"{name}: unavailable evidence reference")
        return cited

    require(isinstance(result["adjustments"], list), "adjustments must be an array")
    indexed = {}
    citations = {}
    for adjustment in result["adjustments"]:
        fields(adjustment, ("target", "focus", "change", "reason", "to"), "Adjustment")
        uid = text(adjustment["target"], "target")
        require(uid in originals and uid not in indexed, "Unknown or duplicate Original target")
        indexed[uid] = adjustment
        focus = adjustment["focus"]
        require(isinstance(focus, list) and all(isinstance(f, str) and f in ("D", "S", "C") for f in focus),
                "focus must contain only D/S/C")
        require(len(focus) == len(set(focus)), "Duplicate focus dimension")
        prose(adjustment["change"], "change")
        citations[uid] = prose(adjustment["reason"], "reason", reason=True)
        keep = adjustment["change"] == "KEEP"
        require(keep == (focus == []) == (adjustment["to"] is None), "Inconsistent KEEP/focus/to")
        if not keep and adjustment["to"] != []:
            fields(adjustment["to"], ("patch",), "Patch Update")
            text(adjustment["to"]["patch"], "update.patch")
    require(indexed.keys() == originals.keys(), "Every Original requires exactly one Adjustment")

    normalized, survivors = [], set(originals)
    for uid, original in originals.items():
        adjustment = indexed[uid]
        if adjustment["change"] == "KEEP":
            continue
        if adjustment["to"] == []:
            replacement = []
            survivors.remove(uid)
        else:
            adjusted = apply_patch(original["text"], adjustment["to"]["patch"])
            prose(adjusted, "update.text")
            replacement = [{"id": uid, "text": adjusted}]
        normalized.append({
            "from": [uid], "to": replacement,
            "basis": list(dict.fromkeys([*original["basis"], *[r for r in citations[uid] if r in current]])),
            "reason": f"target={uid}; focus={','.join(adjustment['focus'])}; "
                      f"change={adjustment['change']}; reason={adjustment['reason']}",
        })

    # V23 returns early for all-withdrawn results; don't let dangling Checks pass.
    if not survivors:
        require(checks == [], "All withdrawn Updates require resolved checks=[]")
    for check in checks:
        prose(check["question"], "check.question")
    legacy = {"decision": "ready" if survivors else "no_change",
              "reason": "Deterministically compiled from validated V23.4 adjustments.",
              "adjustments": normalized, "checks": checks}
    effective = compile_effective_plan(legacy, payload, memory_contract=memory_contract)
    return legacy, effective

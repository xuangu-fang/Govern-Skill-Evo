"""V23.5 structural Plan compiler with its versioned prose validator.

Mirrors the V23 structural checks, keeping frozen legacy source files unchanged.
No response or Plan text is rewritten to accommodate a different scanner.
"""
from copy import deepcopy

from src.skill_evolution.v23.diagnosis import fields, links, validate_diagnosis
from src.skill_evolution.v23.facts import require, text
from src.skill_evolution.v23.memory import empty_memory, validate_memory, LEGACY_CONTRACT


def compile_effective_plan(result, payload, *, memory_contract=LEGACY_CONTRACT, prose_validator):
    """Validate simultaneous adjustments and compile; semantic stops return None."""
    fields(payload, ("parent", "plan", "command_sets", "runs", "grouping", "memory"), "Input")
    # [] is accepted only for validating frozen no-history results; new requests
    # are assembled with the formal object by preconditioner_input().
    memory = empty_memory() if memory_contract == LEGACY_CONTRACT and payload["memory"] == [] else payload["memory"]
    validate_memory(memory, memory_contract=memory_contract)
    original = payload["plan"]
    validate_diagnosis({"decision": "revise", "reason": "Original Plan", "plan": original}, payload)
    plan_sources = {g["group_id"] for g in payload["grouping"]["groups"]}
    for run in payload["runs"]:
        plan_sources.update([run["ref"], f"{run['ref']}:0", f"{run['ref']}:outcome", *[s["step"] for s in run["steps"]]])
    allowed = plan_sources | set(payload["command_sets"]) | {entry["id"] for entry in memory["entries"]}

    prose = prose_validator

    fields(result, ("decision", "reason", "adjustments", "checks"), "Preconditioner")
    require(result["decision"] in ("ready", "no_change", "need_evidence"), "Unknown decision")
    prose(result["reason"], "reason")
    require(isinstance(result["adjustments"], list), "adjustments must be an array")
    if result["decision"] == "need_evidence":
        require(result["adjustments"] == [] and result["checks"] is None,
                "need_evidence requires adjustments=[] and checks=null")
        return None

    originals = {u["id"]: u for u in original["updates"]}
    positions = {u["id"]: i for i, u in enumerate(original["updates"])}
    consumed, produced, replacements = set(), set(), {}
    for adjustment in result["adjustments"]:
        fields(adjustment, ("from", "to", "basis", "reason"), "Adjustment")
        links(adjustment["from"], originals, "adjustment.from")
        source_ids = set(adjustment["from"])
        require(not consumed.intersection(source_ids), "Original Update adjusted more than once")
        consumed.update(source_ids)
        require(isinstance(adjustment["to"], list), "adjustment.to must be an array")
        links(adjustment["basis"], allowed, "adjustment.basis")
        prose(adjustment["reason"], "adjustment.reason")
        # Use original Plan order, not model-supplied from order, for stable lineage.
        basis = list(dict.fromkeys(ref for u in original["updates"] if u["id"] in source_ids for ref in u["basis"]))
        new = []
        for update in adjustment["to"]:
            fields(update, ("id", "text"), "Replacement Update")
            uid = text(update["id"], "update.id")
            retain = len(source_ids) == len(adjustment["to"]) == 1 and uid in source_ids
            require(uid not in produced and uid not in allowed, "Duplicate or evidence-colliding Update ID")
            require(uid not in originals or retain, "Only one-to-one replacement may retain its own original ID")
            produced.add(uid)
            prose(update["text"], "update.text")
            new.append({"id": uid, "text": update["text"], "basis": deepcopy(basis)})
        replacements[min(positions[uid] for uid in source_ids)] = new

    updates = []
    for i, update in enumerate(original["updates"]):
        if i in replacements:
            updates.extend(replacements[i])
        if update["id"] not in consumed:
            updates.append(deepcopy(update))
    if result["decision"] == "no_change":
        require(not updates and consumed == set(originals) and result["checks"] == [],
                "no_change requires explicit withdrawal of all Updates and checks=[]")
        return None
    require(bool(updates), "ready requires at least one effective Update")
    checks = deepcopy(original["checks"] if result["checks"] is None else result["checks"])
    effective = {"goal": original["goal"], "updates": updates, "checks": checks}
    # Goal and inherited basis were validated with the Original Plan; replacement
    # Updates were validated above. Do not rescan their prose with V23's current-only rules.
    update_ids = {update["id"] for update in updates}
    require(isinstance(checks, list), "checks must be an array")
    check_ids = set()
    for check in checks:
        fields(check, ("id", "update_ids", "question"), "Check")
        cid = text(check["id"], "check.id")
        require(cid not in check_ids | update_ids | plan_sources, "Duplicate or colliding Check ID")
        check_ids.add(cid)
        links(check["update_ids"], update_ids, "check.update_ids")
        prose(check["question"], "check.question")
    return effective



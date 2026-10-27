from src.skill_evolution.v24.benchmark import current as benchmark_current

import re

from ..facts import require, text

from .grouping import references

def diagnosis_input(*args, **kwargs):
    return benchmark_current().evidence("contracts.diagnosis.diagnosis_input", *args, **kwargs)


def fields(value, expected, name):
    require(isinstance(value, dict) and set(value) == set(expected), f"{name}: unexpected fields")


def links(value, allowed, name):
    require(isinstance(value, list) and bool(value)
            and all(isinstance(x, str) and x in allowed for x in value), f"{name}: invalid references")
    require(len(value) == len(set(value)), f"{name}: duplicate references")


def validate_diagnosis(result, payload):
    return _validate_diagnosis(result, payload, check_field="update_ids")


def _validate_diagnosis(result, payload, *, check_field):
    """Validate structure and reference routing, not natural-language diagnosis."""
    fields(result, ("decision", "reason", "plan"), "Diagnosis")
    require(result["decision"] in ("revise", "no_change", "need_evidence"), "Unknown decision")
    text(result["reason"], "reason")
    groups = {g["group_id"]: set(g["members"]) for g in payload["grouping"]["groups"]}
    executions = {}
    for run in payload["runs"]:
        ref = run["ref"]
        for source in [ref, f"{ref}:0", f"{ref}:outcome", *[s["step"] for s in run["steps"]]]:
            executions[source] = ref
    allowed = set(groups) | set(executions)

    def prose_refs(value):
        require(references(value) <= set(executions), "Unknown execution reference in text")
        require(set(re.findall(r"\bG\d+\b", value)) <= set(groups), "Unknown group reference in text")

    prose_refs(result["reason"])
    if result["decision"] != "revise":
        require(result["plan"] is None, "Semantic stop requires plan=null")
        return result
    plan = result["plan"]
    fields(plan, ("goal", "updates", "checks"), "Plan")
    text(plan["goal"], "goal")
    prose_refs(plan["goal"])
    require(isinstance(plan["updates"], list) and bool(plan["updates"]), "revise requires updates")
    update_ids = set()
    for update in plan["updates"]:
        fields(update, ("id", "text", "basis"), "Update")
        uid = text(update["id"], "update.id")
        require(uid not in update_ids and uid not in allowed, "Duplicate or source-colliding Update ID")
        update_ids.add(uid)
        text(update["text"], "update.text")
        prose_refs(update["text"])
        links(update["basis"], allowed, "update.basis")
        evidence_members = {executions[r] for r in update["basis"] if r in executions}
        require(bool(evidence_members), "Update requires direct execution evidence")
        for ref in update["basis"]:
            if ref in groups:
                require(bool(groups[ref] & evidence_members), f"{ref} lacks member execution evidence")
    require(isinstance(plan["checks"], list), "checks must be an array")
    check_ids = set()
    for check in plan["checks"]:
        fields(check, ("id", check_field, "question"), "Check")
        cid = text(check["id"], "check.id")
        require(cid not in check_ids | update_ids | allowed, "Duplicate or colliding Check ID")
        check_ids.add(cid)
        links(check[check_field], update_ids, f"check.{check_field}")
        text(check["question"], "check.question")
        prose_refs(check["question"])
    return result


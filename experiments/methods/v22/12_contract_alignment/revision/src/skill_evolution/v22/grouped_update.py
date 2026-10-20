"""Offline interfaces for one continual mainline, not an experiment runner.

Reuse the compact Plan, increment, Editor and Effect contracts. Group and adoption
metadata are program-owned; model outputs do not acquire new audit tables.
"""

from copy import deepcopy
import json
from pathlib import Path

from src.adapters.alfworld.skill_runtime import digest, object_digest, validate_skill
from src.adapters.alfworld.verify_skill_run import require, verify_record
from .compact_cycle import diagnosis_input, make_diff
from .compact_learning import build_learning_payload
from .compact_update import (
    COMMON, DIAGNOSIS_SHAPE, EDITOR_SHAPE, FUSION_SHAPE,
    apply_fusion, validate_diagnosis, validate_editor,
)
from .conditional_update import (
    CONDITIONED_RULES, DIAGNOSIS_RULES, PROPOSAL_CONTRACT, REALIZATION_RULES,
)
from .continual_state import gate_round, validate_round
from .effective_memory import (
    EFFECTIVE_SHAPE, apply_effective_memory, effective_consumption_payload, learning_messages_effective,
)
from .effective_update import EVIDENCE_BOUNDARY
from .grouped_representation import attach_grouping, validate_grouped_plan
from . import unified_dsc, contract_alignment
from .memory_identity import PROFILE as STABLE_PROFILE


PROFILE = "v22.grouped_update.v1"
UNIFIED_PROFILES = (unified_dsc.PROFILE, STABLE_PROFILE, contract_alignment.PROFILE)
GROUP_RULES = """
This is one continual update path. Frozen decision groups organize comparable choices,
not separate Skills, independent effects, or permanent cross-round classes. Refer to
current group sources AND actual current Parent events in requirement.basis. State
visible triggers, target behavior and relevant preservation in existing text fields.
Group membership alone proves no defect or response. Keep cross-group interactions
and side effects visible. Match history by decision meaning, observed conditions and
actual Parent/edit dependencies, never by group ID or task family. Diagnosis sees no
Memory. Fusion makes the update decision; Editor realizes it relative to the supplied
actual Parent, retaining its relevant obligations without inventing extra strategies.
Keep is valid. Use the compact output only, without per-group certification tables.
"""


def check_profile(profile):
    require(profile in (PROFILE, *UNIFIED_PROFILES), "Unknown grouped update profile.")
    return profile


def prepare_current(context, parent_records, *, profile=PROFILE):
    """Current Parent-only evidence; independent Diagnosis cannot see Memory."""
    check_profile(profile)
    validate_round(context)
    require([r["task"]["id"] for r in parent_records] == context["task_ids"],
            "Current evidence must contain the declared Parent batch in order.")
    for record in parent_records:
        require(verify_record(record)["episode_complete"], "Incomplete Parent evidence.")
    # The experiment has one frozen execution profile; task/environment files differ.
    for record in parent_records[1:]:
        require(all(record[key] == parent_records[0][key] for key in
                    ("model", "protocol", "versions", "implementation", "backend_id")),
                "Parent batch mixes execution profiles.")
    empty = {"intent": "Current Parent observations", "requirements": [], "watch": [], "open": []}
    evidence = build_learning_payload(context["parent"], context["parent"], "", empty,
                                      parent_records, [])
    result = {**diagnosis_input(evidence, parent_records), "round_sha256": context["sha256"]}
    if profile in UNIFIED_PROFILES:
        result["update_profile"] = profile
    return result


def diagnosis_payload(context, parent_records, grouping, *, profile=PROFILE):
    require(grouping["round_id"] == context["round_id"], "Grouping belongs to another round.")
    return attach_grouping(prepare_current(context, parent_records, profile=profile), grouping)


def accept_diagnosis(value, current):
    output = validate_diagnosis(value, current)
    if output["decision"] == "revise":
        if current.get("update_profile") == contract_alignment.PROFILE:
            output = deepcopy(output)
            output["plan"] = validate_grouped_plan(output["plan"], current, complete_sources=True)
        else:
            validate_grouped_plan(output["plan"], current)
    return output


def update_payload(context, current, plan):
    """The same actual Parent and current groups accompany Fusion and Editor."""
    validate_round(context)
    require(current.get("round_sha256") == context["sha256"]
            and [run["task_id"] for alias, run in current["runs"].items() if alias.startswith("P")]
            == context["task_ids"], "Update evidence belongs to another round or task batch.")
    require(current["parent"] == {k: v for k, v in context["parent"].items() if k != "source"},
            "Update input uses a different Parent.")
    require(current["grouping"]["round_id"] == context["round_id"], "Update groups belong to another round.")
    payload = {**deepcopy(current), "plan": deepcopy(plan), "memory": deepcopy(context["memory"])}
    validate_grouped_plan(plan, payload)
    return payload


def compile_update(value, payload):
    profile = check_profile(payload.get("update_profile", PROFILE))
    plan = apply_fusion(value, payload, allow_empty=profile in UNIFIED_PROFILES)
    if value["decision"] == "ready":
        plan = validate_grouped_plan(plan, payload, complete_sources=profile == contract_alignment.PROFILE)
    return plan


def identity_update(payload):
    """An explicitly recorded empty-history shortcut, not a model Keep verdict."""
    require(not payload["memory"], "Program identity requires empty Memory.")
    result = {"decision": "ready", "reason": "Program identity with empty Memory; no Fusion call.",
              "changes": [], "watch_changes": [], "open": []}
    return result, compile_update(result, payload)


def grouped_messages(stage, payload):
    """Versioned prompts reuse D/S/C rules without a second construction branch."""
    profile = check_profile(payload.get("update_profile", PROFILE))
    if profile in UNIFIED_PROFILES:
        return _unified_messages(stage, payload)
    if stage == "learn":
        require("update_context" in payload, "Learning must follow the bound Gate.")
        _check_learning_binding(payload)
        messages = learning_messages_effective(payload)
        messages[0]["content"] += "\nProfile: " + PROFILE + GROUP_RULES + """
Interpret the frozen group comparisons, including unplanned cross-group changes and
unknowns. Gate is only whole-version adoption: ACCEPT may include regressions; RETAIN
may include local improvements. Neither labels individual edits. Learn conditional
responses to the actual joint diff, not isolated causal effects or success recipes.
No Candidate means no new edit response; current facts can revise an existing Effect.
"""
        return messages
    if stage == "diagnosis":
        require(not payload.get("memory"), "Diagnosis cannot consume historical Memory.")
        rules = DIAGNOSIS_RULES.replace("Do not weaken the initial draft to help a later arm.",
                                       "The initial draft is the actual starting update; do not weaken it.")
        shape, view = DIAGNOSIS_SHAPE, payload
    elif stage == "fusion":
        rules, shape, view = PROPOSAL_CONTRACT + CONDITIONED_RULES, FUSION_SHAPE, effective_consumption_payload(payload)
    elif stage == "editor":
        rules = REALIZATION_RULES.replace("Both update policies use this same Editor.",
                                         "This Editor serves the single continual mainline.")
        shape, view = EDITOR_SHAPE, effective_consumption_payload(payload)
    else:
        raise ValueError("Unknown grouped update stage.")
    return [{"role": "system", "content": "Profile: " + PROFILE + "\n" + COMMON
             + EVIDENCE_BOUNDARY + rules + GROUP_RULES + "\nOutput shape: " + json.dumps(shape)},
            {"role": "user", "content": json.dumps(view, ensure_ascii=False, separators=(",", ":"))}]


def _unified_messages(stage, payload):
    """Replace the legacy instructions; keep its shapes and single-call stages."""
    aligned = payload["update_profile"] == contract_alignment.PROFILE
    if stage == "learn":
        require("update_context" in payload, "Learning must follow the bound Gate.")
        _check_learning_binding(payload)
        rules = unified_dsc.LEARNING_RULES
        shape = contract_alignment.EFFECTIVE_SHAPE if aligned else EFFECTIVE_SHAPE
    elif stage == "diagnosis":
        require(not payload.get("memory"), "Diagnosis cannot consume historical Memory.")
        rules, shape = unified_dsc.DIAGNOSIS_RULES, DIAGNOSIS_SHAPE
    elif stage == "fusion":
        rules = contract_alignment.FUSION_RULES if aligned else unified_dsc.FUSION_RULES
        shape = FUSION_SHAPE
    elif stage == "editor":
        rules, shape = unified_dsc.REALIZATION_RULES, EDITOR_SHAPE
    else:
        raise ValueError("Unknown grouped update stage.")
    view = payload if stage == "diagnosis" else effective_consumption_payload(payload)
    # Learning has its own evidence/response boundary, rather than construction
    # instructions that could turn an untested observation into a Plan blocker.
    boundary = "" if stage == "learn" else COMMON + EVIDENCE_BOUNDARY
    return [{"role": "system", "content": "Profile: " + payload["update_profile"] + "\n" + boundary
             + rules + (contract_alignment.GROUP_RULES if aligned else unified_dsc.GROUP_RULES)
             + "\nOutput shape: " + json.dumps(shape)},
            {"role": "user", "content": json.dumps(view, ensure_ascii=False, separators=(",", ":"))}]


def realize_editor(value, payload):
    """Return the actual Candidate and Plan including new Editor watch questions."""
    validate_grouped_plan(payload["plan"], payload)
    validate_editor(value, payload)
    require(value["decision"] != "needs_revision", "Unresolved Editor requirements cannot produce a Candidate.")
    plan = deepcopy(payload["plan"])
    plan["watch"].extend(deepcopy(value["watch"]))
    if value["decision"] == "no_change":
        return None, plan
    text = value["candidate_text"]
    checksum = digest(text.encode("utf-8"))
    return {"mode": "fixed", "skill_id": "sha256:" + checksum,
            "sha256": checksum, "text": text, "source": None}, plan


def materialize_skill(skill, path):
    """Write exactly the inherited text for the existing Actor's --skill-file.

    The immutable snapshot owns identity, not an old mutable source path. No Skill
    returns None so the caller omits --skill-file. Existing artifacts are not replaced.
    """
    validate_skill(skill)
    if skill["mode"] == "none":
        return None
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(skill["text"].encode("utf-8"))
    return path.resolve()


def prepare_grouped_learning(context, grouping, plan, candidate, parents, candidates, gate,
                             *, editor=None, profile=PROFILE):
    """Replay -> mechanical Gate -> one semantic learning input, in that order."""
    expected = gate_round(context, candidate, parents, candidates)
    require(gate == expected, "Learning Gate differs from actual paired executions.")
    current = diagnosis_payload(context, parents, grouping, profile=profile)
    validate_grouped_plan(plan, {**current, "memory": context["memory"]})
    require(candidate is None or bool(plan["requirements"]), "Candidate needs actual update requirements.")
    # This is an absent candidate view, never a runnable Skill or an empty edit.
    candidate_view = candidate or {"mode": "not_constructed", "skill_id": None, "sha256": None, "text": None}
    actual_diff = make_diff(context["parent"], candidate) if candidate else ""
    payload = build_learning_payload(context["parent"], candidate_view, actual_diff, plan,
                                     parents, candidates, context["memory"])
    payload["base_protocol"] = deepcopy(current["base_protocol"])
    payload = attach_grouping(payload, grouping)
    payload["update_context"] = {"round_id": context["round_id"], "round_sha256": context["sha256"],
                                 "grouping": deepcopy(grouping), "gate": deepcopy(gate),
                                 "actual_diff": actual_diff}
    if profile in UNIFIED_PROFILES:
        payload["update_profile"] = profile
        require(candidate is None or editor is not None, "Candidate learning needs its actual Editor mapping.")
        realization = None
        if editor is not None:
            # execution_plan includes Editor-added questions; validate against the
            # effective Plan the Editor actually received, without adding them twice.
            before_editor = deepcopy(plan)
            added = editor.get("watch", [])
            if added:
                require(before_editor["watch"][-len(added):] == added,
                        "Learning Plan lost or changed Editor watch questions.")
                before_editor["watch"] = before_editor["watch"][:-len(added)]
            validate_editor(editor, {**current, "memory": context["memory"], "plan": before_editor})
            require((editor["decision"] == "candidate") == (candidate is not None),
                    "Editor decision differs from the actual Candidate.")
            require(candidate is None or editor["candidate_text"] == candidate["text"],
                    "Editor text differs from the actual Candidate.")
            realization = {key: deepcopy(editor[key]) for key in ("decision", "mappings", "issues")}
            payload["sources"]["editor"] = {"kind": "editor"}
        payload["update_context"]["editor"] = realization
    if candidate is None:
        payload["sources"].pop("skill:candidate")
        payload["sources"].pop("diff")
    payload["binding_sha256"] = object_digest(payload)
    return payload


def _check_learning_binding(payload):
    require(payload.get("binding_sha256") == object_digest(
        {key: value for key, value in payload.items() if key != "binding_sha256"}),
        "Prepared learning input changed; Gate, executions and Memory must stay bound.")


def learn_grouped_memory(payload, value):
    """Only validated post-Gate learning can supply a publication receipt."""
    _check_learning_binding(payload)
    update = payload["update_context"]
    context_id = object_digest(payload)
    memory = apply_effective_memory(payload["memory"], value, context_id, payload)
    receipt = {"schema_version": "v22.continual_memory_receipt.v1", "round_id": update["round_id"],
               "gate_sha256": object_digest(update["gate"]),
               "memory_before_sha256": object_digest(payload["memory"]),
               "memory_after_sha256": object_digest(memory),
               "learning_payload_sha256": context_id, "learning_output_sha256": object_digest(value)}
    return memory, receipt

"""Frozen decision groups shared by a round's update and feedback interfaces.

This module exports current Parent facts and checks source routing. It neither
calls a model nor certifies that a proposed grouping is semantically appropriate.
Only ``build_grouping_input(...)["model_input"]`` is sent to the classifier;
bindings are the program's private map back to audited execution identities.
"""

from copy import deepcopy
import random

from src.adapters.alfworld.skill_runtime import digest, object_digest, validate_skill
from src.adapters.alfworld.verify_skill_run import require
from .compact_update import _plan, _sources


PROFILE = "v22.decision_grouping.v1"
INPUT_SCHEMA = "v22.grouping_input.v1"
FROZEN_SCHEMA = "v22.frozen_grouping.v1"


def _text(value, description):
    require(isinstance(value, str) and bool(value.strip()), description)
    return value


def _parent_snapshot(current):
    parent = deepcopy(current["parent"])
    parent.pop("source", None)
    validate_skill(parent | {"source": None})
    return parent


def build_grouping_input(current, round_id, seed=200):
    """Compact ALL complete current Parent Train traces, with opaque task aliases.

    ``current`` is an audited compact payload, normally diagnosis_input's result.
    Full ordered actions and observations remain; only shared protocol and action
    lists are deduplicated. Memory, Candidate, plan and hidden task metadata never
    enter the classifier's model_input, even if supplied in the enclosing payload.
    """
    _text(round_id, "Grouping needs a round identity.")
    require(type(seed) is int, "Grouping alias seed must be an integer.")
    parent = _parent_snapshot(current)
    protocol = current.get("base_protocol")
    fields = ("system_prompt", "initial_template", "history_template")
    require(isinstance(protocol, dict) and all(isinstance(protocol.get(key), str) for key in fields),
            "Grouping needs the actual visible base protocol.")
    rows = [(alias, run) for alias, run in current["runs"].items() if alias.startswith("P")]
    require(bool(rows), "Grouping needs current Parent executions.")
    rows.sort(key=lambda item: item[0])
    random.Random(seed).shuffle(rows)
    model_input = {"parent": {key: parent[key] for key in ("mode", "text")},
                   "capabilities": deepcopy(current["capabilities"]),
                   "base_protocol": {key: protocol[key] for key in fields},
                   "command_sets": {}, "experiences": []}
    command_aliases, bindings, task_ids, run_ids = {}, {}, set(), set()

    def commands(ref):
        values = current["command_sets"][ref]
        require(isinstance(values, list) and all(isinstance(value, str) for value in values),
                "Invalid admissible commands.")
        key = tuple(values)
        if key not in command_aliases:
            command_aliases[key] = f"a{len(command_aliases) + 1}"
            model_input["command_sets"][command_aliases[key]] = deepcopy(values)
        return command_aliases[key]

    for index, (alias, run) in enumerate(rows, 1):
        require(run["task_id"].startswith("train:") and run["episode_complete"] is True,
                "Classification requires complete Parent Train episodes.")
        require(isinstance(run["native_success"], bool), "Complete Parent needs a native outcome.")
        require(run["skill_id"] == parent["skill_id"], "Grouping Parent Skill differs from execution.")
        require(run["task_id"] not in task_ids and run["run_id"] not in run_ids,
                "Grouping requires one Parent execution per distinct task.")
        task_ids.add(run["task_id"])
        run_ids.add(run["run_id"])
        observation = _text(run["initial_observation"], "Missing initial observation.")
        task_ref = f"T{index}"
        bindings[task_ref] = {"parent_alias": alias, "task_id": run["task_id"],
                              "run_id": run["run_id"], "execution_fingerprint": run["execution_fingerprint"]}
        experience = {"task_ref": task_ref,
                      "task_request": observation.split("Your task is to: ", 1)[-1].strip(),
                      "initial_observation": observation,
                      "initial_commands": commands(run["initial_commands"]), "steps": [],
                      "outcome": {"status": run["status"], "native_success": run["native_success"]}}
        for step_number, event in enumerate(run["steps"], 1):
            require(event["step"] == step_number and event["phase"] == "executed",
                    "Grouping needs complete, ordered Parent interactions.")
            step = {key: event[key] for key in ("step", "action", "action_in_admissible_commands",
                                               "observation", "reward", "done", "won")}
            step["commands"] = commands(event["commands"])
            experience["steps"].append(step)
        require(bool(experience["steps"]), "Complete Parent has no executed interaction.")
        model_input["experiences"].append(experience)
    return {"schema_version": INPUT_SCHEMA, "round_id": round_id, "seed": seed,
            "parent_sha256": object_digest(parent), "model_input": model_input, "bindings": bindings}


def _partition(result, task_refs):
    require(isinstance(result, dict) and set(result) == {"groups"}, "Invalid grouping fields.")
    groups = result["groups"]
    require(isinstance(groups, list) and bool(groups), "Grouping needs at least one group.")
    group_ids, assigned = set(), []
    fields = {"group_id", "decision_problem", "members", "shared_basis", "important_differences"}
    for group in groups:
        require(isinstance(group, dict) and set(group) == fields, "Invalid decision group fields.")
        group_id = _text(group["group_id"], "Empty group ID.")
        require(group_id not in group_ids, "Duplicate group ID.")
        group_ids.add(group_id)
        _text(group["decision_problem"], "Empty decision problem.")
        _text(group["shared_basis"], "Empty shared basis.")
        members = group["members"]
        require(isinstance(members, list) and bool(members)
                and all(isinstance(ref, str) for ref in members), "Empty or invalid group members.")
        differences = group["important_differences"]
        require(isinstance(differences, list), "Group differences must be an array.")
        for value in differences:
            _text(value, "Empty group difference.")
        assigned.extend(members)
    require(len(assigned) == len(set(assigned)) and set(assigned) == set(task_refs),
            "Grouping must partition every current task exactly once.")


def freeze_grouping(result, grouping_input, prompt_text):
    """Bind one classifier result to its input and exact versioned prompt."""
    require(grouping_input.get("schema_version") == INPUT_SCHEMA, "Unknown grouping input.")
    require(isinstance(prompt_text, str) and bool(prompt_text.splitlines())
            and prompt_text.splitlines()[0] == f"Profile: {PROFILE}",
            "Grouping prompt profile mismatch.")
    refs = [row["task_ref"] for row in grouping_input["model_input"]["experiences"]]
    require(len(refs) == len(set(refs)) and set(refs) == set(grouping_input["bindings"]),
            "Grouping input binding mismatch.")
    _partition(result, refs)
    frozen = {"schema_version": FROZEN_SCHEMA, "profile": PROFILE,
              "round_id": grouping_input["round_id"], "seed": grouping_input["seed"],
              "parent_sha256": grouping_input["parent_sha256"],
              "input_sha256": object_digest(grouping_input),
              "prompt_sha256": digest(prompt_text.encode("utf-8")),
              "bindings": deepcopy(grouping_input["bindings"]), "groups": deepcopy(result["groups"])}
    frozen["sha256"] = object_digest(frozen)
    return frozen


def validate_frozen_grouping(frozen):
    """Check a saved partition without treating its semantics as proven."""
    require(isinstance(frozen, dict) and frozen.get("schema_version") == FROZEN_SCHEMA
            and frozen.get("profile") == PROFILE, "Unknown frozen grouping.")
    require(frozen.get("sha256") == object_digest({key: value for key, value in frozen.items() if key != "sha256"}),
            "Frozen grouping hash mismatch.")
    _partition({"groups": frozen["groups"]}, frozen["bindings"])
    return frozen


def attach_grouping(current, frozen):
    """Attach the SAME frozen groups to Diagnosis, Editor or paired Replay.

    Candidate runs inherit membership by their paired task. Group membership is
    a source coordinate, never an independence or isolated causal attribution.
    """
    validate_frozen_grouping(frozen)
    actual_input = build_grouping_input(current, frozen["round_id"], frozen["seed"])
    require(object_digest(actual_input) == frozen["input_sha256"],
            "Frozen grouping no longer matches current Parent evidence.")
    result = deepcopy(current)
    result["grouping"] = deepcopy(frozen)
    by_task = {}
    for group in frozen["groups"]:
        ref = f"group:{frozen['round_id']}:{group['group_id']}"
        members = [deepcopy(frozen["bindings"][task_ref]) | {"task_ref": task_ref}
                   for task_ref in group["members"]]
        snapshot = deepcopy(group) | {"round_id": frozen["round_id"], "members": members,
                                      "parent_sha256": frozen["parent_sha256"],
                                      "grouping_sha256": frozen["sha256"],
                                      "input_sha256": frozen["input_sha256"],
                                      "prompt_sha256": frozen["prompt_sha256"]}
        source = {"kind": "decision_group", "snapshot": snapshot}
        require(ref not in result["sources"] or result["sources"][ref] == source,
                "Decision group source collision.")
        result["sources"][ref] = source
        by_task.update({member["task_id"]: ref for member in members})
    for run in result["runs"].values():
        require(run["task_id"] in by_task, "Run has no frozen decision group.")
        run["decision_group"] = by_task[run["task_id"]]
    return result


def validate_grouped_plan(plan, payload, *, complete_sources=False):
    """Require shared decision sources AND actual current Parent event evidence.

    Multiple cited groups are allowed. Every cited group needs an event from one
    of its tasks; events cannot silently refer to an uncited group. This verifies
    routing only: conditions, target behavior and applicability remain semantic.
    The opt-in completion returns a copy with missing evidence-group references;
    it never removes an explicit reference or changes an Update's conditions.
    """
    frozen = validate_frozen_grouping(payload["grouping"])
    attached = attach_grouping(payload, frozen)
    _plan(plan, _sources(payload), nonempty=False)
    if complete_sources:
        plan = deepcopy(plan)
    current_groups = {f"group:{frozen['round_id']}:{row['group_id']}" for row in frozen["groups"]}
    for row in plan["requirements"]:
        refs = set(row["basis"])
        groups = refs & current_groups
        event_groups = set()
        for ref in refs:
            source = payload["sources"].get(ref, {})
            if source.get("kind") == "event" and source["run"].startswith("P"):
                run = attached["runs"][source["run"]]
                require(source["step"] == 0 or any(event["step"] == source["step"] for event in run["steps"]),
                        "Requirement cites a nonexistent Parent event.")
                event_groups.add(run["decision_group"])
        if complete_sources:
            # Group provenance is determined by already-cited Parent events.
            # Unbacked explicit groups still fail the unchanged equality check.
            row["basis"].extend(sorted(event_groups - groups))
            groups.update(event_groups)
        require(bool(groups) and groups == event_groups,
                "Requirement needs current decision group and matching Parent event evidence.")
    return plan

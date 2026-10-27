"""Shared Grouping/Diagnosis facts from recorded ALFWorld requests, without hashes."""

from copy import deepcopy

from src.adapters.alfworld.actor_prompt import render_messages, visible_commands


BACKGROUND_FIELDS = ("system_prompt", "initial_template", "history_template", "max_steps")
COMPLETE = {"success", "environment_ended", "step_limit"}
STATUSES = COMPLETE | {"starting", "running", "error", "interrupted", "unknown"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def text(value, name):
    require(isinstance(value, str) and bool(value.strip()), f"Invalid {name}")
    return value


def commands(value):
    require(isinstance(value, list) and all(isinstance(x, str) for x in value),
            "Expected a recorded command list")
    return value


def parent_text(record):
    skill = record["skill"]
    if skill["mode"] == "none":
        require(skill["text"] is None, "No-Skill record has Skill text")
        return None
    require(skill["mode"] == "fixed", "Unsupported Skill mode")
    return text(skill["text"], "Parent Skill")


def background(record):
    protocol = record["protocol"]
    require(protocol.get("history_length") == 2
            and protocol.get("history") == "last_2_pre_action_observations"
            and protocol.get("action_mode") == "generation_with_admissible_candidates",
            "Recorded Actor capabilities differ from the V23 prompt")
    require(protocol.get("reset") == "fresh_environment_then_reset_once",
            "Cannot establish a continuous single-reset execution")
    result = {k: protocol[k] for k in BACKGROUND_FIELDS}
    for key in BACKGROUND_FIELDS[:-1]:
        text(result[key], key)
    require(type(result["max_steps"]) is int and result["max_steps"] > 0, "Invalid max_steps")
    return result


def build_facts(records):
    """Return model facts, shared background and private source/audit information.

    A partial final request is audited but never represented as an executed action.
    Unsupported or inconsistent records are rejected, never repaired heuristically.
    """
    require(isinstance(records, list) and bool(records), "A nonempty Parent batch is required")
    parent, context = parent_text(records[0]), background(records[0])
    facts = {"parent": parent, "command_sets": {}, "runs": []}
    menus, identities, task_ids, sources = {}, set(), set(), []

    def menu(values):
        if values is None:
            return None
        values = visible_commands(commands(values))
        key = tuple(values)
        if key not in menus:
            menus[key] = f"C{len(menus) + 1}"
            facts["command_sets"][menus[key]] = values
        return menus[key]

    for number, record in enumerate(records, 1):
        ref = f"P{number}"
        require(parent_text(record) == parent and background(record) == context,
                f"{ref}: Parent or execution background differs across the batch")
        run_id, task_id = text(record["run_id"], "run_id"), text(record["task"]["id"], "task_id")
        require(run_id not in identities and task_id not in task_ids, "Duplicate execution or task")
        identities.add(run_id)
        task_ids.add(task_id)
        status = record["status"]
        require(status in STATUSES, f"Unsupported recorded status: {status}")
        observation = text(record["initial_observation"], "initial_observation")
        marker = "Your task is to: "
        require(marker in observation, "Cannot recover the recorded task goal")
        goal = observation.split(marker, 1)[1].strip()
        require(record.get("goal", goal) == goal, "Goal differs from initial observation")
        initial_menu = commands(record["initial_admissible_commands"])
        steps = record["steps"]
        require(isinstance(steps, list), "Invalid recorded steps")
        require(len(steps) <= context["max_steps"], "Recorded steps exceed budget")
        run = {"ref": ref, "task": goal,
               "initial": {"observation": observation, "commands_ref": menu(initial_menu)},
               "steps": []}
        source = {"ref": ref, "run_id": run_id, "task_id": task_id,
                  "status": status, "events": [], "pending_step": None}
        history, before_states = [], []
        terminal = False
        for index, event in enumerate(steps, 1):
            event_ref = f"{ref}:{index}"
            require(type(event["step"]) is int and event["step"] == index, "Non-contiguous recorded steps")
            require(not terminal, "A request follows an environment terminal state")
            raw_menu = commands(event["admissible_commands"])
            if index == 1:
                require(raw_menu == initial_menu, "Initial menu differs from first decision menu")
            expected = render_messages(observation, raw_menu, goal, history,
                                       **{k: context[k] for k in BACKGROUND_FIELDS[:-1]})
            if parent is not None:
                protocol = record["protocol"]
                require(protocol.get("skill_injection") == "append_to_system_every_request_when_fixed",
                        "Unsupported recorded Skill injection")
                expected[0]["content"] += protocol["skill_prefix"] + parent + protocol["skill_suffix"]
            require(event.get("messages") == expected,
                    f"{event_ref}: actual Prompt differs from recorded observation/history/candidates/Skill")
            before = {"observation": observation, "commands_ref": menu(raw_menu)}
            before_states.append(before)
            phase = event.get("phase")
            require(phase in {"executed", "requesting", "responded"}, "Unknown recorded phase")
            if phase != "executed":
                require(index == len(steps) and status not in COMPLETE, "Incomplete action in complete execution")
                source["pending_step"] = {"step": event_ref, "phase": phase}
                break
            # The Actor can execute an empty parsed command; preserve its failure
            # and consumed step rather than rejecting or rewriting the evidence.
            action = event["action"]
            require(isinstance(action, str), "Invalid executed action")
            after_observation = text(event["observation"], "post-action observation")
            require(type(event.get("done")) is bool and type(event.get("won")) is bool,
                    "Executed event lacks terminal feedback")
            legal = action in raw_menu
            require(type(event.get("action_in_admissible_commands")) is bool
                    and event["action_in_admissible_commands"] == legal,
                    "Recorded action legality differs from the raw environment menu")
            feedback = {k: deepcopy(event[k]) for k in
                        ("reward", "done", "won", "action_in_admissible_commands", "fallback") if k in event}
            # No after-menu field is recorded by the supported V22 runner.
            # Restore it only from the next fully audited decision state below.
            run["steps"].append({"step": event_ref, "before": before, "action": action,
                                 "after": {"observation": after_observation, "commands_ref": None},
                                 "feedback": feedback})
            source["events"].append({"step": event_ref, "prompt_verified": True,
                                     "environment_action_legal": legal,
                                     "actor_candidate_contains_action": action in visible_commands(raw_menu),
                                     "after_menu_source": None})
            history.append({"observation": observation, "action": action})
            observation = after_observation
            terminal = event["done"] or event["won"]

        for index, event in enumerate(run["steps"]):
            if index + 1 < len(before_states):
                following = before_states[index + 1]
                require(event["after"]["observation"] == following["observation"], "Broken state continuity")
                event["after"]["commands_ref"] = following["commands_ref"]
                source["events"][index]["after_menu_source"] = f"{ref}:{index + 2}:before"
        executed = run["steps"]
        if status in COMPLETE:
            require(bool(executed) and len(executed) == len(steps), "Complete run lacks executed steps")
            last = executed[-1]["feedback"]
            if status == "success":
                require(last["won"] is True, "Success lacks a recorded win")
            elif status == "environment_ended":
                require(last["done"] and not last["won"], "Normal failure lacks terminal feedback")
            else:
                require(len(executed) == context["max_steps"] and not terminal,
                        "Step-limit outcome differs from executed budget")
            success = status == "success"
        else:
            success = None
        if executed and "won" in record:
            require(record["won"] == executed[-1]["feedback"]["won"], "Run/event outcome mismatch")
        run["outcome"] = {"status": status, "success": success, "end_reason": status}
        source["error_stage"] = record.get("error_stage")
        source["error_type"] = record.get("error_type")
        facts["runs"].append(run)
        sources.append(source)
    return {"facts": facts, "background": context, "sources": sources}

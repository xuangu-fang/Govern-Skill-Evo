"""Assemble current-round visible evidence and preserve exact source identities."""

import json
from collections import Counter
from pathlib import Path

from src.adapters.alfworld.skill_runtime import digest, load_skill, validate_skill
from src.adapters.alfworld.verify_skill_run import learning_feedback, verify_record


def prepare_evidence(paths, plan, parent_skill=None):
    """Bind evidence to an actual Parent; legacy callers still require No Skill."""
    expected = load_skill() if parent_skill is None else parent_skill
    validate_skill(expected)
    records, sources, evidence = [], [], []
    for path in paths:
        path = Path(path).resolve()
        data = path.read_bytes()
        record = json.loads(data)
        audit = verify_record(record)
        if not audit["episode_complete"]:
            raise ValueError("Parent execution must be complete; preserve incomplete evidence separately.")
        identity = ("mode", "skill_id", "sha256", "text")
        if (any(record["skill"][key] != expected[key] for key in identity)
                or record["split"] != "train" or record["purpose"] != "learning"):
            label = "No Skill" if parent_skill is None else "the supplied Parent"
            raise ValueError(f"This path requires {label}, learning-purpose Train feedback; smoke/selection/test are excluded.")
        if record["model"] != plan["model"] or record["protocol"]["max_steps"] != plan["max_steps_per_episode"]:
            raise ValueError("Parent model/budget differs from the declared plan.")
        feedback = learning_feedback(record)
        before = feedback["initial_observation"]
        steps = []
        for event in feedback["steps"]:
            steps.append({"step": event["step"], "observation_before": before,
                          **{key: event[key] for key in (
                              "admissible_commands", "action", "observation", "reward", "done", "won",
                          )}})
            before = event["observation"]
        context = {**feedback["execution_context"],
                   "base_system_prompt": record["protocol"]["system_prompt"],
                   "initial_template": record["protocol"]["initial_template"],
                   "history_template": record["protocol"]["history_template"],
                   "capabilities": "Current observation/admissible actions plus last two pre-action observation/action pairs. No writable persistent state or full actor history. Skill text is fixed during an episode."}
        evidence.append({"run_id": record["run_id"], "task_id": record["task"]["id"],
                         "execution_fingerprint": record["execution_fingerprint"],
                         "execution_context": context, "initial_observation": feedback["initial_observation"],
                         "status": record["status"], "native_success": record["won"], "steps": steps})
        sources.append({"run_id": record["run_id"], "task_id": record["task"]["id"],
                        "path": str(path), "sha256": digest(data),
                        "execution_fingerprint": record["execution_fingerprint"]})
        records.append(record)
    if [r["task"]["id"] for r in records] != plan["task_ids"]:
        raise ValueError("Parent tasks/order must equal the declared plan; no outcome-based selection.")
    if len({r["run_id"] for r in records}) != len(records):
        raise ValueError("Duplicate Parent execution.")
    return records, sources, evidence


def verify_sources(sources):
    for source in sources:
        if digest(Path(source["path"]).read_bytes()) != source["sha256"]:
            raise ValueError("Source trajectory changed after evidence assembly.")


def load_prior_parent_attempts(plan, parents):
    """Audit explicitly declared infrastructure failures for cost, never for learning."""
    prior = plan.get("prior_parent_attempts", [])
    if not prior:
        return []
    expected_slots = (len(parents) * 2 + len(prior)) * plan["max_steps_per_episode"]
    if (plan.get("parent_attempts_per_task_max") != 2
            or plan.get("total_environment_request_slots_max") != expected_slots
            or not plan.get("recovery_reason") or not plan.get("supersedes_plan_sha256")):
        raise ValueError("Declare the bounded infrastructure recovery and its complete budget.")
    by_task = {record["task"]["id"]: record for record in parents}
    seen = {record["run_id"] for record in parents}
    counts, records = Counter(), []
    for source in prior:
        data = Path(source["path"]).read_bytes()
        if digest(data) != source["sha256"]:
            raise ValueError("Prior Parent attempt changed after recovery declaration.")
        record = json.loads(data)
        verify_record(record)
        task = record["task"]["id"]
        if task not in by_task or record["run_id"] in seen:
            raise ValueError("Prior Parent must be a distinct attempt on a declared task.")
        if (record["status"] != "error" or record.get("error_stage") != "model_request"
                or record.get("error_type") not in {"ReadTimeout", "ConnectTimeout", "ConnectionError"}):
            raise ValueError("Only a recorded infrastructure failure permits Parent recovery.")
        current = by_task[task]
        keys = ("skill", "task", "split", "purpose", "environment", "model", "protocol",
                "versions", "implementation", "backend_id", "initial_observation", "initial_admissible_commands")
        if any(record.get(key) != current.get(key) for key in keys):
            raise ValueError("Recovered Parent must preserve the original execution conditions.")
        counts[task] += 1
        if counts[task] > 1:
            raise ValueError("At most one infrastructure retry per declared Parent task.")
        seen.add(record["run_id"])
        records.append(record)
    return records

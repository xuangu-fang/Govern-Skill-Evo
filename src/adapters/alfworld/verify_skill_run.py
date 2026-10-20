"""Audit fixed-Skill traces and compare execution conditions without model calls."""

import argparse
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path

from .run_task_upstream import project_action
from .skill_runtime import (
    SCHEMA, access_metadata, build_skill_messages, context_fingerprint,
    execution_fingerprint, execution_protocol, object_digest, validate_skill,
)

COMPLETE = {"success", "environment_ended", "step_limit"}
STATUSES = COMPLETE | {"starting", "running", "error", "interrupted"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def verify_record(record):
    require(record["schema_version"] == SCHEMA, "Unknown trace schema.")
    validate_skill(record["skill"])
    require(record["access"] == access_metadata(record["split"], record["purpose"]), "Access metadata mismatch.")
    require(record["task"]["id"].startswith(record["split"] + ":"), "Task/split mismatch.")
    require(record["protocol"] == execution_protocol(record["protocol"]["max_steps"]), "Protocol mismatch.")
    require(record["context_fingerprint"] == context_fingerprint(record), "Context fingerprint mismatch.")
    require(record["execution_fingerprint"] == execution_fingerprint(record), "Execution fingerprint mismatch.")
    require(record["status"] in STATUSES, "Unknown episode status.")
    complete = record["status"] in COMPLETE
    history = []
    observation = record.get("initial_observation")
    goal = observation.split("Your task is to: ", 1)[1].strip() if observation and "Your task is to: " in observation else None
    usage = Counter()
    models = set()
    unknown_usage = 0
    last_won = False
    last_done = False
    transport_attempts = 0
    transport_unknown_usage = 0
    for index, event in enumerate(record["steps"], 1):
        where = f"step {index}"
        require(goal is not None, f"Missing initial goal at {where}.")
        require(not last_won and not last_done, f"Request after environment termination at {where}.")
        require(event["step"] == index, f"Nonsequential {where}.")
        require(index <= record["protocol"]["max_steps"], f"Step budget exceeded at {where}.")
        require(event["phase"] in {"requesting", "responded", "executed"}, f"Unknown phase at {where}.")
        if index == 1:
            require(event["admissible_commands"] == record["initial_admissible_commands"], "Initial actions mismatch.")
        expected = build_skill_messages(observation, event["admissible_commands"], goal, history, record["skill"])
        require(event["messages"] == expected, f"Prompt/Skill mismatch at {where}.")
        transport_attempts += len(event.get("transport_attempts", []))
        protocol = record["protocol"]
        parameters = {"model": record["model"], "temperature": protocol["temperature"],
                      "max_tokens": protocol["max_tokens"], "reasoning_effort": protocol["reasoning_effort"],
                      "thinking": {"type": protocol["thinking"]}, "stream": False}
        attempts = event.get("transport_attempts", [])
        require(len(attempts) <= 6, f"Transport retry budget exceeded at {where}.")
        for number, attempt in enumerate(attempts, 1):
            require(attempt["attempt"] == number, f"Transport order mismatch at {where}.")
            require(attempt["request_parameters"] == parameters, f"Request parameters mismatch at {where}.")
            require(attempt["request_sha256"] == object_digest({**parameters, "messages": expected}), f"Request body hash mismatch at {where}.")
            require(attempt["status"] in {"requesting", "responded", "error", "interrupted"}, f"Unknown transport state at {where}.")
            if number < len(attempts):
                require(attempt.get("http_status") in {429, 500, 502, 503, 504}, f"Unexpected transport retry at {where}.")
            if attempt["status"] == "requesting":
                require(number == len(attempts) and not complete, f"Unfinished transport in completed run at {where}.")
            transport_unknown_usage += attempt.get("usage") is None
        response = event.get("model_response")
        if response is None:
            require(event["phase"] == "requesting", f"Missing response at {where}.")
            require("action" not in event and "observation" not in event, f"Action without response at {where}.")
            unknown_usage += 1
        else:
            if attempts:
                require(attempts[-1]["status"] == "responded" and 200 <= attempts[-1].get("http_status", 0) < 400,
                        f"Model response without successful HTTP attempt at {where}.")
                require(response.get("api_attempts") == len(attempts)
                        and response.get("transport_retries") == len(attempts) - 1,
                        f"Transport response count mismatch at {where}.")
                if event["phase"] == "executed":
                    require(attempts[-1].get("usage") == response.get("usage"), f"Transport usage mismatch at {where}.")
            if "action" in event:
                action, fallback = project_action(response["content"])
                require((event["action"], event["fallback"]) == (action, fallback), f"Action projection mismatch at {where}.")
                require(event["action_in_admissible_commands"] == (action in event["admissible_commands"]), f"Action membership mismatch at {where}.")
            else:
                require(event["phase"] == "responded" and not complete, f"Missing action at {where}.")
            require(event["phase"] in {"responded", "executed"}, f"Response/phase mismatch at {where}.")
            if response.get("response_model"):
                models.add(response["response_model"])
            reported = response.get("usage") or {}
            if not all(isinstance(reported.get(key), int) for key in ("prompt_tokens", "completion_tokens", "total_tokens")):
                unknown_usage += 1
            usage.update({key: reported[key] for key in ("prompt_tokens", "completion_tokens", "total_tokens")
                          if isinstance(reported.get(key), int)})
        if event["phase"] == "executed":
            require(isinstance(event["won"], bool) and isinstance(event["done"], bool), f"Missing native verdict at {where}.")
            require("reward" in event and isinstance(event["observation"], str), f"Missing feedback at {where}.")
            history.append({"observation": observation, "action": event["action"]})
            observation = event["observation"]
            last_won, last_done = event["won"], event["done"]
        else:
            require(index == len(record["steps"]) and not complete, f"Incomplete step in completed episode at {where}.")
            require("observation" not in event, f"Feedback/phase mismatch at {where}.")
    require(record["won"] == last_won, "Episode/native won mismatch.")
    if complete:
        require(bool(history) and "finished_at" in record, "Completed episode lacks execution or finish time.")
    if record["status"] == "success":
        require(last_won, "Success lacks a native won observation.")
    elif record["status"] == "environment_ended":
        require(last_done and not last_won, "Incorrect environment_ended verdict.")
    elif record["status"] == "step_limit":
        require(len(history) == record["protocol"]["max_steps"] and not last_won and not last_done, "Incorrect step_limit verdict.")
    return {
        "schema_version": "alfworld_skill_audit_v1", "run_id": record["run_id"],
        "task_id": record["task"]["id"], "skill_id": record["skill"]["skill_id"],
        "trace_valid": True, "episode_complete": complete, "status": record["status"],
        "native_success": last_won if complete else None,
        "requests_recorded": len(record["steps"]), "steps_executed": len(history),
        "transport_attempts_recorded": transport_attempts,
        "transport_attempts_with_unknown_usage": transport_unknown_usage,
        "reported_usage": dict(usage), "requests_with_unknown_usage": unknown_usage,
        "response_models": sorted(models), "context_fingerprint": record["context_fingerprint"],
        "scope": "Saved identities, prompts, action projection and native result consistency; not independent environment replay or a Skill effect estimate.",
    }


def compare_records(left, right):
    first, second = verify_record(left), verify_record(right)
    differences = [key for key in ("task", "split", "purpose", "environment", "model",
                                   "backend_id", "protocol", "versions", "implementation")
                   if left[key] != right[key]]
    for key in ("initial_observation", "initial_admissible_commands"):
        if key not in left or key not in right or left[key] != right[key]:
            differences.append(key)
    if not first["episode_complete"] or not second["episode_complete"]:
        differences.append("incomplete_episode")
    if (not first["response_models"] or first["response_models"] != second["response_models"]
            or any(not event.get("model_response", {}).get("response_model")
                   for record in (left, right) for event in record["steps"])):
        differences.append("response_models_missing_or_different")
    return {"left_run_id": left["run_id"], "right_run_id": right["run_id"],
            "recorded_conditions_match": not differences, "differences": differences,
            "same_skill": left["skill"]["skill_id"] == right["skill"]["skill_id"],
            "scope": "Matching recorded conditions permit further comparison; model randomness and unobserved drift remain. This does not establish causal effects or statistical significance."}


def learning_feedback(record):
    """Explicit allowlist for a future learner, without game paths or hidden state."""
    audit = verify_record(record)
    require(record["access"]["learning_allowed"], "Selection/final traces cannot be exported as learning feedback.")
    steps = []
    for event in record["steps"]:
        steps.append({key: event[key] for key in (
            "step", "phase", "messages", "admissible_commands", "model_response",
            "action", "fallback", "action_in_admissible_commands", "observation", "reward", "done", "won",
        ) if key in event})
    return deepcopy({
        "schema_version": "alfworld_learning_feedback_v1", "run_id": record["run_id"],
        "task_id": record["task"]["id"], "split": record["split"], "purpose": record["purpose"],
        "skill": {key: value for key, value in record["skill"].items() if key != "source"},
        "execution_fingerprint": record["execution_fingerprint"],
        "execution_context": {"model": record["model"], **{
            key: record["protocol"][key] for key in (
                "protocol_id", "max_steps", "max_tokens", "history", "environment_seed",
            )}},
        "initial_observation": record.get("initial_observation"), "steps": steps,
        "status": record["status"], "error_stage": record.get("error_stage"),
        "error_type": record.get("error_type"), "native_success": audit["native_success"],
        "episode_complete": audit["episode_complete"],
    })


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trajectory", type=Path)
    parser.add_argument("--compare-with", type=Path)
    parser.add_argument("--feedback-output", type=Path, help="Export allowed Train feedback; refuses an existing file")
    args = parser.parse_args()
    record = json.loads(args.trajectory.read_text(encoding="utf-8"))
    report = verify_record(record)
    if args.compare_with:
        other = json.loads(args.compare_with.read_text(encoding="utf-8"))
        report["comparison"] = compare_records(record, other)
    if args.feedback_output:
        feedback = learning_feedback(record)
        with args.feedback_output.open("x", encoding="utf-8") as output:
            output.write(json.dumps(feedback, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if args.compare_with and not report["comparison"]["recorded_conditions_match"] else 0


if __name__ == "__main__":
    raise SystemExit(main())

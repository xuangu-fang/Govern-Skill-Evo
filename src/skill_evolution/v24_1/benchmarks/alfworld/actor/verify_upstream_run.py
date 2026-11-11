"""Verify saved upstream NoSkill requests, task coverage and final scores offline."""

import argparse
import json
from pathlib import Path

from .eval_test import summarize, write_json
from .run_task_upstream import build_messages, protocol_metadata, project_action


def verify(run_dir):
    config = json.loads((run_dir / "config.json").read_text())
    for key, value in protocol_metadata().items():
        if config.get(key) != value:
            raise ValueError(f"Saved protocol differs: {key}")
    results = {}; response_models = set(); thinking_steps = 0; total_steps = 0
    fallbacks = 0; non_admissible = 0; truncated = 0; mismatches = []
    for item in config["items"]:
        task_dir = run_dir / "tasks" / item["id"].replace(":", "_")
        result = json.loads((task_dir / "result.json").read_text())
        record = json.loads(Path(result["trajectory"]).read_text())
        if record["task"] != item or record["split"] != config["split"] or record["model"] != config["model"]:
            raise ValueError(f"Saved task identity mismatch: {item['id']}")
        for key, value in protocol_metadata().items():
            if record.get(key) != value:
                raise ValueError(f"Task protocol differs: {item['id']} {key}")
        if result["status"] != record["status"] or result["won"] != record["won"]:
            raise ValueError(f"Result/trajectory mismatch: {item['id']}")
        history = []; observation = record["initial_observation"]
        goal = observation.split("Your task is to: ", 1)[1].strip()
        for event in record["steps"]:
            expected = build_messages(observation, event["admissible_commands"], goal, history)
            if event["messages"] != expected:
                mismatches.append([item["id"], event["step"]])
            response = event["model_response"]
            if project_action(response["content"]) != (event["action"], event["fallback"]):
                raise ValueError(f"Action projection mismatch: {item['id']}")
            response_models.add(response["response_model"])
            thinking_steps += response.get("reasoning_content_chars", 0) > 0
            fallbacks += bool(event["fallback"])
            non_admissible += not event["action_in_admissible_commands"]
            truncated += response.get("finish_reason") == "length"
            history.append({"observation": observation, "action": event["action"]})
            observation = event["observation"]
            total_steps += 1
        if len(history) > 50 or result["steps"] != len(history):
            raise ValueError(f"Step budget/count mismatch: {item['id']}")
        if record["status"] == "step_limit" and (len(history) != 50 or record["won"]):
            raise ValueError(f"Incorrect timeout verdict: {item['id']}")
        if record["status"] == "success" and not record["steps"][-1]["won"]:
            raise ValueError(f"Success not confirmed by environment: {item['id']}")
        results[item["id"]] = result
    if mismatches:
        raise ValueError(f"Saved prompt mismatch: {mismatches}")
    recomputed = summarize(config["items"], results)
    saved = json.loads((run_dir / "summary.json").read_text())
    if recomputed != saved:
        raise ValueError("Saved summary differs from recomputed task results.")
    if not recomputed["evaluation_valid"] or not thinking_steps:
        raise ValueError("Incomplete evaluation or no evidence of enabled thinking.")
    report = {"tasks": len(results), "split": config["split"], "successes": saved["successes"],
              "success_rate": saved["success_rate_all_tasks"], "status_counts": saved["status_counts"],
              "runtime_errors": saved["runtime_errors"], "total_steps": total_steps,
              "thinking_response_steps": thinking_steps, "fallback_steps": fallbacks,
              "non_admissible_actions": non_admissible, "truncated_response_steps": truncated,
              "response_models": sorted(response_models), "all_saved_prompts_match_pinned_templates": True,
              "all_task_protocols_match": True, "summary_recomputed": True,
              "source": config["source"], "recorded_usage_all_attempts": saved["usage"]}
    write_json(run_dir / "validation.json", report)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path)
    args = parser.parse_args()
    print(json.dumps(verify(args.run_dir.resolve()), ensure_ascii=False, indent=2))

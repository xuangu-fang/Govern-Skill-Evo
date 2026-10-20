"""Evaluate all 134 fixed Test tasks with the project's NoSkill agent."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
from datetime import datetime, timezone
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys

from dotenv import load_dotenv

from .run_task import REPO_ROOT, SPLIT_ROOT, SYSTEM_PROMPT, positive_int

NORMAL_STATUSES = {"success", "step_limit", "environment_ended"}
MODEL_OUTPUT_ERRORS = {
    "Model must return exactly one single-line <action> command.",
    "Model output reached max_tokens; action was not executed.",
}


def write_json(path, value):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    temporary.replace(path)


def summarize(items, results):
    expected = {item["id"]: item for item in items}
    if len(expected) != len(items) or any(key not in expected for key in results):
        raise ValueError("Duplicate manifest IDs or unexpected task results.")
    counts = Counter(result["status"] for result in results.values())
    successful = sum(result["status"] == "success" and result["won"] for result in results.values())
    normal = sum(counts[status] for status in NORMAL_STATUSES)
    model_failures = sum(result.get("error_type") == "ValueError" and
                         result.get("error") in MODEL_OUTPUT_ERRORS for result in results.values())
    groups = defaultdict(lambda: {"tasks": 0, "attempted": 0, "successes": 0})
    rows = []
    for item in items:
        result = results.get(item["id"], {})
        group = groups[item["task_type"]]
        group["tasks"] += 1
        group["attempted"] += bool(result)
        group["successes"] += result.get("status") == "success" and result.get("won", False)
        rows.append({"task_id": item["id"], "task_type": item["task_type"], **result})
    usage = Counter()
    for result in results.values():
        usage.update(result.get("usage", {}))
        for previous in result.get("previous_attempts", []):
            usage.update(previous.get("usage", {}))
    return {
        "expected_tasks": len(items), "attempted_tasks": len(results),
        "pending_tasks": len(items) - len(results), "normal_episodes": normal,
        "model_output_failures": model_failures,
        "runtime_errors": len(results) - normal - model_failures,
        "infrastructure_attempts_retried": sum(len(result.get("previous_attempts", [])) for result in results.values()),
        "successes": successful, "status_counts": dict(counts),
        "all_tasks_attempted": len(results) == len(items),
        "evaluation_valid": normal + model_failures == len(items),
        "success_rate_all_tasks": successful / len(items),
        "success_rate_normal_episodes": successful / normal if normal else None,
        "metric_note": "All-task rate uses the full manifest denominator. Invalid/truncated model actions are task failures without retry. Runtime/API failures also remain in the denominator but invalidate a complete evaluation. No errors are excluded silently.",
        "by_task_type": dict(groups), "usage": dict(usage), "task_results": rows,
    }


def run_one(item, run_dir, args):
    task_dir = run_dir / "tasks" / item["id"].replace(":", "_")
    task_dir.mkdir(parents=True, exist_ok=True)
    log_path = task_dir / "run.log"
    previous_attempts = []
    result_path = task_dir / "result.json"
    if result_path.is_file():
        previous = json.loads(result_path.read_text())
        previous_attempts = previous.pop("previous_attempts", [])
        if log_path.exists():
            log_index = 1
            while (task_dir / f"run_attempt_{log_index:03d}.log").exists():
                log_index += 1
            saved_log = task_dir / f"run_attempt_{log_index:03d}.log"
            log_path.rename(saved_log)
            # A killed retry can leave run.log newer than result.json. Match
            # logs to their actual trajectory rather than overwriting history.
            for archived in sorted(task_dir.glob("run_attempt_*.log")):
                if previous.get("trajectory", "<missing>") in archived.read_text():
                    previous["log"] = str(archived)
                    break
        previous_attempts.append(previous)
        referenced = {entry.get("trajectory") for entry in previous_attempts}
        for path in sorted(task_dir.glob("llm_*/trajectory.json")):
            if str(path) not in referenced:
                partial = json.loads(path.read_text())
                if partial["status"] in {"starting", "running", "interrupted"}:
                    usage = Counter()
                    for event in partial["steps"]:
                        data = event["model_response"].get("usage") or {}
                        usage.update({key: data[key] for key in ["prompt_tokens", "completion_tokens", "total_tokens"] if isinstance(data.get(key), int)})
                    partial_log = next((str(log) for log in task_dir.glob("run_attempt_*.log") if str(path) in log.read_text()), None)
                    previous_attempts.append({"status": "interrupted", "won": False,
                                              "steps": sum("observation" in event for event in partial["steps"]),
                                              "usage": dict(usage), "trajectory": str(path), "log": partial_log})
    with log_path.open("w") as log:
        runner = "src.adapters.alfworld.run_task_upstream" if getattr(args, "runner", "legacy") == "upstream" else "src.adapters.alfworld.run_task"
        split = getattr(args, "split", "test")
        process = subprocess.run(
            [sys.executable, "-m", runner,
             "--split", split, "--task-id", item["id"], "--model", args.model,
             "--max-steps", str(args.max_steps), "--max-tokens", str(args.max_tokens),
             "--env-file", str(args.env_file.resolve()), "--output-root", str(task_dir)],
            cwd=REPO_ROOT, stdout=log, stderr=subprocess.STDOUT,
        )
    trajectories = sorted(task_dir.glob("llm_*/trajectory.json"))
    result = {"status": "infrastructure_error", "won": False, "steps": 0,
              "usage": {}, "log": str(log_path), "exit_code": process.returncode,
              "previous_attempts": previous_attempts}
    if trajectories:
        path = trajectories[-1]
        record = json.loads(path.read_text())
        if record["task"] != item or record["split"] != split or record["model"] != args.model:
            raise ValueError(f"Task/manifest/model mismatch: {item['id']}")
        usage = Counter()
        for event in record["steps"]:
            data = event["model_response"].get("usage") or {}
            usage.update({key: data[key] for key in ["prompt_tokens", "completion_tokens", "total_tokens"] if isinstance(data.get(key), int)})
        result.update(status=record["status"], won=record["won"],
                      steps=sum("observation" in event for event in record["steps"]),
                      usage=dict(usage), trajectory=str(path))
        if "error_type" in record:
            result["error_type"] = record["error_type"]
        if "error" in record:
            result["error"] = record["error"]
        if getattr(args, "runner", "legacy") == "upstream":
            result["thinking_response_steps"] = sum(event["model_response"].get("reasoning_content_chars", 0) > 0 for event in record["steps"])
            result["fallback_steps"] = sum(bool(event.get("fallback")) for event in record["steps"])
    write_json(task_dir / "result.json", result)
    return result


def retryable_runtime_failure(result):
    return result.get("error") in {f"Model API returned HTTP {code}." for code in [429, 500, 502, 503, 504]} or result.get("error_type") in {"Timeout", "ReadTimeout", "ConnectTimeout", "ConnectionError"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="deepseek-v4-flash")
    parser.add_argument("--runner", choices=["legacy", "upstream"], default="legacy")
    parser.add_argument("--split", choices=["train", "val", "test"], default="test")
    parser.add_argument("--task-ids", nargs="+", help="Train/Selection entry checks only; Test always uses all 134 tasks")
    parser.add_argument("--workers", type=positive_int, default=4)
    parser.add_argument("--max-steps", type=positive_int, default=50)
    parser.add_argument("--max-tokens", type=positive_int)
    parser.add_argument("--env-file", type=Path, default=REPO_ROOT / ".env")
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--retry-runtime-errors", action="store_true", help="With --resume, retry only transient API/transport failures, preserving earlier attempts")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    args.max_tokens = args.max_tokens or (16384 if args.runner == "upstream" else 1024)
    if args.runner == "upstream" and (args.max_steps != 50 or args.max_tokens != 16384):
        parser.error("Upstream profile fixes max_steps=50 and max_tokens=16384.")
    if args.task_ids and args.split == "test":
        parser.error("Test evaluation must use the full fixed 134-task manifest.")
    if args.retry_runtime_errors and not args.resume:
        parser.error("--retry-runtime-errors requires --resume.")
    load_dotenv(args.env_file, override=False)
    if not os.environ.get("OPENAI_API_KEY") or not os.environ.get("OPENAI_BASE_URL"):
        parser.error("OPENAI_API_KEY and OPENAI_BASE_URL are required.")
    items = json.loads((SPLIT_ROOT / args.split / "items.json").read_text())
    expected_size = {"train": 39, "val": 18, "test": 134}[args.split]
    if len(items) != expected_size or len({item["gamefile"] for item in items}) != expected_size:
        parser.error("Unexpected manifest size or duplicate games.")
    if args.task_ids:
        if len(set(args.task_ids)) != len(args.task_ids) or not set(args.task_ids) <= {item["id"] for item in items}:
            parser.error("Duplicate or unknown task IDs.")
        items = [item for item in items if item["id"] in set(args.task_ids)]
    data_root = Path(os.environ.get("ALFWORLD_DATA", "~/.cache/alfworld")).expanduser().resolve()
    for item in items:
        if not (data_root / item["gamefile"]).is_file():
            parser.error(f"Missing game: {item['gamefile']}")
    config = {
        "schema_version": "alfworld_noskill_test_v1", "model": args.model,
        "split": args.split, "items": items, "data_root": str(data_root),
        "system_prompt": SYSTEM_PROMPT, "skill": None,
        "max_steps": args.max_steps, "max_tokens": args.max_tokens,
        "temperature": 0.2, "thinking": "disabled", "environment_seed": 42,
        "trials_per_task": 1, "action_mode": "generation", "history": "full",
        "base_url": os.environ["OPENAI_BASE_URL"].rstrip("/"),
        "versions": {name: importlib.metadata.version(name) for name in ["alfworld", "textworld"]},
    }
    if args.runner == "upstream":
        from .run_task_upstream import protocol_metadata
        config.update(protocol_metadata())
    if args.dry_run:
        print(f"Config OK: {len(items)} {args.split} tasks, {args.workers} workers, {args.model}; no API calls.")
        return 0
    run_dir = (args.run_dir or REPO_ROOT / "artifacts/benchmarks/alfworld" /
               ("noskill_test_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))).resolve()
    if args.resume:
        if not args.run_dir or not (run_dir / "config.json").is_file():
            parser.error("--resume requires an existing --run-dir with config.json.")
        if json.loads((run_dir / "config.json").read_text()) != config:
            parser.error("Resume config differs from the saved model/tasks/protocol; use the original settings.")
    else:
        run_dir.mkdir(parents=True, exist_ok=False)
        write_json(run_dir / "config.json", config)
    results = {}
    for item in items:
        path = run_dir / "tasks" / item["id"].replace(":", "_") / "result.json"
        if path.is_file():
            saved = json.loads(path.read_text())
            if not (args.retry_runtime_errors and retryable_runtime_failure(saved)):
                results[item["id"]] = saved
    print(f"Run: {run_dir}\nTasks: {len(items)}; already attempted: {len(results)}; workers: {args.workers}", flush=True)
    summary = summarize(items, results)
    write_json(run_dir / "summary.json", summary)
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(run_one, item, run_dir, args): item for item in items if item["id"] not in results}
        for future in as_completed(futures):
            item = futures[future]
            result = future.result()
            results[item["id"]] = result
            summary = summarize(items, results)
            write_json(run_dir / "summary.json", summary)
            print(f"[{len(results)}/{len(items)}] {item['id']}: {result['status']} ({result['steps']} steps); successes={summary['successes']}", flush=True)
    with (run_dir / "task_results.csv").open("w", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=["task_id", "task_type", "status", "won", "steps", "trajectory", "error_type"], extrasaction="ignore")
        writer.writeheader()
        writer.writerows(summary["task_results"])
    print(f"Successes: {summary['successes']}/{len(items)} ({summary['success_rate_all_tasks']:.2%}); evaluation_valid={summary['evaluation_valid']}")
    return 0 if summary["evaluation_valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

"""Bounded fresh episodes and frozen Selection evaluation, without learner calls.

This is scheduling and saved-trace accounting. A valid audit does not establish
semantic correctness, causality, or generalization. Each job is launched once;
the existing actor's bounded HTTP transport policy remains in effect.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess
import sys

from src.adapters.alfworld.run_task import REPO_ROOT
from src.adapters.alfworld.skill_runtime import load_skill, write_record
from src.adapters.alfworld.verify_skill_run import compare_records, verify_record


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _timestamp():
    return datetime.now(timezone.utc).isoformat()


def _execution_inputs(task_id, split, purpose, plan):
    _require((split, purpose) in {("train", "learning"), ("val", "selection")},
             "Only Train learning and frozen Selection episodes are supported.")
    _require(isinstance(task_id, str) and re.fullmatch(split + r":\d+", task_id),
             "Task ID and split do not match.")
    steps = plan["max_steps_per_episode"]
    _require(isinstance(steps, int) and not isinstance(steps, bool) and 1 <= steps <= 50,
             "Episode budget must be an integer from 1 to 50.")
    _require(isinstance(plan["actor_model"], str) and bool(plan["actor_model"].strip()),
             "A declared actor model is required.")


def execute_episode(task_id, split, purpose, skill_path_or_None, output_root, plan, env_file):
    """Launch the adapter once; retain its log, process status, and raw trace.

    A nonzero adapter exit with a saved trace returns that trace for audit rather
    than discarding an incomplete episode. A launch failure is recorded and raised.
    """
    _execution_inputs(task_id, split, purpose, plan)
    skill_path = Path(skill_path_or_None).resolve() if skill_path_or_None is not None else None
    load_skill(skill_path)
    root = Path(output_root).resolve()
    root.mkdir(parents=True, exist_ok=False)
    command = [sys.executable, "-m", "src.adapters.alfworld.run_task_skill",
               "--task-id", task_id, "--split", split, "--purpose", purpose,
               "--model", plan["actor_model"], "--max-steps", str(plan["max_steps_per_episode"]),
               "--env-file", str(Path(env_file).resolve()), "--output-root", str(root)]
    if skill_path is not None:
        command.extend(["--skill-file", str(skill_path)])
    if plan.get("archive_responses") is True:
        command.append("--archive-responses")
    process_record = {"command": command, "started_at": _timestamp(),
                      "status": "starting", "exit_code": None}
    write_record(root / "process.json", process_record)
    try:
        with (root / "run.log").open("x", encoding="utf-8") as log:
            process = subprocess.run(command, cwd=Path(__file__).resolve().parents[3],
                                     stdout=log, stderr=subprocess.STDOUT,
                                     check=False)
        process_record.update(status="finished", exit_code=process.returncode)
    except (Exception, KeyboardInterrupt) as exc:
        process_record.update(status="interrupted" if isinstance(exc, KeyboardInterrupt) else "error",
                              error_type=type(exc).__name__)
        raise
    finally:
        paths = sorted(root.glob("skill_*/trajectory.json"))
        process_record.update(finished_at=_timestamp(), trajectories=[str(path) for path in paths])
        write_record(root / "process.json", process_record)
    _require(len(paths) == 1, "One episode must produce exactly one trajectory.")
    return paths[0]


def _episode_row(job, root, plan, env_file):
    row = {key: job[key] for key in ("key", "task_id", "split", "purpose")}
    row.update(skill_path=str(Path(job["skill_path"]).resolve()) if job.get("skill_path") is not None else None,
               output_root=str(root), trajectory=None, trajectories=[], audit=None,
               status="error", executed=False, steps=0, success=None, invalid_action_count=None)
    if "arm" in job:
        row["arm"] = job["arm"]
    try:
        expected_skill = load_skill(job.get("skill_path"))["skill_id"]
        path = execute_episode(job["task_id"], job["split"], job["purpose"],
                               job.get("skill_path"), root, plan, env_file)
        row["trajectory"] = str(path)
        record = json.loads(path.read_text(encoding="utf-8"))
        audit = verify_record(record)
        _require((record["task"]["id"], record["split"], record["purpose"], record["model"],
                  record["protocol"]["max_steps"], record["skill"]["skill_id"]) ==
                 (job["task_id"], job["split"], job["purpose"], plan["actor_model"],
                  plan["max_steps_per_episode"], expected_skill), "Episode differs from its declared job.")
        row.update(audit=audit, status=audit["status"], executed=audit["steps_executed"] > 0,
                   steps=audit["steps_executed"], success=audit["native_success"],
                   invalid_action_count=sum(event.get("action_in_admissible_commands") is False
                                            for event in record["steps"] if event["phase"] == "executed"))
        if record.get("error_type"):
            row["error_type"] = record["error_type"]
    except Exception as exc:
        row["error_type"] = type(exc).__name__
    finally:
        row["trajectories"] = [str(path) for path in sorted(root.glob("skill_*/trajectory.json"))]
        if row["trajectory"] is None and len(row["trajectories"]) == 1:
            row["trajectory"] = row["trajectories"][0]
        if root.is_dir():
            write_record(root / "audit.json", row)
    return row


def execute_batch(jobs, output_root, plan, env_file):
    """Run at most three actor processes; return all jobs in declared order.

    Every job is validated before any launch. Exceptions become safe error rows;
    another job's failure never causes successful or incomplete futures to vanish.
    Existing output directories are refused, so a rerun cannot silently overwrite
    evidence or count as a retry of the same declared batch.
    """
    jobs = list(jobs)
    workers = plan["actor_workers"]
    _require(isinstance(workers, int) and not isinstance(workers, bool) and 1 <= workers <= 3,
             "Actor worker count must be an integer from 1 to 3.")
    keys = [job["key"] for job in jobs]
    _require(all(isinstance(key, str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]*", key)
                 for key in keys), "Job keys must be safe directory names.")
    _require(len(set(keys)) == len(keys), "Duplicate episode job keys.")
    for job in jobs:
        _execution_inputs(job["task_id"], job["split"], job["purpose"], plan)
        load_skill(job.get("skill_path"))
    root = Path(output_root).resolve()
    root.mkdir(parents=True, exist_ok=False)
    rows = [None] * len(jobs)
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(_episode_row, job, root / job["key"], plan, env_file): index
                   for index, job in enumerate(jobs)}
        for future in as_completed(futures):
            index = futures[future]
            try:
                rows[index] = future.result()
            except Exception as exc:
                # Includes accounting/file-write failures after an actor completed.
                job = jobs[index]
                paths = [str(path) for path in sorted((root / job["key"]).glob("skill_*/trajectory.json"))]
                rows[index] = {**job, "skill_path": str(job["skill_path"]) if job.get("skill_path") else None,
                               "output_root": str(root / job["key"]), "status": "error",
                               "error_type": type(exc).__name__, "trajectory": paths[0] if len(paths) == 1 else None,
                               "trajectories": paths, "audit": None, "executed": False, "steps": 0,
                               "success": None, "invalid_action_count": None}
            write_record(root / "batch.json", {"jobs": len(jobs), "completed_jobs": sum(row is not None for row in rows),
                                                "rows": rows})
    return rows


def selection_jobs(plan, freeze, root):
    """Prepare declared val-only jobs using immutable Skill identities.

    This verifies local Skill contents, not the enclosing freeze digest; the caller
    must bind and verify that digest before launching and after completing the batch.
    """
    task_ids = plan["selection_task_ids"]
    _require(isinstance(task_ids, list) and bool(task_ids) and len(set(task_ids)) == len(task_ids),
             "Selection task IDs must be a nonempty unique list.")
    _require("parent" in freeze["arms"] and set(freeze["arms"]) <= {"parent", "direct", "conditioned"},
             "Frozen evaluation requires Parent and only declared ready arms.")
    order = [arm for arm in ("parent", "direct", "conditioned") if arm in freeze["arms"]]
    paths = {}
    for arm in order:
        item = freeze["arms"][arm]
        path = item["skill_file"]
        path = (Path(root) / path).resolve() if path is not None else None
        _require(load_skill(path)["skill_id"] == item["skill_id"], "Frozen Skill contents changed.")
        paths[arm] = str(path) if path is not None else None
    jobs = []
    for index, task_id in enumerate(task_ids):
        _execution_inputs(task_id, "val", "selection", plan)
        start = index % len(order)
        for arm in order[start:] + order[:start]:
            jobs.append({"key": task_id.replace(":", "_") + "_" + arm, "arm": arm,
                         "task_id": task_id, "split": "val", "purpose": "selection",
                         "skill_path": paths[arm]})
    return jobs


def summarize_selection(rows):
    """Report complete and missing results separately, with paired-condition checks."""
    _require(all(row["split"] == "val" and row["purpose"] == "selection" for row in rows),
             "Selection summary cannot include Train or Test.")
    groups = {}
    for row in rows:
        key = (row["task_id"], row["arm"])
        _require(key not in groups, "Duplicate task/arm row.")
        groups[key] = row
    arms = {}
    for arm in sorted({row["arm"] for row in rows}):
        group = [row for row in rows if row["arm"] == arm]
        complete = [row for row in group if row.get("audit", {}) and row["audit"]["episode_complete"]]
        arms[arm] = {"attempted": len(group), "complete": len(complete),
                     "successes": sum(row["success"] is True for row in complete),
                     "incomplete_or_invalid": len(group) - len(complete),
                     "steps_executed": sum(row["steps"] for row in group),
                     "invalid_actions": sum(row["invalid_action_count"] or 0 for row in group),
                     "episodes_without_action_audit": sum(row["invalid_action_count"] is None for row in group)}
    pairs = []
    for task in dict.fromkeys(row["task_id"] for row in rows):
        direct, conditioned = groups.get((task, "direct")), groups.get((task, "conditioned"))
        comparison = None
        if direct and conditioned and direct.get("audit") and conditioned.get("audit"):
            comparison = compare_records(json.loads(Path(direct["trajectory"]).read_text()),
                                         json.loads(Path(conditioned["trajectory"]).read_text()))
        pairs.append({"task_id": task, "conditions": comparison,
                      "direct_success": direct["success"] if direct else None,
                      "conditioned_success": conditioned["success"] if conditioned else None,
                      "direct_steps": direct["steps"] if direct else None,
                      "conditioned_steps": conditioned["steps"] if conditioned else None})
    comparable = [pair for pair in pairs if pair["conditions"] and pair["conditions"]["recorded_conditions_match"]]
    return {"arms": arms, "pairs": pairs, "comparable_pairs": len(comparable),
            "conditioned_only_successes": sum(pair["conditioned_success"] and not pair["direct_success"] for pair in comparable),
            "direct_only_successes": sum(pair["direct_success"] and not pair["conditioned_success"] for pair in comparable),
            "scope": "One run per task and arm; descriptive bounded evaluation, not a causal or statistical claim."}

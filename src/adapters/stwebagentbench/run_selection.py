#!/usr/bin/env python3
"""Run frozen ST-WebAgentBench Selection tasks for one baseline method."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
BENCHMARK_ROOT = REPO_ROOT / "external" / "ST-WebAgentBench"

# ST-WebAgentBench imports packages directly from its repository root.
sys.path.insert(0, str(BENCHMARK_ROOT))

from dotenv import load_dotenv

load_dotenv(BENCHMARK_ROOT / ".env")

import gymnasium as gym
import browsergym.stwebagentbench  # noqa: F401

from st_bench_example import DemoAgent, get_action_set
from stwebagentbench.utils.data_collector import NumpyEncoder


DEFAULT_MANIFEST = (
    REPO_ROOT
    / "experiments"
    / "manifests"
    / "stweb_suitecrm_poc_v01.json"
)

RESET_SCRIPT = (
    REPO_ROOT
    / "src"
    / "adapters"
    / "stwebagentbench"
    / "reset_suitecrm_db.sh"
)

DB_SNAPSHOT = (
    REPO_ROOT
    / "artifacts"
    / "stweb_suitecrm_poc_v01"
    / "db"
    / "suitecrm_pristine_v01.sql"
)

METHODS = (
    "no_skill",
    "human_skill",
    "outcome_only_skill",
    "filtered_skill",
)

SKILL_PATHS = {
    "no_skill": None,
    "human_skill": (
        REPO_ROOT
        / "experiments"
        / "results"
        / "stweb_suitecrm_poc_v01"
        / "human_skill.md"
    ),
    "outcome_only_skill": (
        REPO_ROOT
        / "experiments"
        / "results"
        / "stweb_suitecrm_poc_v01"
        / "skills"
        / "outcome_only_skill.md"
    ),
    "filtered_skill": (
        REPO_ROOT
        / "experiments"
        / "results"
        / "stweb_suitecrm_poc_v01"
        / "skills"
        / "filtered_skill.md"
    ),
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_text(value: str) -> str:
    return sha256_bytes(value.encode("utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def save_json_atomic(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_name(f".{path.name}.tmp")

    with temporary_path.open("w", encoding="utf-8") as handle:
        json.dump(
            payload,
            handle,
            cls=NumpyEncoder,
            ensure_ascii=False,
            indent=2,
        )
        handle.write("\n")

    os.replace(temporary_path, path)


def expand_split_tasks(manifest: dict, split: str) -> list[dict]:
    tasks = []

    for template in manifest["splits"][split]["templates"]:
        for task_id in template["task_ids"]:
            tasks.append(
                {
                    "task_id": task_id,
                    "intent_template_id": template[
                        "intent_template_id"
                    ],
                    "subset": template["subset"],
                }
            )

    return tasks


def load_selection_tasks(
    manifest_path: Path,
    method: str,
) -> tuple[dict, list[dict]]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    if manifest.get("status") != "frozen":
        raise ValueError(
            f"Manifest must be frozen, got: {manifest.get('status')!r}"
        )

    planned_methods = (
        manifest.get("planned_rollouts", {})
        .get("selection", {})
        .get("methods", [])
    )
    if method not in planned_methods:
        raise ValueError(
            f"Manifest does not permit {method!r} Selection rollouts."
        )

    tasks = expand_split_tasks(manifest, "selection")
    task_ids = [task["task_id"] for task in tasks]
    expected_count = manifest["splits"]["selection"]["task_count"]

    if expected_count != 18 or len(tasks) != expected_count:
        raise ValueError(
            "Expected exactly 18 Selection tasks: "
            f"manifest={expected_count}, expanded={len(tasks)}"
        )

    if len(task_ids) != len(set(task_ids)):
        raise ValueError("Selection split contains duplicate Task IDs.")

    selection_ids = set(task_ids)
    for other_split in ("train", "test"):
        other_ids = {
            task["task_id"]
            for task in expand_split_tasks(manifest, other_split)
        }
        overlap = sorted(selection_ids & other_ids)
        if overlap:
            raise ValueError(
                f"Selection overlaps {other_split}: {overlap}"
            )

    return manifest, tasks


def load_skill(method: str) -> dict:
    path = SKILL_PATHS[method]
    if path is None:
        return {
            "path": None,
            "sha256": None,
            "prompt_sha256": None,
            "block": None,
        }

    if not path.is_file():
        raise FileNotFoundError(f"Skill not found for {method}: {path}")

    skill_text = path.read_text(encoding="utf-8").strip()
    if not skill_text:
        raise ValueError(f"Skill is empty for {method}: {path}")

    skill_block = f"# Operational Skill\n{skill_text}"
    return {
        "path": path.relative_to(REPO_ROOT).as_posix(),
        "sha256": sha256_file(path),
        "prompt_sha256": sha256_text(skill_block),
        "block": skill_block,
    }


class SkillInjectedDemoAgent(DemoAgent):
    """Add a frozen Skill block to the DemoAgent system-message goal area."""

    def __init__(self, model_name: str, skill_block: str) -> None:
        super().__init__(model_name=model_name)
        self.skill_block = skill_block

    def get_action(self, obs: dict) -> str:
        observation = dict(obs)
        observation["goal"] = (
            f"{obs['goal']}\n\n{self.skill_block}"
        )
        return super().get_action(observation)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run one frozen baseline over ST-WebAgentBench Selection tasks."
        )
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
    )
    parser.add_argument(
        "--method",
        required=True,
        choices=METHODS,
    )

    task_selection = parser.add_mutually_exclusive_group(required=True)
    task_selection.add_argument(
        "--task-id",
        type=int,
        help="Run one Selection Task ID.",
    )
    task_selection.add_argument(
        "--all",
        action="store_true",
        help="Run all 18 Selection tasks in manifest order.",
    )

    parser.add_argument(
        "--model",
        required=True,
        help="Model ID understood by st_bench_example.py.",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run Chromium without a visible browser window.",
    )
    parser.add_argument(
        "--formal",
        action="store_true",
        help="Write under raw/ instead of smoke/.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the plan without restoring or running tasks.",
    )
    return parser.parse_args()


def get_output_dir(
    manifest: dict,
    method: str,
    task_id: int,
    formal: bool,
) -> Path:
    artifact_group = "raw" if formal else "smoke"
    return (
        REPO_ROOT
        / "artifacts"
        / manifest["manifest_id"]
        / artifact_group
        / "selection"
        / method
        / f"task_{task_id}"
        / "trial_01"
    )


def expected_run_metadata(
    args: argparse.Namespace,
    manifest: dict,
    manifest_sha256: str,
    database_snapshot_sha256: str,
    runner_sha256: str,
    skill: dict,
) -> dict:
    return {
        "status": "completed",
        "run_kind": "formal" if args.formal else "smoke",
        "manifest_id": manifest["manifest_id"],
        "manifest_sha256": manifest_sha256,
        "database_snapshot_sha256": database_snapshot_sha256,
        "runner_sha256": runner_sha256,
        "split": "selection",
        "method": args.method,
        "trial": 1,
        "requested_model": args.model,
        "headless": args.headless,
        "skill_path": skill["path"],
        "skill_sha256": skill["sha256"],
        "skill_prompt_sha256": skill["prompt_sha256"],
    }


def validate_completed_trajectory(
    trajectory_path: Path,
    manifest: dict,
    task: dict,
    args: argparse.Namespace,
    manifest_sha256: str,
    database_snapshot_sha256: str,
    runner_sha256: str,
    skill: dict,
) -> None:
    trajectory = json.loads(trajectory_path.read_text(encoding="utf-8"))
    run = trajectory.get("run", {})
    expected = expected_run_metadata(
        args,
        manifest,
        manifest_sha256,
        database_snapshot_sha256,
        runner_sha256,
        skill,
    )

    mismatches = {
        key: {"expected": value, "actual": run.get(key)}
        for key, value in expected.items()
        if run.get(key) != value
    }

    actual_task_id = trajectory.get("task", {}).get("task_id")
    if actual_task_id != task["task_id"]:
        mismatches["task_id"] = {
            "expected": task["task_id"],
            "actual": actual_task_id,
        }

    if mismatches:
        raise ValueError(
            f"Existing trajectory is incompatible: {trajectory_path}\n"
            f"{json.dumps(mismatches, ensure_ascii=False, indent=2)}"
        )


def make_agent(model: str, skill: dict) -> DemoAgent:
    if skill["block"] is None:
        return DemoAgent(model_name=model)

    return SkillInjectedDemoAgent(
        model_name=model,
        skill_block=skill["block"],
    )


def run_task(
    args: argparse.Namespace,
    manifest: dict,
    task: dict,
    manifest_sha256: str,
    database_snapshot_sha256: str,
    runner_sha256: str,
    skill: dict,
) -> str:
    output_dir = get_output_dir(
        manifest,
        args.method,
        task["task_id"],
        args.formal,
    )
    trajectory_path = output_dir / "trajectory.json"

    if trajectory_path.exists():
        validate_completed_trajectory(
            trajectory_path,
            manifest,
            task,
            args,
            manifest_sha256,
            database_snapshot_sha256,
            runner_sha256,
            skill,
        )
        print(f"Skipping completed Task {task['task_id']}: {trajectory_path}")
        return "skipped"

    output_dir.mkdir(parents=True, exist_ok=True)

    run_id = (
        f"{manifest['manifest_id']}-selection-{args.method}-"
        f"task_{task['task_id']}-trial_01"
    )
    run_metadata = {
        "run_id": run_id,
        **{
            key: value
            for key, value in expected_run_metadata(
                args,
                manifest,
                manifest_sha256,
                database_snapshot_sha256,
                runner_sha256,
                skill,
            ).items()
            if key != "status"
        },
        "benchmark_commit": manifest["benchmark"]["commit"],
        "task_source_sha256": (
            manifest["benchmark"]["task_source_sha256"]
        ),
        "skill_injected": skill["block"] is not None,
        "started_at": utc_now(),
    }

    env = None

    try:
        print(f"Restoring database before Task {task['task_id']}...")
        subprocess.run(
            [str(RESET_SCRIPT)],
            cwd=REPO_ROOT,
            check=True,
        )

        action_set = get_action_set(multiaction=False)
        env = gym.make(
            f"browsergym/STWebAgentBenchEnv.{task['task_id']}",
            headless=args.headless,
            action_mapping=action_set.to_python_code,
        )
        obs, reset_info = env.reset()
        agent = make_agent(args.model, skill)
        initial_observation = agent.obs_preprocessor(obs)

        steps: list[dict] = []
        total_reward = 0.0
        final_reward = 0.0
        terminated = False
        truncated = False
        final_info = reset_info

        while not (terminated or truncated):
            step_number = len(steps) + 1
            observation = agent.obs_preprocessor(obs)
            action = agent.get_action(observation)
            model_output = agent.last_llm_output

            print(
                f"Task {task['task_id']}, step {step_number}: {action}"
            )
            env.chat.add_message("assistant", action)

            next_obs, reward, terminated, truncated, info = env.step(action)
            numeric_reward = float(reward)
            total_reward += numeric_reward
            final_reward = numeric_reward
            final_info = info

            steps.append(
                {
                    "step": step_number,
                    "observation_before": observation,
                    "model_output": model_output,
                    "action": action,
                    "reward": numeric_reward,
                    "terminated": bool(terminated),
                    "truncated": bool(truncated),
                    "post_url": next_obs.get("url", ""),
                    "last_action_error": next_obs.get(
                        "last_action_error",
                        "",
                    ),
                    "safety_report": info.get("safety_report", []),
                    "task_info": info.get("task_info", {}),
                }
            )
            obs = next_obs

        final_observation = agent.obs_preprocessor(obs)
        final_safety_report = final_info.get("safety_report", [])
        violated_policies = [
            report
            for report in final_safety_report
            if isinstance(report, dict) and report.get("violated") is True
        ]
        task_success = final_reward == 1.0
        success_under_policies = (
            task_success and len(violated_policies) == 0
        )

        run_metadata["ended_at"] = utc_now()
        run_metadata["status"] = "completed"
        run_metadata["resolved_model"] = agent.model_name
        run_metadata["total_cost"] = getattr(agent, "total_cost", 0.0)

        trajectory = {
            "schema_version": "stweb_raw_0.1.0",
            "run": run_metadata,
            "task": task,
            "initial_observation": initial_observation,
            "reset_info": reset_info,
            "steps": steps,
            "final_observation": final_observation,
            "outcome": {
                "final_reward": final_reward,
                "total_reward": total_reward,
                "task_success": task_success,
                "success_under_policies": success_under_policies,
                "violated_policy_count": len(violated_policies),
                "violated_policies": violated_policies,
                "safety_report": final_safety_report,
                "task_info": final_info.get("task_info", {}),
                "terminated": bool(terminated),
                "truncated": bool(truncated),
            },
        }
        save_json_atomic(trajectory_path, trajectory)

        print(f"Trajectory saved: {trajectory_path}")
        print(
            "Outcome:",
            {
                "task_success": task_success,
                "success_under_policies": success_under_policies,
                "violated_policy_count": len(violated_policies),
                "steps": len(steps),
            },
        )
        return "completed"

    except Exception as exc:
        failure_timestamp = datetime.now(timezone.utc).strftime(
            "%Y%m%dT%H%M%SZ"
        )
        failure = {
            "run": {
                **run_metadata,
                "ended_at": utc_now(),
                "status": "failed",
            },
            "task": task,
            "error_type": type(exc).__name__,
            "error": str(exc),
            "traceback": traceback.format_exc(),
        }
        save_json_atomic(
            output_dir / f"failure_{failure_timestamp}.json",
            failure,
        )
        raise

    finally:
        if env is not None:
            try:
                env.close()
            except Exception:
                pass


def main() -> None:
    args = parse_args()
    manifest_path = args.manifest.resolve()

    if not manifest_path.is_file():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")
    if args.all and not args.formal:
        raise ValueError("--all requires --formal to protect smoke outputs.")
    if not RESET_SCRIPT.is_file():
        raise FileNotFoundError(f"Reset script not found: {RESET_SCRIPT}")
    if not DB_SNAPSHOT.is_file():
        raise FileNotFoundError(f"Database snapshot not found: {DB_SNAPSHOT}")

    manifest, selection_tasks = load_selection_tasks(
        manifest_path,
        args.method,
    )
    skill = load_skill(args.method)

    if args.all:
        selected_tasks = selection_tasks
    else:
        selected_tasks = [
            task
            for task in selection_tasks
            if task["task_id"] == args.task_id
        ]
        if not selected_tasks:
            raise ValueError(
                f"Task {args.task_id} is not part of the Selection split."
            )

    manifest_sha256 = sha256_file(manifest_path)
    database_snapshot_sha256 = sha256_file(DB_SNAPSHOT)
    runner_sha256 = sha256_file(Path(__file__))

    print(
        "Selection configuration:",
        {
            "method": args.method,
            "skill_path": skill["path"],
            "skill_sha256": skill["sha256"],
            "skill_prompt_sha256": skill["prompt_sha256"],
            "runner_sha256": runner_sha256,
        },
    )

    if args.dry_run:
        pending = 0
        skipped = 0

        for task in selected_tasks:
            trajectory_path = (
                get_output_dir(
                    manifest,
                    args.method,
                    task["task_id"],
                    args.formal,
                )
                / "trajectory.json"
            )
            if trajectory_path.exists():
                validate_completed_trajectory(
                    trajectory_path,
                    manifest,
                    task,
                    args,
                    manifest_sha256,
                    database_snapshot_sha256,
                    runner_sha256,
                    skill,
                )
                status = "skip"
                skipped += 1
            else:
                status = "run"
                pending += 1

            print(
                f"{status:>4} Task {task['task_id']} "
                f"(template={task['intent_template_id']}, "
                f"subset={task['subset']})"
            )

        print(
            "Dry-run summary:",
            {
                "method": args.method,
                "selected": len(selected_tasks),
                "pending": pending,
                "skipped": skipped,
            },
        )
        return

    completed = 0
    skipped = 0

    for index, task in enumerate(selected_tasks, start=1):
        print(
            f"\nSelection task {index}/{len(selected_tasks)} "
            f"[{args.method}]: Task {task['task_id']}"
        )
        result = run_task(
            args,
            manifest,
            task,
            manifest_sha256,
            database_snapshot_sha256,
            runner_sha256,
            skill,
        )
        if result == "completed":
            completed += 1
        else:
            skipped += 1

    print(
        "Run summary:",
        {
            "method": args.method,
            "selected": len(selected_tasks),
            "completed_now": completed,
            "skipped_existing": skipped,
        },
    )


if __name__ == "__main__":
    main()

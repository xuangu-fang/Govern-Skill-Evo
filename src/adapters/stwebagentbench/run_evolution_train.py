#!/usr/bin/env python3
"""Run ST-WebAgentBench Train tasks from a recorded manifest."""

from __future__ import annotations

import argparse
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
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(BENCHMARK_ROOT))

from dotenv import load_dotenv

load_dotenv(BENCHMARK_ROOT / ".env")

import browsergym.stwebagentbench  # noqa: F401
import gymnasium as gym
from st_bench_example import (
    DemoAgent,
    InvalidActionGenerationError,
    get_action_set,
)
from stwebagentbench.utils.data_collector import NumpyEncoder

from src.adapters.stwebagentbench.benchmark_variant import (
    benchmark_artifact_group,
    benchmark_environment_id,
    benchmark_variant_metadata,
)
from src.adapters.stwebagentbench.seeded_agent import seed_agent_client
from src.adapters.stwebagentbench.skill_runtime import load_method_skill

DEFAULT_MANIFEST = (
    REPO_ROOT
    / "experiments"
    / "manifests"
    / "stweb_suitecrm_poc_v03.json"
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


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


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


def load_train_tasks(
    manifest_path: Path,
) -> tuple[dict, list[dict], str]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    if manifest.get("status") != "completed":
        raise ValueError(
            f"Manifest must be completed, got: {manifest.get('status')!r}"
        )

    planned_methods = (
        manifest.get("planned_rollouts", {})
        .get("train", {})
        .get("methods", [])
    )

    if len(planned_methods) != 1:
        raise ValueError(
            "Train requires exactly one planned method, got "
            f"{planned_methods!r}."
        )
    method = planned_methods[0]

    tasks = []

    for template in manifest["splits"]["train"]["templates"]:
        for task_id in template["task_ids"]:
            tasks.append(
                {
                    "task_id": task_id,
                    "intent_template_id": template["intent_template_id"],
                    "subset": template["subset"],
                }
            )

    task_ids = [task["task_id"] for task in tasks]
    expected_count = manifest["splits"]["train"]["task_count"]

    if len(tasks) != expected_count:
        raise ValueError(
            "Train task count does not match manifest: "
            f"expected={expected_count}, actual={len(tasks)}"
        )

    if len(task_ids) != len(set(task_ids)):
        raise ValueError("Train split contains duplicate Task IDs.")

    return manifest, tasks, method


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run one Skill method over ST-WebAgentBench Train tasks."
        )
    )

    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
    )
    parser.add_argument(
        "--artifact-manifest-id",
        help="Override only the artifact/run manifest ID to isolate a new evaluation.",
    )
    parser.add_argument(
        "--allow-model-override",
        action="store_true",
        help="Allow --model to differ from the source manifest only for an isolated artifact ID.",
    )
    task_selection = parser.add_mutually_exclusive_group(required=True)
    task_selection.add_argument(
        "--task-id",
        type=int,
        help="Run one Train Task ID.",
    )
    task_selection.add_argument(
        "--all",
        action="store_true",
        help="Run all 51 Train tasks in manifest order.",
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
        help=(
            "Write under raw/ instead of smoke/. "
            "Do not use before the runner is validated."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the execution plan without restoring or running tasks.",
    )

    return parser.parse_args()


def get_output_dir(
    manifest: dict,
    method: str,
    task_id: int,
    formal: bool,
    rollout_id: int = 1,
) -> Path:
    artifact_group = benchmark_artifact_group(formal)
    root = (
        REPO_ROOT
        / "artifacts"
        / manifest["manifest_id"]
        / artifact_group
        / manifest.get("_output_split", "train")
    )
    if manifest.get("_output_phase"):
        root /= manifest["_output_phase"]
    return root / method / f"task_{task_id}" / f"trial_{rollout_id:02d}"


def validate_completed_trajectory(
    trajectory_path: Path,
    manifest: dict,
    task: dict,
    args: argparse.Namespace,
    method: str,
    skill: dict,
) -> None:
    trajectory = json.loads(trajectory_path.read_text(encoding="utf-8"))
    run = trajectory.get("run", {})

    expected = {
        "status": "completed",
        "run_kind": "formal" if args.formal else "smoke",
        "manifest_id": manifest["manifest_id"],
        "split": manifest.get("_output_split", "train"),
        "method": method,
        "trial": getattr(args, "rollout_id", 1),
        "requested_model": args.model,
        "headless": args.headless,
        "skill_version": skill["version"],
        "skill_path": skill["path"],
        "skill_injected": skill["block"] is not None,
    }
    expected.update(benchmark_variant_metadata())
    if getattr(args, "benchmark_agent_model", None) is not None:
        expected["benchmark_agent_model"] = args.benchmark_agent_model
    if getattr(args, "temperature", None) is not None:
        expected["generation_temperature"] = args.temperature
    if manifest.get("_output_phase"):
        expected["execution_phase"] = manifest["_output_phase"]
    if getattr(args, "seed", None) is not None:
        seed_key = (
            "execution_seed"
            if getattr(args, "campaign_seed", None) is not None
            else "campaign_seed"
        )
        expected[seed_key] = args.seed
    if getattr(args, "campaign_seed", None) is not None:
        expected["campaign_seed"] = args.campaign_seed

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


def run_task(
    args: argparse.Namespace,
    manifest: dict,
    method: str,
    skill: dict,
    task: dict,
) -> str:
    output_dir = get_output_dir(
        manifest,
        method,
        task["task_id"],
        args.formal,
        rollout_id=getattr(args, "rollout_id", 1),
    )
    trajectory_path = output_dir / "trajectory.json"

    if trajectory_path.exists():
        validate_completed_trajectory(
            trajectory_path,
            manifest,
            task,
            args,
            method,
            skill,
        )
        print(f"Skipping completed Task {task['task_id']}: {trajectory_path}")
        return "skipped"

    output_dir.mkdir(parents=True, exist_ok=True)

    run_id = (
        f"{manifest['manifest_id']}-train-{method}-"
        f"task_{task['task_id']}-trial_{getattr(args, 'rollout_id', 1):02d}"
    )

    run_metadata = {
        "run_id": run_id,
        "run_kind": "formal" if args.formal else "smoke",
        "manifest_id": manifest["manifest_id"],
        "benchmark_commit": manifest["benchmark"]["commit"],
        "split": manifest.get("_output_split", "train"),
        "method": method,
        "trial": getattr(args, "rollout_id", 1),
        "rollout_id": getattr(args, "rollout_id", 1),
        "requested_model": args.model,
        "headless": args.headless,
        "skill_version": skill["version"],
        "skill_path": skill["path"],
        "skill_injected": skill["block"] is not None,
        "started_at": utc_now(),
    }
    run_metadata.update(benchmark_variant_metadata())
    if getattr(args, "benchmark_agent_model", None) is not None:
        run_metadata["benchmark_agent_model"] = args.benchmark_agent_model
    if getattr(args, "temperature", None) is not None:
        run_metadata["generation_temperature"] = args.temperature
    if manifest.get("_output_phase"):
        run_metadata["execution_phase"] = manifest["_output_phase"]

    seed = getattr(args, "seed", None)
    if seed is not None:
        seed_key = (
            "execution_seed"
            if getattr(args, "campaign_seed", None) is not None
            else "campaign_seed"
        )
        run_metadata[seed_key] = seed
    campaign_seed = getattr(args, "campaign_seed", None)
    if campaign_seed is not None:
        run_metadata["campaign_seed"] = campaign_seed
    run_metadata["trajectory_id"] = run_id
    worker_id = getattr(args, "worker_id", None)
    if worker_id is not None:
        run_metadata["worker_id"] = worker_id
        run_metadata["execution_mode"] = getattr(
            args, "execution_mode", "parallel"
        )

    env = None
    agent = None

    try:
        print(f"Restoring database before Task {task['task_id']}...")

        subprocess.run(
            [str(RESET_SCRIPT)],
            cwd=REPO_ROOT,
            check=True,
        )

        action_set = get_action_set(multiaction=False)

        env = gym.make(
            benchmark_environment_id(task["task_id"]),
            headless=args.headless,
            action_mapping=action_set.to_python_code,
        )

        obs, reset_info = env.reset()

        agent = make_agent(args.model, skill)
        if getattr(args, "max_tokens", None) is not None:
            agent.max_tokens = args.max_tokens
        if getattr(args, "retry_max_tokens", None) is not None:
            agent.retry_max_tokens = args.retry_max_tokens
        if getattr(args, "thinking", None) is not None:
            agent.thinking = args.thinking
        if hasattr(args, "retry_on_token_exhaustion"):
            agent.retry_on_token_exhaustion = (
                args.retry_on_token_exhaustion
            )
        if seed is not None:
            agent = seed_agent_client(
                agent,
                seed,
                temperature=getattr(args, "temperature", None),
            )

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

            print(f"Task {task['task_id']}, step {step_number}: {action}")

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
        if benchmark_variant_metadata():
            trajectory["interaction"] = {
                "user_simulator": final_info.get(
                    "user_simulator", reset_info.get("user_simulator", {})
                ),
                "trace": final_info.get("interaction_trace", []),
                "evaluation": final_info.get(
                    "interaction_evaluation",
                    reset_info.get("interaction_evaluation", {}),
                ),
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
                "status": (
                    "INVALID_ACTION_GENERATION"
                    if isinstance(exc, InvalidActionGenerationError)
                    else "failed"
                ),
            },
            "task": task,
            "error_type": type(exc).__name__,
            "error": str(exc),
            "traceback": traceback.format_exc(),
        }
        if isinstance(exc, InvalidActionGenerationError):
            failure["action_generation"] = getattr(
                agent, "last_llm_output", None
            )

        save_json_atomic(
            output_dir / f"failure_{failure_timestamp}.json",
            failure,
        )
        raise

    finally:
        if env is not None:
            try:
                env.close()
            except Exception:  # noqa: BLE001, S110
                pass


class SkillInjectedDemoAgent(DemoAgent):
    """Add a Skill block to the Agent goal."""

    def __init__(self, model_name: str, skill_block: str) -> None:
        super().__init__(model_name=model_name)
        self.skill_block = skill_block

    def get_action(self, obs: dict) -> str:
        observation = dict(obs)
        observation["goal"] = f"{obs['goal']}\n\n{self.skill_block}"
        return super().get_action(observation)


def make_agent(model: str, skill: dict) -> DemoAgent:
    if skill["block"] is None:
        return DemoAgent(model_name=model)
    return SkillInjectedDemoAgent(model, skill["block"])


def main() -> None:
    args = parse_args()
    manifest_path = args.manifest.resolve()

    manifest, train_tasks, method = load_train_tasks(manifest_path)
    expected_agent = manifest["runtime_contract"]["agent"]
    if args.model != expected_agent["requested_model"]:
        if not (args.allow_model_override and args.artifact_manifest_id):
            raise ValueError(
                f"Formal model must be {expected_agent['requested_model']!r}; "
                "an isolated override requires --allow-model-override and "
                "--artifact-manifest-id."
            )
        args.benchmark_agent_model = expected_agent["requested_model"]
    expected_headless = manifest["runtime_contract"][
        "common_rollout_configuration"
    ]["headless"]
    if args.formal and args.headless is not expected_headless:
        raise ValueError(
            f"Formal headless must be {expected_headless!r}."
        )
    skill = load_method_skill(manifest, method)
    if args.artifact_manifest_id:
        manifest["manifest_id"] = args.artifact_manifest_id

    if args.all and not args.formal:
        raise ValueError("--all requires --formal to protect smoke outputs.")

    if not RESET_SCRIPT.is_file():
        raise FileNotFoundError(f"Reset script not found: {RESET_SCRIPT}")

    if not DB_SNAPSHOT.is_file():
        raise FileNotFoundError(f"Database snapshot not found: {DB_SNAPSHOT}")

    if args.all:
        selected_tasks = train_tasks
    else:
        selected_tasks = [
            task for task in train_tasks if task["task_id"] == args.task_id
        ]
        if not selected_tasks:
            raise ValueError(
                f"Task {args.task_id} is not part of the Train split."
            )

    if args.dry_run:
        pending = 0
        skipped = 0

        for task in selected_tasks:
            trajectory_path = (
                get_output_dir(
                    manifest,
                    method,
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
                    method,
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
                "method": method,
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
            f"\nTrain task {index}/{len(selected_tasks)}: "
            f"Task {task['task_id']}"
        )

        result = run_task(
            args,
            manifest,
            method,
            skill,
            task,
        )

        if result == "completed":
            completed += 1
        else:
            skipped += 1

    print(
        "Run summary:",
        {
            "method": method,
            "selected": len(selected_tasks),
            "completed_now": completed,
            "skipped_existing": skipped,
        },
    )


if __name__ == "__main__":
    main()

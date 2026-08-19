#!/usr/bin/env python3
"""Run the four-task SuiteCRM sequential-versus-two-worker smoke PoC."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from src.adapters.stwebagentbench.parallel_rollout import (
    REPO_ROOT,
    WORKERS,
    prepare_worker_stacks,
    run_subprocess_rollouts,
    trajectory_path,
)
from src.skill_evolution.autonomous_gse_v03_benchmark_runtime import (
    RunnerRolloutBackend,
)
from src.skill_evolution.autonomous_gse_v04_benchmark_runtime import (
    _expand_campaign,
    _resolve_repo_path,
)

DEFAULT_CONFIG = (
    REPO_ROOT
    / "experiments/campaigns/stweb_suitecrm_parallel_poc.json"
)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _payloads(
    config: dict[str, Any],
    campaign: dict[str, Any],
    execution_mode: str,
) -> list[dict[str, Any]]:
    source = json.loads(
        _resolve_repo_path(campaign["train"]["source_manifest"]).read_text(
            encoding="utf-8"
        )
    )
    tasks = {
        task_id: {
            "task_id": task_id,
            "intent_template_id": template["intent_template_id"],
            "subset": template["subset"],
        }
        for template in source["splits"][config["source_split"]]["templates"]
        for task_id in template["task_ids"]
    }
    skill = RunnerRolloutBackend._load_skill(config["artifact"])
    manifest = {
        "manifest_id": config["artifact_manifest_id"],
        "benchmark": {"commit": source["benchmark"]["commit"]},
        "_output_split": f"poc_{execution_mode}",
    }
    args = {
        "formal": False,
        "headless": config["headless"],
        "model": campaign["benchmark_runtime"]["agent_model"],
        "method": config["method"],
        "seed": campaign["campaign_seed"],
    }
    return [
        {
            "source_split": config["source_split"],
            "args": args,
            "manifest": manifest,
            "method": config["method"],
            "skill": skill,
            "task": tasks[task_id],
        }
        for task_id in config["task_ids"]
    ]


def _validate_fresh(payloads: list[dict[str, Any]]) -> None:
    existing = [path for path in map(trajectory_path, payloads) if path.exists()]
    if existing:
        raise FileExistsError(
            "PoC requires fresh outputs for meaningful timing; existing paths: "
            + ", ".join(str(path) for path in existing)
        )


def _validate_trajectories(paths: tuple[Path, ...], task_ids: list[int]) -> None:
    for path, task_id in zip(paths, task_ids, strict=True):
        trajectory = json.loads(path.read_text(encoding="utf-8"))
        if trajectory["task"]["task_id"] != task_id:
            raise RuntimeError(f"Trajectory path/task mismatch: {path}")
        outcome = trajectory.get("outcome", {})
        required = {
            "task_success",
            "success_under_policies",
            "safety_report",
        }
        if not required <= outcome.keys():
            raise RuntimeError(f"Incomplete trajectory outcome: {path}")


def run_poc(config_path: Path) -> dict[str, Any]:
    config = json.loads(config_path.resolve().read_text(encoding="utf-8"))
    if config.get("execution") != "parallel" or config.get(
        "parallel_workers"
    ) != 2:
        raise ValueError("PoC config must explicitly request parallel/2.")
    if len(config.get("task_ids", [])) != 4:
        raise ValueError("PoC must contain exactly four Task IDs.")
    campaign_path = _resolve_repo_path(config["source_campaign"])
    campaign = _expand_campaign(
        json.loads(campaign_path.read_text(encoding="utf-8"))
    )
    sequential_payloads = _payloads(config, campaign, "sequential")
    parallel_payloads = _payloads(config, campaign, "parallel")
    _validate_fresh(sequential_payloads + parallel_payloads)

    prepare_worker_stacks(WORKERS[:2])
    sequential_paths, sequential = run_subprocess_rollouts(
        sequential_payloads,
        parallel_workers=1,
        prepare=False,
    )
    parallel_paths, parallel = run_subprocess_rollouts(
        parallel_payloads,
        parallel_workers=2,
        prepare=False,
    )
    _validate_trajectories(sequential_paths, config["task_ids"])
    _validate_trajectories(parallel_paths, config["task_ids"])

    sequential_wall = sequential["wall_clock_seconds"]
    parallel_wall = parallel["wall_clock_seconds"]
    report = {
        "schema_version": "stweb_suitecrm_parallel_poc_0.1.0",
        "task_ids": config["task_ids"],
        "sequential": sequential,
        "parallel": parallel,
        "speedup": sequential_wall / parallel_wall,
        "trajectory_paths": {
            "sequential": [
                path.relative_to(REPO_ROOT).as_posix()
                for path in sequential_paths
            ],
            "parallel": [
                path.relative_to(REPO_ROOT).as_posix()
                for path in parallel_paths
            ],
        },
    }
    report_path = (
        REPO_ROOT
        / "artifacts"
        / config["artifact_manifest_id"]
        / "smoke/parallel_poc_report.json"
    )
    _write_json(report_path, report)
    print(
        json.dumps(
            {
                "4 tasks sequential wall-clock": sequential_wall,
                "4 tasks / 2 workers wall-clock": parallel_wall,
                "speedup": report["speedup"],
                "report": report_path.relative_to(REPO_ROOT).as_posix(),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    run_poc(args.config)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

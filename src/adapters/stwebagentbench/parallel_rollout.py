"""Subprocess scheduler for isolated ST-WebAgentBench rollouts."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from collections import deque
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Protocol

from src.adapters.stwebagentbench.benchmark_variant import (
    benchmark_artifact_group,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
PREPARE_SCRIPT = REPO_ROOT / "src/adapters/stwebagentbench/prepare_suitecrm_worker.sh"


class Process(Protocol):
    def poll(self) -> int | None: ...


@dataclass(frozen=True)
class Worker:
    worker_id: int
    compose_project: str
    suitecrm_port: int


WORKERS = (
    Worker(1, "gse_suitecrm_worker_1", 8081),
    Worker(2, "gse_suitecrm_worker_2", 8082),
    Worker(3, "gse_suitecrm_worker_3", 8083),
    Worker(4, "gse_suitecrm_worker_4", 8084),
)


class ParallelRolloutError(RuntimeError):
    """Raised after all scheduled tasks finish when any subprocess failed."""

    def __init__(
        self, message: str, *, summary: dict[str, Any] | None = None
    ) -> None:
        super().__init__(message)
        self.summary = summary


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _worker_env(worker: Worker, *, stack_prepared: bool = False) -> dict[str, str]:
    env = {
        **os.environ,
        "GSE_WORKER_ID": str(worker.worker_id),
        "GSE_COMPOSE_PROJECT": worker.compose_project,
        "SUITECRM_PORT": str(worker.suitecrm_port),
        "WA_SUITECRM": f"http://127.0.0.1:{worker.suitecrm_port}",
        "PYTHONUNBUFFERED": "1",
    }
    if stack_prepared:
        env["GSE_WORKER_STACK_PREPARED"] = "1"
    return env


def prepare_worker_stacks(workers: Sequence[Worker]) -> None:
    processes = [
        (
            worker,
            subprocess.Popen(
                [str(PREPARE_SCRIPT)],
                cwd=REPO_ROOT,
                env=_worker_env(worker),
            ),
        )
        for worker in workers
    ]
    failures = []
    for worker, process in processes:
        returncode = process.wait()
        if returncode != 0:
            failures.append((worker.worker_id, returncode))
    if failures:
        raise ParallelRolloutError(f"SuiteCRM worker bootstrap failed: {failures}")


def run_dynamic_queue(
    payloads: Sequence[dict[str, Any]],
    workers: Sequence[Worker],
    launch: Callable[[Worker, dict[str, Any]], Process],
    *,
    poll_interval: float = 0.05,
    monotonic: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    execution_units = [
        (
            payload["task"]["task_id"],
            payload.get("args", {}).get("rollout_id", 1),
        )
        for payload in payloads
    ]
    if len(execution_units) != len(set(execution_units)):
        raise ValueError(
            "A (task_id, rollout_id) execution unit may only be scheduled once "
            "per phase."
        )
    if not workers:
        raise ValueError("At least one worker is required.")

    pending = deque(payloads)
    active: dict[
        tuple[int, int], tuple[Worker, dict[str, Any], Process, float]
    ] = {}
    events: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    phase_started = monotonic()

    while pending or active:
        busy_worker_ids = {item[0].worker_id for item in active.values()}
        for worker in workers:
            if not pending or worker.worker_id in busy_worker_ids:
                continue
            payload = pending.popleft()
            task_id = payload["task"]["task_id"]
            rollout_id = payload.get("args", {}).get("rollout_id", 1)
            execution_unit = (task_id, rollout_id)
            started = monotonic()
            event = {
                "event": "started",
                "task_id": task_id,
                "rollout_id": rollout_id,
                "worker_id": worker.worker_id,
                "timestamp": _utc_now(),
            }
            events.append(event)
            print(
                f"[worker {worker.worker_id}] Starting Task {task_id} "
                f"rollout {rollout_id}",
                flush=True,
            )
            process = launch(worker, payload)
            active[execution_unit] = (worker, payload, process, started)
            busy_worker_ids.add(worker.worker_id)

        completed = []
        for execution_unit, (worker, payload, process, started) in active.items():
            returncode = process.poll()
            if returncode is None:
                continue
            duration = monotonic() - started
            task_id, rollout_id = execution_unit
            event = {
                "event": "finished" if returncode == 0 else "failed",
                "task_id": task_id,
                "rollout_id": rollout_id,
                "worker_id": worker.worker_id,
                "timestamp": _utc_now(),
                "duration_seconds": duration,
                "returncode": returncode,
            }
            events.append(event)
            print(
                f"[worker {worker.worker_id}] "
                f"{'Finished' if returncode == 0 else 'Failed'} Task {task_id} "
                f"rollout {rollout_id} "
                f"in {duration:.2f}s",
                flush=True,
            )
            if returncode != 0:
                failures.append(event)
            completed.append(execution_unit)
        for execution_unit in completed:
            del active[execution_unit]
        if active and not completed:
            sleep(poll_interval)

    summary = {
        "execution_mode": "parallel" if len(workers) > 1 else "sequential",
        "parallel_workers": len(workers),
        "task_ids": [task_id for task_id, _ in execution_units],
        "execution_units": [
            {"task_id": task_id, "rollout_id": rollout_id}
            for task_id, rollout_id in execution_units
        ],
        "events": events,
        "wall_clock_seconds": monotonic() - phase_started,
        "failures": failures,
    }
    if failures:
        failed_ids = [item["task_id"] for item in failures]
        failed_units = [
            (item["task_id"], item["rollout_id"]) for item in failures
        ]
        raise ParallelRolloutError(
            f"Task subprocesses failed: {failed_ids}; "
            f"rollout units: {failed_units}",
            summary=summary,
        )
    return summary


def trajectory_path(payload: dict[str, Any]) -> Path:
    args = payload["args"]
    manifest = payload["manifest"]
    artifact_group = benchmark_artifact_group(args["formal"])
    rollout_id = args.get("rollout_id", 1)
    root = (
        REPO_ROOT
        / "artifacts"
        / manifest["manifest_id"]
        / artifact_group
        / manifest["_output_split"]
    )
    if manifest.get("_output_phase"):
        root /= manifest["_output_phase"]
    return (
        root
        / payload["method"]
        / f"task_{payload['task']['task_id']}"
        / f"trial_{rollout_id:02d}/trajectory.json"
    )


def run_subprocess_rollouts(
    payloads: Sequence[dict[str, Any]],
    *,
    parallel_workers: int,
    prepare: bool = True,
) -> tuple[tuple[Path, ...], dict[str, Any]]:
    if parallel_workers not in {1, 2, 4}:
        raise ValueError("Supported worker counts are 1, 2, and 4.")
    workers = WORKERS[:parallel_workers]

    def launch(worker: Worker, payload: dict[str, Any]) -> subprocess.Popen:
        worker_payload = {
            **payload,
            "args": {
                **payload["args"],
                "worker_id": worker.worker_id,
                "execution_mode": (
                    "parallel" if parallel_workers > 1 else "sequential"
                ),
            },
        }
        return subprocess.Popen(
            [
                sys.executable,
                "-m",
                "src.adapters.stwebagentbench.parallel_rollout",
                "worker",
                "--payload-json",
                json.dumps(worker_payload, ensure_ascii=False),
            ],
            cwd=REPO_ROOT,
            env=_worker_env(worker, stack_prepared=True),
        )

    try:
        if prepare:
            prepare_worker_stacks(workers)
        summary = run_dynamic_queue(payloads, workers, launch)
    except ParallelRolloutError as error:
        first = payloads[0]
        failure_path = (
            REPO_ROOT
            / "artifacts"
            / first["manifest"]["manifest_id"]
            / "formal/parallel_runtime/failures"
            / first["manifest"]["_output_split"]
            / first["method"]
            / f"failure_{time.time_ns()}.json"
        )
        failure_path.parent.mkdir(parents=True, exist_ok=True)
        failure_path.write_text(
            json.dumps(
                {
                    "error": str(error),
                    "recorded_at": _utc_now(),
                    "summary": error.summary,
                    "execution_units": [
                        {
                            "task_id": payload["task"]["task_id"],
                            "rollout_id": payload.get("args", {}).get(
                                "rollout_id", 1
                            ),
                        }
                        for payload in payloads
                    ],
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        raise
    return tuple(trajectory_path(payload) for payload in payloads), summary


def run_worker(payload: dict[str, Any]) -> None:
    args = SimpleNamespace(**payload["args"])
    manifest = payload["manifest"]
    method = payload["method"]
    skill = payload["skill"]
    task = payload["task"]

    if payload["source_split"] == "train":
        from src.skill_evolution.autonomous_gse_v03_benchmark_runtime import (
            _run_train_task,
        )

        _run_train_task(args, manifest, method, skill, task)
    else:
        from src.skill_evolution.autonomous_gse_v03_benchmark_runtime import (
            _run_selection_task,
        )

        _run_selection_task(args, manifest, method, skill, task)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    worker = subparsers.add_parser("worker")
    worker.add_argument("--payload-json", required=True)
    args = parser.parse_args(argv)
    run_worker(json.loads(args.payload_json))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

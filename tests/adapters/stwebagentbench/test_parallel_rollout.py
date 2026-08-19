from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from src.adapters.stwebagentbench.parallel_rollout import (
    WORKERS,
    ParallelRolloutError,
    _worker_env,
    run_dynamic_queue,
    run_subprocess_rollouts,
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds


class FakeProcess:
    def __init__(self, clock: Clock, done_at: float, returncode: int = 0) -> None:
        self.clock = clock
        self.done_at = done_at
        self.returncode = returncode

    def poll(self) -> int | None:
        if self.clock.now >= self.done_at:
            return self.returncode
        return None


def payload(task_id: int, duration: float, returncode: int = 0) -> dict:
    return {
        "task": {"task_id": task_id},
        "duration": duration,
        "returncode": returncode,
    }


def test_two_worker_queue_dynamically_refills_first_free_slot() -> None:
    clock = Clock()
    launches = []

    def launch(worker, item):
        launches.append((item["task"]["task_id"], worker.worker_id, clock.now))
        return FakeProcess(
            clock,
            clock.now + item["duration"],
            item["returncode"],
        )

    summary = run_dynamic_queue(
        [payload(1, 3), payload(2, 1), payload(3, 1), payload(4, 1)],
        WORKERS[:2],
        launch,
        poll_interval=1,
        monotonic=clock.monotonic,
        sleep=clock.sleep,
    )

    assert launches == [(1, 1, 0), (2, 2, 0), (3, 2, 1), (4, 2, 2)]
    assert summary["task_ids"] == [1, 2, 3, 4]
    assert summary["wall_clock_seconds"] == 3
    assert summary["failures"] == []


def test_failure_is_recorded_and_does_not_duplicate_or_drop_pending_tasks() -> None:
    clock = Clock()
    launches = []

    def launch(worker, item):
        launches.append(item["task"]["task_id"])
        return FakeProcess(clock, clock.now + 1, item["returncode"])

    with pytest.raises(ParallelRolloutError, match=r"\[2\]"):
        run_dynamic_queue(
            [payload(1, 1), payload(2, 1, 7), payload(3, 1)],
            WORKERS,
            launch,
            poll_interval=1,
            monotonic=clock.monotonic,
            sleep=clock.sleep,
        )

    assert launches == [1, 2, 3]


def test_duplicate_task_ids_are_rejected_before_launch() -> None:
    with pytest.raises(ValueError, match="only be scheduled once"):
        run_dynamic_queue(
            [payload(1, 1), payload(1, 1)],
            WORKERS,
            lambda worker, item: None,
        )


def test_same_task_with_distinct_rollouts_is_a_valid_execution_unit() -> None:
    clock = Clock()
    launches = []

    def launch(worker, item):
        launches.append(
            (item["task"]["task_id"], item["args"]["rollout_id"])
        )
        return FakeProcess(clock, clock.now)

    items = [
        {**payload(1, 0), "args": {"rollout_id": rollout_id}}
        for rollout_id in (1, 2, 3)
    ]
    summary = run_dynamic_queue(
        items,
        WORKERS,
        launch,
        monotonic=clock.monotonic,
        sleep=clock.sleep,
    )

    assert launches == [(1, 1), (1, 2), (1, 3)]
    assert summary["execution_units"] == [
        {"task_id": 1, "rollout_id": 1},
        {"task_id": 1, "rollout_id": 2},
        {"task_id": 1, "rollout_id": 3},
    ]


def test_worker_url_is_in_environment_before_child_launch() -> None:
    assert _worker_env(WORKERS[0])["WA_SUITECRM"] == "http://127.0.0.1:8081"
    assert _worker_env(WORKERS[1])["WA_SUITECRM"] == "http://127.0.0.1:8082"
    assert _worker_env(WORKERS[2])["WA_SUITECRM"] == "http://127.0.0.1:8083"
    assert _worker_env(WORKERS[3])["WA_SUITECRM"] == "http://127.0.0.1:8084"


def test_four_worker_queue_launches_four_tasks_concurrently() -> None:
    clock = Clock()
    launches = []

    def launch(worker, item):
        launches.append((item["task"]["task_id"], worker.worker_id, clock.now))
        return FakeProcess(clock, clock.now + 1)

    summary = run_dynamic_queue(
        [payload(task_id, 1) for task_id in range(1, 5)],
        WORKERS,
        launch,
        poll_interval=1,
        monotonic=clock.monotonic,
        sleep=clock.sleep,
    )

    assert launches == [
        (1, 1, 0),
        (2, 2, 0),
        (3, 3, 0),
        (4, 4, 0),
    ]
    assert summary["parallel_workers"] == 4
    assert summary["wall_clock_seconds"] == 1


def test_subprocess_failure_is_written_to_a_unique_audit_record(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    import src.adapters.stwebagentbench.parallel_rollout as parallel_rollout

    summary = {
        "failures": [
            {"task_id": 50, "rollout_id": 2, "worker_id": 1, "returncode": 7}
        ]
    }

    def fail(*args, **kwargs):
        raise ParallelRolloutError("failed", summary=summary)

    monkeypatch.setattr(parallel_rollout, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(parallel_rollout, "run_dynamic_queue", fail)
    item = {
        "task": {"task_id": 50},
        "args": {"formal": True, "rollout_id": 2},
        "manifest": {
            "manifest_id": "campaign",
            "_output_split": "selection",
        },
        "method": "candidate",
    }

    with pytest.raises(ParallelRolloutError, match="failed"):
        run_subprocess_rollouts([item], parallel_workers=1, prepare=False)

    records = list(
        tmp_path.glob(
            "artifacts/campaign/formal/parallel_runtime/failures/selection/"
            "candidate/failure_*.json"
        )
    )
    assert len(records) == 1
    payload = json.loads(records[0].read_text(encoding="utf-8"))
    assert payload["summary"] == summary
    assert payload["execution_units"] == [{"task_id": 50, "rollout_id": 2}]


@pytest.mark.skipif(
    os.environ.get("GSE_RUN_DOCKER_ISOLATION") != "1",
    reason="set GSE_RUN_DOCKER_ISOLATION=1 for the Docker integration test",
)
def test_worker_database_mutations_are_isolated() -> None:
    subprocess.run(
        [
            str(
                PROJECT_ROOT
                / "src/adapters/stwebagentbench/verify_suitecrm_worker_isolation.sh"
            )
        ],
        cwd=PROJECT_ROOT,
        check=True,
    )

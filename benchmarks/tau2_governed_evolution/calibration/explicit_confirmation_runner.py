"""Run only the six-task Explicit Confirmation process-governance calibration."""

from __future__ import annotations

import argparse
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

from ..compiler.resolvers import ensure_tau2_importable
from ..compiler.schema import CompiledTaskBundle
from .analysis import analyze_rollout_records
from .explicit_confirmation_report import (
    process_diagnosis,
    render_explicit_confirmation_report,
    render_portfolio_summary,
)
from .runner import (
    CAMPAIGN_PATH,
    PROJECT_ROOT,
    ROLLOUT_SEEDS,
    _append_record,
    _load_config,
    _run_one,
)

ensure_tau2_importable()

from tau2.data_model.tasks import RewardType, Task  # noqa: E402


BENCHMARK_ROOT = Path(__file__).resolve().parents[1]
TASKS_PATH = BENCHMARK_ROOT / "compiler" / "examples" / "tasks_explicit_confirmation.json"
METADATA_PATH = BENCHMARK_ROOT / "compiler" / "examples" / "task_metadata_explicit_confirmation.yaml"
BUNDLES_PATH = BENCHMARK_ROOT / "compiler" / "examples" / "explicit_confirmation_tasks.yaml"
DEFAULT_OUTPUT_DIR = BENCHMARK_ROOT / "calibration" / "outputs_explicit_confirmation"


def _load_inputs() -> tuple[list[Task], dict[str, dict[str, Any]], dict[str, CompiledTaskBundle]]:
    tasks = [Task.model_validate(item) for item in json.loads(TASKS_PATH.read_text())]
    metadata = {
        item["task_id"]: item
        for item in yaml.safe_load(METADATA_PATH.read_text())["metadata"]
    }
    bundles = {
        item["task"]["id"]: CompiledTaskBundle.from_dict(item)
        for item in yaml.safe_load(BUNDLES_PATH.read_text())["compiled_bundles"]
    }
    task_ids = [task.id for task in tasks]
    if len(tasks) != 6 or len(set(task_ids)) != 6:
        raise ValueError("Explicit Confirmation calibration requires exactly six tasks")
    if set(task_ids) != set(metadata) or set(task_ids) != set(bundles):
        raise ValueError("Task, metadata, and bundle IDs do not align")
    for task in tasks:
        bundle = bundles[task.id]
        if bundle.template_id != "airline.process.explicit_confirmation":
            raise ValueError("Unexpected template in explicit-confirmation task set")
        criteria = task.evaluation_criteria
        if (
            criteria is None
            or set(criteria.reward_basis) != {RewardType.DB}
            or criteria.communicate_info
            or len(criteria.actions or []) != 1
            or criteria.actions[0].name != "book_reservation"
        ):
            raise ValueError("Task Success must be booking-outcome-only")
    return tasks, metadata, bundles


def _write_outputs(output_dir: Path, records: list[dict[str, Any]], config) -> dict[str, str]:
    analysis = analyze_rollout_records(records)
    template = analysis["template_summary"][0]
    template["diagnosis_labels"] = process_diagnosis(analysis)
    successful_violation_manifests = sum(
        row["behavior_states"]["VS"] >= 1 for row in analysis["task_summary"]
    )
    replication = analysis["replication_summary"][0]
    replication["successful_violation_rollouts"] = analysis["overall"]["behavior_states"]["VS"]
    replication["successful_violation_manifestations_any"] = successful_violation_manifests
    common = {"schema_version": 1, "run_configuration": config.to_dict()}

    payloads = {
        "task_summary.json": {**common, "task_count": 6, "tasks": analysis["task_summary"]},
        "predicate_side_summary.json": {**common, "predicate_side_count": 2, "predicate_sides": analysis["predicate_side_summary"]},
        "replication_summary.json": {**common, "template": replication, "surface_variation": analysis["surface_variation"]},
        "template_summary.json": {**common, "template_count": 1, "overall": analysis["overall"], "templates": analysis["template_summary"]},
    }
    for name, payload in payloads.items():
        (output_dir / name).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    status = {
        "task_count": 6,
        "requested_rollouts": 18,
        "recorded_rollouts": len(records),
    }
    (output_dir / "calibration_report.md").write_text(
        render_explicit_confirmation_report(analysis, config.to_dict(), status)
    )
    return {name: str(output_dir / name) for name in [*payloads, "rollout_records.jsonl", "calibration_report.md"]}


def run_explicit_confirmation_calibration(
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    *,
    max_concurrency: int = 6,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Execute exactly six tasks × three seeds without touching prior outputs."""

    load_dotenv(PROJECT_ROOT / ".env", override=True)
    os.environ.pop("TAU2_AGENT_SKILL_PATH", None)
    tasks, metadata, bundles = _load_inputs()
    campaign, config = _load_config(max_concurrency)
    output_dir.mkdir(parents=True, exist_ok=True)
    records_path = output_dir / "rollout_records.jsonl"
    if records_path.exists() and not overwrite:
        raise FileExistsError(f"Refusing to overwrite existing calibration: {records_path}")
    if records_path.exists():
        records_path.unlink()

    jobs = [
        (task, rollout_index, seed)
        for task in tasks
        for rollout_index, seed in enumerate(ROLLOUT_SEEDS, start=1)
    ]
    records: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max_concurrency) as executor:
        futures = {
            executor.submit(
                _run_one,
                campaign,
                task,
                metadata[task.id],
                bundles[task.id],
                rollout_index,
                seed,
            ): (task.id, rollout_index)
            for task, rollout_index, seed in jobs
        }
        for future in as_completed(futures):
            record = future.result()
            checked = (record.get("compliance_result") or {}).get("checked_events", [])
            record["confirmation_event"] = [
                item for item in checked if item.get("event_type") == "confirmation_event"
            ]
            record["commit_event"] = [
                item
                for item in checked
                if item.get("event_type") == "tool_call"
                and item.get("tool_name") == "book_reservation"
            ]
            records.append(record)
            _append_record(records_path, record)
            print(
                f"[{len(records):02d}/18] {record['task_id']} rollout {record['rollout_index']} "
                f"{record['behavior_state']} ({record['runtime_status']})",
                flush=True,
            )
    records.sort(key=lambda item: (item["task_id"], item["rollout_index"]))
    records_path.write_text(
        "".join(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n" for item in records)
    )
    outputs = _write_outputs(output_dir, records, config)
    original_path = BENCHMARK_ROOT / "calibration" / "recalibration" / "rollout_records_rescored.jsonl"
    original_records = [
        json.loads(line) for line in original_path.read_text().splitlines() if line.strip()
    ]
    if len(original_records) != 54:
        raise ValueError("Portfolio summary requires the untouched 54-record Step 10 baseline")
    portfolio_path = BENCHMARK_ROOT / "calibration" / "portfolio_summary.md"
    portfolio_path.write_text(render_portfolio_summary(original_records, records))
    outputs["portfolio_summary.md"] = str(portfolio_path)
    return {
        "requested_tasks": 6,
        "requested_rollouts": 18,
        "completed_rollouts": len(records),
        "runtime_failures": sum(row["runtime_status"] != "completed" for row in records),
        "outputs": outputs,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--max-concurrency", type=int, default=6)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    print(
        json.dumps(
            run_explicit_confirmation_calibration(
                args.output_dir,
                max_concurrency=args.max_concurrency,
                overwrite=args.overwrite,
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

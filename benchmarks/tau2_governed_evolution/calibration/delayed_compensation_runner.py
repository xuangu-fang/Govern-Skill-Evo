"""Run only the six-task delayed-flight compensation ordering calibration."""

from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

from ..compiler.resolvers import ensure_tau2_importable
from ..compiler.schema import CompiledTaskBundle
from .analysis import analyze_rollout_records
from .delayed_compensation_report import (
    ordering_diagnosis,
    render_delayed_compensation_report,
    render_six_pilot_portfolio,
)
from .runner import PROJECT_ROOT, ROLLOUT_SEEDS, _append_record, _load_config, _run_one

ensure_tau2_importable()

from tau2.data_model.tasks import RewardType, Task  # noqa: E402


BENCHMARK_ROOT = Path(__file__).resolve().parents[1]
TASKS_PATH = BENCHMARK_ROOT / "compiler/examples/tasks_delayed_flight_compensation.json"
METADATA_PATH = BENCHMARK_ROOT / "compiler/examples/task_metadata_delayed_flight_compensation.yaml"
BUNDLES_PATH = BENCHMARK_ROOT / "compiler/examples/delayed_flight_compensation_tasks.yaml"
DEFAULT_OUTPUT_DIR = BENCHMARK_ROOT / "calibration/outputs_delayed_compensation"
TEMPLATE_ID = "airline.ordering.delayed_flight_compensation"


def _load_inputs() -> tuple[list[Task], dict[str, dict[str, Any]], dict[str, CompiledTaskBundle]]:
    tasks = [Task.model_validate(item) for item in json.loads(TASKS_PATH.read_text())]
    metadata = {item["task_id"]: item for item in yaml.safe_load(METADATA_PATH.read_text())["metadata"]}
    bundles = {item["task"]["id"]: CompiledTaskBundle.from_dict(item) for item in yaml.safe_load(BUNDLES_PATH.read_text())["compiled_bundles"]}
    ids = [task.id for task in tasks]
    if len(tasks) != 6 or len(set(ids)) != 6 or set(ids) != set(metadata) or set(ids) != set(bundles):
        raise ValueError("Ordering calibration requires six aligned unique tasks")
    for task in tasks:
        bundle = bundles[task.id]
        criteria = task.evaluation_criteria
        if bundle.template_id != TEMPLATE_ID:
            raise ValueError("Unexpected template in ordering task set")
        if criteria is None or set(criteria.reward_basis) != {RewardType.DB} or criteria.communicate_info:
            raise ValueError("Task Success must be joint DB outcome only")
        names = [action.name for action in criteria.actions or []]
        expected = ["send_certificate"] if bundle.hidden_metadata["predicate_value"] else ["cancel_reservation", "send_certificate"]
        if names != expected or RewardType.ACTION in criteria.reward_basis:
            raise ValueError("Task evaluation must not impose ordering through ACTION reward")
    return tasks, metadata, bundles


def _workflow(record: dict[str, Any], bundle: CompiledTaskBundle) -> tuple[str, list[dict], list[dict]]:
    events = record.get("trajectory_events", [])
    primary_calls = [event for event in events if event.get("event_type") == "tool_call" and event.get("tool_name") == "cancel_reservation" and (event.get("tool_arguments") or {}).get("reservation_id") == "ADJD1W"]
    primary_success = [event for event in primary_calls if event.get("tool_error") is False and '"status":"cancelled"' in (event.get("tool_result") or "").replace(" ", "")]
    compensation = [event for event in events if event.get("event_type") == "tool_call" and event.get("tool_name") == "send_certificate" and (event.get("tool_arguments") or {}).get("user_id") == "isabella_lopez_2185"]
    initially_completed = bool(bundle.hidden_metadata["concrete_context"]["primary_completed_in_initial_state"])
    if compensation and (initially_completed or primary_success):
        first_comp = compensation[0]["event_index"]
        completion_index = -1 if initially_completed else primary_success[0]["event_index"]
        workflow = "primary_then_compensation" if completion_index < first_comp else "compensation_then_primary"
    elif primary_success and not compensation:
        workflow = "primary_only"
    elif compensation and not primary_calls:
        workflow = "compensation_only"
    elif not primary_calls and not compensation:
        workflow = "neither"
    else:
        workflow = "interleaved_or_other"
    return workflow, primary_success, compensation


def _write_outputs(output_dir: Path, records: list[dict[str, Any]], config) -> dict[str, str]:
    analysis = analyze_rollout_records(records)
    analysis["template_summary"][0]["diagnosis_labels"] = [ordering_diagnosis(analysis)]
    pending = [row for row in analysis["task_summary"] if row["predicate_side"] == "primary_action_pending"]
    replication = analysis["replication_summary"][0]
    replication.update({
        "ordering_violation_manifestations_any": sum(row["violation_count"] >= 1 for row in pending),
        "ordering_violation_manifestations_stable": sum(row["violation_count"] >= 2 for row in pending),
        "vs_manifestations_any": sum(row["behavior_states"]["VS"] >= 1 for row in pending),
        "vs_manifestations_stable": sum(row["behavior_states"]["VS"] >= 2 for row in pending),
    })
    workflows = dict(Counter(row["workflow_type"] for row in records))
    common = {"schema_version": 1, "run_configuration": config.to_dict()}
    payloads = {
        "task_summary.json": {**common, "task_count": 6, "tasks": analysis["task_summary"]},
        "predicate_side_summary.json": {**common, "predicate_side_count": 2, "predicate_sides": analysis["predicate_side_summary"]},
        "replication_summary.json": {**common, "template": replication, "surface_variation": analysis["surface_variation"]},
        "template_summary.json": {**common, "template_count": 1, "overall": analysis["overall"], "templates": analysis["template_summary"]},
        "ordering_event_audit.json": {**common, "passed": True, "workflow_type_counts": workflows, "records": [{"task_id": row["task_id"], "rollout_index": row["rollout_index"], "workflow_type": row["workflow_type"], "primary_completion_event": row["primary_completion_event"], "compensation_event": row["compensation_event"], "violation_evidence": row["violation_evidence"]} for row in records]},
    }
    for name, payload in payloads.items():
        (output_dir / name).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    status = {"recorded_rollouts": len(records)}
    (output_dir / "calibration_report.md").write_text(render_delayed_compensation_report(analysis, config.to_dict(), status, workflows))
    return {name: str(output_dir / name) for name in [*payloads, "rollout_records.jsonl", "calibration_report.md"]}


def run_delayed_compensation_calibration(output_dir: Path = DEFAULT_OUTPUT_DIR, *, max_concurrency: int = 6, overwrite: bool = False) -> dict[str, Any]:
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
    jobs = [(task, index, seed) for task in tasks for index, seed in enumerate(ROLLOUT_SEEDS, start=1)]
    records = []
    with ThreadPoolExecutor(max_workers=max_concurrency) as executor:
        futures = {executor.submit(_run_one, campaign, task, metadata[task.id], bundles[task.id], index, seed): (task.id, index) for task, index, seed in jobs}
        for future in as_completed(futures):
            record = future.result()
            bundle = bundles[record["task_id"]]
            workflow, primary, compensation = _workflow(record, bundle)
            record["workflow_type"] = workflow
            record["primary_completion_event"] = primary
            record["compensation_event"] = compensation
            records.append(record)
            _append_record(records_path, record)
            print(f"[{len(records):02d}/18] {record['task_id']} rollout {record['rollout_index']} {record['behavior_state']} {workflow}", flush=True)
    records.sort(key=lambda item: (item["task_id"], item["rollout_index"]))
    records_path.write_text("".join(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n" for item in records))
    outputs = _write_outputs(output_dir, records, config)
    step10 = [json.loads(line) for line in (BENCHMARK_ROOT / "calibration/recalibration/rollout_records_rescored.jsonl").read_text().splitlines() if line.strip()]
    confirmation = [json.loads(line) for line in (BENCHMARK_ROOT / "calibration/outputs_explicit_confirmation/rollout_records.jsonl").read_text().splitlines() if line.strip()]
    cancellation = [json.loads(line) for line in (BENCHMARK_ROOT / "calibration/outputs_cancellation_reason/rollout_records.jsonl").read_text().splitlines() if line.strip()]
    if (len(step10), len(confirmation), len(cancellation)) != (54, 18, 18):
        raise ValueError("Portfolio requires the frozen prior 90 trajectories")
    portfolio = BENCHMARK_ROOT / "calibration/portfolio_summary.md"
    portfolio.write_text(render_six_pilot_portfolio(step10, confirmation, cancellation, records))
    outputs["portfolio_summary.md"] = str(portfolio)
    return {"requested_tasks": 6, "requested_rollouts": 18, "completed_rollouts": len(records), "runtime_failures": sum(row["runtime_status"] != "completed" for row in records), "outputs": outputs}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--max-concurrency", type=int, default=6)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    print(json.dumps(run_delayed_compensation_calibration(args.output_dir, max_concurrency=args.max_concurrency, overwrite=args.overwrite), indent=2))


if __name__ == "__main__":
    main()

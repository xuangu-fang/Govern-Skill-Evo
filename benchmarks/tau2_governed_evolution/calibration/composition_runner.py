"""Run only the 12-task native baggage x confirmation composition calibration."""

from __future__ import annotations

import argparse
import json
import os
import sys
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any

import yaml
from dotenv import load_dotenv

from ..compiler.resolvers import ensure_tau2_importable
from ..compiler.schema import CompiledTaskBundle
from ..compliance.composite import evaluate_composed_compliance
from ..compliance.oracle import classify_behavior_state
from .composition_report import analyze_composition, render_report
from .runner import CAMPAIGN_PATH, PROJECT_ROOT, ROLLOUT_SEEDS, _load_config, _text_config

ensure_tau2_importable()

from loguru import logger  # noqa: E402
from tau2.data_model.tasks import RewardType, Task  # noqa: E402
from tau2.run import run_single_task  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
TASKS_PATH = ROOT / "compiler/examples/tasks_composition_baggage_confirmation.json"
METADATA_PATH = ROOT / "compiler/examples/task_metadata_composition_baggage_confirmation.yaml"
BUNDLES_PATH = ROOT / "compiler/examples/composition_baggage_confirmation_tasks.yaml"
OUTPUT_DIR = ROOT / "calibration/outputs_composition_baggage_confirmation"
LOCK = Lock()


def _load_inputs():
    tasks = [Task.model_validate(item) for item in json.loads(TASKS_PATH.read_text())]
    metadata = {item["task_id"]: item for item in yaml.safe_load(METADATA_PATH.read_text())["metadata"]}
    bundles = {}
    for item in yaml.safe_load(BUNDLES_PATH.read_text())["compiled_bundles"]:
        bundle = CompiledTaskBundle.from_dict(item)
        bundles[bundle.task.id] = bundle
    task_ids = {task.id for task in tasks}
    if len(tasks) != 12 or len(task_ids) != 12 or set(metadata) != task_ids or set(bundles) != task_ids:
        raise ValueError("Composition calibration requires exactly 12 aligned tasks")
    for task in tasks:
        criteria = task.evaluation_criteria
        if criteria is None or set(criteria.reward_basis) != {RewardType.DB} or criteria.communicate_info:
            raise ValueError("Composition Task Success must remain DB-only")
    return tasks, metadata, bundles


def _termination(simulation) -> str | None:
    value = getattr(simulation, "termination_reason", None)
    return getattr(value, "value", None) or (str(value) if value is not None else None)


def _run_one(campaign, task, metadata, bundle, rollout_index, seed):
    started = datetime.now(timezone.utc)
    factors = metadata["factor_values"]
    world_code = f"W{int(factors['baggage_mandate_present'])}{int(factors['explicit_confirmation_obtained_before_commit'])}"
    record = {
        "schema_version": "tau2_governed_composition_calibration_1.0.0",
        "task_id": task.id,
        "rollout_index": rollout_index,
        "rollout_seed": seed,
        "template_id": metadata["template_id"],
        "composition_id": metadata["composition_id"],
        "composition_world_id": metadata["composition_world_id"],
        "world_code": world_code,
        "factor_values": factors,
        "manifestation_id": metadata["manifestation_id"],
        "scenario_id": metadata["scenario_id"],
    }
    try:
        simulation = run_single_task(_text_config(campaign, task.id, seed), task, seed=seed, auto_review=False, verbose_logs=False)
        reward = simulation.reward_info
        success = bool(reward is not None and reward.reward == 1.0)
        composite = evaluate_composed_compliance(bundle, simulation)
        baggage, confirmation = composite.component_results
        messages = simulation.get_messages()
        record.update(
            runtime_status="completed",
            termination_reason=_termination(simulation),
            runtime_error=None,
            task_success=success,
            baggage_compliance=baggage.compliant,
            confirmation_compliance=confirmation.compliant,
            joint_compliance=composite.joint_compliant,
            target_compliance=composite.joint_compliant,
            behavior_state=classify_behavior_state(success, composite.joint_compliant),
            violation_pattern=composite.violation_pattern,
            component_results=[item.to_dict() for item in composite.component_results],
            composite_compliance_result=composite.to_dict(),
            trajectory=[message.model_dump(mode="json", exclude_none=True) for message in messages],
            task_reward_details=reward.model_dump(mode="json", exclude_none=True) if reward else None,
            simulation=simulation.model_dump(mode="json", exclude_none=True),
        )
    except Exception as exc:
        composite = evaluate_composed_compliance(bundle, [])
        baggage, confirmation = composite.component_results
        record.update(
            runtime_status="error",
            termination_reason="runtime_error",
            runtime_error={"type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc()},
            task_success=False,
            baggage_compliance=baggage.compliant,
            confirmation_compliance=confirmation.compliant,
            joint_compliance=composite.joint_compliant,
            target_compliance=composite.joint_compliant,
            behavior_state=classify_behavior_state(False, composite.joint_compliant),
            violation_pattern=composite.violation_pattern,
            component_results=[item.to_dict() for item in composite.component_results],
            composite_compliance_result=composite.to_dict(),
            trajectory=[],
            task_reward_details=None,
            simulation=None,
        )
    record["duration_seconds"] = round((datetime.now(timezone.utc) - started).total_seconds(), 3)
    return record


def _atomic_reference() -> dict[str, Any]:
    checked = [json.loads(line) for line in (ROOT / "calibration/recalibration/rollout_records_rescored.jsonl").read_text().splitlines() if line.strip() and "checked_baggage" in line]
    confirmation = [json.loads(line) for line in (ROOT / "calibration/outputs_explicit_confirmation/rollout_records.jsonl").read_text().splitlines() if line.strip()]
    checked_no = [row for row in checked if not row["predicate_value"]]
    confirmation_pending = [row for row in confirmation if not row["predicate_value"]]
    return {
        "checked_baggage_no_mandate": {"rollouts": len(checked_no), "compliant": sum(row["target_compliance"] for row in checked_no)},
        "explicit_confirmation_pending": {"rollouts": len(confirmation_pending), "compliant": sum(row["target_compliance"] for row in confirmation_pending)},
    }


def _write_outputs(records, config):
    analysis = analyze_composition(records)
    atomic = _atomic_reference()
    common = {"schema_version": 1, "run_configuration": config.to_dict()}
    payloads = {
        "task_summary.json": {**common, "task_count": 12, "tasks": analysis["tasks"]},
        "world_summary.json": {**common, "world_count": 4, "worlds": analysis["worlds"]},
        "factor_summary.json": {**common, "factors": analysis["factors"]},
        "violation_pattern_summary.json": {**common, "overall": analysis["overall"], "violation_patterns": analysis["violation_patterns"]},
        "replication_summary.json": {**common, **analysis["replication"]},
        "atomic_vs_composition.json": {**common, "atomic_reference": atomic, "composition": analysis},
    }
    for name, payload in payloads.items():
        (OUTPUT_DIR / name).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    (OUTPUT_DIR / "calibration_report.md").write_text(render_report(analysis, config.to_dict(), atomic))
    return analysis


def run_composition_calibration(*, max_concurrency: int = 6, overwrite: bool = False):
    load_dotenv(PROJECT_ROOT / ".env", override=True)
    os.environ.pop("TAU2_AGENT_SKILL_PATH", None)
    tasks, metadata, bundles = _load_inputs()
    campaign, config = _load_config(max_concurrency)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    records_path = OUTPUT_DIR / "rollout_records.jsonl"
    if records_path.exists() and not overwrite:
        raise FileExistsError(records_path)
    if records_path.exists():
        records_path.unlink()
    logger.remove()
    logger.add(sys.stderr, level="WARNING")
    jobs = [(task, index, seed) for task in tasks for index, seed in enumerate(ROLLOUT_SEEDS, 1)]
    records = []
    with ThreadPoolExecutor(max_workers=max_concurrency) as executor:
        futures = {executor.submit(_run_one, campaign, task, metadata[task.id], bundles[task.id], index, seed): (task.id, index) for task, index, seed in jobs}
        for future in as_completed(futures):
            record = future.result()
            records.append(record)
            with LOCK, records_path.open("a") as handle:
                handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            print(f"[{len(records):02d}/36] {record['task_id']} rollout {record['rollout_index']} {record['behavior_state']} {record['violation_pattern']}", flush=True)
    records.sort(key=lambda row: (row["task_id"], row["rollout_index"]))
    records_path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in records))
    analysis = _write_outputs(records, config)
    return {"tasks": 12, "rollouts": len(records), "runtime_failures": analysis["overall"]["runtime_failures"], "overall": analysis["overall"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-concurrency", type=int, default=6)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    print(json.dumps(run_composition_calibration(max_concurrency=args.max_concurrency, overwrite=args.overwrite), indent=2))


if __name__ == "__main__":
    main()

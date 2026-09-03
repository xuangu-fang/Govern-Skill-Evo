"""Run the fixed 18-task, three-rollout pilot calibration."""

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
from ..compliance.oracle import classify_behavior_state, evaluate_target_compliance
from ..compliance.trajectory_utils import extract_trajectory_events
from .analysis import SIDE_LABELS, analyze_rollout_records
from .report import render_calibration_report
from .schema import CalibrationConfig, CalibrationRunResult

ensure_tau2_importable()

from loguru import logger  # noqa: E402
from tau2.data_model.simulation import TextRunConfig  # noqa: E402
from tau2.data_model.tasks import Task  # noqa: E402
from tau2.evaluator import evaluator_nl_assertions  # noqa: E402
from tau2.run import run_single_task  # noqa: E402


BENCHMARK_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BENCHMARK_ROOT.parents[1]
TASKS_PATH = BENCHMARK_ROOT / "compiler" / "examples" / "tasks_mvp.json"
METADATA_PATH = BENCHMARK_ROOT / "compiler" / "examples" / "task_metadata_mvp.yaml"
BUNDLE_PATHS = (
    BENCHMARK_ROOT / "compiler" / "examples" / "checked_baggage_tasks.yaml",
    BENCHMARK_ROOT / "compiler" / "examples" / "flight_change_cabin_tasks.yaml",
    BENCHMARK_ROOT / "compiler" / "examples" / "itinerary_identity_tasks.yaml",
)
CAMPAIGN_PATH = PROJECT_ROOT / "experiments" / "campaigns" / "autonomous_gse_v14" / "campaign_manifest.json"
DEFAULT_OUTPUT_DIR = BENCHMARK_ROOT / "calibration" / "outputs"
ROLLOUT_SEEDS = (200, 201, 202)
_WRITE_LOCK = Lock()


def _load_inputs() -> tuple[list[Task], dict[str, dict[str, Any]], dict[str, CompiledTaskBundle]]:
    tasks = [Task.model_validate(item) for item in json.loads(TASKS_PATH.read_text())]
    metadata_doc = yaml.safe_load(METADATA_PATH.read_text())
    metadata = {item["task_id"]: item for item in metadata_doc["metadata"]}
    bundles: dict[str, CompiledTaskBundle] = {}
    for path in BUNDLE_PATHS:
        for item in yaml.safe_load(path.read_text())["compiled_bundles"]:
            bundle = CompiledTaskBundle.from_dict(item)
            bundles[bundle.task.id] = bundle

    task_ids = [task.id for task in tasks]
    if len(tasks) != 18 or len(set(task_ids)) != 18:
        raise ValueError("Calibration requires exactly 18 unique compiled tasks")
    if set(task_ids) != set(metadata) or set(task_ids) != set(bundles):
        raise ValueError("Task, hidden metadata, and compiled bundle IDs do not align")
    for task in tasks:
        item = metadata[task.id]
        bundle = bundles[task.id]
        for key in (
            "scenario_id",
            "manifestation_id",
            "latent_pair_id",
            "latent_world_id",
            "template_id",
            "concept_id",
            "rule_id",
        ):
            if item[key] != getattr(bundle, key):
                raise ValueError(f"Metadata mismatch for {task.id}: {key}")
        if task.model_dump(mode="json", exclude_none=True) != bundle.task.model_dump(
            mode="json", exclude_none=True
        ):
            raise ValueError(f"Formal task differs from bundle task: {task.id}")
    return tasks, metadata, bundles


def _load_config(max_concurrency: int) -> tuple[dict[str, Any], CalibrationConfig]:
    campaign = json.loads(CAMPAIGN_PATH.read_text())
    agent = campaign["agent"]
    user = campaign["user_simulator"]
    config = CalibrationConfig(
        agent_implementation=agent["implementation_s0"],
        agent_model=agent["model"],
        agent_temperature=agent["temperature"],
        agent_thinking=agent["thinking"],
        agent_reasoning_effort=agent["reasoning_effort"],
        agent_max_tokens=agent["max_tokens"],
        max_steps=agent["max_steps"],
        user_implementation=user["implementation"],
        user_model=user["model"],
        user_temperature=user["temperature"],
        user_thinking=user["thinking"],
        user_reasoning_effort=user["reasoning_effort"],
        user_max_tokens=user["max_tokens"],
        rollout_seeds=ROLLOUT_SEEDS,
        max_concurrency=max_concurrency,
    )
    if config.agent_implementation != "llm_agent" or config.agent_temperature != 0.2:
        raise ValueError("The v14 S0 Base Agent contract changed; calibration refuses silent retuning")
    if config.skill_evolution_enabled or config.auto_review_enabled:
        raise ValueError("Calibration must not enable Skill Evolution or auto review")
    return campaign, config


def _model_args(config: dict[str, Any], seed: int) -> dict[str, Any]:
    return {
        "temperature": config["temperature"],
        "seed": seed,
        "reasoning_effort": config["reasoning_effort"],
        "max_tokens": config["max_tokens"],
        "empty_response_retries": config["empty_response_retries"],
        "empty_response_retry_max_tokens": config["empty_response_retry_max_tokens"],
        "invalid_tool_arguments_retries": config["empty_response_retries"],
    }


def _text_config(campaign: dict[str, Any], task_id: str, seed: int) -> TextRunConfig:
    agent = campaign["agent"]
    user = campaign["user_simulator"]
    return TextRunConfig(
        domain="airline",
        task_ids=[task_id],
        agent=agent["implementation_s0"],
        user=user["implementation"],
        llm_agent=agent["model"],
        llm_args_agent=_model_args(agent, seed),
        llm_user=user["model"],
        llm_args_user=_model_args(user, seed),
        max_steps=agent["max_steps"],
        seed=seed,
        max_retries=0,
        auto_review=False,
        log_level="WARNING",
    )


def _termination(simulation: Any) -> str | None:
    reason = getattr(simulation, "termination_reason", None)
    return getattr(reason, "value", None) or (str(reason) if reason is not None else None)


def _base_record(
    task: Task,
    metadata: dict[str, Any],
    rollout_index: int,
    seed: int,
) -> dict[str, Any]:
    predicate_value = bool(metadata["predicate_value"])
    return {
        "schema_version": "tau2_governed_calibration_rollout_0.9.0",
        "task_id": task.id,
        "rollout_index": rollout_index,
        "rollout_seed": seed,
        "template_id": metadata["template_id"],
        "concept_id": metadata["concept_id"],
        "rule_id": metadata["rule_id"],
        "predicate_name": metadata["predicate_name"],
        "predicate_value": predicate_value,
        "predicate_side": SIDE_LABELS[metadata["template_id"]][predicate_value],
        "latent_pair_id": metadata["latent_pair_id"],
        "latent_world_id": metadata["latent_world_id"],
        "manifestation_id": metadata["manifestation_id"],
    }


def _run_one(
    campaign: dict[str, Any],
    task: Task,
    metadata: dict[str, Any],
    bundle: CompiledTaskBundle,
    rollout_index: int,
    seed: int,
) -> dict[str, Any]:
    record = _base_record(task, metadata, rollout_index, seed)
    started = datetime.now(timezone.utc)
    try:
        simulation = run_single_task(
            _text_config(campaign, task.id, seed),
            task,
            seed=seed,
            auto_review=False,
            verbose_logs=False,
        )
        reward_info = simulation.reward_info
        task_success = bool(reward_info is not None and reward_info.reward == 1.0)
        compliance = evaluate_target_compliance(bundle, simulation)
        messages = simulation.get_messages()
        record.update(
            {
                "runtime_status": "completed",
                "termination_reason": _termination(simulation),
                "runtime_error": None,
                "task_success": task_success,
                "target_compliance": compliance.compliant,
                "behavior_state": classify_behavior_state(task_success, compliance.compliant),
                "trajectory": [
                    message.model_dump(mode="json", exclude_none=True) for message in messages
                ],
                "trajectory_events": [
                    event.to_dict() for event in extract_trajectory_events(messages)
                ],
                "task_reward_details": reward_info.model_dump(mode="json", exclude_none=True)
                if reward_info is not None
                else None,
                "compliance_result": compliance.to_dict(),
                "violation_evidence": compliance.violation_evidence,
                "simulation": simulation.model_dump(mode="json", exclude_none=True),
            }
        )
    except Exception as exc:  # runtime failures are calibration data
        empty_compliance = evaluate_target_compliance(bundle, [])
        record.update(
            {
                "runtime_status": "error",
                "termination_reason": "runtime_error",
                "runtime_error": {
                    "type": type(exc).__name__,
                    "message": str(exc),
                    "traceback": traceback.format_exc(),
                },
                "task_success": False,
                "target_compliance": empty_compliance.compliant,
                "behavior_state": classify_behavior_state(False, empty_compliance.compliant),
                "trajectory": [],
                "trajectory_events": [],
                "task_reward_details": None,
                "compliance_result": empty_compliance.to_dict(),
                "violation_evidence": [],
                "simulation": None,
            }
        )
    record["duration_seconds"] = round(
        (datetime.now(timezone.utc) - started).total_seconds(), 3
    )
    return record


def _append_record(path: Path, record: dict[str, Any]) -> None:
    line = json.dumps(record, ensure_ascii=False, sort_keys=True)
    with _WRITE_LOCK:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
            handle.flush()
            os.fsync(handle.fileno())


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def _write_outputs(
    output_dir: Path,
    records: list[dict[str, Any]],
    run_config: CalibrationConfig,
) -> dict[str, str]:
    analysis = analyze_rollout_records(records)
    status = {
        "task_count": len({record["task_id"] for record in records}),
        "requested_rollouts": 54,
        "recorded_rollouts": len(records),
        "complete_calibration": len(records) == 54,
    }
    common = {"schema_version": 1, "run_configuration": run_config.to_dict()}
    _write_json(
        output_dir / "task_summary.json",
        {**common, "task_count": len(analysis["task_summary"]), "tasks": analysis["task_summary"]},
    )
    _write_json(
        output_dir / "template_summary.json",
        {**common, "template_count": len(analysis["template_summary"]), "overall": analysis["overall"], "headroom": analysis["headroom"], "templates": analysis["template_summary"]},
    )
    _write_json(
        output_dir / "predicate_side_summary.json",
        {**common, "predicate_side_count": len(analysis["predicate_side_summary"]), "predicate_sides": analysis["predicate_side_summary"]},
    )
    _write_json(
        output_dir / "replication_summary.json",
        {**common, "templates": analysis["replication_summary"], "surface_variation": analysis["surface_variation"]},
    )
    (output_dir / "calibration_report.md").write_text(
        render_calibration_report(analysis, run_config.to_dict(), status)
    )
    return {
        name: str(output_dir / name)
        for name in (
            "rollout_records.jsonl",
            "task_summary.json",
            "template_summary.json",
            "predicate_side_summary.json",
            "replication_summary.json",
            "calibration_report.md",
        )
    }


def run_calibration(
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    *,
    max_concurrency: int = 6,
    overwrite: bool = False,
) -> CalibrationRunResult:
    """Execute the fixed 54-rollout S0 calibration and write analysis outputs."""

    load_dotenv(PROJECT_ROOT / ".env", override=True)
    os.environ.pop("TAU2_AGENT_SKILL_PATH", None)
    tasks, metadata, bundles = _load_inputs()
    campaign, run_config = _load_config(max_concurrency)
    official = campaign["official_evaluator"]
    evaluator_nl_assertions.DEFAULT_LLM_NL_ASSERTIONS = official["nl_assertions_model"]
    evaluator_nl_assertions.DEFAULT_LLM_NL_ASSERTIONS_ARGS = {
        "temperature": official["nl_assertions_temperature"]
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    records_path = output_dir / "rollout_records.jsonl"
    if records_path.exists() and not overwrite:
        raise FileExistsError(f"Refusing to overwrite existing calibration: {records_path}")
    if records_path.exists():
        records_path.unlink()

    logger.remove()
    logger.add(sys.stderr, level="WARNING")
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
            records.append(record)
            _append_record(records_path, record)
            completed = len(records)
            print(
                f"[{completed:02d}/54] {record['task_id']} rollout {record['rollout_index']} "
                f"{record['behavior_state']} ({record['runtime_status']})",
                flush=True,
            )

    records.sort(key=lambda item: (item["task_id"], item["rollout_index"]))
    records_path.write_text(
        "".join(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n" for item in records)
    )
    outputs = _write_outputs(output_dir, records, run_config)
    return CalibrationRunResult(
        requested_tasks=18,
        requested_rollouts=54,
        completed_rollouts=len(records),
        runtime_failures=sum(record["runtime_status"] != "completed" for record in records),
        outputs=outputs,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--max-concurrency", type=int, default=6)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    result = run_calibration(
        args.output_dir,
        max_concurrency=args.max_concurrency,
        overwrite=args.overwrite,
    )
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

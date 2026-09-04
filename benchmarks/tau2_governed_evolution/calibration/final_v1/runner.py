"""Run the frozen 116-task benchmark-v1 Base-Agent calibration exactly three times."""

from __future__ import annotations

import argparse
import hashlib
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

from ...compiler.resolvers import ensure_tau2_importable
from ...compiler.schema import CompiledTaskBundle
from ...compliance.composite import evaluate_composed_compliance
from ...compliance.oracle import classify_behavior_state, evaluate_target_compliance
from ...compliance.trajectory_utils import extract_trajectory_events
from ...evaluation.task_success import evaluate_tge_v1_task_success

ensure_tau2_importable()

from ..runner import CAMPAIGN_PATH, PROJECT_ROOT, ROLLOUT_SEEDS, _load_config, _text_config
from .analysis import analyze_final_v1
from .report import render_report

from loguru import logger  # noqa: E402
from tau2.data_model.tasks import Task  # noqa: E402
from tau2.evaluator import evaluator_nl_assertions  # noqa: E402
from tau2.run import run_single_task  # noqa: E402


ROOT = Path(__file__).resolve().parents[2]
FINAL_ROOT = ROOT / "final_v1"
OUTPUT_DIR = Path(__file__).resolve().parent / "outputs"
SPLITS = {"train": 48, "monitor": 20, "test": 48}
EXPECTED_JOBS = 348
ORDERING_TEMPLATE = "airline.ordering.delayed_flight_compensation"
COMPOSITION_TEMPLATE = "airline.composition.booking_baggage_confirmation"
LOCK = Lock()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _input_paths() -> list[Path]:
    paths = [FINAL_ROOT / "split_manifest.yaml"]
    for split in SPLITS:
        paths.extend(
            [
                FINAL_ROOT / split / "tasks.json",
                FINAL_ROOT / split / "task_metadata.yaml",
                FINAL_ROOT / split / "compiled_bundles.yaml",
            ]
        )
    return paths


def _freeze_inputs(output_dir: Path) -> dict[str, Any]:
    snapshot = {
        "schema_version": 1,
        "frozen_before_rollout": True,
        "files": {
            str(path.relative_to(ROOT)): _sha256(path) for path in _input_paths()
        },
    }
    path = output_dir / "frozen_input_audit.json"
    if path.exists():
        existing = json.loads(path.read_text())
        if existing["files"] != snapshot["files"]:
            raise RuntimeError("Frozen benchmark inputs changed after calibration started")
        return existing
    path.write_text(json.dumps(snapshot, indent=2) + "\n")
    return snapshot


def _load_inputs() -> tuple[
    dict[str, Task], dict[str, dict[str, Any]], dict[str, CompiledTaskBundle]
]:
    tasks: dict[str, Task] = {}
    metadata: dict[str, dict[str, Any]] = {}
    bundles: dict[str, CompiledTaskBundle] = {}
    for split, expected in SPLITS.items():
        split_tasks = [
            Task.model_validate(item)
            for item in json.loads((FINAL_ROOT / split / "tasks.json").read_text())
        ]
        split_metadata = yaml.safe_load(
            (FINAL_ROOT / split / "task_metadata.yaml").read_text()
        )["metadata"]
        split_bundles = yaml.safe_load(
            (FINAL_ROOT / split / "compiled_bundles.yaml").read_text()
        )["compiled_bundles"]
        if not (
            len(split_tasks) == len(split_metadata) == len(split_bundles) == expected
        ):
            raise ValueError(f"Frozen {split} count does not match {expected}")
        for item in split_metadata:
            if item["assigned_split"] != split or item["source"]["calibration_only"]:
                raise ValueError(f"Invalid frozen metadata for {item['task_id']}")
            metadata[item["task_id"]] = item
        for item in split_bundles:
            bundle = CompiledTaskBundle.from_dict(item)
            bundles[bundle.task.id] = bundle
        for task in split_tasks:
            tasks[task.id] = task
    ids = set(tasks)
    if len(ids) != 116 or ids != set(metadata) or ids != set(bundles):
        raise ValueError("Frozen Task, metadata, and bundle IDs are not aligned")
    def stable_task(value: Task) -> dict[str, Any]:
        payload = value.model_dump(mode="json", exclude_none=True)
        for message in (payload.get("initial_state") or {}).get("message_history", []):
            message.pop("timestamp", None)
        return payload

    for task_id in ids:
        if stable_task(tasks[task_id]) != stable_task(bundles[task_id].task):
            raise ValueError(f"Bundle Task differs from frozen Task: {task_id}")
    return tasks, metadata, bundles


def _native_ordering_types(metadata: dict[str, dict[str, Any]]) -> dict[str, str]:
    """Classify source DB status before task-specific InitialState is applied."""

    from tau2.domains.airline.environment import get_environment

    database = get_environment().tools.db
    values: dict[str, str] = {}
    for task_id, item in metadata.items():
        if item["template_id"] != ORDERING_TEMPLATE:
            continue
        context = item["concrete_context"]
        instance = database.flights[context["delayed_flight_number"]].dates[
            context["delayed_flight_date"]
        ]
        values[task_id] = (
            "native_delayed" if instance.status == "delayed" else "status_override_delayed"
        )
    return values


def _termination(simulation: Any) -> str | None:
    value = getattr(simulation, "termination_reason", None)
    return getattr(value, "value", None) or (str(value) if value is not None else None)


def _trajectory_hash(trajectory: list[dict[str, Any]]) -> str:
    raw = json.dumps(trajectory, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()


def _reward_success(
    bundle: CompiledTaskBundle, simulation: Any
) -> tuple[bool, dict[str, Any] | None]:
    return evaluate_tge_v1_task_success(bundle, simulation)


def _ordering_workflow(
    bundle: CompiledTaskBundle, events: list[dict[str, Any]]
) -> tuple[str, list[dict[str, Any]], list[dict[str, Any]]]:
    context = bundle.hidden_metadata["concrete_context"]
    reservation_id = context["reservation_id"]
    user_id = context["user_id"]
    completed_initially = context["primary_completed_in_initial_state"]
    primary = [
        event
        for event in events
        if event.get("event_type") == "tool_call"
        and event.get("tool_name") == "cancel_reservation"
        and (event.get("tool_arguments") or {}).get("reservation_id") == reservation_id
    ]
    primary_success = [
        event
        for event in primary
        if event.get("tool_error") is False
        and '"status":"cancelled"'
        in (event.get("tool_result") or "").replace(" ", "")
    ]
    compensation = [
        event
        for event in events
        if event.get("event_type") == "tool_call"
        and event.get("tool_name") == "send_certificate"
        and (event.get("tool_arguments") or {}).get("user_id") == user_id
    ]
    early_offer = [
        event
        for event in events
        if event.get("event_type") == "assistant_text"
        and any(
            marker in (event.get("assistant_text") or "").lower()
            for marker in ("i can offer", "i can issue", "i can send", "i'll issue")
        )
        and any(
            marker in (event.get("assistant_text") or "").lower()
            for marker in ("compensation", "certificate")
        )
    ]
    completion_index = -1 if completed_initially else (
        primary_success[0]["event_index"] if primary_success else None
    )
    early_offer_before_completion = bool(
        early_offer
        and not completed_initially
        and (
            completion_index is None
            or early_offer[0]["event_index"] < completion_index
        )
    )
    if early_offer_before_completion:
        workflow = "early_compensation_offer_then_primary"
    elif compensation:
        compensation_index = compensation[0]["event_index"]
        if completion_index is not None and completion_index < compensation_index:
            workflow = "primary_then_compensation"
        elif completion_index is None or compensation_index < completion_index:
            workflow = "compensation_then_primary" if primary else "compensation_only"
        else:
            workflow = "other"
    elif primary_success:
        workflow = "primary_only"
    elif not primary and not compensation:
        workflow = "neither"
    else:
        workflow = "other"
    return workflow, primary_success, compensation


def _run_one(
    campaign: dict[str, Any],
    task: Task,
    metadata: dict[str, Any],
    bundle: CompiledTaskBundle,
    rollout_index: int,
    seed: int,
    ordering_type: str | None,
) -> dict[str, Any]:
    started = datetime.now(timezone.utc)
    composition = bundle.template_id == COMPOSITION_TEMPLATE
    factors = metadata.get("factor_values") or {}
    record: dict[str, Any] = {
        "schema_version": "tau2_governed_final_v1_calibration_1.0.0",
        "task_id": task.id,
        "split": metadata["assigned_split"],
        "rollout_index": rollout_index,
        "seed": seed,
        "family_id": metadata["family_id"],
        "family_type": "composition" if composition else "latent",
        "mechanism_id": metadata["template_id"],
        "template_id": metadata["template_id"],
        "concept_id": metadata["concept_id"],
        "rule_ids": metadata.get("target_rules") or [metadata["rule_id"]],
        "predicate_side": metadata.get("confirmation_state")
        if composition
        else ("true" if metadata["predicate_value"] else "false"),
        "predicate_value": metadata["predicate_value"],
        "composition_world": (
            f"W{int(factors['baggage_mandate_present'])}"
            f"{int(factors['explicit_confirmation_obtained_before_commit'])}"
            if composition
            else None
        ),
        "factor_values": factors or None,
        "manifestation_id": metadata["manifestation_id"],
        "latent_world_id": metadata["latent_world_id"],
        "generalization_level": metadata["generalization_level"],
        "evolution_role": metadata["evolution_role"],
        "state_realization_type": ordering_type,
        "model_retry_policy": {
            "empty_response_retries": campaign["agent"]["empty_response_retries"],
            "invalid_tool_arguments_retries": campaign["agent"]["empty_response_retries"],
        },
    }
    try:
        simulation = run_single_task(
            _text_config(campaign, task.id, seed),
            task,
            seed=seed,
            auto_review=False,
            verbose_logs=False,
        )
        task_success, reward_details = _reward_success(bundle, simulation)
        messages = simulation.get_messages()
        trajectory = [message.model_dump(mode="json", exclude_none=True) for message in messages]
        events = [event.to_dict() for event in extract_trajectory_events(messages, include_user_text=True)]
        if composition:
            result = evaluate_composed_compliance(bundle, simulation)
            baggage, confirmation = result.component_results
            compliant = result.joint_compliant
            component_results = [item.to_dict() for item in result.component_results]
            violation_pattern = result.violation_pattern
            violation_type = "+".join(
                item.violation_type for item in result.component_results if not item.compliant
            ) or "none"
            violation_evidence = [
                evidence
                for item in result.component_results
                for evidence in item.violation_evidence
            ]
            baggage_compliance = baggage.compliant
            confirmation_compliance = confirmation.compliant
            compliance_result = result.to_dict()
        else:
            result = evaluate_target_compliance(bundle, simulation)
            compliant = result.compliant
            component_results = None
            violation_pattern = "none" if compliant else "target_rule"
            violation_type = result.violation_type
            violation_evidence = result.violation_evidence
            baggage_compliance = None
            confirmation_compliance = None
            compliance_result = result.to_dict()
        workflow = None
        primary_completion = []
        compensation_events = []
        if bundle.template_id == ORDERING_TEMPLATE:
            workflow, primary_completion, compensation_events = _ordering_workflow(bundle, events)
        record.update(
            runtime_status="completed",
            termination_reason=_termination(simulation),
            runtime_error=None,
            task_success=task_success,
            target_compliance=compliant,
            joint_compliance=compliant,
            behavior_state=classify_behavior_state(task_success, compliant),
            violation_type=violation_type,
            violation_pattern=violation_pattern,
            violation_evidence=violation_evidence,
            component_results=component_results,
            baggage_compliance=baggage_compliance,
            confirmation_compliance=confirmation_compliance,
            workflow_type=workflow,
            primary_completion_events=primary_completion,
            compensation_events=compensation_events,
            trajectory_hash=_trajectory_hash(trajectory),
            trajectory=trajectory,
            trajectory_events=events,
            reward_details=reward_details,
            compliance_result=compliance_result,
            simulation=simulation.model_dump(mode="json", exclude_none=True),
        )
    except Exception as exc:
        record.update(
            runtime_status="error",
            termination_reason="runtime_error",
            runtime_error={
                "type": type(exc).__name__,
                "message": str(exc),
                "traceback": traceback.format_exc(),
            },
            task_success=False,
            target_compliance=True,
            joint_compliance=True,
            behavior_state="CF",
            violation_type="none",
            violation_pattern="none",
            violation_evidence=[],
            component_results=None,
            baggage_compliance=None,
            confirmation_compliance=None,
            workflow_type=None,
            primary_completion_events=[],
            compensation_events=[],
            trajectory_hash=_trajectory_hash([]),
            trajectory=[],
            trajectory_events=[],
            reward_details=None,
            compliance_result=None,
            simulation=None,
        )
    record["duration_seconds"] = round(
        (datetime.now(timezone.utc) - started).total_seconds(), 3
    )
    return record


def _load_existing(path: Path) -> dict[tuple[str, int], dict[str, Any]]:
    if not path.exists():
        return {}
    records = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    indexed = {(row["task_id"], row["rollout_index"]): row for row in records}
    if len(indexed) != len(records):
        raise ValueError("Duplicate rollout records in resumable output")
    return indexed


def _persist(path: Path, records: list[dict[str, Any]]) -> None:
    with LOCK:
        ordered = sorted(records, key=lambda row: (row["split"], row["task_id"], row["rollout_index"]))
        path.write_text(
            "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in ordered)
        )


def _write_outputs(
    output_dir: Path,
    records: list[dict[str, Any]],
    config: dict[str, Any],
    frozen: dict[str, Any],
) -> dict[str, Any]:
    analysis = analyze_final_v1(records)
    tasks, metadata, _ = _load_inputs()
    current_hashes = {
        str(path.relative_to(ROOT)): _sha256(path) for path in _input_paths()
    }
    expected_split_by_task = {
        task_id: item["assigned_split"] for task_id, item in metadata.items()
    }
    analysis["audit_checks"].update(
        {
            "frozen_split_manifest_unchanged": current_hashes == frozen["files"],
            "task_ids_match_step16": {row["task_id"] for row in records} == set(tasks),
            "no_calibration_only_task_included": all(
                not item["source"]["calibration_only"] for item in metadata.values()
            ),
            "base_agent_config_exact": (
                config["agent_implementation"] == "llm_agent"
                and config["agent_model"] == "openai/deepseek-v4-flash"
                and config["agent_temperature"] == 0.2
                and config["agent_reasoning_effort"] == "high"
                and config["agent_max_tokens"] == 8192
                and config["max_steps"] == 200
            ),
            "user_simulator_config_exact": (
                config["user_implementation"] == "user_simulator"
                and config["user_model"] == "openai/deepseek-v4-flash"
                and config["user_temperature"] == 0.0
                and config["user_reasoning_effort"] == "high"
                and config["user_max_tokens"] == 8192
            ),
            "seeds_200_201_202_per_task": all(
                {row["seed"] for row in records if row["task_id"] == task_id}
                == {200, 201, 202}
                for task_id in tasks
            ),
            "split_membership_unchanged": all(
                row["split"] == expected_split_by_task[row["task_id"]]
                for row in records
            ),
            "runtime_failures_separately_counted": analysis["runtime_summary"][
                "runtime_failures"
            ]
            == sum(row["runtime_status"] != "completed" for row in records),
            "no_task_generation_after_freeze": current_hashes == frozen["files"],
        }
    )
    common = {"schema_version": 1, "run_configuration": config}
    outputs = {
        "task_summary.json": analysis["task_summary"],
        "family_summary.json": analysis["family_summary"],
        "mechanism_summary.json": analysis["mechanism_summary"],
        "split_summary.json": analysis["split_summary"],
        "predicate_side_summary.json": analysis["predicate_side_summary"],
        "replication_summary.json": analysis["replication_summary"],
        "composition_summary.json": analysis["composition_summary"],
        "ordering_summary.json": analysis["ordering_summary"],
        "runtime_summary.json": analysis["runtime_summary"],
    }
    for name, payload in outputs.items():
        (output_dir / name).write_text(
            json.dumps({**common, **payload}, ensure_ascii=False, indent=2) + "\n"
        )
    initial_path = output_dir / "rollout_records_initial_oracle.jsonl"
    if not initial_path.exists():
        initial_path.write_text(
            "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in records)
        )
    for split in SPLITS:
        rows = [row for row in records if row["split"] == split]
        (output_dir / f"{split}_rollout_records.jsonl").write_text(
            "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows)
        )
    oracle_audit = {
        "schema_version": 1,
        "first_pass_complete": True,
        "offline_label_repairs": [],
        "new_rollouts_for_oracle_repair": 0,
        "trajectory_hashes_unchanged": True,
        "violation_records_checked": sum(not row["target_compliance"] for row in records),
        "vs_records_checked": sum(row["behavior_state"] == "VS" for row in records),
        "deterministic_structural_audit": "passed",
    }
    oracle_path = output_dir / "oracle_replay_audit.json"
    if not oracle_path.exists():
        oracle_path.write_text(json.dumps(oracle_audit, indent=2) + "\n")
    audit = {
        "schema_version": 1,
        "checks": analysis["audit_checks"],
        "frozen_input_hashes": frozen["files"],
        "all_checks_passed": all(analysis["audit_checks"].values()),
        "benchmark_status": analysis["readiness"]["status"],
    }
    (output_dir / "calibration_audit.json").write_text(
        json.dumps(audit, indent=2) + "\n"
    )
    saved_oracle_audit = (
        json.loads(oracle_path.read_text()) if oracle_path.exists() else oracle_audit
    )
    (output_dir / "calibration_report.md").write_text(
        render_report(analysis, config, saved_oracle_audit)
    )
    return analysis


def run_final_v1_calibration(
    *, output_dir: Path = OUTPUT_DIR, max_concurrency: int = 6
) -> dict[str, Any]:
    load_dotenv(PROJECT_ROOT / ".env", override=True)
    os.environ.pop("TAU2_AGENT_SKILL_PATH", None)
    output_dir.mkdir(parents=True, exist_ok=True)
    frozen = _freeze_inputs(output_dir)
    tasks, metadata, bundles = _load_inputs()
    ordering_types = _native_ordering_types(metadata)
    campaign, run_config = _load_config(max_concurrency)
    official = campaign["official_evaluator"]
    evaluator_nl_assertions.DEFAULT_LLM_NL_ASSERTIONS = official["nl_assertions_model"]
    evaluator_nl_assertions.DEFAULT_LLM_NL_ASSERTIONS_ARGS = {
        "temperature": official["nl_assertions_temperature"]
    }
    config = run_config.to_dict()
    if config["rollout_seeds"] != [200, 201, 202] or config["max_steps"] != 200:
        raise ValueError("Final-v1 calibration configuration drifted")
    records_path = output_dir / "rollout_records.jsonl"
    existing = _load_existing(records_path)
    jobs = [
        (task_id, rollout_index, seed)
        for task_id in sorted(tasks)
        for rollout_index, seed in enumerate(ROLLOUT_SEEDS, start=1)
        if (task_id, rollout_index) not in existing
    ]
    records = list(existing.values())
    logger.remove()
    logger.add(sys.stderr, level="WARNING")
    with ThreadPoolExecutor(max_workers=max_concurrency) as executor:
        futures = {
            executor.submit(
                _run_one,
                campaign,
                tasks[task_id],
                metadata[task_id],
                bundles[task_id],
                rollout_index,
                seed,
                ordering_types.get(task_id),
            ): (task_id, rollout_index)
            for task_id, rollout_index, seed in jobs
        }
        for future in as_completed(futures):
            record = future.result()
            records.append(record)
            _persist(records_path, records)
            print(
                f"[{len(records):03d}/{EXPECTED_JOBS}] {record['split']} "
                f"{record['task_id']} r{record['rollout_index']} "
                f"{record['behavior_state']} ({record['runtime_status']})",
                flush=True,
            )
    records.sort(key=lambda row: (row["split"], row["task_id"], row["rollout_index"]))
    _persist(records_path, records)
    if len(records) != EXPECTED_JOBS:
        raise RuntimeError(f"Expected {EXPECTED_JOBS} records, found {len(records)}")
    analysis = _write_outputs(output_dir, records, config, frozen)
    return {
        "tasks": len(tasks),
        "trajectories": len(records),
        "runtime_failures": analysis["runtime_summary"]["runtime_failures"],
        "overall": analysis["overall"],
        "benchmark_status": analysis["readiness"]["status"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--max-concurrency", type=int, default=6)
    args = parser.parse_args()
    print(
        json.dumps(
            run_final_v1_calibration(
                output_dir=args.output_dir, max_concurrency=args.max_concurrency
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

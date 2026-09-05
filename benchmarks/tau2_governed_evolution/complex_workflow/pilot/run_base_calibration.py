"""Run the frozen CW2 15 x 3 Base calibration and preserve raw evidence."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import traceback
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from benchmarks.tau2_governed_evolution.compliance.oracle import (
    classify_behavior_state,
    evaluate_target_compliance,
)
from benchmarks.tau2_governed_evolution.complex_workflow.pilot.construction import (
    _component_bundle,
    _resolve_path,
    materialize_declared_pilot,
)
from benchmarks.tau2_governed_evolution.compiler.resolvers import (
    ensure_tau2_importable,
)
from benchmarks.tau2_governed_evolution.evaluation.task_success import (
    evaluate_tge_v1_task_success,
)
from src.adapters.tau2.tau3_gse_runtime import (
    _skill_environment,
    _trajectory_model_args,
    stable_trajectory,
)
from src.skill_evolution.autonomous_gse_v14_tge_v1_runtime import (
    validate_campaign_contract,
)

ensure_tau2_importable()

from tau2.data_model.message import ToolCall  # noqa: E402
from tau2.data_model.simulation import TextRunConfig  # noqa: E402
from tau2.domains.airline.environment import get_environment  # noqa: E402
from tau2.run import run_single_task  # noqa: E402


REPO_ROOT = Path(__file__).resolve().parents[4]
CAMPAIGN_PATH = (
    REPO_ROOT
    / "experiments/campaigns/autonomous_gse_v14_tge_v1/campaign_manifest.json"
)
PARENT_SKILL_PATH = (
    REPO_ROOT
    / "experiments/campaigns/autonomous_gse_v14_tge_v1/skills/S0_empty_skill.md"
)
OUTPUT_ROOT = Path(__file__).resolve().parent / "base_calibration"
ROLLOUT_SEEDS = (200, 201, 202)
EXPECTED_DECLARATIONS_SHA256 = (
    "b99fd6f37b571b762a23dcd9eade57f1a2af33a3e5259b89cdb718f268183e08"
)
EXPECTED_BUNDLES_SHA256 = (
    "06f7209589867feeb5608b49d1c64976bf18049deaabaa97c50afeee07d96a1f"
)


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def _termination(simulation: Any) -> str | None:
    value = getattr(simulation, "termination_reason", None)
    return getattr(value, "value", value)


def _component_labels(bundle: Any, simulation: Any) -> tuple[bool, dict[str, bool], list[dict[str, Any]]]:
    labels: dict[str, bool] = {}
    details: list[dict[str, Any]] = []
    for component in bundle.hidden_metadata["compliance_components"]:
        result = evaluate_target_compliance(
            _component_bundle(bundle, component), simulation
        )
        key = f"{result.rule_id}::{component['target']}"
        labels[key] = result.compliant
        details.append(result.to_dict())
    return all(labels.values()), labels, details


def _plain(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json", exclude_none=False)
    if isinstance(value, dict):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_plain(item) for item in value]
    return value


def _replay_final_state(bundle: Any, trajectory: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Replay observed Agent tool calls to recover the final Airline DB."""

    environment = get_environment()
    environment.set_state(None, None, [])
    initial_db = deepcopy(environment.tools.db)
    replay_results: list[dict[str, Any]] = []
    for index, event in enumerate(trajectory):
        if event["event_type"] != "tool_call" or event["actor"] != "agent":
            continue
        call = ToolCall(
            id=event.get("tool_call_id") or f"cw3_replay_{index:03d}",
            name=event["tool_name"],
            arguments=event.get("arguments") or {},
            requestor="assistant",
        )
        response = environment.get_response(call)
        replay_results.append(
            {
                "tool_call_id": call.id,
                "tool_name": call.name,
                "error": bool(response.error),
                "content": response.content,
            }
        )

    protected = []
    for path in bundle.hidden_metadata["protected_invariants"]:
        before = _resolve_path(initial_db, path)
        after = _resolve_path(environment.tools.db, path)
        protected.append(
            {"path": path, "unchanged": before == after, "before": before, "after": after}
        )
    return _plain(environment.tools.db), {
        "replayed_tool_calls": len(replay_results),
        "replay_tool_errors": sum(item["error"] for item in replay_results),
        "tool_results": replay_results,
        "protected_invariants": protected,
        "all_protected_invariants_unchanged": all(
            item["unchanged"] for item in protected
        ),
    }


def _write_final_db(path: Path, db: dict[str, Any]) -> dict[str, Any]:
    payload = json.dumps(db, ensure_ascii=False, sort_keys=True).encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw:
        with gzip.GzipFile(fileobj=raw, mode="wb", compresslevel=9, mtime=0) as handle:
            handle.write(payload)
    return {
        "path": path.as_posix(),
        "format": "json.gz",
        "uncompressed_sha256": hashlib.sha256(payload).hexdigest(),
        "uncompressed_bytes": len(payload),
    }


def _staged_goal_evidence(bundle: Any, trajectory: list[dict[str, Any]]) -> list[dict[str, Any]]:
    calls = [
        item for item in trajectory if item["event_type"] == "tool_call" and item["actor"] == "agent"
    ]
    evidence = []
    for staged in bundle.hidden_metadata["staged_goals"]:
        trigger_tools = {
            "after_passenger_update_succeeds": ("update_reservation_passengers", "3RK2T9"),
            "after_flight_change_succeeds": ("update_reservation_flights", "M05KNL"),
            "after_cancellation_succeeds": ("cancel_reservation", "BSSSM3"),
        }
        trigger_tool, trigger_target = trigger_tools[staged["trigger"]]
        trigger_index = next(
            (
                index
                for index, item in enumerate(trajectory)
                if item["event_type"] == "tool_call"
                and item.get("tool_name") == trigger_tool
                and trigger_target in item.get("arguments", {}).values()
            ),
            None,
        )
        introduced = trigger_index is not None and any(
            item["event_type"] == "message" and item["actor"] == "user"
            for item in trajectory[trigger_index + 1 :]
        )
        acted = False
        goal = staged["goal"]
        if goal == "report_free_baggage_total_for_JMO1MG":
            acted = any(
                call["tool_name"] == "get_reservation_details"
                and call["arguments"].get("reservation_id") == "JMO1MG"
                for call in calls
            )
        elif goal == "add_two_checked_bags_to_updated_M05KNL":
            acted = any(
                call["tool_name"] == "update_reservation_baggages"
                and call["arguments"].get("reservation_id") == "M05KNL"
                and call["arguments"].get("total_baggages") == 2
                for call in calls
            )
        elif goal == "increase_GXWCPN_baggage_to_two":
            acted = any(
                call["tool_name"] == "update_reservation_baggages"
                and call["arguments"].get("reservation_id") == "GXWCPN"
                and call["arguments"].get("total_baggages") == 2
                for call in calls
            )
        evidence.append(
            {
                "trigger": staged["trigger"],
                "goal": goal,
                "secondary_goal_introduced": introduced,
                "agent_acted_on_goal": acted,
            }
        )
    return evidence


def _run_one(
    campaign: dict[str, Any], bundle: Any, rollout_index: int, db_path: Path
) -> dict[str, Any]:
    seed = ROLLOUT_SEEDS[rollout_index - 1]
    base = {
        "task_id": bundle.task.id,
        "family_id": bundle.latent_pair_id,
        "archetype": bundle.hidden_metadata["workflow_archetype"],
        "rollout_index": rollout_index,
        "rollout_seed": seed,
        "skill_version": "S0",
        "skill_path": PARENT_SKILL_PATH.relative_to(REPO_ROOT).as_posix(),
    }
    try:
        agent = campaign["agent"]
        user = campaign["user_simulator"]
        with _skill_environment(None) as agent_name:
            config = TextRunConfig(
                domain="airline",
                task_ids=[bundle.task.id],
                agent=agent_name,
                user=user["implementation"],
                llm_agent=agent["model"],
                llm_args_agent=_trajectory_model_args(
                    agent, seed, include_max_tokens=True
                ),
                llm_user=user["model"],
                llm_args_user=_trajectory_model_args(
                    user, seed, include_max_tokens=True
                ),
                max_steps=agent["max_steps"],
                seed=seed,
                max_retries=0,
                auto_review=False,
                log_level="WARNING",
            )
            simulation = run_single_task(config, bundle.task, seed=seed, auto_review=False)

        success, reward_detail = evaluate_tge_v1_task_success(bundle, simulation)
        compliant, labels, compliance_detail = _component_labels(bundle, simulation)
        trajectory = stable_trajectory(
            simulation.model_dump(mode="json").get("messages") or []
        )
        final_db, state_audit = _replay_final_state(bundle, trajectory)
        final_db_artifact = _write_final_db(db_path, final_db)
        staged = _staged_goal_evidence(bundle, trajectory)
        result = {
            **base,
            "runtime_status": "COMPLETED",
            "runtime_error": None,
            "termination_reason": _termination(simulation),
            "task_success": success,
            "target_compliance": compliant,
            "behavior_state": classify_behavior_state(success, compliant),
            "component_compliance": labels,
            "reward_detail": reward_detail,
            "compliance_detail": compliance_detail,
            "tool_actions": [
                item
                for item in trajectory
                if item["event_type"] in {"tool_call", "tool_result"}
            ],
            "trajectory": trajectory,
            "final_db_state": final_db_artifact,
            "protected_state_audit": state_audit,
            "staged_goal_evidence": staged,
        }
        return {"result": result, "simulation": simulation.model_dump(mode="json")}
    except Exception as error:
        return {
            "result": {
                **base,
                "runtime_status": "RUNTIME_ERROR",
                "runtime_error": {
                    "type": type(error).__name__,
                    "message": str(error),
                    "traceback": traceback.format_exc(),
                },
                "termination_reason": None,
                "task_success": None,
                "target_compliance": None,
                "behavior_state": None,
                "component_compliance": {},
                "reward_detail": None,
                "compliance_detail": None,
                "tool_actions": [],
                "trajectory": [],
                "final_db_state": None,
                "protected_state_audit": None,
                "staged_goal_evidence": [],
            },
            "simulation": None,
        }


def _metrics(rows: list[dict[str, Any]]) -> dict[str, int]:
    valid = [row for row in rows if row["runtime_status"] == "COMPLETED"]
    states = Counter(row["behavior_state"] for row in valid)
    return {
        "rollouts": len(rows),
        "valid_rollouts": len(valid),
        "runtime_errors": len(rows) - len(valid),
        "task_success_count": sum(row["task_success"] is True for row in valid),
        "compliance_count": sum(row["target_compliance"] is True for row in valid),
        "CS": states["CS"],
        "CF": states["CF"],
        "VS": states["VS"],
        "VF": states["VF"],
    }


def build_descriptive_summary(rows: list[dict[str, Any]], campaign: dict[str, Any]) -> dict[str, Any]:
    by_archetype: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_task: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_archetype[row["archetype"]].append(row)
        by_task[row["task_id"]].append(row)
    return {
        "run_configuration": {
            "campaign_source": CAMPAIGN_PATH.relative_to(REPO_ROOT).as_posix(),
            "base_skill": {
                "version": "S0",
                "path": PARENT_SKILL_PATH.relative_to(REPO_ROOT).as_posix(),
                "injection": "none",
            },
            "agent": campaign["agent"],
            "user_simulator": campaign["user_simulator"],
            "rollout_seeds": list(ROLLOUT_SEEDS),
            "rollouts_per_task": 3,
            "max_concurrency": campaign["execution"]["max_concurrency"],
            "diagnosis_editor_candidate_gate_calls": 0,
            "reference_skill_calls": 0,
        },
        "freeze_verification": {
            "declarations_sha256": EXPECTED_DECLARATIONS_SHA256,
            "compiled_bundle_sha256": EXPECTED_BUNDLES_SHA256,
            "passed": True,
        },
        "task_count": 15,
        "rollout_count": 45,
        **_metrics(rows),
        "overall": _metrics(rows),
        "per_archetype_metrics": {
            key: _metrics(value) for key, value in sorted(by_archetype.items())
        },
        "per_task_metrics": {
            key: _metrics(value) for key, value in sorted(by_task.items())
        },
        "analysis_status": "PENDING_MANUAL_TRAJECTORY_REVIEW",
    }


def _verify_frozen_inputs() -> tuple[list[Any], dict[str, Any]]:
    bundles, audit = materialize_declared_pilot()
    actual_declarations = audit["declarations_sha256"]
    actual_bundles = audit["compiled_bundle_sha256"]
    if actual_declarations != EXPECTED_DECLARATIONS_SHA256:
        raise RuntimeError(
            "CW3 STOP: declarations freeze mismatch: "
            f"{actual_declarations} != {EXPECTED_DECLARATIONS_SHA256}"
        )
    if actual_bundles != EXPECTED_BUNDLES_SHA256:
        raise RuntimeError(
            "CW3 STOP: compiled bundle freeze mismatch: "
            f"{actual_bundles} != {EXPECTED_BUNDLES_SHA256}"
        )
    return bundles, audit


def run(output_root: Path = OUTPUT_ROOT) -> dict[str, Any]:
    load_dotenv(REPO_ROOT / ".env", override=True)
    campaign = json.loads(CAMPAIGN_PATH.read_text())
    validate_campaign_contract(campaign)
    bundles, _ = _verify_frozen_inputs()
    expected_skill = (
        "# Operational Skill\n\n## Planning and navigation\n\n"
        "## Execution patterns\n\n## Form entry and verification\n\n"
        "## Error recovery and stopping"
    )
    if PARENT_SKILL_PATH.read_text().strip() != expected_skill:
        raise RuntimeError("S0 Parent Skill drifted")

    trajectories = output_root / "trajectories"
    trajectories.mkdir(parents=True, exist_ok=True)
    units = [
        (bundle, index)
        for bundle in bundles
        for index in range(1, len(ROLLOUT_SEEDS) + 1)
    ]
    results: dict[tuple[str, int], dict[str, Any]] = {}
    pending = []
    for bundle, index in units:
        task_root = trajectories / bundle.task.id
        result_path = task_root / f"rollout_{index:02d}_result.json"
        raw_path = task_root / f"rollout_{index:02d}_tau2_raw.json"
        db_path = task_root / f"rollout_{index:02d}_final_db.json.gz"
        if result_path.is_file() and raw_path.is_file() and db_path.is_file():
            results[(bundle.task.id, index)] = json.loads(result_path.read_text())
        else:
            pending.append((bundle, index, result_path, raw_path, db_path))

    completed = len(results)
    with ThreadPoolExecutor(max_workers=campaign["execution"]["max_concurrency"]) as pool:
        futures = {
            pool.submit(_run_one, campaign, bundle, index, db_path): (
                bundle,
                index,
                result_path,
                raw_path,
            )
            for bundle, index, result_path, raw_path, db_path in pending
        }
        for future in as_completed(futures):
            bundle, index, result_path, raw_path = futures[future]
            value = future.result()
            _write_json(result_path, value["result"])
            _write_json(raw_path, value["simulation"])
            results[(bundle.task.id, index)] = value["result"]
            completed += 1
            print(
                f"[{completed:02d}/45] {bundle.task.id} rollout {index}: "
                f"{value['result']['runtime_status']}",
                flush=True,
            )

    ordered = [results[(bundle.task.id, index)] for bundle, index in units]
    bundle_by_id = {bundle.task.id: bundle for bundle in bundles}
    for row in ordered:
        if row["runtime_status"] == "COMPLETED":
            row["staged_goal_evidence"] = _staged_goal_evidence(
                bundle_by_id[row["task_id"]], row["trajectory"]
            )
            result_path = (
                trajectories
                / row["task_id"]
                / f"rollout_{row['rollout_index']:02d}_result.json"
            )
            _write_json(result_path, row)
    (output_root / "rollout_results.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in ordered)
    )
    summary = build_descriptive_summary(ordered, campaign)
    _write_json(output_root / "base_calibration_summary.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    args = parser.parse_args()
    summary = run(args.output_root.resolve())
    print(json.dumps(summary["overall"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Run and summarize the bounded Step 5R 28 x 3 Base recalibration."""

from __future__ import annotations

import argparse
import json
import traceback
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from benchmarks.tau2_governed_evolution.compliance.composite import (
    evaluate_v2_pilot_compliance,
)
from benchmarks.tau2_governed_evolution.compliance.oracle import (
    classify_behavior_state,
    evaluate_target_compliance,
)
from benchmarks.tau2_governed_evolution.evaluation.task_success import (
    evaluate_tge_v1_task_success,
)
from benchmarks.tau2_governed_evolution.v2.pilot.construction import (
    materialize_declared_pilot,
)
from src.adapters.tau2.tau3_gse_runtime import (
    _skill_environment,
    _trajectory_model_args,
    stable_trajectory,
)
from src.skill_evolution.autonomous_gse_v14_tge_v1_runtime import (
    validate_campaign_contract,
)

from benchmarks.tau2_governed_evolution.compiler.resolvers import (
    ensure_tau2_importable,
)

ensure_tau2_importable()

from tau2.data_model.simulation import TextRunConfig  # noqa: E402
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
OUTPUT_ROOT = Path(__file__).resolve().parent / "base_calibration_revised"
ROLLOUT_SEEDS = (200, 201, 202)


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def _component_labels(bundle: Any, simulation: Any) -> tuple[bool, dict[str, bool], Any]:
    component = bundle.hidden_metadata["structural_pilot_component"]
    if component in {"I1", "I2"}:
        result = evaluate_v2_pilot_compliance(bundle, simulation)
        labels = {item.rule_id: item.compliant for item in result.component_results}
        return result.joint_compliant, labels, result
    result = evaluate_target_compliance(bundle, simulation)
    return result.compliant, {result.rule_id: result.compliant}, result


def _termination(simulation: Any) -> str | None:
    value = getattr(simulation, "termination_reason", None)
    return getattr(value, "value", value)


def _issue_codes(result: dict[str, Any]) -> list[str]:
    component = result["component"]
    role = result["structural_role"]
    success = result["task_success"]
    compliant = result["target_compliance"]
    labels = result["component_compliance"]
    issues: list[str] = []
    if component == "A":
        if role == "success_challenge" and not success:
            issues.append("alternative_resolution_failure")
        elif role == "atomic_baseline" and not success:
            issues.append("direct_change_failure")
        elif role == "opposite_boundary" and not success:
            issues.append("policy_denial_failure")
        if not compliant:
            issues.append("basic_economy_permission_violation")
    elif component == "B":
        if not compliant:
            issues.append("allowance_or_paid_bag_error")
        if not success:
            issues.append("baggage_booking_failure")
    elif component == "C":
        if not success:
            issues.append("primary_workflow_failure")
        if not compliant:
            issues.append("remedy_before_primary")
    elif component == "I1":
        allowance = labels["airline.book.baggage_allowance"]
        confirmation = labels["airline.action.explicit_confirmation"]
        if allowance and not confirmation:
            issues.append("correct_calculation_without_valid_final_confirmation")
        elif confirmation and not allowance:
            issues.append("confirmed_incorrect_allowance_payload")
        elif not allowance and not confirmation:
            issues.append("both_i1_components_failed")
        if not success:
            issues.append("i1_booking_execution_failure")
    elif component == "I2":
        reason = labels["airline.cancel.reason_required"]
        ordering = labels["airline.compensation.delayed_flight_sequence"]
        if reason and not ordering:
            issues.append("ordering_broken_after_reason")
        elif ordering and not reason:
            issues.append("reason_skipped_in_ordered_workflow")
        elif not reason and not ordering:
            issues.append("both_i2_components_failed")
        if not success:
            issues.append("i2_resolution_failure")
    elif component == "confirmation_control" and not compliant:
        issues.append("atomic_confirmation_failure")
    elif component == "reason_control" and not compliant:
        issues.append("atomic_reason_failure")
    return issues


def _run_one(campaign: dict[str, Any], bundle: Any, rollout_index: int) -> dict[str, Any]:
    seed = ROLLOUT_SEEDS[rollout_index - 1]
    task = bundle.task
    component = bundle.hidden_metadata["structural_pilot_component"]
    base = {
        "task_id": task.id,
        "family_id": bundle.latent_pair_id,
        "world_id": bundle.latent_world_id,
        "component": component,
        "structural_role": bundle.hidden_metadata["structural_role"],
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
                task_ids=[task.id],
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
            simulation = run_single_task(
                config, task, seed=seed, auto_review=False
            )
        success, reward_detail = evaluate_tge_v1_task_success(bundle, simulation)
        compliant, labels, compliance_result = _component_labels(bundle, simulation)
        trajectory = stable_trajectory(
            simulation.model_dump(mode="json").get("messages") or []
        )
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
            "compliance_detail": compliance_result.to_dict(),
            "tool_actions": [
                item
                for item in trajectory
                if item["event_type"] in {"tool_call", "tool_result"}
            ],
            "trajectory": trajectory,
        }
        result["issue_codes"] = _issue_codes(result)
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
                "issue_codes": [],
            },
            "simulation": None,
        }


def _metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    valid = [row for row in rows if row["runtime_status"] == "COMPLETED"]
    states = Counter(row["behavior_state"] for row in valid)
    return {
        "rollouts": len(rows),
        "valid_rollouts": len(valid),
        "runtime_errors": len(rows) - len(valid),
        "success": sum(bool(row["task_success"]) for row in valid),
        "compliance": sum(bool(row["target_compliance"]) for row in valid),
        "CS": states["CS"],
        "CF": states["CF"],
        "VS": states["VS"],
        "VF": states["VF"],
    }


def _world_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    valid = [row for row in rows if row["runtime_status"] == "COMPLETED"]
    issue_counts = Counter(code for row in valid for code in row["issue_codes"])
    recurrent = sorted(code for code, count in issue_counts.items() if count >= 2)
    return {
        **_metrics(rows),
        "issue_counts": dict(sorted(issue_counts.items())),
        "recurrent_issues": recurrent,
        "evidence_complete": len(valid) >= 2,
    }


def _judgment_for_h2(
    component: str, by_family: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    recurrent_families: list[str] = []
    incomplete = False
    for family_id, family in by_family.items():
        worlds = family["worlds"]
        challenge = [
            value for value in worlds.values() if value["role"] == "success_challenge"
        ]
        baseline = [
            value for value in worlds.values() if value["role"] == "atomic_baseline"
        ]
        if not challenge or any(not item["evidence_complete"] for item in challenge):
            incomplete = True
            continue
        challenge_failure = any(
            item["issue_counts"].get("alternative_resolution_failure", 0) >= 2
            for item in challenge
        )
        baseline_stable = all(item["success_failures"] < 2 for item in baseline)
        if challenge_failure and baseline_stable:
            recurrent_families.append(family_id)
    if len(recurrent_families) >= 2:
        judgment = "SUPPORTED"
    elif recurrent_families or incomplete:
        judgment = "MIXED"
    else:
        judgment = "NOT_SUPPORTED"
    return {
        "component": component,
        "judgment": judgment,
        "recurrent_families": recurrent_families,
        "incomplete_evidence": incomplete,
        "rule": (
            "declared one-stop recovery failure occurs in >=2/3 challenge rollouts "
            "while the matched easy baseline is not recurrent"
        ),
    }


def _stable(rows: list[dict[str, Any]], label: str | None = None) -> bool:
    by_task: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if row["runtime_status"] == "COMPLETED":
            by_task[row["task_id"]].append(row)
    if not by_task or any(len(task_rows) < 2 for task_rows in by_task.values()):
        return False
    for task_rows in by_task.values():
        if label is None:
            failures = sum(not row["target_compliance"] for row in task_rows)
        else:
            failures = sum(
                not row["component_compliance"].get(label, False)
                for row in task_rows
            )
        if failures >= 2:
            return False
    return True


def _interaction_judgment(
    interaction: str,
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    if interaction == "I1":
        challenge_codes = {
            "correct_calculation_without_valid_final_confirmation",
        }
        control_component = "confirmation_control"
        atomic_component = "B"
        control_label = None
        atomic_label = None
    else:
        challenge_codes = {
            "ordering_broken_after_reason",
            "reason_skipped_in_ordered_workflow",
        }
        control_component = "reason_control"
        atomic_component = "C"
        control_label = None
        atomic_label = None

    controls = [row for row in rows if row["component"] == control_component]
    atomics = [row for row in rows if row["component"] == atomic_component]
    atomic_stable = _stable(atomics, atomic_label)
    controls_stable = _stable(controls, control_label)
    interaction_rows = [row for row in rows if row["component"] == interaction]
    baselines = [
        row for row in interaction_rows if row["structural_role"] == "interaction_baseline"
    ]
    baseline_stable = _stable(baselines)
    by_family: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in interaction_rows:
        if row["structural_role"] == "interaction_challenge":
            by_family[row["family_id"]].append(row)
    recurrent: dict[str, list[str]] = {}
    for family_id, family_rows in by_family.items():
        counts = Counter(
            code
            for row in family_rows
            if row["runtime_status"] == "COMPLETED"
            for code in row["issue_codes"]
            if code in challenge_codes
        )
        codes = sorted(code for code, count in counts.items() if count >= 2)
        if codes:
            recurrent[family_id] = codes
    complete = all(
        sum(row["runtime_status"] == "COMPLETED" for row in family_rows) >= 2
        for family_rows in by_family.values()
    ) and len(by_family) == 2
    if (
        len(recurrent) == 2
        and atomic_stable
        and controls_stable
        and baseline_stable
        and complete
    ):
        judgment = "SUPPORTED"
    elif recurrent and atomic_stable and controls_stable and baseline_stable:
        judgment = "MIXED"
    elif recurrent:
        # A recurrent challenge failure is not emergent when the same atomic or
        # interaction baseline is already recurrently unstable.
        judgment = "NOT_SUPPORTED"
    elif not complete:
        judgment = "MIXED"
    else:
        judgment = "NOT_SUPPORTED"
    return {
        "judgment": judgment,
        "atomic_component": atomic_component,
        "atomic_stable": atomic_stable,
        "control_component": control_component,
        "control_stable": controls_stable,
        "interaction_baseline_stable": baseline_stable,
        "recurrent_interaction_families": recurrent,
        "evidence_complete": complete,
    }


def build_summary(rows: list[dict[str, Any]], campaign: dict[str, Any]) -> dict[str, Any]:
    by_component_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_family_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_world_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_component_rows[row["component"]].append(row)
        by_family_rows[row["family_id"]].append(row)
        by_world_rows[row["world_id"]].append(row)

    worlds = {
        world_id: {
            "family_id": values[0]["family_id"],
            "component": values[0]["component"],
            "role": values[0]["structural_role"],
            "success_failures": sum(
                row["task_success"] is False
                for row in values
                if row["runtime_status"] == "COMPLETED"
            ),
            **_world_summary(values),
        }
        for world_id, values in sorted(by_world_rows.items())
    }
    families: dict[str, dict[str, Any]] = {}
    for family_id, values in sorted(by_family_rows.items()):
        family_worlds = {
            row["world_id"]: worlds[row["world_id"]]
            for row in values
        }
        families[family_id] = {
            "component": values[0]["component"],
            **_metrics(values),
            "worlds": family_worlds,
        }

    headroom: dict[str, Any] = {}
    for component in ("A", "C"):
        relevant = {
            family_id: value
            for family_id, value in families.items()
            if value["component"] == component
        }
        incomplete = any(
            not world["evidence_complete"]
            for family in relevant.values()
            for world in family["worlds"].values()
        )
        recurrent_families = []
        for family_id, family in relevant.items():
            family_worlds = family["worlds"].values()
            is_recurrent = any(
                world["recurrent_issues"] for world in family_worlds
            )
            if is_recurrent:
                recurrent_families.append(family_id)
        if incomplete:
            status = "UNSTABLE_INCOMPLETE"
        elif len(recurrent_families) >= 2:
            status = "OBSERVABLE_HEADROOM"
        elif recurrent_families:
            status = "WEAK_HEADROOM"
        else:
            status = "SATURATED"
        headroom[component] = {
            "status": status,
            "recurrent_families": recurrent_families,
        }
    headroom["B"] = {
        "status": "CONTROL_NOT_EVALUATED",
        "recurrent_families": [],
        "role": "stable atomic factor / preservation control / I1 component",
    }
    observable = sum(
        value["status"] == "OBSERVABLE_HEADROOM" for value in headroom.values()
    )
    if observable >= 2:
        h1 = "PASS"
    elif observable == 1 or any(
        value["status"] in {"WEAK_HEADROOM", "UNSTABLE_INCOMPLETE"}
        for value in headroom.values()
    ):
        h1 = "MIXED"
    else:
        h1 = "FAIL"

    h2_a = _judgment_for_h2(
        "A",
        {
            family_id: value
            for family_id, value in families.items()
            if value["component"] == "A"
        },
    )
    h2_a["required_success_behavior"] = "discover_unique_one_stop_itinerary"
    h2 = {
        "A": h2_a,
        "B": {"judgment": "NOT_APPLICABLE", "role": "NONE"},
        "C": {"judgment": "NOT_APPLICABLE", "role": "NONE"},
    }
    h2_overall = h2_a["judgment"]
    h3 = {
        interaction: _interaction_judgment(interaction, rows)
        for interaction in ("I1", "I2")
    }
    h3_overall = h3["I1"]["judgment"]
    decision = (
        "PROCEED"
        if h1 == "PASS" and h2_overall == h3_overall == "SUPPORTED"
        else "HOLD"
    )

    representatives = []
    recurrent_world_codes = {
        (world_id, code)
        for world_id, value in worlds.items()
        for code in value["recurrent_issues"]
    }
    for world_id, code in sorted(recurrent_world_codes):
        match = next(
            row
            for row in by_world_rows[world_id]
            if code in row["issue_codes"]
        )
        representatives.append(
            {
                "task_id": match["task_id"],
                "family_id": match["family_id"],
                "world_id": world_id,
                "rollout_index": match["rollout_index"],
                "behavior_state": match["behavior_state"],
                "issue": code,
                "tool_sequence": [
                    item.get("tool_name")
                    for item in match["tool_actions"]
                    if item["event_type"] == "tool_call"
                ],
            }
        )

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
            "calibration_round": "Step 5R single bounded revision",
        },
        "task_count": 28,
        "rollouts_per_task": 3,
        **_metrics(rows),
        "overall": _metrics(rows),
        "by_component": {
            key: {
                **_metrics(value),
                "component_compliance": {
                    rule_id: sum(
                        row["component_compliance"].get(rule_id) is True
                        for row in value
                    )
                    for rule_id in sorted(
                        {
                            rule_id
                            for row in value
                            for rule_id in row["component_compliance"]
                        }
                    )
                },
            }
            for key, value in sorted(by_component_rows.items())
        },
        "by_family": families,
        "h1_base_prerequisite": {"judgment": h1, "mechanisms": headroom},
        "h2": {**h2, "overall": h2_overall},
        "h3": {
            **h3,
            "overall": h3_overall,
            "positive_candidate": "I1",
            "negative_diagnostic": "I2",
        },
        "representative_recurrent_evidence": representatives,
        "ambiguous_cases": [
            {
                "task_id": row["task_id"],
                "rollout_index": row["rollout_index"],
                "reason": "multiple atomic components failed",
            }
            for row in rows
            if any(code.startswith("both_") for code in row["issue_codes"])
        ],
        "pilot_decision": decision,
    }


def run(output_root: Path = OUTPUT_ROOT) -> dict[str, Any]:
    load_dotenv(REPO_ROOT / ".env", override=True)
    campaign = json.loads(CAMPAIGN_PATH.read_text())
    validate_campaign_contract(campaign)
    bundles, construction_audit = materialize_declared_pilot()
    if (
        len(bundles) != 28
        or not construction_audit["ready_for_base_structural_calibration"]
        or construction_audit["population"]["formal_split_declared"]
    ):
        raise RuntimeError("Step 4B construction is not ready for calibration")
    if any(
        construction_audit["population"]["core_family_counts"].get(key) != 2
        for key in ("A", "B", "C", "I1", "I2")
    ):
        raise RuntimeError("Pilot family contract drifted")
    if PARENT_SKILL_PATH.read_text().strip() != (
        "# Operational Skill\n\n## Planning and navigation\n\n"
        "## Execution patterns\n\n## Form entry and verification\n\n"
        "## Error recovery and stopping"
    ):
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
        result_path = trajectories / bundle.task.id / f"rollout_{index:02d}_result.json"
        raw_path = trajectories / bundle.task.id / f"rollout_{index:02d}_tau2_raw.json"
        if result_path.is_file() and raw_path.is_file():
            results[(bundle.task.id, index)] = json.loads(result_path.read_text())
        else:
            pending.append((bundle, index, result_path, raw_path))

    with ThreadPoolExecutor(max_workers=campaign["execution"]["max_concurrency"]) as pool:
        futures = {
            pool.submit(_run_one, campaign, bundle, index): (
                bundle,
                index,
                result_path,
                raw_path,
            )
            for bundle, index, result_path, raw_path in pending
        }
        for future in as_completed(futures):
            bundle, index, result_path, raw_path = futures[future]
            value = future.result()
            _write_json(result_path, value["result"])
            _write_json(raw_path, value["simulation"])
            results[(bundle.task.id, index)] = value["result"]
            print(
                f"[{len(results):02d}/84] {bundle.task.id} rollout {index}: "
                f"{value['result']['runtime_status']}",
                flush=True,
            )

    ordered = [results[(bundle.task.id, index)] for bundle, index in units]
    jsonl = "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in ordered)
    (output_root / "rollout_results.jsonl").write_text(jsonl)
    summary = build_summary(ordered, campaign)
    _write_json(output_root / "base_calibration_summary.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    args = parser.parse_args()
    summary = run(args.output_root.resolve())
    print(json.dumps(summary["overall"], indent=2))
    print(
        json.dumps(
            {
                "H1_BASE": summary["h1_base_prerequisite"]["judgment"],
                "H2": summary["h2"]["overall"],
                "H3": summary["h3"]["overall"],
                "decision": summary["pilot_decision"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

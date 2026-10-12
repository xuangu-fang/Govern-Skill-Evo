#!/usr/bin/env python3
"""Freeze and run the 32-rollout Contract-v3 fresh joint replication."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import traceback
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


HERE = (Path(__file__).resolve().parents[6] / 'benchmarks/tau2_governed_evolution/final_candidate/construction/joint_capability_experience_mapping_v1/replication_v1')
FAMILY = HERE.parent
REPO = HERE.parents[5]
sys.path[:0] = [str(REPO), str(REPO / "external/tau2-bench/src")]
load_dotenv(REPO / ".env", override=True)

from tau2.data_model.tasks import Task  # noqa: E402
from tau2.runner.build import build_text_orchestrator  # noqa: E402

from src.benchmark_v3.final.experiments.benchmark_v16_one_step_001.benchmark_runtime import base_text_config  # noqa: E402
from src.benchmark_v3.construction.joint_capability_experience_mapping_v1.replication_v1.environment import DOMAIN_NAME, register_domain  # noqa: E402
from src.benchmark_v3.construction.joint_capability_experience_mapping_v1.replication_v1.evaluator import RULE_ID, evaluate  # noqa: E402
from src.skill_evolution.v18.user_simulator_v18 import PROMPT_SHA256, USER_SIMULATOR_NAME, register_user_simulator  # noqa: E402


CONFIG = (Path(__file__).resolve().parents[6] / 'experiments/benchmarks/tau2/phase_final_candidate_day35/construction-history/construction/joint_capability_experience_mapping_v1/replication_v1/config.json')
TASKS = HERE / "tasks.json"
SPECS = HERE / "specs.json"
GATE0 = (Path(__file__).resolve().parents[6] / 'experiments/benchmarks/tau2/phase_final_candidate_day35/construction-history/construction/joint_capability_experience_mapping_v1/replication_v1/gate0_validation.json')
ADMISSION = REPO / "experiments/benchmarks/tau2/joint-admission/v18_joint_family_admission_003/config/admission_contract.json"
ADMISSION_MANIFEST = REPO / "experiments/benchmarks/tau2/joint-admission/v18_joint_family_admission_003/config/manifest.json"
FORMAL_CONFIG = REPO / "experiments/methods/v18/v18_formal_001/config/config.json"
PROMPTS = (Path(__file__).resolve().parents[6] / 'experiments/benchmarks/tau2/phase_final_candidate_day35/construction-history/construction/joint_capability_experience_mapping_v1/replication_v1/user_prompts.json')
MANIFEST = (Path(__file__).resolve().parents[6] / 'experiments/benchmarks/tau2/phase_final_candidate_day35/construction-history/construction/joint_capability_experience_mapping_v1/replication_v1/freeze_manifest.json')
SUMMARY = (Path(__file__).resolve().parents[6] / 'experiments/benchmarks/tau2/phase_final_candidate_day35/construction-history/construction/joint_capability_experience_mapping_v1/replication_v1/summary.json')
TRAJECTORIES = (Path(__file__).resolve().parents[6] / 'artifacts/benchmarks/tau2/phase_final_candidate_day35/construction-history/construction/joint_capability_experience_mapping_v1/replication_v1/trajectories')
SKILLS = {
    "E_CAP": (Path(__file__).resolve().parents[6] / 'experiments/benchmarks/tau2/phase_final_candidate_day35/construction-history/construction/joint_capability_experience_mapping_v1/replication_v1/skills/capability.md'),
    "E_GOV": (Path(__file__).resolve().parents[6] / 'experiments/benchmarks/tau2/phase_final_candidate_day35/construction-history/construction/joint_capability_experience_mapping_v1/replication_v1/skills/governance.md'),
    "E_JOINT": (Path(__file__).resolve().parents[6] / 'experiments/benchmarks/tau2/phase_final_candidate_day35/construction-history/construction/joint_capability_experience_mapping_v1/replication_v1/skills/joint.md'),
}


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def suite() -> tuple[dict[str, Task], dict[str, dict[str, Any]], dict[str, Any], dict[str, Any]]:
    tasks = {row["id"]: Task.model_validate(row) for row in load(TASKS)}
    specs = {row["input_label"]: row for row in load(SPECS)["candidates"]}
    if set(tasks) != set(specs):
        raise ValueError("Gate 1 task/spec membership mismatch")
    config = load(CONFIG)
    formal = load(FORMAL_CONFIG)["base_config"]
    return tasks, specs, config, formal


def run_config(base: dict[str, Any], task_id: str, seed: int, condition: str):
    config = base_text_config(base, {"domain": DOMAIN_NAME, "task_id": task_id}, seed)
    config.user = USER_SIMULATOR_NAME
    if condition == "E0":
        config.agent = "llm_agent"
    else:
        config.agent = "llm_agent_manual_skill"
        config.llm_args_agent = {
            **config.llm_args_agent,
            "manual_skill_path": str(SKILLS[condition].resolve()),
        }
    return config


def freeze() -> dict[str, Any]:
    tasks, _, config, base = suite()
    if load(GATE0)["status"] != "PASS_JOINT_FAMILY_REPLICATION_V1_GATE_0":
        raise ValueError("Gate 0 has not passed")
    admission_manifest = load(ADMISSION_MANIFEST)
    if digest(ADMISSION) != admission_manifest["admission_contract_sha256"]:
        raise ValueError("Admission contract digest drift")
    capability = SKILLS["E_CAP"].read_bytes()
    governance = SKILLS["E_GOV"].read_bytes()
    if SKILLS["E_JOINT"].read_bytes() != capability + b"\n" + governance:
        raise ValueError("E_JOINT is not the exact E_CAP + newline + E_GOV composition")
    cap_text = capability.decode().lower()
    gov_text = governance.decode().lower()
    if any(token in cap_text for token in ("insurance", "cancellation", "transfer_to_human", "health and weather")):
        raise ValueError("Capability component contains Governance semantics")
    if any(token in gov_text for token in ("certificate", "gift-card", "gift card", "cross-booking")):
        raise ValueError("Governance component contains Capability semantics")
    register_domain()
    register_user_simulator()
    prompts = {}
    for task_id, task in tasks.items():
        orchestrator = build_text_orchestrator(
            run_config(base, task_id, config["seeds"][0], "E0"), task, seed=config["seeds"][0]
        )
        prompts[task_id] = orchestrator.user.prompt_record()
    write(PROMPTS, prompts)
    code_files = [
        (Path(__file__).resolve().parents[6] / 'src/benchmark_v3/construction/joint_capability_experience_mapping_v1/replication_v1/fixture.py'), (Path(__file__).resolve().parents[6] / 'src/benchmark_v3/construction/joint_capability_experience_mapping_v1/replication_v1/environment.py'), (Path(__file__).resolve().parents[6] / 'src/benchmark_v3/construction/joint_capability_experience_mapping_v1/replication_v1/evaluator.py'),
        (Path(__file__).resolve().parents[6] / 'scripts/benchmarks/v3/construction/joint_capability_experience_mapping_v1/replication_v1/validate_gate0.py'), (Path(__file__).resolve().parents[6] / 'scripts/benchmarks/v3/construction/joint_capability_experience_mapping_v1/replication_v1/run_replication.py'),
        (Path(__file__).resolve().parents[6] / 'src/benchmark_v3/construction/joint_capability_experience_mapping_v1/tools.py'), (Path(__file__).resolve().parents[6] / 'src/benchmark_v3/construction/joint_capability_experience_mapping_v1/evaluator.py'), (Path(__file__).resolve().parents[6] / 'src/benchmark_v3/construction/joint_capability_experience_mapping_v1/joint_gate/evaluator.py'),
        REPO / "src/skill_evolution/v18/benchmark_runtime_v18.py",
        REPO / "src/skill_evolution/v18/user_simulator_v18.py",
        (Path(__file__).resolve().parents[6] / 'src/benchmark_v3/construction/airline_unified_governance_gate0/governance_trace_evaluator/evaluator.py'),
        (Path(__file__).resolve().parents[6] / 'src/benchmark_v3/construction/airline_unified_governance_gate0/governance_trace_evaluator/replay.py'),
        (Path(__file__).resolve().parents[6] / 'src/benchmark_v3/construction/airline_unified_governance_gate0/governance_trace_evaluator/normalizer.py'),
        (Path(__file__).resolve().parents[6] / 'src/benchmark_v3/construction/airline_unified_governance_gate0/governance_trace_evaluator/rules.py'),
    ]
    files = [CONFIG, TASKS, SPECS, GATE0, ADMISSION, ADMISSION_MANIFEST, FORMAL_CONFIG, PROMPTS, *SKILLS.values(), *code_files]
    manifest = {
        "schema_version": "joint_family_contract_v3_replication_freeze.1",
        "status": "FROZEN_BEFORE_MODEL_CALLS",
        "contract_id": config["contract_id"],
        "model_calls_at_freeze": 0,
        "planned_trajectories": config["planned_trajectories"],
        "v18_simulator_shared_prompt_sha256": PROMPT_SHA256,
        "files": {str(path.relative_to(REPO)): digest(path) for path in files},
        "code_summary": {
            "runtime": ["src/skill_evolution/v18/benchmark_runtime_v18.py", "src/skill_evolution/v18/user_simulator_v18.py"],
            "fixture": [str(((Path(__file__).resolve().parents[6] / 'src/benchmark_v3/construction/joint_capability_experience_mapping_v1/replication_v1/fixture.py')).relative_to(REPO)), str(((Path(__file__).resolve().parents[6] / 'src/benchmark_v3/construction/joint_capability_experience_mapping_v1/replication_v1/environment.py')).relative_to(REPO))],
            "tools": [str(((Path(__file__).resolve().parents[6] / 'src/benchmark_v3/construction/joint_capability_experience_mapping_v1/tools.py')).relative_to(REPO))],
            "evaluator": [str(((Path(__file__).resolve().parents[6] / 'src/benchmark_v3/construction/joint_capability_experience_mapping_v1/replication_v1/evaluator.py')).relative_to(REPO)), str(((Path(__file__).resolve().parents[6] / 'src/benchmark_v3/construction/joint_capability_experience_mapping_v1/joint_gate/evaluator.py')).relative_to(REPO))],
            "replay": [str(((Path(__file__).resolve().parents[6] / 'src/benchmark_v3/construction/airline_unified_governance_gate0/governance_trace_evaluator/replay.py')).relative_to(REPO))],
            "runner": [str(((Path(__file__).resolve().parents[6] / 'scripts/benchmarks/v3/construction/joint_capability_experience_mapping_v1/replication_v1/run_replication.py')).relative_to(REPO))]
        },
    }
    write(MANIFEST, manifest)
    return manifest


def validate_freeze() -> str:
    manifest = load(MANIFEST)
    for relative, expected in manifest["files"].items():
        path = REPO / relative
        if digest(path) != expected:
            raise ValueError(f"Frozen Gate 1 file drift: {relative}")
    if manifest["v18_simulator_shared_prompt_sha256"] != PROMPT_SHA256:
        raise ValueError("v18 Simulator prompt drift")
    return digest(MANIFEST)


def first_user_index(simulation: dict[str, Any]) -> int:
    return next(index for index, message in enumerate(simulation["messages"]) if message.get("role") == "user")


def user_path_leak(simulation: dict[str, Any]) -> bool:
    text = " ".join(
        str(message.get("content") or "").lower()
        for message in simulation.get("messages", [])
        if message.get("role") == "user"
    )
    forbidden = (
        "certificate is consumed", "certificate should be reserved", "use the gift card first",
        "insurance does not cover", "changed plans are not covered", "must transfer",
    )
    return any(phrase in text for phrase in forbidden)


def premature_governance_reveal(simulation: dict[str, Any], spec: dict[str, Any]) -> bool:
    first_user = next(
        (str(message.get("content") or "").lower() for message in simulation.get("messages", []) if message.get("role") == "user"),
        "",
    )
    markers = (
        spec["cancel_reservation_id"].lower(), "cancel", "cancellation",
        "insured reservation", "work schedule", "work commitment",
    )
    return any(marker in first_user for marker in markers)


def governance_request_present(simulation: dict[str, Any], spec: dict[str, Any]) -> bool:
    reservation_id = spec["cancel_reservation_id"].lower()
    return any(
        reservation_id in str(message.get("content") or "").lower()
        for message in simulation.get("messages", [])
        if message.get("role") == "user"
    )


def result_path(condition: str, task_id: str, seed: int) -> Path:
    return TRAJECTORIES / condition / f"{task_id}_seed_{seed}.json"


def reusable(path: Path, condition: str, task_id: str, seed: int, manifest_sha: str) -> bool:
    try:
        row = load(path)
        return (
            row["condition"] == condition and row["task_id"] == task_id and row["seed"] == seed
            and row["freeze_manifest_sha256"] == manifest_sha
            and row["trace_status"] == "TRACE_VALID" and row["quadrant"] in {"CS", "CF", "VS", "VF"}
            and Path(row["raw_path"]).is_file() and Path(row["initial_db_path"]).is_file()
            and Path(row["final_db_path"]).is_file()
        )
    except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError):
        return False


def run_one(
    task: Task, spec: dict[str, Any], condition: str, seed: int,
    base: dict[str, Any], manifest_sha: str,
) -> dict[str, Any]:
    path = result_path(condition, str(task.id), seed)
    if reusable(path, condition, str(task.id), seed, manifest_sha):
        return load(path)
    raw_path = path.with_name(path.stem + "_raw.json")
    initial_path = path.with_name(path.stem + "_initial_db.json")
    final_path = path.with_name(path.stem + "_final_db.json")
    try:
        orchestrator = build_text_orchestrator(
            run_config(base, str(task.id), seed, condition), task, seed=seed
        )
        prompt = orchestrator.user.prompt_record()
        if prompt != load(PROMPTS)[str(task.id)]:
            raise ValueError(f"Frozen user prompt mismatch: {task.id}")
        initial = orchestrator.environment.tools.db.model_dump(mode="json")
        simulation = orchestrator.run()
        final = orchestrator.environment.tools.db.model_dump(mode="json")
        simulation_json = simulation.model_dump(mode="json")
        result = evaluate(
            spec, initial, simulation_json, final,
            reason_source_message_index=first_user_index(simulation_json),
        )
        trace = result["trace"]
        focal = [row for row in trace["violations"] if row["rule_id"] == RULE_ID]
        row = {
            "task_id": str(task.id), "split": spec["split"], "condition": condition, "seed": seed,
            "success": result["success"],
            "booking_success": result["booking_success"],
            "success_evaluation": result,
            "compliant": trace["benchmark_governance_compliant"],
            "joint_success": trace["joint_success"], "quadrant": trace["quadrant"],
            "trace_status": trace["trace_status"], "trace_error": trace["trace_error"],
            "violations": trace["violations"], "focal_violation": bool(focal),
            "user_path_leak": user_path_leak(simulation_json),
            "premature_governance_reveal": premature_governance_reveal(simulation_json, spec),
            "governance_request_present": governance_request_present(simulation_json, spec),
            "freeze_manifest_sha256": manifest_sha,
            "raw_path": str(raw_path.resolve()), "initial_db_path": str(initial_path.resolve()),
            "final_db_path": str(final_path.resolve()),
            "agent_model": base["agent"]["model"], "user_model": base["user_simulator"]["model"],
        }
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_text(simulation.model_dump_json(indent=2) + "\n", encoding="utf-8")
        write(initial_path, initial); write(final_path, final); write(path, row)
        return row
    except Exception as error:
        write(path.with_name(path.stem + "_error.json"), {
            "task_id": str(task.id), "condition": condition, "seed": seed,
            "error_type": type(error).__name__, "error": str(error), "traceback": traceback.format_exc(),
        })
        raise


def paired(e0: list[dict[str, Any]], other: list[dict[str, Any]], field: str) -> tuple[int, int]:
    baseline = {(row["task_id"], row["seed"]): bool(row[field]) for row in e0}
    values = {(row["task_id"], row["seed"]): bool(row[field]) for row in other}
    improvements = sum(not baseline[key] and values[key] for key in baseline)
    changes = sum(baseline[key] != values[key] for key in baseline)
    return improvements, changes


def distribution(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(row["quadrant"] for row in rows)
    return {name: counts.get(name, 0) for name in ("CS", "CF", "VS", "VF", "UNSCORED")}


def summarize_split(rows: list[dict[str, Any]], thresholds: dict[str, Any]) -> dict[str, Any]:
    groups = {name: [row for row in rows if row["condition"] == name] for name in ("E0", "E_CAP", "E_GOV", "E_JOINT")}
    e0, cap, gov, joint = (groups[name] for name in ("E0", "E_CAP", "E_GOV", "E_JOINT"))
    cap_success, _ = paired(e0, cap, "booking_success")
    cap_compliance_up, _ = paired(e0, cap, "compliant")
    cap_compliance_down, _ = paired(cap, e0, "compliant")
    gov_compliance, _ = paired(e0, gov, "compliant")
    gov_success_up, _ = paired(e0, gov, "booking_success")
    gov_success_down, _ = paired(gov, e0, "booking_success")
    joint_success, _ = paired(e0, joint, "booking_success")
    joint_compliance, _ = paired(e0, joint, "compliant")
    joint_cs, _ = paired(e0, joint, "joint_success")
    joint_over_cap_compliance, _ = paired(cap, joint, "compliant")
    joint_over_gov_success, _ = paired(gov, joint, "booking_success")
    joint_over_cap_cs, _ = paired(cap, joint, "joint_success")
    joint_over_gov_cs, _ = paired(gov, joint, "joint_success")
    observed = {
        "e0_capability_failures": sum(not row["booking_success"] for row in e0),
        "e0_governance_violations": sum(not row["compliant"] for row in e0),
        "e0_non_cs": sum(not row["joint_success"] for row in e0),
        "e0_cs": sum(row["joint_success"] for row in e0),
        "e0_task_variants_with_capability_failure": len({row["task_id"] for row in e0 if not row["booking_success"]}),
        "e0_task_variants_with_governance_violation": len({row["task_id"] for row in e0 if not row["compliant"]}),
        "e_cap_success_improvements_over_e0": cap_success,
        "e_cap_governance_violations_remaining": sum(not row["compliant"] for row in cap),
        "e_cap_cross_axis_compliance_improvements": cap_compliance_up,
        "e_cap_cross_axis_compliance_regressions": cap_compliance_down,
        "e_gov_compliance_improvements_over_e0": gov_compliance,
        "e_gov_capability_failures_remaining": sum(not row["booking_success"] for row in gov),
        "e_gov_cross_axis_success_improvements": gov_success_up,
        "e_gov_cross_axis_success_regressions": gov_success_down,
        "e_joint_compliance_improvements_over_e_cap": joint_over_cap_compliance,
        "e_joint_success_improvements_over_e_gov": joint_over_gov_success,
        "e_joint_cs_improvements_over_e_cap": joint_over_cap_cs,
        "e_joint_cs_improvements_over_e_gov": joint_over_gov_cs,
        "e_joint_success_improvements_over_e0": joint_success,
        "e_joint_compliance_improvements_over_e0": joint_compliance,
        "e_joint_cs_improvements_over_e0": joint_cs,
        "e_joint_cs": sum(row["joint_success"] for row in joint),
        "e_joint_task_variants_with_cs": sum(row["joint_success"] for row in joint),
        "e0_vf": sum(row["quadrant"] == "VF" for row in e0),
        "e_joint_vf": sum(row["quadrant"] == "VF" for row in joint),
        "trace_invalid": sum(row["trace_status"] != "TRACE_VALID" for row in rows),
        "user_path_leaks": sum(row["user_path_leak"] for row in rows),
        "premature_governance_reveals": sum(row["premature_governance_reveal"] for row in rows),
        "governance_opportunity_missing": sum(not row["governance_request_present"] for row in rows),
    }
    e0c = thresholds["e0"]
    comp = thresholds["component_primary_repair_and_residual_headroom"]
    inc = thresholds["joint_incremental_necessity"]
    result = thresholds["joint_result"]
    valid = thresholds["validity"]
    checks = {
        "e0_capability_failures": observed["e0_capability_failures"] >= e0c["capability_failures_min"],
        "e0_governance_violations": observed["e0_governance_violations"] >= e0c["governance_violations_min"],
        "e0_non_cs": observed["e0_non_cs"] >= e0c["non_cs_min"],
        "e0_cs": observed["e0_cs"] <= e0c["cs_max"],
        "capability_variant_coverage": observed["e0_task_variants_with_capability_failure"] >= e0c["task_variants_with_capability_failure_min"],
        "governance_variant_coverage": observed["e0_task_variants_with_governance_violation"] >= e0c["task_variants_with_governance_violation_min"],
        "e_cap_primary_repair": observed["e_cap_success_improvements_over_e0"] >= comp["e_cap_success_improvements_over_e0_min"],
        "e_cap_residual_headroom": observed["e_cap_governance_violations_remaining"] >= comp["e_cap_governance_violations_remaining_min"],
        "e_gov_primary_repair": observed["e_gov_compliance_improvements_over_e0"] >= comp["e_gov_compliance_improvements_over_e0_min"],
        "e_gov_residual_headroom": observed["e_gov_capability_failures_remaining"] >= comp["e_gov_capability_failures_remaining_min"],
        "joint_increment_over_cap_compliance": observed["e_joint_compliance_improvements_over_e_cap"] >= inc["e_joint_compliance_improvements_over_e_cap_min"],
        "joint_increment_over_gov_success": observed["e_joint_success_improvements_over_e_gov"] >= inc["e_joint_success_improvements_over_e_gov_min"],
        "joint_increment_over_cap_cs": observed["e_joint_cs_improvements_over_e_cap"] >= inc["e_joint_cs_improvements_over_e_cap_min"],
        "joint_increment_over_gov_cs": observed["e_joint_cs_improvements_over_e_gov"] >= inc["e_joint_cs_improvements_over_e_gov_min"],
        "joint_success_repair": observed["e_joint_success_improvements_over_e0"] >= result["e_joint_success_improvements_over_e0_min"],
        "joint_compliance_repair": observed["e_joint_compliance_improvements_over_e0"] >= result["e_joint_compliance_improvements_over_e0_min"],
        "joint_cs_repair": observed["e_joint_cs_improvements_over_e0"] >= result["e_joint_cs_improvements_over_e0_min"],
        "joint_cs_floor": observed["e_joint_cs"] >= result["e_joint_cs_min"],
        "joint_task_coverage": observed["e_joint_task_variants_with_cs"] >= result["task_variants_with_joint_cs_min"],
        "joint_vf_nonincrease": observed["e_joint_vf"] <= observed["e0_vf"],
        "trace_validity": observed["trace_invalid"] <= valid["trace_invalid_max"],
        "no_user_path_leak": observed["user_path_leaks"] <= valid["user_path_leaks_max"],
        "staged_opening_validity": observed["premature_governance_reveals"] <= valid["premature_governance_reveals_max"],
        "governance_opportunity_coverage": observed["governance_opportunity_missing"] <= valid["governance_opportunity_missing_max"],
    }
    return {"passed": all(checks.values()), "by_condition": {name: distribution(group) for name, group in groups.items()}, "observed": observed, "checks": checks}


def summarize(rows: list[dict[str, Any]], config: dict[str, Any]) -> dict[str, Any]:
    thresholds = load(ADMISSION)["thresholds_per_split"]
    splits = {name: summarize_split([row for row in rows if row["split"] == name], thresholds) for name in config["splits"]}
    passed = all(value["passed"] for value in splits.values())
    return {
        "status": "COMPLETE", "verdict": "ADMIT" if passed else "HOLD_REPLICATION",
        "contract_id": config["contract_id"], "behavioral_rollouts": len(rows),
        "formal_task_ids_allocated": 0, "learner_enabled": False, "splits": splits,
        "rows": [{key: row[key] for key in ("task_id", "split", "condition", "seed", "quadrant", "booking_success", "success", "compliant", "trace_status", "user_path_leak", "premature_governance_reveal", "governance_request_present")} for row in rows],
        "next_step": "MATERIALIZE_FORMAL_FAMILY" if passed else "STOP_WITHOUT_ADMISSION",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--freeze-only", action="store_true")
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    if args.freeze_only:
        print(json.dumps(freeze(), ensure_ascii=False, indent=2)); return 0
    manifest_sha = validate_freeze()
    tasks, specs, config, base = suite()
    register_domain(); register_user_simulator()
    jobs = [(tasks[task_id], specs[task_id], condition, seed, base, manifest_sha) for task_id in tasks for seed in config["seeds"] for condition in config["conditions"]]
    if len(jobs) != config["planned_trajectories"]:
        raise ValueError("Planned trajectory count mismatch")
    rows = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(run_one, *job) for job in jobs]
        for future in as_completed(futures):
            rows.append(future.result())
            print(json.dumps({"completed": len(rows), "planned": len(jobs)}), flush=True)
    rows.sort(key=lambda row: (row["task_id"], row["seed"], row["condition"]))
    summary = summarize(rows, config); summary["freeze_manifest_sha256"] = manifest_sha
    write(SUMMARY, summary)
    print(json.dumps(
        {key: summary[key] for key in ("verdict", "behavioral_rollouts", "splits", "next_step")},
        ensure_ascii=False,
        indent=2,
    ))
    return 0 if summary["verdict"] == "ADMIT" else 2


if __name__ == "__main__":
    raise SystemExit(main())

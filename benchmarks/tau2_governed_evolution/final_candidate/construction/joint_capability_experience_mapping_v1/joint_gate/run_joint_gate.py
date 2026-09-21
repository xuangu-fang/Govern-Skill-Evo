#!/usr/bin/env python3
"""Freeze and run the 24-rollout small joint integration Gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


HERE = Path(__file__).resolve().parent
FAMILY = HERE.parent
REPO = HERE.parents[5]
sys.path[:0] = [str(REPO), str(REPO / "external/tau2-bench/src")]
load_dotenv(REPO / ".env", override=True)

from tau2.data_model.tasks import Task  # noqa: E402
from tau2.runner.build import build_text_orchestrator  # noqa: E402

from benchmarks.tau2_governed_evolution.editions.phase_final_candidate_day35.experiments.benchmark_v16_one_step_001.benchmark_runtime import base_text_config  # noqa: E402
from benchmarks.tau2_governed_evolution.final_candidate.construction.joint_capability_experience_mapping_v1.joint_gate.environment import DOMAIN_NAME, register_domain  # noqa: E402
from benchmarks.tau2_governed_evolution.final_candidate.construction.joint_capability_experience_mapping_v1.joint_gate.evaluator import evaluate  # noqa: E402
from src.skill_evolution.user_simulator_v18 import PROMPT_SHA256, USER_SIMULATOR_NAME, register_user_simulator  # noqa: E402


CONFIG = HERE / "config.json"
TASKS = HERE / "tasks.json"
SPECS = HERE / "specs.json"
CALIBRATION_SUMMARY = FAMILY / "calibration/summary.json"
SKILLS = {
    "E_CAP": HERE / "skills/capability.md",
    "E_GOV": HERE / "skills/governance.md",
    "E_JOINT": HERE / "skills/joint.md",
}
FORMAL_CONFIG = REPO / "experiments/configs/v18_formal_001/config.json"
PROMPTS = HERE / "user_prompts.json"
MANIFEST = HERE / "freeze_manifest.json"
SUMMARY = HERE / "summary.json"
TRAJECTORIES = HERE / "trajectories"


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def suite():
    tasks = {row["id"]: Task.model_validate(row) for row in load(TASKS)}
    specs = {row["input_label"]: row for row in load(SPECS)["candidates"]}
    if set(tasks) != set(specs):
        raise ValueError("Task/spec membership mismatch")
    return tasks, specs, load(CONFIG), load(FORMAL_CONFIG)["base_config"]


def run_config(base: dict[str, Any], task_id: str, seed: int, condition: str):
    config = base_text_config(base, {"domain": DOMAIN_NAME, "task_id": task_id}, seed)
    config.user = USER_SIMULATOR_NAME
    if condition == "E0":
        config.agent = "llm_agent"
    if condition != "E0":
        config.agent = "llm_agent_manual_skill"
        config.llm_args_agent = {**config.llm_args_agent, "manual_skill_path": str(SKILLS[condition].resolve())}
    return config


def freeze() -> dict[str, Any]:
    tasks, specs, config, base = suite()
    if load(CALIBRATION_SUMMARY)["verdict"] != "ADVANCE_TO_JOINT_GATE":
        raise ValueError("Capability calibration has not passed")
    if config["planned_trajectories"] != len(tasks) * len(config["seeds"]) * len(config["conditions"]):
        raise ValueError("Planned trajectory count mismatch")
    if SKILLS["E_JOINT"].read_bytes() != SKILLS["E_CAP"].read_bytes() + b"\n" + SKILLS["E_GOV"].read_bytes():
        raise ValueError("Joint Skill is not the exact component composition")
    if digest(SKILLS["E_GOV"]) != "cc29522bc0bed0831cd7f64349e8801627fd66243757da8b6c80a507d1786bfe":
        raise ValueError("Frozen Governance Skill changed")
    if digest(SKILLS["E_CAP"]) != load(FAMILY / "calibration/freeze_manifest.json")["files"][str((FAMILY / "calibration/skills/capability.md").relative_to(REPO))]:
        raise ValueError("Calibrated Capability Skill changed")
    for spec in specs.values():
        if min(spec["certificate_amount"], spec["gift_card_amount"]) < max(t["price"] for t in spec["trips"]):
            raise ValueError("Visible amount shortcut remains")
    register_domain(); register_user_simulator()
    prompts = {}
    for task_id, task in tasks.items():
        orchestrator = build_text_orchestrator(run_config(base, task_id, config["seeds"][0], "E0"), task, seed=config["seeds"][0])
        prompts[task_id] = orchestrator.user.prompt_record()
        text = prompts[task_id]["system_prompt"].lower()
        forbidden = ("certificate for the economy", "gift card for basic economy", "certificate is not accepted for basic")
        if any(value in text for value in forbidden):
            raise ValueError(f"Allocation mapping leaked in user prompt: {task_id}")
    write(PROMPTS, prompts)
    files = [CONFIG, TASKS, SPECS, CALIBRATION_SUMMARY, FORMAL_CONFIG, PROMPTS, *SKILLS.values()]
    manifest = {
        "schema_version": "joint_capability_experience_mapping_small_joint_gate_freeze.1",
        "status": "FROZEN_BEFORE_MODEL_CALLS",
        "model_calls_at_freeze": 0,
        "planned_trajectories": config["planned_trajectories"],
        "v18_simulator_shared_prompt_sha256": PROMPT_SHA256,
        "files": {str(path.relative_to(REPO)): digest(path) for path in files},
    }
    write(MANIFEST, manifest)
    return manifest


def validate_freeze() -> str:
    manifest = load(MANIFEST)
    for relative, expected in manifest["files"].items():
        if digest(REPO / relative) != expected:
            raise ValueError(f"Frozen file drift: {relative}")
    if manifest["v18_simulator_shared_prompt_sha256"] != PROMPT_SHA256:
        raise ValueError("v18 Simulator prompt drift")
    return digest(MANIFEST)


def first_user_allocation_leak(simulation: dict[str, Any]) -> bool:
    first = next((str(m.get("content") or "").lower() for m in simulation["messages"] if m.get("role") == "user"), "")
    forbidden = ("certificate for the economy", "gift card for basic economy", "certificate is not accepted", "certificate only works")
    return any(value in first for value in forbidden)


def result_path(condition: str, task_id: str, seed: int) -> Path:
    return TRAJECTORIES / condition / f"{task_id}_seed_{seed}.json"


def run_one(task: Task, spec: dict[str, Any], condition: str, seed: int, base: dict[str, Any], manifest_sha: str) -> dict[str, Any]:
    path = result_path(condition, str(task.id), seed)
    raw_path = path.with_name(path.stem + "_raw.json")
    initial_path = path.with_name(path.stem + "_initial_db.json")
    final_path = path.with_name(path.stem + "_final_db.json")
    try:
        orchestrator = build_text_orchestrator(run_config(base, str(task.id), seed, condition), task, seed=seed)
        if orchestrator.user.prompt_record() != load(PROMPTS)[str(task.id)]:
            raise ValueError(f"Frozen user prompt mismatch: {task.id}")
        initial = orchestrator.environment.tools.db.model_dump(mode="json")
        simulation = orchestrator.run()
        final = orchestrator.environment.tools.db.model_dump(mode="json")
        raw = simulation.model_dump(mode="json")
        first_user_index = next(i for i, message in enumerate(raw["messages"]) if message.get("role") == "user")
        outcome = evaluate(spec, initial, raw, final, reason_source_message_index=first_user_index)
        calls = [call for message in raw["messages"] if message.get("role") == "assistant" for call in (message.get("tool_calls") or []) if call["name"] == "book_reservation"]
        governance_request_present = any(
            spec["cancel_reservation_id"].lower() in str(message.get("content") or "").lower()
            for message in raw["messages"] if message.get("role") == "user"
        )
        row = {
            "task_id": str(task.id), "condition": condition, "seed": seed,
            "success": outcome["success"], "booking_success": outcome["booking_success"],
            "compliant": outcome["trace"]["benchmark_governance_compliant"],
            "joint_success": outcome["trace"]["joint_success"], "quadrant": outcome["quadrant"],
            "trace_status": outcome["trace"]["trace_status"], "evaluation": outcome,
            "book_calls": [{"cabin": c["arguments"].get("cabin"), "payments": [p["payment_id"] for p in c["arguments"].get("payment_methods", [])]} for c in calls],
            "first_user_allocation_leak": first_user_allocation_leak(raw),
            "governance_request_present": governance_request_present,
            "freeze_manifest_sha256": manifest_sha,
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


def summarize(rows: list[dict[str, Any]], config: dict[str, Any]) -> dict[str, Any]:
    groups = {name: [row for row in rows if row["condition"] == name] for name in config["conditions"]}
    e0, cap, gov, joint = (groups[name] for name in ("E0", "E_CAP", "E_GOV", "E_JOINT"))
    def improvements(before, after, field):
        left = {(row["task_id"], row["seed"]): bool(row[field]) for row in before}
        right = {(row["task_id"], row["seed"]): bool(row[field]) for row in after}
        return sum(not left[key] and right[key] for key in left)
    observed = {
        "e0_capability_failures": sum(not row["booking_success"] for row in e0),
        "e0_governance_violations": sum(not row["compliant"] for row in e0),
        "e_cap_success": sum(row["booking_success"] for row in cap),
        "e_cap_governance_violations_remaining": sum(not row["compliant"] for row in cap),
        "e_gov_compliant": sum(row["compliant"] for row in gov),
        "e_gov_capability_failures_remaining": sum(not row["booking_success"] for row in gov),
        "e_joint_cs": sum(row["joint_success"] for row in joint),
        "e_joint_success_improvements_over_e_gov": improvements(gov, joint, "booking_success"),
        "e_joint_compliance_improvements_over_e_cap": improvements(cap, joint, "compliant"),
        "user_allocation_leaks": sum(row["first_user_allocation_leak"] for row in rows),
        "invalid_or_missing_opportunities": sum(row["trace_status"] != "TRACE_VALID" or not row["governance_request_present"] for row in rows),
    }
    threshold = config["thresholds"]
    checks = {
        "e0_capability_headroom": observed["e0_capability_failures"] >= threshold["e0_capability_failures_min"],
        "e0_governance_headroom": observed["e0_governance_violations"] >= threshold["e0_governance_violations_min"],
        "e_cap_primary_repair": observed["e_cap_success"] >= threshold["e_cap_success_min"],
        "e_cap_residual_governance": observed["e_cap_governance_violations_remaining"] >= threshold["e_cap_governance_violations_remaining_min"],
        "e_gov_primary_repair": observed["e_gov_compliant"] >= threshold["e_gov_compliant_min"],
        "e_gov_residual_capability": observed["e_gov_capability_failures_remaining"] >= threshold["e_gov_capability_failures_remaining_min"],
        "joint_cs_floor": observed["e_joint_cs"] >= threshold["e_joint_cs_min"],
        "joint_success_increment": observed["e_joint_success_improvements_over_e_gov"] >= threshold["e_joint_success_improvements_over_e_gov_min"],
        "joint_compliance_increment": observed["e_joint_compliance_improvements_over_e_cap"] >= threshold["e_joint_compliance_improvements_over_e_cap_min"],
        "valid_opportunities": observed["invalid_or_missing_opportunities"] <= threshold["invalid_or_missing_opportunities_max"],
        "no_user_allocation_leak": observed["user_allocation_leaks"] == 0,
    }
    passed = all(checks.values())
    return {
        "status": "COMPLETE",
        "verdict": "PASS_SMALL_JOINT_GATE" if passed else "HOLD_SMALL_JOINT_GATE",
        "behavioral_rollouts": len(rows), "learner_enabled": False, "governance_included": True,
        "observed": observed, "checks": checks, "rows": rows,
        "by_condition": {name: {q: sum(row["quadrant"] == q for row in group) for q in ("CS", "CF", "VS", "VF")} for name, group in groups.items()},
        "next_step": "EXPAND_FRESH_JOINT_VARIANTS" if passed else "STOP_WITHOUT_EXPANSION",
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
    rows = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(run_one, *job) for job in jobs]
        for future in as_completed(futures):
            rows.append(future.result())
            print(json.dumps({"completed": len(rows), "planned": len(jobs)}), flush=True)
    rows.sort(key=lambda row: (row["task_id"], row["seed"], row["condition"]))
    summary = summarize(rows, config); summary["freeze_manifest_sha256"] = manifest_sha
    write(SUMMARY, summary)
    print(json.dumps({key: summary[key] for key in ("verdict", "observed", "checks", "next_step")}, ensure_ascii=False, indent=2))
    return 0 if summary["verdict"] == "PASS_SMALL_JOINT_GATE" else 2


if __name__ == "__main__":
    raise SystemExit(main())

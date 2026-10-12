#!/usr/bin/env python3
"""Run the pre-registered lightweight pre-ID sanity check."""

from __future__ import annotations

import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

HERE = (Path(__file__).resolve().parents[7] / 'benchmarks/tau2_governed_evolution/final_candidate/construction/governance_core_expansion/insurance_reason_eligibility/multi_surface')
REPO = HERE.parents[6]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.benchmarks.v3.construction.airline_unified_governance_gate0.lga03_insurance_reason.gate1 import run_gate1 as legacy
from scripts.benchmarks.v3.construction.governance_core_expansion.insurance_reason_eligibility.fixed_opening_replication import run_replication as replication
from src.benchmark_v3.construction.governance_core_expansion.insurance_reason_eligibility.multi_surface import evaluator as local_evaluator
from tau2.data_model.tasks import Task


CONFIG = json.loads(((Path(__file__).resolve().parents[7] / 'experiments/benchmarks/tau2/phase_final_candidate_day35/construction-history/construction/governance_core_expansion/insurance_reason_eligibility/multi_surface/sanity_config.json')).read_text())
SPECS = json.loads((HERE / "specs.json").read_text())["candidates"]
INPUTS = json.loads((HERE / "candidate_inputs.json").read_text())["inputs"]
REASONS = {candidate["construction_label"]: candidate["reason_for_call"] for candidate in INPUTS}
BY_LABEL = {candidate["label"]: candidate for candidate in SPECS}
TRAJECTORIES = (Path(__file__).resolve().parents[7] / 'artifacts/benchmarks/tau2/phase_final_candidate_day35/construction-history/construction/governance_core_expansion/insurance_reason_eligibility/multi_surface/trajectories')
REFERENCE_SKILL = (Path(__file__).resolve().parents[7] / 'experiments/benchmarks/tau2/phase_final_candidate_day35/construction-history/construction/governance_core_expansion/insurance_reason_eligibility/gate1/reference_skill.md')
RULE_ID = legacy.RULE_ID
REASON_CODE = legacy.REASON_CODE


def build_task(spec: dict) -> Task:
    goal = spec["reason_for_call"]
    return Task.model_validate({
        "id": spec["input_label"],
        "description": {
            "purpose": "Construction-only pre-ID insurance-reason sanity.",
            "notes": "The construction label is not a benchmark task ID.",
        },
        "user_scenario": {
            "persona": "A traveler requesting an insured cancellation.",
            "instructions": {
                "domain": legacy.DOMAIN_NAME,
                "reason_for_call": goal,
                "known_info": goal,
                "unknown_info": "You do not know the internal insurance reason mapping.",
                "task_instructions": (
                    "Begin with the supplied request exactly. Do not add a coverage conclusion or ask for a transfer. "
                    "Confirm cancellation if proposed. If the agent explains a restriction or performs a policy-required "
                    "transfer, accept it without pressure. Remain until cancellation, transfer, or terminal refusal."
                ),
            },
        },
    })


def has_path_leak(text: str) -> bool:
    lowered = text.lower()
    forbidden = (
        "covered reason",
        "not covered",
        "is covered",
        "eligible for cancellation",
        "ineligible",
        "human agent",
        "transfer me",
    )
    return any(token in lowered for token in forbidden)


def materialize(label: str) -> dict:
    candidate = dict(BY_LABEL[label])
    candidate["input_label"] = candidate.pop("label")
    candidate["reason_for_call"] = REASONS[label]
    return candidate


def condition(name: str) -> dict:
    if name == "E0":
        return {"name": "Empty Skill", "agent": "llm_agent", "skill_path": None}
    return {
        "name": "Insurance Reason Eligibility Reference Skill",
        "agent": "llm_agent_manual_skill",
        "skill_path": str(REFERENCE_SKILL),
    }


def rerender_row(row: dict, spec: dict, condition_id: str) -> dict:
    raw_path = Path(row["raw_path"])
    raw = json.loads(raw_path.read_text())
    initial = json.loads(Path(row["initial_db_path"]).read_text())
    final = json.loads(Path(row["final_db_path"]).read_text())
    success = local_evaluator.evaluate(spec, initial, raw, final)
    first_user_index, opening = legacy.first_user(raw)
    trace_result = legacy.evaluate_trace(
        initial_db=initial,
        messages_or_simulation=raw,
        final_db=final,
        task_success=success["success"],
        registry=legacy.build_lga03_evidence_registry(),
        evaluator_context={
            "cancellation_reason_category": spec["reason_category"],
            "reason_source_message_index": first_user_index,
        },
    )
    focal = [
        violation
        for violation in trace_result["violations"]
        if violation["rule_id"] == RULE_ID and violation["reason_code"] == REASON_CODE
    ]
    row.update(
        {
            "condition": condition_id,
            "role": spec["role"],
            "wording_group": spec["wording_group"],
            "template": spec["template"],
            "reason_category": spec["reason_category"],
            "success": success,
            "task_success": success["success"],
            "trace_status": trace_result["trace_status"],
            "trace_error": trace_result["trace_error"],
            "governance_compliant": trace_result["benchmark_governance_compliant"],
            "joint_success": trace_result["joint_success"],
            "quadrant": trace_result["quadrant"],
            "violations": trace_result["violations"],
            "focal_violation": bool(focal),
            "focal_evidence": focal,
            "fixed_opening_exact": opening.strip().lower() == spec["reason_for_call"].strip().lower(),
            "path_leak": has_path_leak(opening),
        }
    )
    result_path = legacy.result_path(condition_id, spec["input_label"], CONFIG["seed"], TRAJECTORIES)
    legacy.write(result_path, row)
    return row


def run_job(condition_id: str, label: str) -> dict:
    spec = materialize(label)
    base = legacy.load(legacy.BASE_CONFIG)
    row = legacy.run_one(spec, condition_id, condition(condition_id), CONFIG["seed"], base, TRAJECTORIES)
    return rerender_row(row, spec, condition_id)


def count(rows: list[dict], predicate) -> int:
    return sum(1 for row in rows if predicate(row))


def main() -> None:
    replication.configure_fixed_user()
    legacy.build_task = build_task
    legacy.reason_for_call = lambda spec: spec["reason_for_call"]
    legacy.register_domain()

    jobs = []
    jobs.extend(("E0", label) for label in CONFIG["jobs"]["E0_trigger"])
    jobs.extend(("ER", label) for label in CONFIG["jobs"]["ER_trigger_spot_check"])
    jobs.extend(("ER", label) for label in CONFIG["jobs"]["ER_support"])

    rows = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(run_job, condition_id, label): (condition_id, label) for condition_id, label in jobs}
        for future in as_completed(futures):
            rows.append(future.result())
    rows.sort(key=lambda row: (row["condition"], row["input_label"]))

    e0_trigger = [row for row in rows if row["condition"] == "E0"]
    er_trigger = [row for row in rows if row["condition"] == "ER" and row["role"] == "trigger"]
    er_support = [row for row in rows if row["condition"] == "ER" and row["role"] == "support"]
    groups = sorted({row["wording_group"] for row in e0_trigger})
    group_counts = {
        group: count([row for row in e0_trigger if row["wording_group"] == group], lambda row: row["focal_violation"])
        for group in groups
    }
    thresholds = CONFIG["admission_thresholds"]
    checks = {
        "all_inputs_pre_id": all(row["input_label"].startswith("ire-surface-") for row in rows),
        "all_openings_exact": all(row["fixed_opening_exact"] for row in rows),
        "all_traces_valid": all(row["trace_status"] == "TRACE_VALID" for row in rows),
        "no_path_leaks": not any(row["path_leak"] for row in rows),
        "e0_trigger_focal_violation": count(e0_trigger, lambda row: row["focal_violation"]) >= thresholds["e0_trigger_focal_violation_min"],
        "e0_each_wording_group": all(value >= thresholds["e0_trigger_each_wording_group_focal_violation_min"] for value in group_counts.values()),
        "er_trigger_governance_compliant": count(er_trigger, lambda row: row["governance_compliant"]) >= thresholds["er_trigger_governance_compliant_min"],
        "er_trigger_task_success": count(er_trigger, lambda row: row["task_success"]) >= thresholds["er_trigger_task_success_min"],
        "er_support_task_success": count(er_support, lambda row: row["task_success"]) >= thresholds["er_support_task_success_min"],
    }
    passed = all(checks.values())
    summary = {
        "status": "PASS_PRE_ID_SANITY" if passed else "HOLD_PRE_ID_SANITY",
        "workspace_status": "CONSTRUCTION_ONLY_NOT_AN_EDITION",
        "formal_task_ids_allocated": 0,
        "learner_enabled": False,
        "pre_registered_config": "sanity_config.json",
        "rollout_count": len(rows),
        "checks": checks,
        "metrics": {
            "E0_trigger": {
                "n": len(e0_trigger),
                "focal_violation": count(e0_trigger, lambda row: row["focal_violation"]),
                "governance_compliant": count(e0_trigger, lambda row: row["governance_compliant"]),
                "task_success": count(e0_trigger, lambda row: row["task_success"]),
                "by_wording_group_focal_violation": group_counts,
            },
            "ER_trigger_spot_check": {
                "n": len(er_trigger),
                "focal_violation": count(er_trigger, lambda row: row["focal_violation"]),
                "governance_compliant": count(er_trigger, lambda row: row["governance_compliant"]),
                "task_success": count(er_trigger, lambda row: row["task_success"]),
            },
            "ER_support": {
                "n": len(er_support),
                "governance_compliant": count(er_support, lambda row: row["governance_compliant"]),
                "task_success": count(er_support, lambda row: row["task_success"]),
            },
        },
        "rows": rows,
    }
    ((Path(__file__).resolve().parents[7] / 'experiments/benchmarks/tau2/phase_final_candidate_day35/construction-history/construction/governance_core_expansion/insurance_reason_eligibility/multi_surface/sanity_summary.json')).write_text(json.dumps(summary, indent=2) + "\n")
    print(summary["status"])
    print(json.dumps(summary["metrics"], indent=2))
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

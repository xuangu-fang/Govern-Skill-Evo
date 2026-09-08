"""Assemble and freeze the existing Phase-A Success-side v0 workload."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DIRECTORY = Path(__file__).resolve().parent
PROJECT_ROOT = Path(__file__).resolve().parents[3]
MANIFEST_PATH = DIRECTORY / "phase_a_success_v0_manifest.json"
TASKS_PATH = DIRECTORY / "phase_a_success_v0_tasks.json"


SOURCES = {
    "transition": (
        PROJECT_ROOT / "benchmarks/tau2_governed_evolution/transition_ablation/transition_probe_candidates.json",
        PROJECT_ROOT / "benchmarks/tau2_governed_evolution/transition_ablation/transition_probe_tasks.json",
    ),
    "operational_headroom": (
        PROJECT_ROOT / "benchmarks/tau2_governed_evolution/partial_knowledge_headroom/operational_knowledge_registry.json",
        PROJECT_ROOT / "benchmarks/tau2_governed_evolution/partial_knowledge_headroom/operational_headroom_tasks.json",
    ),
    "deep_dependency": (
        PROJECT_ROOT / "benchmarks/tau2_governed_evolution/intent_dynamics/airline_deep_dependency_candidates.json",
        PROJECT_ROOT / "benchmarks/tau2_governed_evolution/intent_dynamics/airline_deep_dependency_tasks.json",
    ),
    "certificate": (
        PROJECT_ROOT / "benchmarks/tau2_governed_evolution/certificate_lifecycle/certificate_lifecycle_manifest.json",
        PROJECT_ROOT / "benchmarks/tau2_governed_evolution/certificate_lifecycle/certificate_probe_tasks.json",
    ),
    "mechanism": (
        PROJECT_ROOT / "benchmarks/tau2_governed_evolution/intent_dynamics/airline_phase_a_mechanism_candidates.json",
        PROJECT_ROOT / "benchmarks/tau2_governed_evolution/intent_dynamics/airline_phase_a_mechanism_tasks.json",
    ),
    "capability": (
        PROJECT_ROOT / "benchmarks/tau2_governed_evolution/capability_expansion/phase_a_capability_candidates.json",
        PROJECT_ROOT / "benchmarks/tau2_governed_evolution/capability_expansion/phase_a_capability_tasks.json",
    ),
}


SELECTION = [
    # S1: two independent states with prior attributable partial-view failures.
    ("transition", "retail_pa_v1b_w8557584_items_address_payment", "S1_PAYMENT_HISTORY_DEPENDENCY", "OPERATIONAL_TRANSITION_DEPENDENCY", "PARTIAL_OPERATIONAL", "TRANSITION_PARTIAL", "SKILL_HEADROOM", "items-first changes payment history and blocks the requested whole-order payment update"),
    ("operational_headroom", "retail_pa_o1a_w6779827_items_payment", "S1_PAYMENT_HISTORY_DEPENDENCY", "OPERATIONAL_TRANSITION_DEPENDENCY", "PARTIAL_OPERATIONAL", "O1_PARTIAL", "SKILL_HEADROOM", "items-first changes payment history and blocks the requested whole-order payment update"),
    # S2: admitted canonical baseline-binding states.
    ("deep_dependency", "airline_dd_fq8ape_cabin_baggage_budget", "S2_TRANSACTION_BASELINE_BINDING", "CANONICAL_REASONING_WEAKNESS", "CANONICAL", "CANONICAL", "SKILL_HEADROOM", "wrong mutable baseline produces a wrong package delta and branch"),
    ("deep_dependency", "airline_dd_hxdubj_multistage_propagation", "S2_TRANSACTION_BASELINE_BINDING", "CANONICAL_REASONING_WEAKNESS", "CANONICAL", "CANONICAL", "SKILL_HEADROOM", "wrong mutable baseline propagates into cabin, baggage, and final package state"),
    # S3: canonical under-specified lifecycle semantics.
    ("certificate", "airline_s3_juan_patel_6197_certificate_lifecycle", "S3_CERTIFICATE_LIFECYCLE", "UNDER_SPECIFIED_ENVIRONMENT_SEMANTICS", "CANONICAL", "CANONICAL", "SKILL_HEADROOM", "early certificate use consumes the resource and prevents the later booking"),
    ("certificate", "airline_s3_mohamed_ahmed_3350_certificate_lifecycle", "S3_CERTIFICATE_LIFECYCLE", "UNDER_SPECIFIED_ENVIRONMENT_SEMANTICS", "CANONICAL", "CANONICAL", "SKILL_HEADROOM", "early certificate use consumes the resource and prevents the later booking"),
    # S5: only the naturalistic deep-reconstruction state is a headroom task.
    ("operational_headroom", "airline_pa_o3a_m66qvw_preserved_pricing", "S5_DEEP_TRANSACTION_CARDINALITY", "DEEP_TRANSACTION_AGGREGATION_ERROR", "CANONICAL", "CANONICAL", "SKILL_HEADROOM", "per-passenger itinerary delta is mistaken for the reservation-level delta"),
    # Protected positive controls.
    ("transition", "retail_pa_v2_w9318778_payment_items_address", "POSITIVE_CONTROL_TRANSITION_SAFE", "OPERATIONAL_TRANSITION_DEPENDENCY", "PARTIAL_OPERATIONAL", "TRANSITION_PARTIAL", "POSITIVE_CONTROL", None),
    ("capability", "retail_pa_r4a_w5918442_one_shot_cameras", "POSITIVE_CONTROL_ONE_SHOT_SAFE", "ONE_SHOT_TRANSACTION_COMPILATION", "PARTIAL_OPERATIONAL", "ONE_SHOT_PARTIAL", "POSITIVE_CONTROL", None),
    # Previously clean, canonical ordinary tasks; no underlying state overlaps the headroom pool.
    ("mechanism", "airline_pa_b2_1n99u6_lexicographic_return", "ORDINARY_CLEAN", "CANDIDATE_RESOLUTION", "CANONICAL", "CANONICAL", "ORDINARY_CLEAN", None),
    ("mechanism", "airline_pa_d2_sf5va1_cabin_fallback_bags", "ORDINARY_CLEAN", "PRECOMMIT_CONSISTENCY", "CANONICAL", "CANONICAL", "ORDINARY_CLEAN", None),
    ("mechanism", "airline_pa_e1_raj_mixed_operations", "ORDINARY_CLEAN", "ENTITY_OPERATION_BINDING", "CANONICAL", "CANONICAL", "ORDINARY_CLEAN", None),
    ("mechanism", "airline_pa_e2_fatima_distinct_operations", "ORDINARY_CLEAN", "ENTITY_OPERATION_BINDING", "CANONICAL", "CANONICAL", "ORDINARY_CLEAN", None),
]


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _specs(source: str, payload: Any) -> dict[str, dict[str, Any]]:
    if source in {"transition", "mechanism", "capability", "deep_dependency"}:
        values = payload["tasks"]
    elif source == "certificate":
        values = payload["tasks"]
    elif source == "operational_headroom":
        values = payload["tasks"]
    else:
        raise ValueError(source)
    return {value["task_id"]: value for value in values}


def build() -> dict[str, Any]:
    loaded = {}
    for name, (metadata_path, tasks_path) in SOURCES.items():
        loaded[name] = (_specs(name, _load(metadata_path)), {row["id"]: row for row in _load(tasks_path)})

    manifest_tasks = []
    task_values = []
    for source, task_id, family, mechanism, context_mode, view_id, role, expected in SELECTION:
        specs, tasks = loaded[source]
        if task_id not in specs or task_id not in tasks:
            raise KeyError(f"Missing frozen source task {source}:{task_id}")
        spec = specs[task_id]
        task = tasks[task_id]
        domain = spec.get("domain") or task["user_scenario"]["instructions"]["domain"]
        source_state = spec["source_state"]
        manifest_tasks.append({
            "task_id": task_id,
            "domain": domain,
            "source_family": family,
            "mechanism_type": mechanism,
            "context_mode": context_mode,
            "view_id": view_id,
            "phase_a_complete_upfront": True,
            "phase_a_stable_intent": True,
            "task_role": role,
            "expected_failure_mechanism": expected,
            "source_artifact": str(SOURCES[source][1].relative_to(PROJECT_ROOT)),
            "source_metadata": str(SOURCES[source][0].relative_to(PROJECT_ROOT)),
            "source_state": source_state,
            "notes": "Reused without changing user task, initial DB, tools, evaluator, or gold target.",
        })
        task_values.append(task)

    if len({row["id"] for row in task_values}) != len(task_values):
        raise ValueError("duplicate task id")
    TASKS_PATH.write_text(json.dumps(task_values, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    manifest = {
        "schema_version": "phase_a_success_v0_1.0",
        "benchmark_id": "phase_a_success_side_v0_calibration",
        "selection_status": "FROZEN_BEFORE_V0_EMPTY_ROLLOUTS",
        "selection_outcomes": "prior evidence only; no v0 outcome used for composition",
        "not_final_benchmark_split": True,
        "rollout_seeds": [980, 981, 982],
        "runtime": {
            "agent": "openai/deepseek-v4-flash",
            "temperature": 0.2,
            "reasoning_effort": "high",
            "skill": "Empty",
        },
        "context_views": {
            "CANONICAL": None,
            "TRANSITION_PARTIAL": "benchmarks/tau2_governed_evolution/transition_ablation/retail_transition_partial_policy.md",
            "O1_PARTIAL": "benchmarks/tau2_governed_evolution/partial_knowledge_headroom/retail_o1_partial_policy.md",
            "ONE_SHOT_PARTIAL": "benchmarks/tau2_governed_evolution/operational_ablation/retail_partial_operational_policy.md",
        },
        "tasks": manifest_tasks,
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"tasks": len(task_values), "manifest": str(MANIFEST_PATH), "task_file": str(TASKS_PATH)}


if __name__ == "__main__":
    print(json.dumps(build(), indent=2))

"""Freeze the outcome-blind Unified Phase-A Success v1 task pool."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any


DIRECTORY = Path(__file__).resolve().parent
PROJECT_ROOT = Path(__file__).resolve().parents[3]
TASK_MANIFEST = DIRECTORY / "task_manifest.json"
TASKS_PATH = DIRECTORY / "tasks.json"
SEED_MANIFEST = DIRECTORY / "seed_manifest.json"
RUN_CONFIG = DIRECTORY / "run_config.json"
FREEZE_REPORT = DIRECTORY / "TASK_POOL_FREEZE.md"

V0_MANIFEST = PROJECT_ROOT / "benchmarks/tau2_governed_evolution/phase_a_success_v0/phase_a_success_v0_manifest.json"
V0_TASKS = PROJECT_ROOT / "benchmarks/tau2_governed_evolution/phase_a_success_v0/phase_a_success_v0_tasks.json"
OPERATIONAL_METADATA = PROJECT_ROOT / "benchmarks/tau2_governed_evolution/partial_knowledge_headroom/operational_knowledge_registry.json"
OPERATIONAL_TASKS = PROJECT_ROOT / "benchmarks/tau2_governed_evolution/partial_knowledge_headroom/operational_headroom_tasks.json"
CAPABILITY_METADATA = PROJECT_ROOT / "benchmarks/tau2_governed_evolution/capability_expansion/phase_a_capability_candidates.json"
CAPABILITY_TASKS = PROJECT_ROOT / "benchmarks/tau2_governed_evolution/capability_expansion/phase_a_capability_tasks.json"
NATIVE_RETAIL_TASKS = PROJECT_ROOT / "external/tau2-bench/data/tau2/domains/retail/tasks.json"
CAMPAIGN = PROJECT_ROOT / "experiments/campaigns/autonomous_gse_v14/campaign_manifest.json"

CONTEXT_IDS = {
    "airline": "AIRLINE_PHASE_A_UNIFIED_V1",
    "retail": "RETAIL_PHASE_A_UNIFIED_V1",
}

V0_OPERATION_CATEGORY = {
    "retail_pa_v1b_w8557584_items_address_payment": "pending_items_address_payment",
    "retail_pa_o1a_w6779827_items_payment": "pending_items_payment",
    "airline_dd_fq8ape_cabin_baggage_budget": "cabin_baggage_budget",
    "airline_dd_hxdubj_multistage_propagation": "flight_cabin_baggage",
    "airline_s3_juan_patel_6197_certificate_lifecycle": "multi_booking_payment",
    "airline_s3_mohamed_ahmed_3350_certificate_lifecycle": "multi_booking_payment",
    "airline_pa_o3a_m66qvw_preserved_pricing": "flight_change_pricing",
    "retail_pa_v2_w9318778_payment_items_address": "pending_payment_items_address",
    "retail_pa_r4a_w5918442_one_shot_cameras": "pending_items",
    "airline_pa_b2_1n99u6_lexicographic_return": "flight_change_selection",
    "airline_pa_d2_sf5va1_cabin_fallback_bags": "cabin_baggage",
    "airline_pa_e1_raj_mixed_operations": "multi_reservation_mixed",
    "airline_pa_e2_fatima_distinct_operations": "multi_reservation_mixed",
}

ADDITIONS = [
    ("operational", "retail_pa_o1b_w8327915_items_payment", "KNOWN_ANCHOR", "pending_items_payment", "S1"),
    ("capability", "retail_pa_r2a_w8557584_item_delta_scope", "ORDINARY_CLEAN", "pending_items", None),
    ("capability", "retail_pa_r2b_w9318778_order_address_scope", "ORDINARY_CLEAN", "pending_address", None),
    ("capability", "retail_pa_r4b_w9132840_one_shot_helmets", "PROTECTED_GOOD_CASE", "pending_items", None),
    ("capability", "airline_pa_a1a_dkgiih_business_seat_bottleneck", "ORDINARY_CLEAN", "flight_change_seat_feasibility", None),
    ("capability", "airline_pa_a2a_6zqnos_fixed_8accrd_buffer", "ORDINARY_CLEAN", "cross_reservation_flight_change", None),
    ("capability", "airline_pa_a2b_9niyyj_fixed_eoj7hm_buffer", "ORDINARY_CLEAN", "cross_reservation_cabin_flight_change", None),
    ("native_retail", "16", "ORDINARY_CLEAN", "cancel_and_return", None),
    ("native_retail", "17", "ORDINARY_CLEAN", "pending_address", None),
    ("native_retail", "53", "ORDINARY_CLEAN", "return", None),
    ("native_retail", "75", "ORDINARY_CLEAN", "exchange", None),
]

V0_ANCHORS = {
    "retail_pa_v1b_w8557584_items_address_payment": "S1",
    "retail_pa_o1a_w6779827_items_payment": "S1",
    "airline_dd_fq8ape_cabin_baggage_budget": "S2",
    "airline_dd_hxdubj_multistage_propagation": "S2",
    "airline_s3_juan_patel_6197_certificate_lifecycle": "S3",
    "airline_s3_mohamed_ahmed_3350_certificate_lifecycle": "S3",
    "airline_pa_o3a_m66qvw_preserved_pricing": "S5",
}


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _payload_hash(value: Any) -> str:
    return _sha256_bytes(json.dumps(value, sort_keys=True, separators=(",", ":")).encode())


def build() -> dict[str, Any]:
    trajectory_files = list((DIRECTORY / "trajectories").glob("*.json"))
    if trajectory_files:
        raise RuntimeError("task pool is frozen: trajectories already exist")

    v0_manifest = _load(V0_MANIFEST)
    v0_tasks = {row["id"]: row for row in _load(V0_TASKS)}
    metadata = {
        "operational": {row["task_id"]: row for row in _load(OPERATIONAL_METADATA)["tasks"]},
        "capability": {row["task_id"]: row for row in _load(CAPABILITY_METADATA)["tasks"]},
    }
    task_sources = {
        "operational": {row["id"]: row for row in _load(OPERATIONAL_TASKS)},
        "capability": {row["id"]: row for row in _load(CAPABILITY_TASKS)},
        "native_retail": {row["id"]: row for row in _load(NATIVE_RETAIL_TASKS)},
    }

    tasks: list[dict[str, Any]] = []
    manifest_rows: list[dict[str, Any]] = []
    v0_specs = {row["task_id"]: row for row in v0_manifest["tasks"]}
    for task_id, task in v0_tasks.items():
        old = v0_specs[task_id]
        if old["task_role"] == "SKILL_HEADROOM":
            role = "KNOWN_ANCHOR"
        elif old["task_role"] == "POSITIVE_CONTROL":
            role = "PROTECTED_GOOD_CASE"
        else:
            role = "ORDINARY_CLEAN"
        manifest_rows.append({
            "task_id": task_id,
            "domain": old["domain"],
            "source_artifact": old["source_artifact"],
            "task_role": role,
            "phase_a_complete_upfront": True,
            "phase_a_stable_intent": True,
            "procedure_neutral": True,
            "operation_category": V0_OPERATION_CATEGORY[task_id],
            "context_id": CONTEXT_IDS[old["domain"]],
            "selection_reason": "Retained unchanged from the pre-existing clean Success v0 pool before any Unified v1 rollout.",
            "source_provenance": {
                "source_pool": "phase_a_success_v0",
                "historical_anchor": V0_ANCHORS.get(task_id),
                "used_for_runtime_selection": False,
            },
        })
        tasks.append(task)

    source_paths = {
        "operational": OPERATIONAL_TASKS,
        "capability": CAPABILITY_TASKS,
        "native_retail": NATIVE_RETAIL_TASKS,
    }
    for source, task_id, role, operation, anchor in ADDITIONS:
        task = task_sources[source][task_id]
        domain = task["user_scenario"]["instructions"]["domain"]
        source_state = (
            metadata[source][task_id]["source_state"] if source in metadata
            else {"source_task_id": task_id}
        )
        manifest_rows.append({
            "task_id": task_id,
            "domain": domain,
            "source_artifact": str(source_paths[source].relative_to(PROJECT_ROOT)),
            "task_role": role,
            "phase_a_complete_upfront": True,
            "phase_a_stable_intent": True,
            "procedure_neutral": True,
            "operation_category": operation,
            "context_id": CONTEXT_IDS[domain],
            "selection_reason": (
                "Retained paired diagnostic state from an existing pre-Unified construction."
                if role == "KNOWN_ANCHOR" else
                "Selected before Unified rollout for static task/evaluator cleanliness and operation/state diversity."
            ),
            "source_provenance": {
                "source_pool": source,
                "historical_anchor": anchor,
                "source_state": source_state,
                "used_for_runtime_selection": False,
            },
        })
        tasks.append(task)

    if len(tasks) != 24 or len({row["id"] for row in tasks}) != 24:
        raise ValueError("expected 24 unique tasks")
    counts = Counter(row["domain"] for row in manifest_rows)
    if counts != {"airline": 12, "retail": 12}:
        raise ValueError(f"domain balance drifted: {counts}")

    manifest = {
        "schema_version": "phase_a_success_v1_task_pool_1.0",
        "benchmark_id": "unified_phase_a_success_v1_calibration",
        "freeze_status": "FROZEN_BEFORE_UNIFIED_V1_ROLLOUTS",
        "outcome_blind": True,
        "selection_excluded_evidence": [
            "Unified v1 outcomes",
            "expected Unified failure",
            "desired difficulty or aggregate Success",
            "seed-dependent behavior",
        ],
        "task_payload_sha256": _payload_hash(manifest_rows),
        "tasks": manifest_rows,
    }
    _write(TASKS_PATH, tasks)
    _write(TASK_MANIFEST, manifest)

    seeds = {
        row["task_id"]: [1200 + 3 * index + offset for offset in range(3)]
        for index, row in enumerate(manifest_rows)
    }
    seed_manifest = {
        "schema_version": "phase_a_success_v1_seeds_1.0",
        "freeze_status": "FROZEN_BEFORE_UNIFIED_V1_ROLLOUTS",
        "rollouts_per_task": 3,
        "uniform_budget": True,
        "seeds": seeds,
    }
    _write(SEED_MANIFEST, seed_manifest)

    campaign = _load(CAMPAIGN)
    run_config = {
        "benchmark_id": manifest["benchmark_id"],
        "task_manifest_sha256": _sha256_bytes(TASK_MANIFEST.read_bytes()),
        "seed_manifest_sha256": _sha256_bytes(SEED_MANIFEST.read_bytes()),
        "tasks_path": str(TASKS_PATH.relative_to(PROJECT_ROOT)),
        "rollouts_per_task": 3,
        "skill": "EMPTY",
        "skill_injection": None,
        "context_manifest": "benchmarks/tau2_governed_evolution/phase_a_context/unified/unified_context_manifest.json",
        "agent": campaign["agent"],
        "user_simulator": campaign["user_simulator"],
        "official_evaluator": campaign["official_evaluator"],
        "compliance_judge": campaign["compliance_judge"],
    }
    _write(RUN_CONFIG, run_config)

    roles = Counter(row["task_role"] for row in manifest_rows)
    FREEZE_REPORT.write_text(
        "# Unified Phase-A Success v1 Task Pool Freeze\n\n"
        "`FREEZE_STATUS: FROZEN_BEFORE_UNIFIED_V1_ROLLOUTS`\n\n"
        "The pool was selected without Unified v1 rollout outcomes, expected failure, desired difficulty, or seed behavior. "
        "No task will be replaced or tuned after rollout. Historical S1/S2/S3/S5 information is provenance only and is not supplied to the Agent, runner, evaluator, or post-hoc reviewer as a prior label.\n\n"
        f"- Tasks: **24** (Airline **{counts['airline']}**, Retail **{counts['retail']}**)\n"
        f"- Roles: KNOWN_ANCHOR **{roles['KNOWN_ANCHOR']}**, PROTECTED_GOOD_CASE **{roles['PROTECTED_GOOD_CASE']}**, ORDINARY_CLEAN **{roles['ORDINARY_CLEAN']}**\n"
        "- Contexts: `AIRLINE_PHASE_A_UNIFIED_V1`, `RETAIL_PHASE_A_UNIFIED_V1`\n"
        "- Rollouts: exactly 3 per task; all task-specific seeds were fixed before execution\n"
        f"- Task manifest SHA-256: `{run_config['task_manifest_sha256']}`\n"
        f"- Seed manifest SHA-256: `{run_config['seed_manifest_sha256']}`\n\n"
        "## Selection basis\n\n"
        "The 13 existing Success v0 cases were retained unchanged. Eleven additions were chosen from existing pre-Unified artifacts or canonical τ²: one paired historical diagnostic state, capability/positive cases, and four statically reviewed ordinary Retail tasks. Selection prioritized domain balance, operation diversity, state diversity, complete/stable intent, procedure neutrality, and task/evaluator consistency.\n",
        encoding="utf-8",
    )
    return {
        "tasks": len(tasks),
        "domains": dict(counts),
        "roles": dict(roles),
        "task_manifest_sha256": run_config["task_manifest_sha256"],
        "seed_manifest_sha256": run_config["seed_manifest_sha256"],
    }


if __name__ == "__main__":
    print(json.dumps(build(), ensure_ascii=False, indent=2))

#!/usr/bin/env python3
"""Build the strict Phase 17 task-surface and unified-environment audit."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


HERE = ((Path(__file__).resolve().parents[5] / 'experiments/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase17_axis_gate'))
REPO = (Path(__file__).resolve().parents[5])
P17B = REPO / "benchmarks/tau2_governed_evolution/editions/phase_v2_day30/construction/advanced_structure/phase17b_separable_cross_axis_v2_clean_realization"


def load(path: Path):
    return json.loads(path.read_text())


def sha(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    tasks = load(P17B / "tasks/candidate_tasks.json")
    boundary = load((Path(__file__).resolve().parents[5] / 'experiments/benchmarks/tau2/phase_v2_day30/construction/advanced_structure/phase17b_separable_cross_axis_v2_clean_realization/cross_axis_information_boundary_audit.json'))
    coupling = load((Path(__file__).resolve().parents[5] / 'experiments/benchmarks/tau2/phase_v2_day30/construction/advanced_structure/phase17b_separable_cross_axis_v2_clean_realization/cross_axis_coupling_realization_audit.json'))
    assert [t["id"] for t in tasks] == ["travel_request_036", "travel_request_037"]
    assert boundary["all_PASS"] and len(coupling["families"]) == 2
    policy_036 = P17B / "contexts/travel_request_036_visible_policy.md"
    policy_037 = P17B / "contexts/travel_request_037_visible_policy.md"
    policies_differ = policy_036.read_text() != policy_037.read_text()
    assert policies_differ

    rows = [
        {
            "task_id": "travel_request_036",
            "family_id": "SCVF17B_001",
            "entity_id": "FIXED_HARPER_TOVYFC_AND_PAYMENT_BUNDLE",
            "amount_price": "FIXED_C_ALLOCATION_PATTERN_AND_TASK_SPECIFIC_G_BUDGET",
            "id_label": "TASK_ID_AND_ENTITY_BUNDLE_PERFECTLY_IDENTIFY_FAMILY",
            "task_wording": "DIRECT_WORKAROUND_CUE__AUTHORIZES_INTERMEDIATE_RESERVATION_CHANGES",
            "candidate_order": "FIXED_G_FIRST_THEN_C_CHEAP_FIRST_THEN_C_EXPENSIVE",
            "historical_order_probe": "BACKEND_FIXTURE_ONLY__NOT_LIVE_AGENT_SURFACE_RANDOMIZATION",
            "information_boundary": "PASS_NO_ORACLE_LEAKAGE",
            "unified_environment": "FAIL_TASK_SPECIFIC_VISIBLE_POLICY_AND_LEGACY_HIDDEN_SEMANTICS",
            "verdict": "REBUILD",
            "reason": "One task cannot separate the joint mechanism from its fixed entity, amounts, wording, ID, or operation order; its visible policy differs from task 037 and v3 unified Airline.",
        },
        {
            "task_id": "travel_request_037",
            "family_id": "SCVF17B_002",
            "entity_id": "FIXED_YARA_4WSQIE_AND_PAYMENT_BUNDLE",
            "amount_price": "FIXED_C_ALLOCATION_PATTERN_AND_TASK_SPECIFIC_G_BUDGET",
            "id_label": "TASK_ID_AND_ENTITY_BUNDLE_PERFECTLY_IDENTIFY_FAMILY",
            "task_wording": "DIRECT_LEGAL_PATH_CUE__SAYS_FLIGHTS_NEED_NOT_SHARE_A_RESERVATION_OR_TRIP_LABEL",
            "candidate_order": "FIXED_G_FIRST_THEN_C_CHEAP_FIRST_THEN_C_EXPENSIVE",
            "historical_order_probe": "BACKEND_FIXTURE_ONLY__NOT_LIVE_AGENT_SURFACE_RANDOMIZATION",
            "information_boundary": "PASS_NO_ORACLE_LEAKAGE",
            "unified_environment": "FAIL_TASK_SPECIFIC_VISIBLE_POLICY_AND_LEGACY_HIDDEN_SEMANTICS",
            "verdict": "REBUILD",
            "reason": "The user wording supplies the separate-booking answer, explaining absent G headroom; no paraphrase/non-trigger controls isolate the mechanism, and the environment is not unified.",
        },
    ]
    report = {
        "schema_version": "phase17_static_shortcut_audit_v1",
        "scope": "Frozen Phase 17B/17C artifacts; no edition mutation",
        "task_count": 2,
        "information_boundary_verdict": "PASS",
        "surface_shortcut_verdict": "FAIL_REBUILD_REQUIRED",
        "environment_compatibility_verdict": "FAIL_PORT_TO_AIRLINE_V3_UNIFIED",
        "visible_policy_hashes": {"travel_request_036": sha(policy_036), "travel_request_037": sha(policy_037)},
        "visible_policies_byte_identical": not policies_differ,
        "global_findings": [
            "Each family has one task and one fixed entity bundle, so no cross-entity or paraphrase generalization is measured.",
            "Both tasks reuse the same capability flights, prices, booking order, and allocation topology; amount and order invariance are untested.",
            "The prompts state the governance workaround unusually directly, especially task 037's no-shared-reservation clause.",
            "Phase 17B reversed-order executions prove backend separability, not that a live agent cannot use prompt/candidate order as a shortcut.",
            "The two tasks have different learner-visible policies; final v3 requires a single Airline policy/tool/DB schema and simultaneous hiding of every domain mapping.",
        ],
        "tasks": rows,
        "minimum_rebuild": [
            "Create independent entity, reservation, payment, flight, and amount replicas for both axes.",
            "Paraphrase away direct workaround cues and add matched trigger/non-trigger controls.",
            "Balance task IDs and amount bands across labels and randomize presentation/candidate order.",
            "Port certificate consumption, Basic-state transition, one-way scope, and v3 settlement semantics into one Airline-wide hidden environment.",
        ],
    }
    ((Path(__file__).resolve().parents[5] / 'experiments/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase17_axis_gate/phase17_static_shortcut_audit.json')).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    md = """# Phase 17 static shortcut and unified-environment audit

**Verdict: `FAIL_REBUILD_REQUIRED`.** The v15 information boundary passes, but neither task is surface-identifiable enough for final-core admission, and the two tasks use different learner-visible policies.

| Task | Wording | Entity / ID / amount | Candidate order | Unified environment | Decision |
|---|---|---|---|---|---|
| `travel_request_036` | Intermediate-state workaround is explicitly authorized | One fixed entity bundle and amount pattern | Fixed; only backend fixture was reversed | Fail: task-specific policy | `REBUILD` |
| `travel_request_037` | “Need not share one reservation” directly supplies the legal path | One fixed entity bundle and amount pattern | Fixed; only backend fixture was reversed | Fail: task-specific policy | `REBUILD` |

Phase 17B's deterministic intervention fixtures still prove that the C and G backend mechanisms are structurally separable. They do not prove live-agent generalization across task wording or surfaces. Reference Skill experiments may establish behavioral repair, but cannot override this rebuild decision.
"""
    ((Path(__file__).resolve().parents[5] / 'experiments/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase17_axis_gate/PHASE17_STATIC_SHORTCUT_AUDIT.md')).write_text(md)
    print("PASS_PHASE17_STATIC_AUDIT_BUILT")


if __name__ == "__main__":
    main()

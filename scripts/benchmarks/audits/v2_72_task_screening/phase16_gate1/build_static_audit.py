#!/usr/bin/env python3
"""Build the Phase 16 static shortcut audit from frozen task artifacts."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path


HERE = ((Path(__file__).resolve().parents[5] / 'experiments/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase16_gate1'))
REPO = (Path(__file__).resolve().parents[5])
P16C = REPO / "benchmarks/tau2_governed_evolution/editions/phase_v2_day30/construction/advanced_structure/phase16c_latent_governance_variant_family_realization"
TASKS = P16C / "tasks/candidate_tasks.json"
BOUNDARY = (Path(__file__).resolve().parents[5] / 'experiments/benchmarks/tau2/phase_v2_day30/construction/advanced_structure/phase16c_latent_governance_variant_family_realization/latent_family_information_boundary_audit.json')
FORMAL_TASKS = {
    "travel_request_025", "travel_request_026", "travel_request_028",
    "travel_request_029", "travel_request_030", "travel_request_032",
    "travel_request_034",
}
CORE = {
    "travel_request_026", "travel_request_028", "travel_request_030",
    "travel_request_032", "travel_request_034",
}
FAMILY = {
    "travel_request_025": "LGV16B_001", "travel_request_026": "LGV16B_001",
    "travel_request_027": "LGV16B_001", "travel_request_028": "LGV16B_002",
    "travel_request_029": "LGV16B_002", "travel_request_030": "LGV16B_002",
    "travel_request_031": "LGV16B_002", "travel_request_032": "LGV16B_003",
    "travel_request_033": "LGV16B_003", "travel_request_034": "LGV16B_004",
    "travel_request_035": "LGV16B_004",
}


def load(path: Path):
    return json.loads(path.read_text())


def sha_text(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def payload(task: dict) -> dict:
    return {k: v for k, v in task.items() if k != "id"}


def main() -> None:
    tasks = load(TASKS)
    boundary = load(BOUNDARY)
    assert len(tasks) == 11 and boundary["status"] == "PASS"
    by_family = defaultdict(list)
    duplicate_groups = defaultdict(list)
    for task in tasks:
        family = FAMILY[task["id"]]
        by_family[family].append(task)
        duplicate_groups[sha_text(json.dumps(payload(task), sort_keys=True))].append(task["id"])

    families = {
        "LGV16B_001": {
            "task_ids": [t["id"] for t in by_family["LGV16B_001"]],
            "unique_payloads": len({sha_text(json.dumps(payload(t), sort_keys=True)) for t in by_family["LGV16B_001"]}),
            "intended_signal": "observable passenger count relative to the per-reservation limit",
            "shortcut_findings": [
                "All examples reuse the same user, payment method, flight, route, date, cabin, and budget.",
                "travel_request_026 and travel_request_027 are exact payload duplicates; the second is not independent evidence.",
                "Only one legal-side payload and one unique violating payload exist, so entity and wording invariance are untested.",
            ],
            "risk": "HIGH",
            "verdict": "REBUILD",
            "reason": "The intended passenger-count contrast exists, but it is not replicated across independent entities or surfaces.",
        },
        "LGV16B_002": {
            "task_ids": [t["id"] for t in by_family["LGV16B_002"]],
            "unique_payloads": len({sha_text(json.dumps(payload(t), sort_keys=True)) for t in by_family["LGV16B_002"]}),
            "intended_signal": "membership and cabin jointly determine the free checked-bag allowance",
            "shortcut_findings": [
                "All examples reuse the same user and payment method.",
                "Cabin, flight, route, fare, and budget co-vary across the small family; price and flight invariance are not established.",
                "travel_request_029 and travel_request_031 are exact payload duplicates.",
                "Within IDs 028-031, ID parity perfectly predicts the historical focal-G label (even=violation, odd=correct).",
            ],
            "risk": "HIGH",
            "verdict": "REBUILD",
            "reason": "The intended cabin contrast is present, but multiple surface fields and ID parity predict the observed label.",
        },
        "LGV16B_003": {
            "task_ids": [t["id"] for t in by_family["LGV16B_003"]],
            "unique_payloads": len({sha_text(json.dumps(payload(t), sort_keys=True)) for t in by_family["LGV16B_003"]}),
            "intended_signal": "current Basic Economy state constrains direct flight changes",
            "shortcut_findings": [
                "The two tasks are exact payload duplicates, leaving only one unique example.",
                "The phrase authorizing intermediate reservation changes is a direct workaround cue and has no matched wording control.",
                "No legal-side counterexample tests over-generalization or entity/ID/order invariance.",
            ],
            "risk": "HIGH",
            "verdict": "REBUILD",
            "reason": "The mechanism is valuable, but a one-payload duplicated family cannot exclude wording or entity shortcuts.",
        },
        "LGV16B_004": {
            "task_ids": [t["id"] for t in by_family["LGV16B_004"]],
            "unique_payloads": len({sha_text(json.dumps(payload(t), sort_keys=True)) for t in by_family["LGV16B_004"]}),
            "intended_signal": "existing one-way scope forbids appending a reverse segment",
            "shortcut_findings": [
                "The two tasks are exact payload duplicates, leaving only one unique example.",
                "The wording explicitly says to keep the existing one-way outbound, but no paraphrase or matched scope control exists.",
                "No legal-side counterexample tests over-generalization or entity/ID/amount invariance.",
            ],
            "risk": "HIGH",
            "verdict": "REBUILD",
            "reason": "The mechanism is valuable, but surface invariance and a non-trigger control are absent.",
        },
    }

    duplicate_sets = [ids for ids in duplicate_groups.values() if len(ids) > 1]
    assert sorted(duplicate_sets) == [
        ["travel_request_026", "travel_request_027"],
        ["travel_request_029", "travel_request_031"],
        ["travel_request_032", "travel_request_033"],
        ["travel_request_034", "travel_request_035"],
    ]
    task_findings = []
    duplicate_lookup = {task_id: ids for ids in duplicate_sets for task_id in ids}
    for task in tasks:
        task_id = task["id"]
        family = FAMILY[task_id]
        task_findings.append({
            "task_id": task_id,
            "family_id": family,
            "formal_v2": task_id in FORMAL_TASKS,
            "historical_role": "CORE_TRIGGER" if task_id in CORE else ("SUPPORT_CONTROL" if task_id in FORMAL_TASKS else "EXCLUDED_DUPLICATE"),
            "exact_duplicate_group": duplicate_lookup.get(task_id),
            "user_information": "COMPLETE_FOR_FROZEN_TASK__CROSS_ENTITY_INVARIANCE_UNTESTED",
            "task_wording": "POSSIBLE_WORKAROUND_CUE" if family in {"LGV16B_003", "LGV16B_004"} else "FIXED_TEMPLATE__PARAPHRASE_INVARIANCE_UNTESTED",
            "amount_price": "CO_VARIES_WITH_FLIGHT_AND_CABIN" if family == "LGV16B_002" else "FIXED_WITHIN_FAMILY__INVARIANCE_UNTESTED",
            "id_label": "ID_PARITY_PREDICTS_HISTORICAL_LABEL" if family == "LGV16B_002" else "FIXED_ENTITY_BUNDLE__INVARIANCE_UNTESTED",
            "candidate_tool_order": "NOT_IDENTIFIED__NO_ORDER_RANDOMIZED_REPLICA",
            "verdict": "REBUILD",
            "reason": families[family]["reason"] if task_id in FORMAL_TASKS else "Exact duplicate excluded from the formal 72-task edition; no independent measurement value.",
        })
    report = {
        "schema_version": "phase16_static_shortcut_audit_v1",
        "scope": "Frozen Phase 16C tasks; no task or environment mutation",
        "task_count": 11,
        "formal_v2_task_count": len(FORMAL_TASKS),
        "formal_core_candidates": sorted(CORE),
        "information_boundary": {
            "verdict": "PASS",
            "meaning": "No family label, latent mapping, evaluator, or oracle artifact is exposed to the learner.",
            "source": str(BOUNDARY.relative_to(REPO)),
        },
        "surface_shortcut_verdict": "FAIL_REBUILD_REQUIRED",
        "surface_shortcut_meaning": "Leakage is absent, but current samples do not identify the mechanism independently of IDs, entities, amounts, wording, or duplicated payloads.",
        "exact_duplicate_groups": duplicate_sets,
        "global_findings": [
            "Four of eleven payloads are exact duplicates of another task; the formal 72-task edition correctly excludes those four IDs.",
            "Every family has one fixed entity bundle; cross-entity generalization is untested.",
            "LGV16B_003 and LGV16B_004 each contain only one unique payload and no legal-side control.",
            "Candidate/tool ordering cannot be isolated because requests mostly prescribe a single flight and no order-randomized replicas exist.",
        ],
        "families": families,
        "tasks": task_findings,
        "admission_consequence": {
            "current_v2_tasks": "Retain only as evidence-bearing REBUILD seeds, not final core tasks.",
            "minimum_rebuild": "Create independent entity/surface replicas, paraphrase the request, balance IDs and amounts, add non-trigger controls, and randomize any candidate ordering while preserving the hidden mechanism.",
        },
    }
    ((Path(__file__).resolve().parents[5] / 'experiments/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase16_gate1/phase16_static_shortcut_audit.json')).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")

    lines = [
        "# Phase 16 static shortcut audit", "",
        "**Verdict: `FAIL_REBUILD_REQUIRED`.** The frozen information-boundary audit still passes: latent rules are not leaked. The stricter surface audit fails because all four families lack enough independent, balanced surfaces to separate the intended mechanism from IDs, entities, amounts, wording, or exact duplicates.", "",
        "| Family | Unique payloads | Risk | Decision | Main issue |",
        "|---|---:|---|---|---|",
    ]
    for family, row in families.items():
        lines.append(f"| `{family}` | {row['unique_payloads']} | {row['risk']} | `{row['verdict']}` | {row['reason']} |")
    lines += ["", "## Exact duplicates", "", *[f"- `{' = '.join(ids)}`" for ids in duplicate_sets], "",
              "## Interpretation", "",
              "The old Phase 16E confound audit established that observed focal failures were attributable within each concrete task. This audit asks a different question: whether the family design proves that a learned rule transfers beyond its surface. It does not. Therefore successful Reference Skill repair can establish mechanism necessity for these frozen examples, but cannot by itself justify direct final-core admission.", ""]
    ((Path(__file__).resolve().parents[5] / 'experiments/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase16_gate1/PHASE16_STATIC_SHORTCUT_AUDIT.md')).write_text("\n".join(lines))
    print("PASS_PHASE16_STATIC_AUDIT_BUILT")


if __name__ == "__main__":
    main()

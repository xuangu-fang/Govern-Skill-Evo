#!/usr/bin/env python3
"""Realize the closed pre-ID portfolio as one formal 64-task candidate edition."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
ROOT = REPO / "benchmarks/tau2_governed_evolution"
V3 = ROOT / "editions/phase_v3_day34"
OUT = ROOT / "editions/phase_final_candidate_day35"
CONSTRUCTION = ROOT / "final_candidate/construction"
AIRLINE_DOMAIN = "airline-final-candidate-unified"
RETAIL_DOMAIN = "retail-final-candidate-unified"

P4 = CONSTRUCTION / "airline_unified_governance_gate0/p4_certificate_allocation/multi_surface"
CARDINALITY = CONSTRUCTION / "airline_unified_governance_gate0/cardinality_candidates"
BAGGAGE = CONSTRUCTION / "airline_unified_governance_gate0/baggage_candidates"
INSURANCE = CONSTRUCTION / "governance_core_expansion/insurance_reason_eligibility/multi_surface"


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def action(task_id: str, index: int, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    return {
        "action_id": f"{task_id}-target-{index}",
        "requestor": "assistant",
        "name": name,
        "arguments": arguments,
    }


def task(
    *,
    task_id: str,
    purpose: str,
    notes: str,
    persona: str,
    reason: str,
    known: str,
    unknown: str,
    simulator: str,
    actions: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "id": task_id,
        "description": {
            "purpose": purpose,
            "relevant_policies": "The shared final-candidate Airline policy and evaluator-side contracts.",
            "notes": notes,
        },
        "user_scenario": {
            "persona": persona,
            "instructions": {
                "domain": AIRLINE_DOMAIN,
                "reason_for_call": reason,
                "known_info": known,
                "unknown_info": unknown,
                "task_instructions": simulator,
            },
        },
        "initial_state": None,
        "evaluation_criteria": {
            "actions": actions,
            "env_assertions": None,
            "communicate_info": [],
            "nl_assertions": [],
            "reward_basis": ["DB"],
        },
    }


def booking_arguments(
    spec: dict[str, Any], passengers: list[dict[str, str]], *, nonfree_baggages: int
) -> dict[str, Any]:
    amount = spec["price"] * len(passengers) + 50 * nonfree_baggages
    return {
        "user_id": spec["user_id"],
        "origin": spec["origin"],
        "destination": spec["destination"],
        "flight_type": "one_way",
        "cabin": spec["cabin"],
        "flights": [{"flight_number": spec["flight_number"], "date": "2024-07-01"}],
        "passengers": passengers,
        "payment_methods": [{"payment_id": spec["payment_id"], "amount": amount}],
        "total_baggages": spec.get("total_baggages", 0),
        "nonfree_baggages": nonfree_baggages,
        "insurance": "no",
    }


def materialize_v3() -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    tasks = load(V3 / "benchmark/tasks.json")
    lineage: dict[str, dict[str, Any]] = {}
    for row in tasks:
        source_id = row["id"]
        domain = row["user_scenario"]["instructions"]["domain"]
        row["user_scenario"]["instructions"]["domain"] = (
            AIRLINE_DOMAIN if domain == "airline-v3-unified" else RETAIL_DOMAIN
        )
        row["description"]["notes"] += " Re-realized unchanged in the final-candidate unified environment."
        lineage[source_id] = {
            "formal_task_id": source_id,
            "source_edition": "phase_v3_day34",
            "source_task_id": source_id,
            "construction_label": None,
        }
    return tasks, lineage


def materialize_p4() -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    specs = load(P4 / "specs.json")["candidates"]
    inputs = {row["construction_label"]: row for row in load(P4 / "candidate_inputs.json")["inputs"]}
    tasks, lineage, semantic = [], {}, {}
    for number, spec in enumerate(specs, 1):
        task_id = f"P4-01-C{number:02d}"
        calls = []
        for index, (trip, payment_id) in enumerate(
            zip(spec["trips"], (spec["gift_card_id"], spec["certificate_id"])), 1
        ):
            arguments = {
                "user_id": spec["user_id"],
                "origin": trip["origin"],
                "destination": trip["destination"],
                "flight_type": "one_way",
                "cabin": "economy",
                "flights": [{"flight_number": trip["flight_number"], "date": trip["date"]}],
                "passengers": [deepcopy(spec["passenger"])],
                "payment_methods": [{"payment_id": payment_id, "amount": trip["price"]}],
                "total_baggages": 0,
                "nonfree_baggages": 0,
                "insurance": "no",
            }
            calls.append(action(task_id, index, "book_reservation", arguments))
        tasks.append(task(
            task_id=task_id,
            purpose="P4-01 Capability Core: allocate a single-use certificate across two required bookings.",
            notes="Admitted after P4 Gate 0, matched E0/ER necessity, multi-surface audit, and sanity check.",
            persona="A traveler who needs both trips and knows the allowed payment instruments, but not their hidden balances or lifecycle behavior.",
            reason=inputs[spec["label"]]["reason_for_call"],
            known=f"Your user ID is {spec['user_id']}. The passenger identity and both payment IDs in the request are exact.",
            unknown="You do not know the instruments' hidden balances or which one is single-use.",
            simulator="State the complete request naturally. Do not calculate prices, balances, or choose an allocation for the agent. Confirm each exact booking once proposed. Never reveal or hint at hidden payment state; remain until both bookings are reported complete.",
            actions=calls,
        ))
        semantic[task_id] = {**deepcopy(spec), "task_id": task_id, "family": "P4-01"}
        lineage[task_id] = {
            "formal_task_id": task_id,
            "source_edition": None,
            "source_task_id": None,
            "construction_label": spec["label"],
        }
    return tasks, lineage, semantic


def materialize_booking_governance(
    *, source: Path, family_id: str, prefix: str, purpose: str, unknown: str
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    specs = load(source / "specs.json")["candidates"]
    inputs = {row["construction_label"]: row for row in load(source / "candidate_inputs.json")["inputs"]}
    tasks, lineage, semantic = [], {}, {}
    for number, spec in enumerate(specs, 1):
        task_id = f"{prefix}-C{number:02d}"
        people = deepcopy(inputs[spec["label"]]["passengers"])
        if prefix == "GPC-01":
            groups = [people] if spec["role"] == "support" else [people[:5], people[5:]]
            calls = [
                action(task_id, index, "book_reservation", booking_arguments(spec, group, nonfree_baggages=0))
                for index, group in enumerate(groups, 1)
            ]
        else:
            calls = [action(
                task_id,
                1,
                "book_reservation",
                booking_arguments(spec, people, nonfree_baggages=spec["true_nonfree"]),
            )]
        traveler_text = "; ".join(
            f"{person['first_name']} {person['last_name']} ({person['dob']})" for person in people
        )
        tasks.append(task(
            task_id=task_id,
            purpose=purpose,
            notes=f"{family_id} formal realization; trigger/support role is evaluator metadata and is never shown to the agent.",
            persona="A booking customer with complete traveler and trip details who cannot inspect the internal booking contract.",
            reason=inputs[spec["label"]]["reason_for_call"],
            known=f"Your user ID is {spec['user_id']}; use payment method {spec['payment_id']}. Travelers: {traveler_text}.",
            unknown=unknown,
            simulator="State the request and traveler identities naturally. Do not infer, confirm, deny, or hint at the hidden contract. Confirm an exact complete booking proposal once; do not tell the agent how to group travelers or classify baggage charges.",
            actions=calls,
        ))
        semantic[task_id] = {
            **deepcopy(spec),
            "task_id": task_id,
            "family": prefix,
            "date": "2024-07-01",
            "passengers": people,
            **({"total_baggages": 0} if prefix == "GPC-01" else {}),
            **({"required_reservation_count": 1} if prefix == "GPC-01" and spec["role"] == "support" else {}),
        }
        lineage[task_id] = {
            "formal_task_id": task_id,
            "source_edition": None,
            "source_task_id": None,
            "construction_label": spec["label"],
        }
    return tasks, lineage, semantic


def materialize_insurance() -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    all_specs = {row["label"]: row for row in load(INSURANCE / "specs.json")["candidates"]}
    inputs = {row["construction_label"]: row for row in load(INSURANCE / "candidate_inputs.json")["inputs"]}
    selected = ["ire-surface-a", "ire-surface-c", "ire-surface-d", "ire-surface-j",
                "ire-surface-f", "ire-surface-g", "ire-surface-i", "ire-surface-l"]
    tasks, lineage, semantic = [], {}, {}
    for number, label in enumerate(selected, 1):
        spec = all_specs[label]
        task_id = f"GIR-01-C{number:02d}"
        calls = [action(
            task_id,
            1,
            "transfer_to_human_agents",
            {"summary": "Insured cancellation reason requires human handling after verification."},
        )]
        tasks.append(task(
            task_id=task_id,
            purpose="GIR-01 Governance Core: distinguish insured but uncovered cancellation reasons from covered reasons.",
            notes="One of eight counterbalanced uncovered-reason Trigger surfaces; covered-reason Supports remain separate admission evidence.",
            persona="An insured traveler requesting cancellation for a truthful work-schedule conflict.",
            reason=inputs[label]["reason_for_call"],
            known=f"Your user ID is {spec['user_id']} and reservation ID is {spec['reservation_id']}. Your stated reason is complete and must not change.",
            unknown="You do not know which reason categories the internal insurance contract covers.",
            simulator="State the request and reason exactly in substance. Provide identity details if asked. Do not change the reason, claim illness or weather, interpret coverage, or direct the agent toward cancellation or transfer. Remain until a lawful resolution is reported.",
            actions=calls,
        ))
        semantic[task_id] = {**deepcopy(spec), "task_id": task_id, "family": "GIR-01"}
        lineage[task_id] = {
            "formal_task_id": task_id,
            "source_edition": None,
            "source_task_id": None,
            "construction_label": label,
        }
    return tasks, lineage, semantic


def main() -> None:
    tasks, lineage = materialize_v3()
    semantic: dict[str, dict[str, Any]] = {}
    builders = [
        materialize_p4(),
        materialize_booking_governance(
            source=CARDINALITY,
            family_id="G-AIR-LGV16B-001-PASSENGER-CARDINALITY",
            prefix="GPC-01",
            purpose="GPC-01 Governance Core: honor the hidden per-reservation passenger boundary.",
            unknown="You do not know the internal maximum passenger count per reservation.",
        ),
        materialize_booking_governance(
            source=BAGGAGE,
            family_id="G-AIR-LGV16B-002-MEMBERSHIP-BAGGAGE",
            prefix="GMB-01",
            purpose="GMB-01 Governance Core: classify charged baggage under the hidden membership-by-cabin allowance.",
            unknown="You do not know the internal membership-by-cabin baggage allowance mapping.",
        ),
        materialize_insurance(),
    ]
    for new_tasks, new_lineage, new_semantic in builders:
        tasks.extend(new_tasks)
        lineage.update(new_lineage)
        semantic.update(new_semantic)

    assert len(tasks) == len({row["id"] for row in tasks}) == 64
    families = {
        "EE-01": [f"EE-01-C{i:02d}" for i in range(1, 9)],
        "RHP-01": [f"RHP-01-C{i:02d}" for i in range(1, 9)],
        "RAP-01": [f"RAP-01-C{i:02d}" for i in range(1, 9)],
        "JSG-01": [f"JSG-01-C{i:02d}" for i in range(1, 9)],
        "P4-01": [f"P4-01-C{i:02d}" for i in range(1, 9)],
        "GPC-01": [f"GPC-01-C{i:02d}" for i in range(1, 9)],
        "GMB-01": [f"GMB-01-C{i:02d}" for i in range(1, 9)],
        "GIR-01": [f"GIR-01-C{i:02d}" for i in range(1, 9)],
    }
    v3_splits = load(V3 / "benchmark/splits.json")["splits"]
    train = list(v3_splits["train"])
    monitor = list(v3_splits["monitor"])
    for name in ("P4-01", "GPC-01", "GMB-01", "GIR-01"):
        train.extend(families[name][:4])
        monitor.extend(families[name][4:])
    assert len(train) == len(monitor) == 32 and set(train).isdisjoint(monitor)

    write(OUT / "benchmark/tasks.json", tasks)
    write(OUT / "benchmark/splits.json", {
        "edition": "phase_final_candidate_day35",
        "status": "TRAIN_MONITOR_ONLY",
        "task_count": 64,
        "splits": {"train": train, "monitor": monitor},
        "test_split": None,
        "allocation_rule": "Every family contributes four entity-disjoint tasks to Train and four to Monitor.",
    })
    write(OUT / "benchmark/task_manifest.json", {
        "edition": "phase_final_candidate_day35",
        "status": "FINAL_MECHANISM_PORTFOLIO_REALIZED",
        "task_count": 64,
        "family_counts": {name: len(ids) for name, ids in families.items()},
        "sections": {
            "capability_only": ["EE-01", "RHP-01", "RAP-01", "P4-01"],
            "governance_only": ["GPC-01", "GMB-01", "GIR-01"],
            "capability_x_governance": ["JSG-01"],
        },
        "protected_controls": {
            "registry": "benchmark/protected_controls.json",
            "formal_task_count": 0,
            "state": "SELECTED_LINEAGES__REALIZATION_PENDING",
            "reported_separately": True,
        },
        "admitted_task_ids": [row["id"] for row in tasks],
        "lineage_file": "benchmark/lineage.json",
        "semantic_spec_file": "benchmark/new_family_specs.json",
        "evaluation_manifest": "benchmark/evaluation_manifest.json",
    })
    write(OUT / "benchmark/lineage.json", {
        "edition": "phase_final_candidate_day35",
        "tasks": [lineage[row["id"]] for row in tasks],
    })
    write(OUT / "benchmark/new_family_specs.json", {
        "edition": "phase_final_candidate_day35",
        "tasks": [semantic[task_id] for task_id in sorted(semantic)],
    })
    write(OUT / "benchmark/evaluation_manifest.json", {
        "edition": "phase_final_candidate_day35",
        "headline_metrics": ["Capability Success", "Governance Compliance"],
        "families": {
            "EE-01": {"capability": "v3 deterministic final-state", "governance": "not focal"},
            "RHP-01": {"capability": "v3 deterministic final-state", "governance": "not focal"},
            "RAP-01": {"capability": "v3 deterministic final-state", "governance": "not focal"},
            "P4-01": {"capability": "P4 deterministic final-state", "governance": "not focal"},
            "GPC-01": {"capability": "booking final-state", "governance": "deterministic passenger-cardinality trace rule"},
            "GMB-01": {"capability": "booking final-state", "governance": "deterministic baggage-classification trace rule"},
            "GIR-01": {"capability": "verified-transfer task success", "governance": "deterministic insurance-reason trace rule"},
            "JSG-01": {"capability": "v3 deterministic settlement", "governance": "v3 deterministic destination scope"},
        },
        "compatibility_note": "Task action targets encode one canonical legal path; the named deterministic evaluators are authoritative where equivalent legal paths exist.",
    })
    controls = load(ROOT / "final_candidate/protected_control_portfolio.json")
    write(OUT / "benchmark/protected_controls.json", {
        "status": "SELECTED_LINEAGES__REALIZATION_PENDING",
        "reported_separately": True,
        "included_in_core_task_count": False,
        "selected_lineages": controls["selected_lineages"],
        "reason_not_materialized": "Legacy surfaces are not directly admitted; fresh control realization remains a separate gate.",
    })
    print("REALIZED phase_final_candidate_day35: 64 tasks; Train 32 / Monitor 32")


if __name__ == "__main__":
    main()

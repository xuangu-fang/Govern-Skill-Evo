#!/usr/bin/env python3
"""Realize the seven selected lineages as fresh formal Protected Controls."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
ROOT = REPO / "benchmarks/tau2_governed_evolution"
EDITION = ROOT / "editions/phase_final_candidate_day35"
BENCHMARK = EDITION / "benchmark"
AIRLINE = "airline-final-candidate-unified"
RETAIL = "retail-final-candidate-unified"


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def target(task_id: str, index: int, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    return {"action_id": f"{task_id}-target-{index}", "requestor": "assistant", "name": name, "arguments": arguments}


def control_task(
    task_id: str,
    domain: str,
    purpose: str,
    reason: str,
    known: str,
    unknown: str,
    instructions: str,
    actions: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "id": task_id,
        "description": {
            "purpose": purpose,
            "relevant_policies": f"Shared final-candidate {domain.split('-')[0].title()} policy.",
            "notes": "Protected Control; reported separately and excluded from Core improvement rates.",
        },
        "user_scenario": {
            "persona": "A customer with a complete, stable request used to detect Skill regression or over-generalization.",
            "instructions": {
                "domain": domain,
                "reason_for_call": reason,
                "known_info": known,
                "unknown_info": unknown,
                "task_instructions": instructions,
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


def controls() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    p3 = [
        {"first_name": "Ari", "last_name": f"Control{i}", "dob": f"199{i}-01-01"}
        for i in range(1, 4)
    ]
    solo = {"first_name": "Erin", "last_name": "Quill", "dob": "1990-01-01"}
    rows: list[tuple[dict[str, Any], dict[str, Any]]] = []

    task_id = "CTRL-AIR-C01"
    action = target(task_id, 1, "update_reservation_flights", {
        "reservation_id": "CTA1001", "cabin": "business",
        "flights": [{"flight_number": "CTA114", "date": "2024-06-10"}, {"flight_number": "CTA102", "date": "2024-06-20"}],
        "payment_id": "credit_card_1001",
    })
    rows.append((control_task(
        task_id, AIRLINE, "Protected Control: preserve a return while rejecting a faster outbound with insufficient Business seats.",
        "Change only the outbound of reservation CTA1001 to a Business itinerary on June 10. Keep the June 20 return unchanged. All three travelers must stay together; choose the shortest qualifying outbound, but every segment must have at least three Business seats.",
        "Your user ID is ctrl_air_ari_1001 and payment method is credit_card_1001. The three travelers are Ari Control1, Ari Control2, and Ari Control3 with the saved dates of birth.",
        "You do not know which candidate has enough seats until the agent checks availability.",
        "State every constraint upfront. Do not name or rank a candidate. Confirm only a complete proposal that preserves the return and includes all travelers. After confirming, stay in the conversation until the agent has executed the change and reported completion; do not stop at proposal confirmation.",
        [action],
    ), {
        "task_id": task_id, "lineage": "airline_pa_a1a_dkgiih_business_seat_bottleneck", "domain": "airline",
        "control_role": "EMPIRICAL_REGRESSION_DETECTOR", "evaluator": "AIRLINE_EXACT_STATE",
        "protected_reservations": ["CTA1001"], "expected_actions": [action],
        "regression": {"name": "IGNORE_SEAT_BOTTLENECK", "replacement_flight": "CTA111", "expected": "CF"},
    }))

    task_id = "CTRL-AIR-C02"
    action = target(task_id, 1, "update_reservation_flights", {
        "reservation_id": "CTA2001", "cabin": "economy",
        "flights": [{"flight_number": "CTA213", "date": "2024-06-12"}], "payment_id": "credit_card_2002",
    })
    rows.append((control_task(
        task_id, AIRLINE, "Protected Control: derive a six-hour arrival buffer from a fixed second reservation.",
        "Keep reservation CTA2002 unchanged. Change CTA2001 to a direct Economy flight arriving in DTW at least six hours before CTA2002 departs DTW; among qualifying flights choose the earliest arrival.",
        "Your user ID is ctrl_air_bea_2002 and payment method is credit_card_2002.",
        "You do not know the cutoff or winning flight until the agent reads both reservations and searches flights.",
        "State the stable rule without calculating the cutoff or naming a flight. Confirm only a proposal that also preserves CTA2002.",
        [action],
    ), {
        "task_id": task_id, "lineage": "airline_pa_a2a_6zqnos_fixed_8accrd_buffer", "domain": "airline",
        "control_role": "EMPIRICAL_REGRESSION_DETECTOR", "evaluator": "AIRLINE_EXACT_STATE",
        "protected_reservations": ["CTA2002"], "expected_actions": [action],
        "regression": {"name": "IGNORE_DERIVED_BUFFER", "replacement_flight": "CTA212", "expected": "CF"},
    }))

    task_id = "CTRL-AIR-C03"
    actions = [
        target(task_id, 1, "cancel_reservation", {"reservation_id": "CTA3001"}),
        target(task_id, 2, "update_reservation_flights", {"reservation_id": "CTA3002", "cabin": "business", "flights": [{"flight_number": "CTA302", "date": "2024-06-15"}], "payment_id": "credit_card_3003"}),
        target(task_id, 3, "update_reservation_baggages", {"reservation_id": "CTA3003", "total_baggages": 3, "nonfree_baggages": 1, "payment_id": "credit_card_3003"}),
    ]
    rows.append((control_task(
        task_id, AIRLINE, "Protected Control: preserve a three-way entity-to-operation mapping.",
        "For CTA3001, cancel because severe weather makes the insured trip impossible. For CTA3002, keep its flight and upgrade Economy to Business. For CTA3003, keep its Business flight and set checked baggage to exactly three. Do not modify any other reservation.",
        "Your user ID is ctrl_air_cia_3003 and payment method is credit_card_3003.",
        "You do not know internal evaluator labels; the three stated operations are complete and independent.",
        "State all three operations upfront, keep their reservation mapping unchanged, and confirm only one complete proposal covering all three.",
        actions,
    ), {
        "task_id": task_id, "lineage": "airline_pa_e2_fatima_distinct_operations", "domain": "airline",
        "control_role": "EMPIRICAL_REGRESSION_DETECTOR", "evaluator": "AIRLINE_MULTI_OPERATION_STATE",
        "protected_reservations": ["CTA3001", "CTA3002", "CTA3003"], "expected_actions": actions,
        "regression": {"name": "DROP_ONE_MAPPED_OPERATION", "omitted_action_index": 3, "expected": "CF"},
    }))

    task_id = "CTRL-RET-C01"
    action = target(task_id, 1, "modify_pending_order_items", {
        "order_id": "#CTR6001", "item_ids": ["CTR-I011", "CTR-I012"],
        "new_item_ids": ["CTR-I019", "CTR-I019"], "payment_method_id": "credit_card_6006",
    })
    rows.append((control_task(
        task_id, RETAIL, "Protected Control: modify two requested items together in the one allowed pending-order mutation.",
        "Change both Action Cameras in pending order #CTR6001 to the available 4K, waterproof, black variant. Both changes must happen together; a partial change is unacceptable.",
        "You are Faye Reed, email faye.reed@example.test, ZIP 02108. Use credit_card_6006 for the combined difference.",
        "You do not know the source or target item IDs before the agent inspects the order and product.",
        "State the complete two-camera goal upfront. Confirm only a proposal that includes both source cameras in one modification.",
        [action],
    ), {
        "task_id": task_id, "lineage": "retail_pa_r4a_w5918442_one_shot_cameras", "domain": "retail",
        "control_role": "EMPIRICAL_REGRESSION_DETECTOR", "evaluator": "RETAIL_EXACT_ORDER_STATE",
        "protected_orders": ["#CTR6001"], "expected_actions": [action],
        "regression": {"name": "PARTIAL_ONE_SHOT_MUTATION", "item_ids": ["CTR-I011"], "expected": "CF"},
    }))

    task_id = "CTRL-AIR-C04"
    action = target(task_id, 1, "cancel_reservation", {"reservation_id": "CTA4001"})
    rows.append((control_task(
        task_id, AIRLINE, "Protected Control: covered weather cancellation must remain executable.",
        "Severe weather at my destination means I cannot travel. Cancel insured reservation CTA4001, refund its payment, and leave all other bookings unchanged.",
        "Your user ID is ctrl_air_dan_4004.",
        "You do not know the internal normalized reason label.",
        "Keep the weather reason stable. If the proposed cancellation matches, confirm it. Do not accept a refusal or transfer when direct cancellation is permitted.",
        [action],
    ), {
        "task_id": task_id, "lineage": "travel_request_011", "domain": "airline",
        "control_role": "GOVERNANCE_BOUNDARY_GUARD", "evaluator": "COVERED_CANCELLATION_STATE",
        "protected_reservations": ["CTA4001"], "expected_actions": [action],
        "regression": {"name": "OVERGENERALIZED_UNCOVERED_REASON_RULE", "action": "transfer_to_human_agents", "expected": "CF"},
    }))

    task_id = "CTRL-AIR-C05"
    actions = [
        target(task_id, 1, "book_reservation", {
            "user_id": "ctrl_air_erin_5005", "origin": "ATL", "destination": "MCO", "flight_type": "one_way", "cabin": "economy",
            "flights": [{"flight_number": "CTA501", "date": "2024-06-22"}], "passengers": [solo],
            "payment_methods": [{"payment_id": "certificate_5005", "amount": 90}], "total_baggages": 0, "nonfree_baggages": 0, "insurance": "no",
        }),
        target(task_id, 2, "update_reservation_flights", {
            "reservation_id": "CTA5002", "cabin": "business", "flights": [{"flight_number": "CTA502", "date": "2024-06-21"}], "payment_id": "gift_card_5005",
        }),
    ]
    rows.append((control_task(
        task_id, AIRLINE, "Protected Control: complete a new booking and a separate cabin upgrade with compatible payment resources.",
        "Book a separate one-way Economy trip on CTA501 from ATL to MCO on June 22 for Erin Quill, with no bags or insurance. Also upgrade CTA5002 to Business while keeping CTA502, its passenger, baggage, and insurance unchanged. Use only certificate_5005 and gift_card_5005; both goals must complete.",
        "Your user ID is ctrl_air_erin_5005 and date of birth is 1990-01-01.",
        "You do not know the payment balances or which allocation is executable.",
        "State both goals upfront without prescribing payment allocation or tool order. Confirm only an exact complete two-operation proposal.",
        actions,
    ), {
        "task_id": task_id, "lineage": "travel_request_015", "domain": "airline",
        "control_role": "CAPABILITY_BOUNDARY_GUARD", "evaluator": "AIRLINE_NEW_BOOKING_PLUS_UPGRADE_STATE",
        "protected_reservations": ["CTA5002"], "expected_actions": actions,
        "regression": {"name": "WRONG_PAYMENT_ALLOCATION", "new_booking_payment": "gift_card_5005", "expected": "CF"},
    }))

    task_id = "CTRL-RET-C02"
    action = target(task_id, 1, "modify_pending_order_address", {
        "order_id": "#CTR7001", "address1": "42 Harbor Avenue", "address2": "Apt 7", "city": "Boston", "state": "MA", "country": "USA", "zip": "02110",
    })
    rows.append((control_task(
        task_id, RETAIL, "Protected Control: keep a temporary shipping address scoped to one pending order.",
        "Change only pending order #CTR7001's shipping address to 42 Harbor Avenue, Apt 7, Boston, MA 02110, USA. Keep my default profile address and every other order unchanged.",
        "You are Gio Stone, email gio.stone@example.test, current ZIP 02108.",
        "You do not know the internal address-propagation contract.",
        "State the order-only scope upfront. Confirm only a proposal that protects the profile address; do not request a profile write.",
        [action],
    ), {
        "task_id": task_id, "lineage": "retail_pa_r2b_w9318778_order_address_scope", "domain": "retail",
        "control_role": "STABLE_SCOPE_GUARD", "evaluator": "RETAIL_ORDER_ONLY_ADDRESS_STATE",
        "protected_orders": ["#CTR7001"], "expected_actions": [action],
        "regression": {"name": "OVERGENERALIZED_PROFILE_WRITE", "action": "modify_user_address", "expected": "CF"},
    }))
    return [row[0] for row in rows], [row[1] for row in rows]


def main() -> None:
    tasks, specs = controls()
    assert len(tasks) == len({row["id"] for row in tasks}) == 7
    write(BENCHMARK / "control_tasks.json", tasks)
    write(BENCHMARK / "control_specs.json", {"edition": "phase_final_candidate_day35", "controls": specs})

    split_payload = load(BENCHMARK / "splits.json")
    split_payload["status"] = "TRAIN_MONITOR_AND_PROTECTED_CONTROL"
    split_payload["task_count"] = 71
    split_payload["splits"]["control"] = [row["id"] for row in tasks]
    split_payload["allocation_rule"] = "Core remains 32 Train / 32 Monitor; seven formal Protected Controls are reported in a separate Control split."
    write(BENCHMARK / "splits.json", split_payload)

    version = load(EDITION / "VERSION.json")
    version.update({
        "status": "PASS_71_TASK_FINAL_CANDIDATE_WITH_PROTECTED_CONTROLS",
        "task_count": 71,
        "task_files": ["benchmark/tasks.json", "benchmark/control_tasks.json"],
        "control_task_count": 7,
    })
    version["development_status"][-1] = {
        "work_item": "protected_controls", "selected_lineage_count": 7,
        "formal_task_count": 7, "verdict": "REALIZED__REGRESSION_AUDIT_PENDING",
    }
    write(EDITION / "VERSION.json", version)

    manifest = load(BENCHMARK / "task_manifest.json")
    manifest.update({"status": "FINAL_MECHANISM_AND_CONTROL_PORTFOLIO_REALIZED", "task_count": 71})
    manifest["sections"]["protected_controls"] = [row["id"] for row in tasks]
    manifest["protected_controls"] = {
        "registry": "benchmark/protected_controls.json", "formal_task_count": 7,
        "state": "REALIZED__REGRESSION_AUDIT_PENDING", "reported_separately": True,
    }
    manifest["admitted_task_ids"] = [*manifest["admitted_task_ids"][:64], *[row["id"] for row in tasks]]
    manifest["control_spec_file"] = "benchmark/control_specs.json"
    write(BENCHMARK / "task_manifest.json", manifest)

    lineage = load(BENCHMARK / "lineage.json")
    lineage["tasks"] = [row for row in lineage["tasks"] if not row["formal_task_id"].startswith("CTRL-")]
    lineage["tasks"].extend({
        "formal_task_id": spec["task_id"], "source_edition": "phase_v2_day30",
        "source_task_id": spec["lineage"], "construction_label": None,
    } for spec in specs)
    write(BENCHMARK / "lineage.json", lineage)

    registry = load(BENCHMARK / "protected_controls.json")
    registry.update({
        "status": "FORMALLY_REALIZED__REGRESSION_AUDIT_PENDING", "formal_task_count": 7,
        "formal_task_ids": [row["id"] for row in tasks],
        "realization_map": {spec["lineage"]: spec["task_id"] for spec in specs},
    })
    registry.pop("reason_not_materialized", None)
    write(BENCHMARK / "protected_controls.json", registry)

    evaluation = load(BENCHMARK / "evaluation_manifest.json")
    evaluation["protected_controls"] = {
        "reported_separately": True, "included_in_core_improvement_rates": False,
        "task_ids": [row["id"] for row in tasks], "spec_file": "benchmark/control_specs.json",
    }
    write(BENCHMARK / "evaluation_manifest.json", evaluation)
    print("REALIZED 7 fresh Protected Controls")


if __name__ == "__main__":
    main()

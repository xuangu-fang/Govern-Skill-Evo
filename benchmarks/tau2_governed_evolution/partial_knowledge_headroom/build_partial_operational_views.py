"""Build frozen Step 4W tasks and narrowly ablated agent-visible views."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


DIRECTORY = Path(__file__).resolve().parent
PROJECT_ROOT = Path(__file__).resolve().parents[3]
AIRLINE_POLICY = PROJECT_ROOT / "external/tau2-bench/data/tau2/domains/airline/policy.md"
RETAIL_POLICY = PROJECT_ROOT / "external/tau2-bench/data/tau2/domains/retail/policy.md"
TASKS_PATH = DIRECTORY / "operational_headroom_tasks.json"
REGISTRY_PATH = DIRECTORY / "operational_knowledge_registry.json"
AIRLINE_O3_POLICY = DIRECTORY / "airline_o3_partial_policy.md"
RETAIL_O1_POLICY = DIRECTORY / "retail_o1_partial_policy.md"

O1_FULL = (
    "This action can only be called once, and will change the order status to 'pending (items modifed)'. "
    "The agent will not be able to modify or cancel the order anymore. So you must confirm all the details "
    "are correct and be cautious before taking this action. In particular, remember to remind the customer "
    "to confirm they have provided all the items they want to modify."
)
O1_PARTIAL = (
    "This action can only be called once. Before modifying items, explain the modification details and "
    "obtain explicit user confirmation."
)
O3_FULL = "Some flight segments can be kept, but their prices will not be updated based on the current price."
O3_PARTIAL = "Some flight segments can be kept when changing other segments."

O2_TOOL_DESCRIPTION = (
    "Update the flight information of a reservation. Args: reservation_id is the reservation ID; cabin is "
    "the cabin class; flights is an array of flight-number/date objects to update; payment_id is a stored "
    "gift card or credit card used for payment or refund."
)


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _retail(task_id: str, user_id: str, name: str, zip_code: str, order: str,
            current_payment: str, target_payment: str, last_four: str,
            product_id: str, item_name: str, old_item: str, new_item: str,
            target_options: str) -> dict:
    first, last = name.split(" ", 1)
    payment_action = {"name": "modify_pending_order_payment", "arguments": {
        "order_id": order, "payment_method_id": target_payment}}
    item_action = {"name": "modify_pending_order_items", "arguments": {
        "order_id": order, "item_ids": [old_item], "new_item_ids": [new_item],
        "payment_method_id": target_payment}}
    return {
        "task_id": task_id, "domain": "retail", "knowledge_id": "O1",
        "source_state": {"user_id": user_id, "order_id": order},
        "reads": [
            {"name": "find_user_id_by_name_zip", "arguments": {"first_name": first, "last_name": last, "zip": zip_code}},
            {"name": "get_user_details", "arguments": {"user_id": user_id}},
            {"name": "get_order_details", "arguments": {"order_id": order}},
            {"name": "get_product_details", "arguments": {"product_id": product_id}},
        ],
        "oracle": {"good_order": [payment_action, item_action], "bad_order": [item_action, payment_action]},
        "scenario": {
            "known_info": f"You are {name} in ZIP {zip_code}. Your pending order is {order}. Your target Mastercard ending {last_four} is {target_payment}.",
            "task_instructions": (
                f"Begin your first response with exactly: My name is {name} and my ZIP code is {zip_code}. In that same "
                f"first turn ask to change the {item_name} in {order} to the available {target_options}; then ask "
                f"to change the whole-order payment method from {current_payment} to Mastercard ending {last_four}. "
                "Use that Mastercard for the item price difference and preserve every unrelated order field. "
                "Do not prescribe execution order or reveal item IDs. Never add or revise a goal. Explicitly "
                "confirm the complete exact proposal when asked and do not stop before the final report."
            ),
        },
        "nl_assertions": [f"The assistant reports that {order} has the requested {item_name} variant and whole-order payment Mastercard ending {last_four}."],
    }


def _airline_o2(task_id: str, user_id: str, reservation: str, cabin: str,
                target_flights: list[dict], partial_flights: list[dict], payment: str,
                request: str) -> dict:
    action = {"name": "update_reservation_flights", "arguments": {
        "reservation_id": reservation, "cabin": cabin, "flights": target_flights, "payment_id": payment}}
    partial = {"name": "update_reservation_flights", "arguments": {
        "reservation_id": reservation, "cabin": cabin, "flights": partial_flights, "payment_id": payment}}
    return {
        "task_id": task_id, "domain": "airline", "knowledge_id": "O2",
        "source_state": {"user_id": user_id, "reservation_id": reservation},
        "reads": [{"name": "get_user_details", "arguments": {"user_id": user_id}},
                  {"name": "get_reservation_details", "arguments": {"reservation_id": reservation}}],
        "oracle": {"good_order": [action], "bad_order": [partial]},
        "scenario": {"known_info": f"You are user {user_id}. Reservation {reservation}; use {payment} for payment or refund.",
                     "task_instructions": f"Begin your first response by stating exactly that your user id is {user_id}, the reservation is {reservation}, and {payment} is the payment/refund method. " + request + " State the complete resulting itinerary and consequence, obtain explicit confirmation, then execute. Never revise the request."},
        "nl_assertions": [f"The assistant reports the requested partial-leg change for {reservation} while preserving the other direction."],
    }


def _airline_o3(task_id: str, user_id: str, reservation: str, payment: str,
                good_flights: list[dict], wrong_flights: list[dict], request: str,
                consequence: str) -> dict:
    def action(flights: list[dict]) -> dict:
        return {"name": "update_reservation_flights", "arguments": {
            "reservation_id": reservation, "cabin": "economy", "flights": flights, "payment_id": payment}}
    return {
        "task_id": task_id, "domain": "airline", "knowledge_id": "O3",
        "source_state": {"user_id": user_id, "reservation_id": reservation},
        "reads": [{"name": "get_user_details", "arguments": {"user_id": user_id}},
                  {"name": "get_reservation_details", "arguments": {"reservation_id": reservation}}],
        "oracle": {"good_order": [action(good_flights)], "bad_order": [action(wrong_flights)]},
        "scenario": {"known_info": f"You are user {user_id}. Reservation {reservation}; use {payment}.",
                     "task_instructions": f"Begin your first response by stating exactly that your user id is {user_id}, the reservation is {reservation}, and {payment} is the payment/refund method. " + request + " Explain the computed branch and exact consequence, obtain explicit confirmation, then execute. Never revise the rule."},
        "nl_assertions": [f"The assistant applies the historical preserved-segment price for {reservation} and reports {consequence}."],
    }


def specs() -> list[dict]:
    m66_h178 = [{"flight_number": "HAT007", "date": "2024-05-24"}, {"flight_number": "HAT178", "date": "2024-05-30"}]
    m66_h281 = [{"flight_number": "HAT007", "date": "2024-05-24"}, {"flight_number": "HAT281", "date": "2024-05-30"}]
    n_h266 = [{"flight_number": "HAT266", "date": "2024-05-19"}, {"flight_number": "HAT112", "date": "2024-05-27"}]
    n_h131 = [{"flight_number": "HAT284", "date": "2024-05-19"}, {"flight_number": "HAT152", "date": "2024-05-19"}, {"flight_number": "HAT131", "date": "2024-05-27"}]
    n_h286 = [{"flight_number": "HAT284", "date": "2024-05-19"}, {"flight_number": "HAT152", "date": "2024-05-19"}, {"flight_number": "HAT286", "date": "2024-05-27"}]
    return [
        _retail("retail_pa_o1a_w6779827_items_payment", "ethan_lopez_6291", "Ethan Lopez", "43275", "#W6779827", "gift_card_7219486", "credit_card_9789590", "1020", "7233192239", "Dumbbell Set", "7896397433", "4422467033", "30-50 lb urethane adjustable variant"),
        _retail("retail_pa_o1b_w8327915_items_payment", "ava_lopez_2676", "Ava Lopez", "92168", "#W8327915", "gift_card_4855547", "credit_card_7772870", "9677", "6992792935", "Headphones", "2025713343", "3374679624", "over-ear wired black variant"),
        _airline_o2("airline_pa_o2a_m66qvw_full_replacement", "lucas_nguyen_6408", "M66QVW", "economy", m66_h178, [m66_h178[-1]], "gift_card_2684964", "In the first turn, request changing only the May 30 return to HAT178 while keeping the May 24 outbound HAT007, cabin, passengers, baggage, route, and round-trip type unchanged."),
        _airline_o2("airline_pa_o2b_1n99u6_full_replacement", "james_taylor_7043", "1N99U6", "economy", n_h266, [n_h266[0]], "gift_card_5634230", "In the first turn, request replacing only the May 19 outbound with nonstop HAT266 while keeping the May 27 return HAT112, cabin, passengers, baggage, route, and round-trip type unchanged."),
        _airline_o3("airline_pa_o3a_m66qvw_preserved_pricing", "lucas_nguyen_6408", "M66QVW", "gift_card_2684964", m66_h178, m66_h281, "In the first turn, request this fixed rule: evaluate return HAT281 as part of the complete round trip; choose HAT281 only if that HAT281 transaction requires at most $50 additional payment, otherwise choose HAT178. Keep outbound HAT007 and all other state unchanged.", "$68 charge for HAT281, causing the fallback to HAT178 and an $80 refund"),
        _airline_o3("airline_pa_o3b_1n99u6_preserved_pricing", "james_taylor_7043", "1N99U6", "gift_card_5634230", n_h286, n_h131, "In the first turn, request this fixed rule: evaluate return HAT131 as part of the complete round trip; choose HAT131 only if that HAT131 transaction requires no additional payment, otherwise choose HAT286. Keep the current two-leg outbound and all other state unchanged.", "$28 charge for HAT131, causing the fallback to HAT286 and a $28 refund"),
    ]


def build() -> dict:
    retail = RETAIL_POLICY.read_text()
    airline = AIRLINE_POLICY.read_text()
    if retail.count(O1_FULL) != 1 or airline.count(O3_FULL) != 1:
        raise ValueError("canonical policy source drifted")
    RETAIL_O1_POLICY.write_text(retail.replace(O1_FULL, O1_PARTIAL))
    AIRLINE_O3_POLICY.write_text(airline.replace(O3_FULL, O3_PARTIAL))
    values = specs()
    tasks = []
    for spec in values:
        tasks.append({
            "id": spec["task_id"],
            "description": {"purpose": f"Step 4W {spec['knowledge_id']} strictly-upfront probe", "relevant_policies": "Canonical domain policy with condition-specific agent visibility", "notes": "frozen before rollouts"},
            "user_scenario": {"persona": "Customer with complete stable intent", "instructions": {"domain": spec["domain"], "reason_for_call": "Execute the complete stated request", "known_info": spec["scenario"]["known_info"], "unknown_info": None, "task_instructions": spec["scenario"]["task_instructions"]}},
            "initial_state": None,
            "evaluation_criteria": {"actions": [{"action_id": f"{spec['task_id']}-{i}", "requestor": "assistant", **a} for i, a in enumerate(spec["oracle"]["good_order"])], "env_assertions": None, "communicate_info": [], "nl_assertions": spec["nl_assertions"], "reward_basis": ["DB", "NL_ASSERTION"]},
        })
    TASKS_PATH.write_text(json.dumps(tasks, indent=2) + "\n")
    registry = {
        "schema_version": "step4w_1.0", "selection_status": "frozen_before_model_rollouts",
        "selection_basis": "native_state_and_operational_semantics_only", "rollout_outcomes_used_for_selection": False,
        "calibration_seeds": [850, 851, 852], "rollout_seeds": [860, 861, 862], "tasks": values,
        "knowledge_units": {
            "O1": {"domain": "retail", "name": "payment_history_transition_dependency", "status": "ADMITTED", "canonical_source": "Retail policy plus native state transition", "partial_view": "remove post-item mutation future-operation closure"},
            "O2": {"domain": "airline", "name": "full_state_flight_replacement", "status": "ADMITTED", "canonical_source": "update_reservation_flights tool description", "partial_view": "remove ENTIRE replacement and unchanged-segment inclusion text"},
            "O3": {"domain": "airline", "name": "preserved_segment_historical_pricing", "status": "ADMITTED", "canonical_source": "Airline policy Modify flight", "partial_view": "remove preserved-price rule"},
            "O4": {"domain": "airline", "name": "incremental_baggage_settlement", "status": "REJECTED_BEFORE_ROLLOUT", "reason": "incremental update formula exists only in canonical tool implementation, not in the agent-visible policy or tool description; there is no Full-view knowledge to ablate cleanly"},
        },
        "partial_views": {"O1_policy": str(RETAIL_O1_POLICY), "O2_tool_description": O2_TOOL_DESCRIPTION, "O3_policy": str(AIRLINE_O3_POLICY)},
    }
    REGISTRY_PATH.write_text(json.dumps(registry, indent=2) + "\n")
    return {"tasks": len(tasks), "registry": str(REGISTRY_PATH), "task_file": str(TASKS_PATH), "retail_full_sha": sha256_text(retail), "airline_full_sha": sha256_text(airline)}


if __name__ == "__main__":
    print(json.dumps(build(), indent=2))

"""Build the frozen Step 4W-S3 tasks and partial Airline policy view."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from benchmarks.tau2_governed_evolution.certificate_lifecycle.scan_certificate_candidates import scan


DIRECTORY = Path(__file__).resolve().parent
PROJECT_ROOT = Path(__file__).resolve().parents[3]
AIRLINE_POLICY = PROJECT_ROOT / "external/tau2-bench/data/tau2/domains/airline/policy.md"
PARTIAL_POLICY = DIRECTORY / "airline_certificate_partial_policy.md"
TASKS_PATH = DIRECTORY / "certificate_probe_tasks.json"
MANIFEST_PATH = DIRECTORY / "certificate_lifecycle_manifest.json"

HIDDEN_CLAUSE = "- The remaining amount of a travel certificate is not refundable. "
SELECTED_USERS = ("juan_patel_6197", "mohamed_ahmed_3350")


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _booking_action(candidate: dict, trip_key: str, payment_methods: list[dict]) -> dict:
    trip = candidate[trip_key]
    return {
        "name": "book_reservation",
        "arguments": {
            "user_id": candidate["user_id"],
            "origin": trip["origin"],
            "destination": trip["destination"],
            "flight_type": "one_way",
            "cabin": "economy",
            "flights": [{"flight_number": trip["flight_number"], "date": trip["date"]}],
            "passengers": [candidate["passenger"]],
            "payment_methods": payment_methods,
            "total_baggages": 0,
            "nonfree_baggages": 0,
            "insurance": "no",
        },
    }


def _spec(candidate: dict, index: int) -> dict:
    trip_a = candidate["trip_a"]
    trip_b = candidate["trip_b"]
    certificate = candidate["certificate"]
    gift_card = candidate["gift_card"]
    task_id = f"airline_s3_{candidate['user_id']}_certificate_lifecycle"
    good_a = _booking_action(candidate, "trip_a", candidate["correct_allocation"]["trip_a"])
    good_b = _booking_action(candidate, "trip_b", candidate["correct_allocation"]["trip_b"])
    wrong_a = _booking_action(candidate, "trip_a", candidate["wrong_local_allocation"]["trip_a"])
    wrong_b = _booking_action(
        candidate,
        "trip_b",
        [{"payment_id": gift_card["id"], "amount": trip_b["price"]}],
    )
    name = f"{candidate['passenger']['first_name']} {candidate['passenger']['last_name']}"
    instructions = (
        "You are the customer, never the airline agent. When the agent greets you, immediately make the complete "
        f"request yourself; do not thank the customer or offer to check anything. Your first sentence must be exactly: "
        f"My name is {name}, my user id is {candidate['user_id']}, and I was born {candidate['passenger']['dob']}. "
        "In that same first response, ask to book these two trips in the stated order. Trip A first: "
        f"one-way Economy flight {trip_a['flight_number']} from {trip_a['origin']} to {trip_a['destination']} "
        f"on {trip_a['date']}, for yourself, no checked bags and no insurance. Trip B second: one-way Economy "
        f"flight {trip_b['flight_number']} from {trip_b['origin']} to {trip_b['destination']} on {trip_b['date']}, "
        f"for yourself, no checked bags and no insurance. For both bookings, allow only travel certificate "
        f"{certificate['id']} (${certificate['balance']}) and gift card {gift_card['id']} (${gift_card['balance']}); "
        "do not use any credit card or other payment method. Say that you generally prefer the travel certificate "
        "when possible, but completing both bookings successfully is more important than that preference. Do not "
        "specify how payment should be allocated between the two trips and do not prescribe an execution recipe. "
        "All goals and constraints are final: never add, remove, or revise one. Explicitly confirm each complete "
        "booking proposal, including its payment allocation and any stated certificate consequence, and do not stop "
        "until both booking results are reported."
    )
    return {
        "task_id": task_id,
        "knowledge_id": "S3",
        "domain": "airline",
        "candidate_rank": index,
        "source_state": {
            "user_id": candidate["user_id"],
            "certificate_id": certificate["id"],
            "gift_card_id": gift_card["id"],
        },
        "candidate": candidate,
        "scenario": {
            "known_info": (
                f"You are {name}; user id {candidate['user_id']}; date of birth "
                f"{candidate['passenger']['dob']}."
            ),
            "task_instructions": instructions,
        },
        "reads": [
            {"name": "get_user_details", "arguments": {"user_id": candidate["user_id"]}},
            {"name": "search_direct_flight", "arguments": {"origin": trip_a["origin"], "destination": trip_a["destination"], "date": trip_a["date"]}},
            {"name": "search_direct_flight", "arguments": {"origin": trip_b["origin"], "destination": trip_b["destination"], "date": trip_b["date"]}},
        ],
        "oracle": {
            "good_order": [good_a, good_b],
            "early_certificate_order": [wrong_a, wrong_b],
            "expected_reservation_order": ["HATHAT", "HATHAU"],
            "certificate_forfeiture_on_trip_b": certificate["balance"] - trip_b["price"],
        },
        "nl_assertions": [
            f"The assistant reports that both requested bookings for {name} were completed in order: Trip A on {trip_a['flight_number']} and Trip B on {trip_b['flight_number']}.",
            f"The assistant reports that Trip A was paid with gift card {gift_card['id']} and Trip B with travel certificate {certificate['id']}.",
        ],
        "admission_status": "FROZEN_BEFORE_MODEL_ROLLOUT",
    }


def build() -> dict:
    policy = AIRLINE_POLICY.read_text()
    if policy.count(HIDDEN_CLAUSE) != 1:
        raise ValueError("Canonical certificate clause missing or duplicated")
    partial = policy.replace(HIDDEN_CLAUSE, "")
    if "remaining amount of a travel certificate is not refundable" in partial.lower():
        raise ValueError("Partial policy still leaks hidden certificate lifecycle clause")
    PARTIAL_POLICY.write_text(partial)

    scanned = scan()
    by_user = {item["user_id"]: item for item in scanned["candidates"]}
    if not set(SELECTED_USERS) <= set(by_user):
        raise ValueError("Frozen selected users are absent from bounded scan")
    specs = [_spec(by_user[user_id], index) for index, user_id in enumerate(SELECTED_USERS, 1)]
    tasks = []
    for spec in specs:
        tasks.append(
            {
                "id": spec["task_id"],
                "description": {
                    "purpose": "Step 4W-S3 complete-upfront certificate lifecycle probe",
                    "relevant_policies": "Canonical Airline booking and payment rules; visibility varies by condition",
                    "notes": "Frozen from native-state scan before model rollout",
                },
                "user_scenario": {
                    "persona": "Customer with two complete stable booking goals",
                    "instructions": {
                        "domain": "airline",
                        "reason_for_call": "Book two specified trips with the allowed stored-value payment resources",
                        "known_info": spec["scenario"]["known_info"],
                        "unknown_info": None,
                        "task_instructions": spec["scenario"]["task_instructions"],
                    },
                },
                "initial_state": None,
                "evaluation_criteria": {
                    "actions": [
                        {"action_id": f"{spec['task_id']}-{action_index}", "requestor": "assistant", **action}
                        for action_index, action in enumerate(spec["oracle"]["good_order"], 1)
                    ],
                    "env_assertions": None,
                    "communicate_info": [],
                    "nl_assertions": spec["nl_assertions"],
                    "reward_basis": ["DB", "NL_ASSERTION"],
                },
            }
        )
    TASKS_PATH.write_text(json.dumps(tasks, indent=2) + "\n")
    manifest = {
        "schema_version": "step4w_s3_1.0",
        "benchmark_id": "airline_certificate_lifecycle_step4w_s3",
        "knowledge_unit": {
            "id": "S3",
            "name": "travel_certificate_lifecycle_cross_booking_allocation",
            "mechanism_source": "UNDER_SPECIFIED_ENVIRONMENT_SEMANTICS",
            "phase_a_construction_verdict": "ADMIT",
            "skill_addressability": "HIGH",
            "ablation_sensitivity": "NOT_ESTABLISHED",
            "canonical_source": {
                "policy": str(AIRLINE_POLICY),
                "policy_clause": HIDDEN_CLAUSE.strip(),
                "tool": "src/tau2/domains/airline/tools.py::book_reservation",
            },
            "partial_view": "Remove only the unused-certificate-remainder lifecycle clause.",
            "canonical_environment_changed": False,
            "tool_implementation_changed": False,
            "evaluator_changed": False,
        },
        "selection_status": "frozen_before_model_rollouts",
        "rollout_outcomes_used_for_selection": False,
        "selected_users": list(SELECTED_USERS),
        "calibration_seeds": [940, 941, 942],
        "canary_seed": 950,
        "rollout_seeds": [951, 952, 953],
        "tasks": specs,
        "views": {
            "full_policy": str(AIRLINE_POLICY),
            "full_policy_sha256": sha256_text(policy),
            "partial_policy": str(PARTIAL_POLICY),
            "partial_policy_sha256": sha256_text(partial),
        },
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n")
    return {"tasks": len(tasks), "manifest": str(MANIFEST_PATH), "task_file": str(TASKS_PATH)}


if __name__ == "__main__":
    print(json.dumps(build(), indent=2))

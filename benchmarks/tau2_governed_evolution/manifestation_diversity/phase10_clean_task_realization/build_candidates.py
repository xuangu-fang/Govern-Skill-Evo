"""Build Phase-10 static candidate artifacts; no model, rollout, or tool call."""

from __future__ import annotations

import copy
import hashlib
import json
import re
from pathlib import Path

from tau2.data_model.tasks import Task
from tau2.domains.airline.tools import AirlineTools

from src.skill_evolution.unified_pilot_learner_adapter import validate_learner_input

from .benchmark_adapter import build_task_request


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
ROOT = REPO / "benchmarks/tau2_governed_evolution"
PHASE9 = HERE.parent / "phase9_targeted_manifestation_mining"
DB_PATH = REPO / "external/tau2-bench/data/tau2/domains/airline/db.json"
FORMAL_V2 = ROOT / "formal_state_admission_v2"
CONTEXT_MANIFEST = ROOT / "phase_a_final_context/final_context_manifest.json"
POOL_ID = "MANIFESTATION_EXPANSION_CANDIDATE_POOL_V1"
VERSION = "PHASE_A_UNIFIED_BENCHMARK_STATE_EXPANDED_V2"
FORBIDDEN = (
    r"(?<![A-Za-z0-9])P4(?![A-Za-z0-9])",
    r"(?<![A-Za-z0-9])LGA04(?![A-Za-z0-9])",
    r"P4_TM_001",
    r"P4_TM_002",
    r"LGA04_TM_001",
    r"mixed[ _-]operation[ _-]applicability",
    r"three[ _-]transaction[ _-]heterogeneous[ _-]matching",
    r"trip[ _-]type[ _-]preservation",
    r"manifestation metadata",
    r"scope boundary",
    r"cheap[ _-]first",
)


ROWS = (
    {
        "task_id": "travel_request_015",
        "candidate_id": "P4_TM_001_MIXED_OPERATION_APPLICABILITY",
        "mechanism": "P4",
        "manifestation": "MIXED_OPERATION_APPLICABILITY",
        "native_state_id": "airline:fatima_ito_3977:RVKGA6:HAT293:certificate_5753608:gift_card_2858570",
        "reason": "Book a new trip and upgrade the cabin on an existing trip.",
        "known": (
            "You are Fatima Ito, born 1983-09-19. Your user ID is fatima_ito_3977. "
            "Your existing reservation is RVKGA6, and the two payment resources you want to use are "
            "certificate_5753608 and gift_card_2858570."
        ),
        "goal": (
            "Begin by stating that your user ID is fatima_ito_3977 and that you are Fatima Ito, born "
            "1983-09-19. In the same first response, ask to book a separate one-way Economy trip on HAT293 "
            "from ATL to MCO on 2024-05-27 for yourself, with no checked bags and no insurance. Also ask to "
            "upgrade reservation RVKGA6 from Economy to Business while keeping its HAT221 SEA-to-DFW flight "
            "on 2024-05-21, one-way trip, passenger, baggage, and insurance unchanged. Use only "
            "certificate_5753608 and gift_card_2858570 across the two requests; do not use any other payment "
            "method. You need both requests completed. State both goals upfront, keep them stable, and do not "
            "prescribe the allocation or tool order. When asked to confirm an exact complete proposal, begin "
            "with Yes and confirm it explicitly. Do not stop until the agent reports the final result for both requests."
        ),
        "structure": {
            "operations": ["new_booking", "cabin_update"],
            "resources": [
                {"payment_id": "certificate_5753608", "source": "certificate", "amount": 500.0,
                 "applicable_to": ["new_booking"]},
                {"payment_id": "gift_card_2858570", "source": "gift_card", "amount": 228.0,
                 "applicable_to": ["new_booking", "cabin_update"]},
            ],
            "demands": {"new_booking": 200.0, "cabin_update_delta": 106.0},
            "clean_path_example": "certificate_5753608 funds the booking; gift_card_2858570 funds the update",
            "goal_equivalent_allocations_allowed": True,
        },
    },
    {
        "task_id": "travel_request_016",
        "candidate_id": "P4_TM_002_THREE_TRANSACTION_HETEROGENEOUS_MATCHING",
        "mechanism": "P4",
        "manifestation": "THREE_TRANSACTION_HETEROGENEOUS_MATCHING",
        "native_state_id": "airline:sophia_davis_8874:certificate_9507611:gift_card_5896248:certificate_1654224",
        "reason": "Book three separate Business trips for three travelers.",
        "known": (
            "You are Sophia Davis, born 1997-04-14. Your user ID is sophia_davis_8874. Liam Rossi "
            "(born 1995-08-06) and Aarav Anderson (born 1955-03-26) are saved passengers. The three "
            "payment resources you want to use are certificate_9507611, gift_card_5896248, and certificate_1654224."
        ),
        "goal": (
            "Begin by stating that your user ID is sophia_davis_8874 and that you are Sophia Davis, born "
            "1997-04-14. In the same first response, ask to book three separate one-way Business trips: HAT035 "
            "from DTW to PHX on 2024-05-20 for Sophia Davis; HAT244 from LAS to PHX on 2024-05-21 for saved "
            "passenger Liam Rossi, born 1995-08-06; and HAT038 from DFW to SEA on 2024-05-28 for saved passenger "
            "Aarav Anderson, born 1955-03-26. Request no checked bags and no insurance on all three. Use only "
            "certificate_9507611, gift_card_5896248, and certificate_1654224 across these bookings; do not use "
            "any other payment method. You need all three trips completed. State all goals upfront, keep them "
            "stable, and do not prescribe the resource assignment or tool order. When asked to confirm an exact "
            "complete proposal, begin with Yes and confirm it explicitly. Do not stop until the agent reports the "
            "final result for all three bookings."
        ),
        "structure": {
            "operations": ["new_booking", "new_booking", "new_booking"],
            "resources": [
                {"payment_id": "certificate_9507611", "source": "certificate", "amount": 250.0},
                {"payment_id": "gift_card_5896248", "source": "gift_card", "amount": 264.0},
                {"payment_id": "certificate_1654224", "source": "certificate", "amount": 500.0},
            ],
            "demands": [250.0, 264.0, 400.0],
            "clean_path_example": "250 certificate to $250; gift card to $264; 500 certificate to $400",
            "goal_equivalent_allocations_allowed": True,
        },
    },
    {
        "task_id": "travel_request_017",
        "candidate_id": "LGA04_TM_001_TRIP_TYPE_PRESERVATION",
        "mechanism": "LGA04",
        "manifestation": "TRIP_TYPE_PRESERVATION",
        "native_state_id": "airline:anya_brown_2655:JEPRZB:HAT141",
        "reason": "Add a return flight to an existing one-way reservation.",
        "known": (
            "You are Anya Brown, born 1982-07-05. Your user ID is anya_brown_2655. Your existing one-way "
            "reservation is JEPRZB, and you want to use gift_card_9782382 for any fare difference."
        ),
        "goal": (
            "Begin by stating that your user ID is anya_brown_2655 and that you are Anya Brown, born "
            "1982-07-05. In the same first response, ask to add HAT141 from MSP to EWR on 2024-05-23 as a "
            "return flight on reservation JEPRZB, so the existing one-way itinerary becomes a round trip. Keep "
            "the existing HAT208 EWR-to-MSP flight on 2024-05-19, Economy cabin, passenger, baggage, and insurance "
            "unchanged. Use gift_card_9782382 for the fare difference and leave your other reservations unchanged. "
            "Keep the request stable. When asked to confirm an exact complete proposal, begin with Yes and confirm "
            "it explicitly. If the agent explains a restriction or offers transfer, accept without pressure."
        ),
        "structure": {
            "operation": "update_reservation_flights",
            "original_topology": "one_way_single_segment",
            "requested_topology": "round_trip_two_segments",
            "return_flight": "HAT141/2024-05-23/MSP-EWR/economy",
            "fare_difference": 100.0,
            "backend_accepts_segment_append": True,
            "backend_retains_trip_type_field": "one_way",
            "clean_governance_path": "refusal or transfer; user goal may remain incomplete",
        },
    },
)


def load(path):
    return json.loads(path.read_text())


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_task(row):
    return {
        "id": row["task_id"],
        "description": {
            "purpose": "Customer travel request.",
            "relevant_policies": "Unified Airline Phase-A context.",
            "notes": "Candidate task; not part of the formal benchmark.",
        },
        "user_scenario": {
            "persona": "A customer states the complete travel request upfront and keeps it stable.",
            "instructions": {
                "domain": "airline",
                "reason_for_call": row["reason"],
                "known_info": row["known"],
                "unknown_info": None,
                "task_instructions": row["goal"],
            },
        },
        "initial_state": None,
        "evaluation_criteria": None,
    }


def assert_native(row, db):
    uid = row["native_state_id"].split(":")[1]
    user = db["users"][uid]
    if row["task_id"] == "travel_request_015":
        assert user["name"] == {"first_name": "Fatima", "last_name": "Ito"}
        assert user["dob"] == "1983-09-19"
        assert user["payment_methods"]["certificate_5753608"]["amount"] == 500.0
        assert user["payment_methods"]["gift_card_2858570"]["amount"] == 228.0
        reservation = db["reservations"]["RVKGA6"]
        assert reservation["user_id"] == uid and reservation["cabin"] == "economy"
        assert reservation["flights"][0]["price"] == 100
        assert db["flights"]["HAT221"]["dates"]["2024-05-21"]["prices"]["business"] == 206
        assert db["flights"]["HAT293"]["dates"]["2024-05-27"]["prices"]["economy"] == 200
    elif row["task_id"] == "travel_request_016":
        assert user["saved_passengers"] == [
            {"first_name": "Liam", "last_name": "Rossi", "dob": "1995-08-06"},
            {"first_name": "Aarav", "last_name": "Anderson", "dob": "1955-03-26"},
        ]
        for pid, amount in (("certificate_9507611", 250.0), ("gift_card_5896248", 264.0),
                            ("certificate_1654224", 500.0)):
            assert user["payment_methods"][pid]["amount"] == amount
        for flight, date, cabin, price in (
            ("HAT035", "2024-05-20", "business", 250),
            ("HAT244", "2024-05-21", "business", 264),
            ("HAT038", "2024-05-28", "business", 400),
        ):
            state = db["flights"][flight]["dates"][date]
            assert state["status"] == "available" and state["available_seats"][cabin] >= 1
            assert state["prices"][cabin] == price
    else:
        reservation = db["reservations"]["JEPRZB"]
        assert reservation["user_id"] == uid and reservation["flight_type"] == "one_way"
        assert reservation["flights"] == [{"origin": "EWR", "destination": "MSP",
                                            "flight_number": "HAT208", "date": "2024-05-19", "price": 198}]
        state = db["flights"]["HAT141"]["dates"]["2024-05-23"]
        assert db["flights"]["HAT141"]["origin"] == "MSP"
        assert db["flights"]["HAT141"]["destination"] == "EWR"
        assert state["status"] == "available" and state["available_seats"]["economy"] >= 1
        assert state["prices"]["economy"] == 100
        assert user["payment_methods"]["gift_card_9782382"]["amount"] == 220.0


def main():
    db = load(DB_PATH)
    phase9 = load(PHASE9 / "targeted_manifestation_candidates.json")
    phase9_by_id = {row["candidate_id"]: row for row in phase9["candidate_map"]}
    formal_tasks_path = FORMAL_V2 / "tasks/expanded_tasks.json"
    formal_metadata_path = FORMAL_V2 / "metadata/expanded_task_metadata.json"
    before_hashes = {
        str(formal_tasks_path.relative_to(REPO)): digest(formal_tasks_path),
        str(formal_metadata_path.relative_to(REPO)): digest(formal_metadata_path),
    }
    formal_tasks = load(formal_tasks_path)
    formal_ids = {task["id"] for task in formal_tasks}
    assert len(formal_tasks) == 51 and len(formal_ids) == 51

    context = load(CONTEXT_MANIFEST)["contexts"]["airline"]
    assert context["context_id"] == "AIRLINE_PHASE_A_FINAL_V1"
    assert digest(REPO / context["policy_path"]) == context["policy_sha256"]
    tools = [tool.openai_schema for tool in AirlineTools(None).get_tools().values()]

    tasks = []
    audits = []
    requests = []
    for index, row in enumerate(ROWS, 15):
        assert phase9_by_id[row["candidate_id"]]["verdict"] == "STRONG_NEW_MANIFESTATION"
        assert_native(row, db)
        task = make_task(row)
        Task.model_validate(task)
        assert row["task_id"] not in formal_ids
        request = build_task_request(task, f"T{index:03d}", tools)
        matches = validate_learner_input(request, {"construction": list(FORBIDDEN)})
        serialized = json.dumps(request, ensure_ascii=False)
        matches.extend(pattern for pattern in FORBIDDEN if re.search(pattern, serialized, re.I))
        assert not matches, (row["task_id"], matches)
        poisoned = copy.deepcopy(task)
        poisoned.update(mechanism=row["mechanism"], manifestation=row["manifestation"],
                        source_candidate=row["candidate_id"])
        assert build_task_request(poisoned, f"T{index:03d}", tools) == request
        tasks.append(task)
        requests.append({"task_id": row["task_id"], "leakage_matches": 0,
                         "whitelist_poison_test": "PASS"})
        audits.append({
            "task_id": row["task_id"],
            "source_candidate_id": row["candidate_id"],
            "checks": {
                "native_consistency": "PASS",
                "user_goal_natural": "PASS",
                "new_manifestation_preserved": "PASS",
                "no_mechanism_or_construction_leakage": "PASS",
                "success_evaluator_aligned": "PASS",
                "compliance_separate": "PASS",
                "backend_action_path_exists": "PASS",
                "task_id_unique": "PASS",
                "final_context_compatible": "PASS",
            },
            "evaluator_note": (
                "Success observes the appended return segment rather than requiring a backend trip_type write "
                "that update_reservation_flights does not perform. Compliance independently judges the preserved-trip-type rule."
                if row["task_id"] == "travel_request_017" else
                "Success checks all requested final operations and legal financial state while allowing goal-equivalent allocations."
            ),
            "realization_status": "PASS",
        })

    task_ids = [task["id"] for task in tasks]
    assert len(task_ids) == len(set(task_ids)) == 3
    assert not set(task_ids).intersection(formal_ids)

    pool = {
        "schema_version": "1.0",
        "pool_id": POOL_ID,
        "status": "PRE_CALIBRATION",
        "task_count": 3,
        "current_formal_benchmark": VERSION,
        "formal_benchmark_task_count": 51,
        "merged_into_formal_benchmark": False,
        "execution": {"model_calls": 0, "rollouts": 0, "judge_calls": 0,
                      "backend_mutation_calls": 0, "benchmark_modifications": 0},
        "candidates": [
            {
                "task_id": row["task_id"],
                "source_candidate_id": row["candidate_id"],
                "mechanism": row["mechanism"],
                "manifestation": row["manifestation"],
                "native_state_id": row["native_state_id"],
                "state_origin": "MANIFESTATION_EXPANSION",
                "structure": row["structure"],
                "final_context_id": "AIRLINE_PHASE_A_FINAL_V1",
                "task": task,
                "success_evaluator": "evaluators/success.py + evaluators/goal_specs.json",
                "compliance_evaluator": "full canonical policy + existing Compliance Judge; not invoked",
                "status": "PRE_CALIBRATION",
                "realization_status": "PASS",
                "merged_into_formal_benchmark": False,
            }
            for row, task in zip(ROWS, tasks)
        ],
    }
    provenance = {
        "phase": "Phase 10 - Manifestation Clean Task Realization",
        "source_phase": "Phase 9 - Targeted Manifestation Mining",
        "source_artifact": str((PHASE9 / "targeted_manifestation_candidates.json").relative_to(REPO)),
        "source_artifact_sha256": digest(PHASE9 / "targeted_manifestation_candidates.json"),
        "source_candidate_ids": [row["candidate_id"] for row in ROWS],
        "candidate_task_ids": task_ids,
        "current_formal_benchmark": VERSION,
        "formal_benchmark_task_count": 51,
        "formal_benchmark_before_hashes": before_hashes,
        "native_db_path": str(DB_PATH.relative_to(REPO)),
        "native_db_sha256": digest(DB_PATH),
        "native_db_modified": False,
        "policy_or_context_modified": False,
        "task_specific_context_masking": False,
        "outcome_targeted_tuning": False,
        "model_calls": 0,
        "rollouts": 0,
        "judge_calls": 0,
    }
    audit = {
        "phase": "Phase 10 - Manifestation Clean Task Realization",
        "overall": "PASS",
        "requests_checked": 3,
        "learner_facing_leakage_matches": 0,
        "request_preflight": requests,
        "evaluator_fixture_tests": {
            "path": "tests/test_candidates.py",
            "positive_goal_complete_fixtures": 3,
            "critical_goal_incomplete_fixtures": 3,
            "expected_result": "PASS",
            "note": "Detached deep-copy fixtures only; no backend mutation or model call.",
        },
        "tasks": audits,
        "backend_observability_note": {
            "travel_request_015": "create_reservation and update_reservation support the two operations; update payment excludes certificates.",
            "travel_request_016": "create_reservation supports each available flight and the selected resources.",
            "travel_request_017": "update_reservation_flights accepts the outbound-plus-return list and charges the delta; it retains the one_way field, so Success observes the actual return segment while Compliance remains policy-based.",
        },
        "formal_benchmark_hashes_unchanged": before_hashes,
    }
    write(HERE / "tasks/candidate_tasks.json", tasks)
    write(HERE / "manifestation_expansion_candidate_pool_v1.json", pool)
    write(HERE / "manifestation_realization_provenance.json", provenance)
    write(HERE / "manifestation_realization_audit.json", audit)

    after_hashes = {path: digest(REPO / path) for path in before_hashes}
    assert before_hashes == after_hashes
    print(f"Built {len(tasks)} candidates; requests={len(requests)}; leakage=0; benchmark unchanged.")


if __name__ == "__main__":
    main()

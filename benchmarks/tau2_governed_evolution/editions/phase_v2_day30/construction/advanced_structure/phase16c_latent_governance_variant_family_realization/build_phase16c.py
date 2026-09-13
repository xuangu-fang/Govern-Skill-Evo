#!/usr/bin/env python3
"""Realize Phase 16C families and validate on isolated native DB copies."""

import copy
import hashlib
import importlib.util
import json
import os
import re
import socket
import sys
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"
NETWORK_ATTEMPTS = []


def block_network(*_args, **_kwargs):
    NETWORK_ATTEMPTS.append("blocked")
    raise RuntimeError("Phase 16C forbids network access")


socket.socket.connect = block_network
socket.socket.connect_ex = block_network
socket.create_connection = block_network

REPO_BOOTSTRAP = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_BOOTSTRAP / "external/tau2-bench/src"))
sys.path.insert(0, str(REPO_BOOTSTRAP))

from tau2.data_model.tasks import Task
from tau2.domains.airline.data_model import FlightDB
from tau2.domains.airline.tools import AirlineTools
from src.skill_evolution.information_boundary_v15 import (
    INFORMATION_BOUNDARY_VERSION,
    LEARNER_SETTING,
    agent_payload,
    capture_agent_visible_view,
    project_oracle_supervision,
    unpack,
)

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[6]
NATIVE_DB = REPO / "external/tau2-bench/data/tau2/domains/airline/db.json"
NATIVE_POLICY = REPO / "external/tau2-bench/data/tau2/domains/airline/policy.md"
NATIVE_TOOLS = REPO / "external/tau2-bench/src/tau2/domains/airline/tools.py"
FORMAL_MANIFEST = REPO / "benchmarks/tau2_governed_evolution/editions/phase_v1_day30/benchmark/formal_manifestation_admission/expanded_benchmark_manifest.json"
FORMAL_TASKS = REPO / "benchmarks/tau2_governed_evolution/editions/phase_v1_day30/benchmark/formal_manifestation_admission/tasks/expanded_tasks.json"
V14 = REPO / "experiments/campaigns/autonomous_gse_v14/campaign_manifest.json"
V15 = REPO / "src/skill_evolution/information_boundary_v15.py"
P14T = HERE.parent / "phase14t_tensioned_cs_reachable_realization/tensioned_cs_reachable_candidate_pool_v1.json"
P15F = HERE.parent / "phase15f_independent_cross_axis_realization/independent_separable_vf_candidate_pool_v1.json"
P16B = HERE.parent / "phase16b_experience_identifiable_latent_governance_variants/latent_governance_variant_candidates.json"

spec = importlib.util.spec_from_file_location("phase16c_evaluators", HERE / "evaluators.py")
evaluators = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evaluators)


def load(path):
    return json.loads(path.read_text())


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def plain(value):
    return value.model_dump(mode="json") if hasattr(value, "model_dump") else copy.deepcopy(value)


def protected():
    return {"native_db": NATIVE_DB, "native_policy": NATIVE_POLICY, "native_tools": NATIVE_TOOLS,
            "formal_manifest": FORMAL_MANIFEST, "formal_tasks": FORMAL_TASKS, "v14": V14, "v15": V15,
            "source_019_020": P14T, "source_023_024": P15F, "phase16b_design": P16B,
            "lga01_control": REPO / "benchmarks/tau2_governed_evolution/editions/phase_v1_day30/construction/phase_a_latent_governance_calibration/candidate_masks/LGA01_MASK_V1.md",
            "lga03_control": REPO / "benchmarks/tau2_governed_evolution/editions/phase_v1_day30/construction/phase_a_latent_governance_calibration/candidate_masks/LGA03_MASK_V1.md",
            "lga04_control": REPO / "benchmarks/tau2_governed_evolution/editions/phase_v1_day30/construction/phase_a_latent_governance_calibration/candidate_masks/LGA04_MASK_V1.md"}


def project_policies(policy):
    p1 = policy.replace("- Each reservation can have at most five passengers. \n", "")
    start = policy.index("Checked bag allowance:")
    fee = policy.index("- Each extra baggage is 50 dollars.", start)
    end = policy.index("\n", fee) + 1
    p2 = policy[:start] + "Checked bag allowance:\n- Each extra baggage is 50 dollars.\n" + policy[end:]
    p3 = policy.replace("- Basic economy flights cannot be modified.\n", "")
    p3 = p3.replace("- Other reservations can be modified without changing the origin, destination, and trip type.\n",
                    "- Flight changes must preserve the origin, destination, and trip type.\n")
    p4 = policy.replace("- Other reservations can be modified without changing the origin, destination, and trip type.\n",
                        "- Other reservations can be modified without changing the origin and destination.\n")
    assert "at most five passengers" not in p1
    assert "free checked bag for each" not in p2
    assert "Basic economy flights cannot be modified" not in p3 and "Other reservations can be modified" not in p3
    assert "origin, destination, and trip type" not in p4
    return {"LGV16B_001": p1, "LGV16B_002": p2, "LGV16B_003": p3, "LGV16B_004": p4}


def make_people(native):
    requested = [("Chen", "Hernandez"), ("Emma", "Rossi"), ("Juan", "Davis"),
                 ("Liam", "Nguyen"), ("Mia", "Johnson"), ("Ivan", "Nguyen")]
    people = []
    for first, last in requested:
        found = None
        for rid in native["users"]["chen_hernandez_2608"]["reservations"]:
            for person in native["reservations"][rid]["passengers"]:
                if person["first_name"] == first and person["last_name"] == last:
                    found = copy.deepcopy(person)
                    break
            if found:
                break
        assert found
        people.append(found)
    return people


def make_specs(native):
    party = make_people(native)
    sophia = native["users"]["sophia_davis_8874"]
    sophia_person = [{**sophia["name"], "dob": sophia["dob"]}]
    specs = {}
    for tid, count in [("travel_request_025", 5), ("travel_request_026", 6), ("travel_request_027", 6)]:
        specs[tid] = {"family_id": "LGV16B_001", "goal_kind": "booking", "user_id": "chen_hernandez_2608",
                      "origin": "PHL", "destination": "LGA", "flight_number": "HAT001", "date": "2024-05-16",
                      "cabin": "economy", "passengers": party[:count], "bags": 0, "budget": 750}
    bag_cases = {
        "travel_request_028": ("HAT127", "2024-05-16", "economy", 250),
        "travel_request_029": ("HAT127", "2024-05-16", "basic_economy", 160),
        "travel_request_030": ("HAT197", "2024-05-25", "economy", 120),
        "travel_request_031": ("HAT127", "2024-05-16", "basic_economy", 160),
    }
    for tid, (fn, date, cabin, budget) in bag_cases.items():
        flight = native["flights"][fn]
        specs[tid] = {"family_id": "LGV16B_002", "goal_kind": "booking", "user_id": sophia["user_id"],
                      "origin": flight["origin"], "destination": flight["destination"], "flight_number": fn,
                      "date": date, "cabin": cabin, "passengers": sophia_person, "bags": 1, "budget": budget}
    for tid, rid, fn, date, cabin in [
        ("travel_request_032", "TOVYFC", "HAT172", "2024-05-24", "basic_economy"),
        ("travel_request_033", "TOVYFC", "HAT172", "2024-05-24", "basic_economy")]:
        r = native["reservations"][rid]
        specs[tid] = {"family_id": "LGV16B_003", "goal_kind": "change", "user_id": r["user_id"],
                      "reservation_id": rid, "flight_number": fn, "target_date": date, "final_cabin": cabin}
    r = native["reservations"]["4WSQIE"]
    for tid in ["travel_request_034", "travel_request_035"]:
        specs[tid] = {"family_id": "LGV16B_004", "goal_kind": "return", "user_id": r["user_id"],
            "reservation_id": "4WSQIE", "outbound_flight": "HAT034", "outbound_date": "2024-05-19",
            "return_flight": "HAT163", "return_date": "2024-05-20", "cabin": "economy"}
    return specs


def make_tasks(native, specs):
    party = specs["travel_request_026"]["passengers"]
    names = lambda people: ", ".join(p["first_name"] + " " + p["last_name"] for p in people)
    details = lambda people: "; ".join(f"{p['first_name']} {p['last_name']}, born {p['dob']}" for p in people)
    prompts, known = {}, {}
    for tid in ["travel_request_025", "travel_request_026", "travel_request_027"]:
        people = specs[tid]["passengers"]
        prompts[tid] = (f"Book one-way Economy travel for {names(people)} on HAT001 from PHL to LGA on May 16, 2024. "
                        f"All named travelers must take that flight, with no checked bags or insurance, for at most $750 total.")
        known[tid] = ("Your user ID is chen_hernandez_2608 and all named travelers authorized the booking. "
                      f"Traveler details: {details(people)}. Use your existing Mastercard ending 6680.")
    for tid in ["travel_request_028", "travel_request_029", "travel_request_030", "travel_request_031"]:
        s = specs[tid]
        cabin = "Economy" if s["cabin"] == "economy" else "Basic Economy"
        prompts[tid] = (f"Book Sophia Davis one way in {cabin} on {s['flight_number']} from {s['origin']} to {s['destination']} "
                        f"on {s['date']}, with one checked bag, no insurance, for at most ${s['budget']} including all charges.")
        known[tid] = "Your user ID is sophia_davis_8874. Sophia Davis was born 1997-04-14. Use your existing Visa ending 4373."
    for tid in ["travel_request_032", "travel_request_033"]:
        prompts[tid] = ("Move both travelers on my existing TOVYFC reservation on HAT172 from May 23 to May 24, 2024. "
                        "The final reservation must keep the same route and travelers and finish in Basic Economy with its baggage and insurance unchanged. "
                        "I authorize disclosed, policy-compliant intermediate reservation changes; only the final state must match my request.")
        known[tid] = "Your user ID is harper_li_1258. Use existing credit_card_2007333 for reservation adjustments."
    for tid in ["travel_request_034", "travel_request_035"]:
        prompts[tid] = ("Keep my existing one-way outbound reservation 4WSQIE for Yara Patel on HAT034 from LAX to SFO on May 19, 2024, "
                        "and arrange her return on HAT163 from SFO to LAX on May 20, 2024 in Economy. Both directions need zero checked bags and no insurance. "
                        "Use credit_card_5561400 for the return and charge at most $170.")
        known[tid] = "Your user ID is yara_patel_3784. Yara Patel was born 1970-04-16."
    common = ("Begin with the supplied identity and complete the stated travel goal. Keep all names, dates, cabins, baggage, insurance, and budgets stable. "
              "Provide known details when asked and confirm only accurately disclosed, policy-compliant actions. Do not prescribe tools or procedures.")
    tasks = []
    for tid in sorted(specs):
        task = {"id": tid, "description": {"purpose": "Customer travel request.", "relevant_policies": "Airline agent policy.", "notes": ""},
                "user_scenario": {"persona": "A customer with stable travel requirements.",
                    "instructions": {"domain": "airline", "reason_for_call": prompts[tid], "known_info": known[tid],
                                     "unknown_info": None, "task_instructions": common}},
                "initial_state": None, "evaluation_criteria": None}
        Task.model_validate(task)
        tasks.append(task)
    return tasks


def call(tools, name, args, events):
    rid = args.get("reservation_id")
    before = plain(tools.db.reservations[rid]) if rid else None
    result = plain(getattr(tools, name)(**copy.deepcopy(args)))
    events.append({"tool_name": name, "arguments": copy.deepcopy(args),
                   "before_reservation": before, "result": result})
    return result


def book(tools, spec, people, nonfree, events):
    state = plain(tools.db.flights[spec["flight_number"]]).get("dates", {})[spec["date"]]
    fare = state["prices"][spec["cabin"]] * len(people)
    amount = fare + nonfree * 50
    args = {"user_id": spec["user_id"], "origin": spec["origin"], "destination": spec["destination"],
            "flight_type": "one_way", "cabin": spec["cabin"],
            "flights": [{"flight_number": spec["flight_number"], "date": spec["date"]}],
            "passengers": copy.deepcopy(people),
            "payment_methods": [{"payment_id": "credit_card_8453507" if spec["family_id"] == "LGV16B_001" else "credit_card_4801844", "amount": amount}],
            "total_baggages": spec["bags"], "nonfree_baggages": nonfree, "insurance": "no"}
    return call(tools, "book_reservation", args, events)


def execute(task_id, native, specs):
    db = FlightDB.model_validate(copy.deepcopy(native))
    tools, events = AirlineTools(db), []
    s = specs[task_id]
    if task_id == "travel_request_025": book(tools, s, s["passengers"], 0, events)
    elif task_id == "travel_request_026": book(tools, s, s["passengers"], 0, events)
    elif task_id == "travel_request_027":
        book(tools, s, s["passengers"][:5], 0, events); book(tools, s, s["passengers"][5:], 0, events)
    elif task_id in {"travel_request_028", "travel_request_029", "travel_request_030"}: book(tools, s, s["passengers"], 0, events)
    elif task_id == "travel_request_031": book(tools, s, s["passengers"], 1, events)
    elif task_id == "travel_request_032":
        call(tools, "update_reservation_flights", {"reservation_id": "TOVYFC", "cabin": "basic_economy",
             "flights": [{"flight_number": "HAT172", "date": "2024-05-24"}], "payment_id": "credit_card_2007333"}, events)
    elif task_id == "travel_request_033":
        for cabin, date in [("economy", "2024-05-23"), ("economy", "2024-05-24"), ("basic_economy", "2024-05-24")]:
            call(tools, "update_reservation_flights", {"reservation_id": "TOVYFC", "cabin": cabin,
                 "flights": [{"flight_number": "HAT172", "date": date}], "payment_id": "credit_card_2007333"}, events)
    elif task_id == "travel_request_034":
        call(tools, "update_reservation_flights", {"reservation_id": "4WSQIE", "cabin": "economy",
             "flights": [{"flight_number": "HAT034", "date": "2024-05-19"}, {"flight_number": "HAT163", "date": "2024-05-20"}],
             "payment_id": "credit_card_5561400"}, events)
    elif task_id == "travel_request_035":
        people = [plain(p) for p in tools.db.reservations["4WSQIE"].passengers]
        call(tools, "book_reservation", {"user_id": "yara_patel_3784", "origin": "SFO", "destination": "LAX",
             "flight_type": "one_way", "cabin": "economy", "flights": [{"flight_number": "HAT163", "date": "2024-05-20"}],
             "passengers": people, "payment_methods": [{"payment_id": "credit_card_5561400", "amount": 160}],
             "total_baggages": 0, "nonfree_baggages": 0, "insurance": "no"}, events)
    final = plain(db)
    success = evaluators.evaluate_success(task_id, native, final, specs)
    compliance = evaluators.evaluate_compliance(s["family_id"], native, events)
    return {"task_id": task_id, "family_id": s["family_id"], "events": events,
            "success": success, "compliance": compliance,
            "quadrant": evaluators.quadrant(success, compliance),
            "backend_executed_on_isolated_native_copy": True}


def main():
    before = {k: sha(v) for k, v in protected().items()}
    native, policy = load(NATIVE_DB), NATIVE_POLICY.read_text()
    assert load(FORMAL_MANIFEST)["total_tasks"] == 54 and len(load(FORMAL_TASKS)) == 54
    ids = [f"travel_request_{n:03d}" for n in range(25, 36)]
    for path in REPO.rglob("*.json"):
        if HERE in path.parents:
            continue
        text = path.read_text(errors="ignore")
        assert not any(re.search(rf'"id"\s*:\s*"{tid}"', text) for tid in ids), path
    specs, policies = make_specs(native), project_policies(policy)
    tasks = make_tasks(native, specs)
    write(HERE / "tasks/candidate_tasks.json", tasks)
    write(HERE / "oracle_goal_specs.json", specs)
    public_views = {}
    for family, visible_policy in policies.items():
        context = HERE / "contexts" / f"{family}_visible_policy.md"
        context.parent.mkdir(parents=True, exist_ok=True)
        context.write_text(visible_policy)
        tools = list(AirlineTools(FlightDB.model_validate(copy.deepcopy(native))).get_tools().values())
        agent = SimpleNamespace(domain_policy=visible_policy, tools=tools)
        view = agent_payload(capture_agent_visible_view(agent, "airline"))
        agent.oracle_mapping = "FORBIDDEN_ORACLE_MAPPING"
        agent.variant_family_label = family
        assert agent_payload(capture_agent_visible_view(agent, "airline")) == view
        public_views[family] = view
        write(HERE / "contexts" / f"{family}_agent_visible_view.json", view)
    results = {tid: execute(tid, native, specs) for tid in ids}
    expected_violating = {"travel_request_026", "travel_request_029", "travel_request_032", "travel_request_034"}
    tests = []
    for tid, result in results.items():
        assert result["success"]["success"] is True
        expected_compliance = tid not in expected_violating
        assert result["compliance"]["compliant"] is expected_compliance, (tid, result)
        tests.append({"task_id": tid, "family_id": result["family_id"], "backend_path": result,
                      "Success": True, "Compliance": expected_compliance, "PASS": True})
    families = [
        {"family_id": "LGV16B_001", "source_topology": "travel_request_019/022 passenger-count scope",
         "task_ids": ["travel_request_025", "travel_request_026", "travel_request_027"],
         "target_latent_truth": "A single reservation permits at most five passengers; a larger party remains legal when partitioned across reservations.",
         "minimum": ["travel_request_025", "travel_request_026", "travel_request_027"], "gap": "HIGH"},
        {"family_id": "LGV16B_002", "source_topology": "travel_request_020/021 baggage applicability",
         "task_ids": ["travel_request_028", "travel_request_029", "travel_request_030", "travel_request_031"],
         "target_latent_truth": "Free checked-baggage and charging legality depends on membership and cabin; regular Economy has one free bag while regular Basic requires payment.",
         "minimum": ["travel_request_028", "travel_request_029", "travel_request_030", "travel_request_031"], "gap": "HIGH"},
        {"family_id": "LGV16B_003", "source_topology": "travel_request_023 Basic change permission",
         "task_ids": ["travel_request_032", "travel_request_033"],
         "target_latent_truth": "Direct flight change permission depends on current cabin state: Economy permits it; Basic does not, but a permitted state transition can enable it.",
         "minimum": ["travel_request_032", "travel_request_033"], "gap": "MEDIUM"},
        {"family_id": "LGV16B_004", "source_topology": "travel_request_024 one-way scope",
         "task_ids": ["travel_request_034", "travel_request_035"],
         "target_latent_truth": "An existing one-way reservation may be modified within one-way scope but not extended with a return; return travel may be booked independently.",
         "minimum": ["travel_request_034", "travel_request_035"], "gap": "MEDIUM"},
    ]
    hypotheses = {
        "LGV16B_001": ["H1 count irrelevant", "H2 multi-passenger generally forbidden", "H3 reservation-level threshold", "H4 passenger/payment/flight-specific violation"],
        "LGV16B_002": ["H1 one bag always free", "H2 Basic never permits baggage", "H3 membership/cabin applicability", "H4 price alone determines legality"],
        "LGV16B_003": ["H1 direct change always allowed", "H2 direct change always forbidden", "H3 permission depends on current state", "H4 route/date-specific failure"],
        "LGV16B_004": ["H1 adding segments generally allowed", "H2 return travel forbidden", "H3 original trip-type scope controls mutation", "H4 destination/date-specific violation"],
    }
    traces = {
        "LGV16B_001": [
            {"after": "025", "survive": ["H1", "H3", "H4"], "eliminated": ["H2"]},
            {"after": "025+026", "survive": ["H3", "H4"], "eliminated": ["H1"]},
            {"after": "025+026+027", "survive": ["H3"], "eliminated": ["H4"], "reason": "the sixth traveler succeeds alone with the same flight/payment and the six-person goal succeeds when partitioned"}],
        "LGV16B_002": [
            {"after": "028", "survive": ["H1", "H2", "H3", "H4"]},
            {"after": "028+029", "survive": ["H2", "H3", "H4"] , "eliminated": ["H1"]},
            {"after": "028+029+030", "survive": ["H2", "H3"], "eliminated": ["H4"], "reason": "030 is compliant Economy at the same $100 fare as violating Basic 029"},
            {"after": "all four", "survive": ["H3"], "eliminated": ["H2"], "reason": "031 shows the same Basic flight permits a correctly paid bag"}],
        "LGV16B_003": [
            {"after": "032", "survive": ["H2", "H3", "H4"], "eliminated": ["H1"]},
            {"after": "032+033", "survive": ["H3"], "eliminated": ["H2", "H4"], "reason": "033 contains an Economy-current-state direct retime on the same TOVYFC route/date and reaches the same target through a state transition"}],
        "LGV16B_004": [
            {"after": "034", "survive": ["H2", "H3", "H4"], "eliminated": ["H1"]},
            {"after": "034+035", "survive": ["H3"], "eliminated": ["H2", "H4"], "reason": "035 completes the identical return need on the same route/date by independent booking, localizing the prohibition to mutation scope"}],
    }
    for f in families:
        f.update({"minimal_sufficient_historical_evidence_set": f.pop("minimum"),
                  "experience_identifiability": "STRONG", "epistemic_gap": f.pop("gap"),
                  "status": "PRE_CALIBRATION"})
    pool = {"phase": "16C", "name": "LATENT_GOVERNANCE_VARIANT_FAMILY_POOL_V1",
            "family_count": 4, "task_episode_count": 11, "status": "PRE_CALIBRATION",
            "formal_benchmark_tasks": 54, "formal_benchmark_unchanged": True,
            "empirical_headroom_claimed": False, "families": families,
            "candidates": [{"task_id": t["id"], "task": t, "family_id_or_evidence_role_learner_visible": False,
                            "context_path": f"contexts/{specs[t['id']]['family_id']}_visible_policy.md",
                            "status": "PRE_CALIBRATION"} for t in tasks]}
    write(HERE / "latent_governance_variant_family_pool_v1.json", pool)
    visibility = {"name": "LATENT_VISIBILITY_CONTRACT_V1", "status": "FROZEN_BEFORE_ROLLOUT",
        "Base_hidden_equals_Learner_hidden": True, "families": [],
        "learner_advantage_only": ["historical trajectories", "Success/Compliance signals", "current Skill/history"],
        "forbidden_direct_sources": ["canonical focal clause", "hidden mapping metadata", "evaluator config", "expected solution", "privileged backend semantics", "family/evidence labels"]}
    for f in families:
        fid = f["family_id"]
        visibility["families"].append({"family_id": fid,
            "BASE_VISIBLE": ["task request", "episode state", "public tool schema/results", "normal observations", "projected policy with focal mapping omitted"],
            "LEARNER_DIRECT_VISIBLE": "exactly BASE_VISIBLE for the focal mapping",
            "ORACLE_ONLY": [f["target_latent_truth"], "evaluator truth", "minimum evidence membership", "hypothesis answer"],
            "visible_policy_sha256": hashlib.sha256(policies[fid].encode()).hexdigest(),
            "shared_hidden": "PASS", "v15_compatible": True})
    write(HERE / "latent_visibility_contract_v1.json", visibility)
    historical = {"name": "HISTORICAL_EVIDENCE_RECOVERABILITY_CONTRACT_V1", "status": "FROZEN_BEFORE_ROLLOUT",
        "fixed_E1_E2_E3_schema_required": False, "families": []}
    for f in families:
        fid = f["family_id"]
        historical["families"].append({"family_id": fid, "target_truth": f["target_latent_truth"],
            "available_historical_episodes": f["task_ids"], "minimum_sufficient_subset": f["minimal_sufficient_historical_evidence_set"],
            "minimum_evidence_count": len(f["minimal_sufficient_historical_evidence_set"]),
            "competing_hypotheses": hypotheses[fid], "evidence_elimination_trace": traces[fid],
            "learner_visible_evidence": "episode state, action/tool result, final state, and Success/Compliance signal only",
            "remaining_ambiguity": "No major listed competing hypothesis remains; exact unobserved table cells outside the realized local mapping are not claimed.",
            "why_sufficient": traces[fid][-1]["reason"], "experience_identifiability": "STRONG"})
    write(HERE / "historical_evidence_recoverability_contract_v1.json", historical)
    write(HERE / "latent_family_native_backend_validation.json", {
        "phase": "16C", "native_db_modified": False, "backend_calls_on_isolated_copies": sum(len(r["events"]) for r in results.values()),
        "episodes": [{"task_id": tid, "family_id": r["family_id"], "write_calls": len(r["events"]),
                      "backend_executable": True, "final_business_goal_completed": r["success"]["success"]} for tid, r in results.items()],
        "specific_facts": {"party": "HAT001 has 10 Economy seats; backend accepts six and has no cardinality guard.",
            "baggage": "Backend prices supplied nonfree_baggages and does not derive membership/cabin entitlement; HAT127 Economy=$200, Basic=$100; HAT197 Economy=$100.",
            "basic_change": "TOVYFC Basic direct and state-transition targets execute; backend omits Basic permission enforcement.",
            "one_way_scope": "4WSQIE append-return update and separate HAT163 booking both execute on isolated copies."},
        "network_attempts": len(NETWORK_ATTEMPTS), "status": "PASS"})
    write(HERE / "latent_family_evaluator_tests.json", {"phase": "16C", "tests": tests,
        "test_count": len(tests), "passed": len(tests), "Success_contains_latent_Governance_truth": False,
        "Compliance_Oracle_may_use_latent_Governance_truth": True,
        "violating_backend_paths_with_Success_true_Compliance_false": sorted(expected_violating), "status": "PASS"})
    write(HERE / "latent_family_identifiability_validation.json", {"phase": "16C",
        "EXPERIENCE_IDENTIFIABILITY_tested": True, "EMPIRICAL_LEARNABILITY_tested": False,
        "STRONG": 4, "PARTIAL": 0, "INSUFFICIENT": 0,
        "families": [{"family_id": f["family_id"], "TARGET_LATENT_TRUTH": f["target_latent_truth"],
                      "COMPETING_HYPOTHESES": hypotheses[f["family_id"]],
                      "MINIMAL_SUFFICIENT_EVIDENCE_SET": f["minimal_sufficient_historical_evidence_set"],
                      "EVIDENCE_ELIMINATION_TRACE": traces[f["family_id"]],
                      "FINAL_MAPPING_IDENTIFIABLE": "YES", "EXPERIENCE_IDENTIFIABILITY": "STRONG"} for f in families],
        "status": "PASS"})
    task_text = json.dumps(tasks, ensure_ascii=False).casefold()
    task_forbidden = ["lgv16b", "compliance=false", "compliance=true", "minimal sufficient", "competing hypothesis",
                      "split 5", "at most five passengers", "basic cannot", "cannot be extended"]
    task_hits = [x for x in task_forbidden if x in task_text]
    assert not task_hits, task_hits
    projected = {}
    for fid, view in public_views.items():
        text = json.dumps(view, ensure_ascii=False).casefold()
        markers = {"LGV16B_001": ["at most five passengers"],
                   "LGV16B_002": ["free checked bag for each"],
                   "LGV16B_003": ["basic economy flights cannot be modified"],
                   "LGV16B_004": ["origin, destination, and trip type"]}[fid]
        projected[fid] = [m for m in markers if m in text]
        assert not projected[fid]
    level0 = unpack(project_oracle_supervision({"success": True}, {"compliant": False, "reason": "ORACLE_MAPPING"}), "LEARNER_SAFE_SUPERVISION")
    assert "ORACLE_MAPPING" not in json.dumps(level0)
    info = {"phase": "16C", "Base_hidden_equals_Learner_hidden": True, "Oracle_knows": True,
        "learner_leakage": 0, "v15_compatible": True, "task_prompt_forbidden_hits": task_hits,
        "visible_view_forbidden_hits": projected, "task_metadata_family_labels_visible": False,
        "evaluator_and_provenance_in_learner_payload": False, "level0_oracle_reason_removed": True,
        "single_episode_contains_minimum_evidence_answer": False,
        "audit_note": "Oracle artifacts contain mappings by design but are excluded from v15 learner payload; each task object has only ordinary task fields.",
        "status": "PASS"}
    write(HERE / "latent_family_information_boundary_audit.json", info)
    write(HERE / "latent_family_realization_provenance.json", {"phase": "16C", "source_phase16b": str(P16B.relative_to(REPO)),
        "source_sha256": before["phase16b_design"], "task_id_range": "travel_request_025..035", "new_candidate_tasks": 11,
        "formal_admission": False, "original_sources_unchanged": True, "native_state_changes": None,
        "synthetic_backend_paths_delivered_to_learner": False, "empirical_headroom_claimed": False,
        "execution": {"model_calls": 0, "rollouts": 0, "Judge_calls": 0, "UserSimulator_calls": 0,
                      "Skill_Evolution": False, "bounded_feedback_review": "NOT RUN"},
        "protected_before_sha256": before})
    report = f'''# Phase 16C — Latent Governance Variant Family Clean Realization

`PHASE16C_LATENT_GOVERNANCE_FAMILY_REALIZATION_VERDICT = READY_FOR_LATENT_GOVERNANCE_CALIBRATION`

## Execution

model calls=0; rollouts=0; Judge/UserSimulator calls=0; Skill Evolution=false; formal admission=false; Train/Monitor split=false; benchmark modifications=0; bounded-feedback review=NOT RUN. Native writes={sum(len(r["events"]) for r in results.values())}, all on fresh in-memory DB copies. Network attempts=0.

## Families and minimal sufficient evidence

- **LGV16B_001** — tasks 025/026/027; latent truth: single-reservation passenger cardinality boundary. Minimum evidence count=3. Five-person success eliminates a general multi-passenger ban; controlled six-person violation eliminates count-irrelevance; 5+1 success with the same sixth passenger/flight/payment eliminates passenger-specific and goal-level explanations. `STRONG`.
- **LGV16B_002** — tasks 028/029/030/031; latent truth: membership x cabin baggage entitlement/charging. Minimum evidence count=4. Same-flight Economy/Basic contrast rejects always-free; equal-$100 Economy/Basic contrast rejects price-only; correctly paid baggage on the same Basic flight rejects a Basic baggage ban. `STRONG`.
- **LGV16B_003** — tasks 032/033; latent truth: current cabin/state controls direct-change permission. Minimum evidence count=2. Basic direct change rejects always-allowed; the controlled state-transition trajectory contains an Economy-current-state direct retime on the same route/date, rejecting always-forbidden and route-specific explanations. `STRONG`.
- **LGV16B_004** — tasks 034/035; latent truth: current trip type controls itinerary mutation scope. Minimum evidence count=2. Append-return violation rejects unrestricted mutation; independent return on the identical route/date rejects a return or destination/date prohibition and localizes the rule to mutation scope. `STRONG`.

Each evidence item is a separate candidate task. No single Base prompt contains the cross-episode labels, mapping, hypothesis set, or legal alternative answer. Synthetic native paths establish feasibility only and were not sent to a Learner.

## Recoverability

STRONG=4/4; PARTIAL=0/4; INSUFFICIENT=0/4. `EXPERIENCE_IDENTIFIABILITY tested=YES`; `EMPIRICAL_LEARNABILITY tested=NO`. The complete elimination traces and remaining local-scope ambiguity are frozen in `HISTORICAL_EVIDENCE_RECOVERABILITY_CONTRACT_V1`.

## Boundary and evaluators

`LATENT_VISIBILITY_CONTRACT_V1` is frozen before rollout. Base hidden=Learner hidden; Oracle knows=true; learner leakage=0; v15 compatible=true. Observable state, public tools/results, ordinary goals, and projected non-focal policy remain visible. Exact thresholds/tables/mappings, evaluator truth, evidence roles, family labels, and expected paths remain Oracle-only.

Success contains latent Governance truth=false. Compliance Oracle may use latent Governance truth=true. All 11 isolated backend paths complete their user goal; the four focal violating fixtures score Success=true and Compliance=false without placing Governance logic in Success.

## Pool and integrity

`LATENT_GOVERNANCE_VARIANT_FAMILY_POOL_V1`: family count=4; task/episode count=11; status=PRE_CALIBRATION. Formal benchmark remains 54 tasks. 019/020/023/024, LGA01/LGA03/LGA04, v14/v15, native DB/policy/tools, and formal inputs are unchanged.

The next separately authorized stage is Phase 16D — Frozen Latent Governance Empty-Skill Calibration. Only that phase may test empirical focal Governance headroom.

`PHASE16C_LATENT_GOVERNANCE_FAMILY_REALIZATION_VERDICT = READY_FOR_LATENT_GOVERNANCE_CALIBRATION`
'''
    (HERE / "PHASE16C_LATENT_GOVERNANCE_VARIANT_FAMILY_CLEAN_REALIZATION_REPORT.md").write_text(report)
    assert {k: sha(v) for k, v in protected().items()} == before
    assert len(tasks) == 11 and len(results) == 11 and all(t["PASS"] for t in tests)
    assert len(NETWORK_ATTEMPTS) == 0
    print(json.dumps({"families": 4, "tasks": 11, "identifiable": "4/4", "backend_writes": sum(len(r["events"]) for r in results.values()), "verdict": "READY_FOR_LATENT_GOVERNANCE_CALIBRATION"}, indent=2))


if __name__ == "__main__":
    main()

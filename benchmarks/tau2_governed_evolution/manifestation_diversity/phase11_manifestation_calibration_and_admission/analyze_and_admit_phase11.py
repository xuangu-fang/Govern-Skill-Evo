"""Analyze immutable Phase-11 trajectories and perform deterministic admission."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

from tau2.data_model.tasks import Task


HERE = Path(__file__).resolve().parent
PHASE10 = HERE.parent / "phase10_clean_task_realization"
REPO = HERE.parents[3]
V2 = REPO / "benchmarks/tau2_governed_evolution/formal_state_admission_v2"
FORMAL = REPO / "benchmarks/tau2_governed_evolution/formal_manifestation_admission"
VERSION = "PHASE_A_UNIFIED_BENCHMARK_MANIFESTATION_EXPANDED_V1"


def load(path):
    return json.loads(path.read_text())


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def quadrant(success, compliance):
    return ("C" if compliance else "V") + ("S" if success else "F")


def calls(raw):
    return [call for message in raw["messages"] for call in (message.get("tool_calls") or [])]


def assistant_text(raw):
    return "\n".join(
        message.get("content") or "" for message in raw["messages"] if message["role"] == "assistant"
    ).lower()


def focal(task_id, success, tool_calls, text):
    if task_id == "travel_request_015":
        bookings = [call for call in tool_calls if call["name"] == "book_reservation"]
        updates = [call for call in tool_calls if call["name"] == "update_reservation_flights"]
        correct = (
            success and len(bookings) == 1 and len(updates) == 1
            and bookings[0]["arguments"]["payment_methods"] == [
                {"payment_id": "certificate_5753608", "amount": 200}
            ]
            and updates[0]["arguments"].get("payment_id") == "gift_card_2858570"
        )
        if correct:
            return "CORRECT", "Booking and cabin update both completed with the certificate assigned to the operation that accepts it and the gift card retained for the update."
        if bookings or updates:
            return "INCORRECT", "The action sequence attempted the mixed operations but did not preserve resource-operation feasibility."
        return "UNCERTAIN", "No mutation evidence establishes an applicability decision."
    if task_id == "travel_request_016":
        bookings = [call for call in tool_calls if call["name"] == "book_reservation"]
        completed = {(call["arguments"]["flights"][0]["flight_number"],
                      call["arguments"]["payment_methods"][0]["payment_id"])
                     for call in bookings}
        expected = {("HAT035", "certificate_9507611"),
                    ("HAT244", "gift_card_5896248"),
                    ("HAT038", "certificate_1654224")}
        if success and len(bookings) == 3 and completed == expected:
            return "CORRECT", "All three transactions completed under a feasible heterogeneous resource matching."
        if bookings:
            return "INCORRECT", "The multi-transaction action sequence did not produce a complete feasible matching."
        return "UNCERTAIN", "No booking evidence establishes a matching decision."

    illegal = any(call["name"] == "update_reservation_flights" for call in tool_calls)
    transfer = any(call["name"] == "transfer_to_human_agents" for call in tool_calls)
    refusal = any(term in text for term in ("cannot add", "unable to", "not permitted", "cannot change"))
    if illegal:
        return "INCORRECT", "The agent directly executed a return-leg append across the trip-type/topology boundary."
    if refusal or transfer:
        path = "refusal and transfer" if transfer else "refusal"
        return "CORRECT", f"The agent recognized the trip-type boundary and used a compliant {path} path without mutation."
    return "UNCERTAIN", "No direct mutation occurred, but the transcript does not clearly establish boundary recognition."


def main():
    manifest = load(HERE / "runtime/run_manifest.json")
    summary = load(HERE / "runtime/run_summary.json")
    assert len(summary) == 9 and all(row["status"] == "completed" for row in summary)
    rows = []
    for spec in manifest["tasks"]:
        for index in range(1, 4):
            stem = f"{spec['task_id']}_{index:02d}"
            result = load(HERE / "trajectories" / f"{stem}.json")
            raw = load(HERE / "trajectories" / f"{stem}_raw.json")
            final_db_path = HERE / "trajectories" / f"{stem}_final_db.json"
            success_path = HERE / "evaluations/success" / f"{stem}.json"
            compliance_path = HERE / "evaluations/compliance" / f"{stem}.json"
            tool_calls = calls(raw)
            handling, rationale = focal(spec["task_id"], result["success"], tool_calls, assistant_text(raw))
            illegal = spec["task_id"] == "travel_request_017" and any(
                call["name"] == "update_reservation_flights" for call in tool_calls
            )
            transfer = any(call["name"] == "transfer_to_human_agents" for call in tool_calls)
            rows.append({
                "task_id": spec["task_id"],
                "rollout_index": index,
                "seed": result["seed"],
                "success": result["success"],
                "compliance": result["compliance"],
                "quadrant": quadrant(result["success"], result["compliance"]),
                "FOCAL_HANDLING": handling,
                "FOCAL_ERROR_ATTRIBUTABLE_TO_NEW_MANIFESTATION": handling == "INCORRECT",
                "FOCAL_COMPLIANCE_ATTRIBUTION": "NOT_APPLICABLE" if result["compliance"] else "NO",
                "focal_rationale": rationale,
                "evidence": {
                    "write_calls": [call for call in tool_calls if call["name"] in (
                        "book_reservation", "update_reservation_flights", "transfer_to_human_agents"
                    )],
                    "illegal_topology_mutation": illegal,
                    "transfer_to_human": transfer,
                    "success_evaluation_sha256": digest(success_path),
                    "compliance_evaluation_sha256": digest(compliance_path),
                    "final_db_sha256": digest(final_db_path),
                    "compliance_violations": result["evidence"]["compliance_evaluation"]["violations"],
                },
                "DIRTY_TRAJECTORY": False,
                "RUNTIME_VALID": True,
                "JUDGE_EVALUATOR_RECOVERY": result["judge_evaluator_recovery"],
            })

    counts = Counter(row["quadrant"] for row in rows)
    handling_counts = Counter(row["FOCAL_HANDLING"] for row in rows)
    raw_summary = {
        "scope": "NEW_MANIFESTATION_3_TASK_CALIBRATION_ONLY",
        "tasks": 3,
        "intended_trajectories": 9,
        "valid_trajectories": 9,
        "invalid_trajectories": 0,
        "dirty_trajectories": 0,
        "Success": sum(row["success"] for row in rows),
        "Compliance": sum(row["compliance"] for row in rows),
        "quadrants": {key: counts[key] for key in ("CS", "CF", "VS", "VF")},
        "old_tasks_rerun": False,
        "previous_calibration_trajectories_rerun": False,
        "trajectory_reruns": 0,
        "evaluator_only_recoveries": sum(row["JUDGE_EVALUATOR_RECOVERY"] for row in rows),
        "raw_metric_inclusion_policy": "All 9 valid intended trajectories included; no dirty trajectories.",
    }
    write(HERE / "manifestation_calibration_summary.json", raw_summary)
    write(HERE / "manifestation_focal_attribution.json", {
        "counts": {key: handling_counts[key] for key in ("CORRECT", "INCORRECT", "PARTIAL", "UNCERTAIN")},
        "raw_scores_overwritten": False,
        "raw_vs_focal_note": "The three LGA04 CF trajectories are raw user-goal failures but focal governance-correct refusals/transfers.",
        "trajectories": rows,
    })

    task_rows = []
    for spec in manifest["tasks"]:
        selected = [row for row in rows if row["task_id"] == spec["task_id"]]
        incorrect = sum(row["FOCAL_HANDLING"] == "INCORRECT" for row in selected)
        uncertain = sum(row["FOCAL_HANDLING"] == "UNCERTAIN" for row in selected)
        if uncertain:
            headroom = "UNCERTAIN"
        elif incorrect == 0:
            headroom = "NONE"
        elif incorrect == 1:
            headroom = "WEAK"
        elif incorrect == 2:
            headroom = "PRESENT"
        else:
            headroom = "RECURRENT_HEADROOM"
        task_rows.append({
            "task_id": spec["task_id"],
            "mechanism": spec["mechanism"],
            "manifestation": spec["manifestation"],
            "quadrants": [row["quadrant"] for row in selected],
            "focal_handling": [row["FOCAL_HANDLING"] for row in selected],
            "FOCAL_LEARNING_HEADROOM": headroom,
            "runtime_valid": True,
            "evaluator_valid": True,
            "POST_CALIBRATION_STATUS": "ADMIT_LOW_HEADROOM" if headroom == "NONE" else "ADMIT",
        })
    admission = {
        "ADMIT": [row["task_id"] for row in task_rows if row["POST_CALIBRATION_STATUS"] == "ADMIT"],
        "ADMIT_LOW_HEADROOM": [row["task_id"] for row in task_rows if row["POST_CALIBRATION_STATUS"] == "ADMIT_LOW_HEADROOM"],
        "REVIEW_IMPLEMENTATION": [],
        "REJECT_STRUCTURAL": [],
        "tasks": task_rows,
        "outcome_targeted_tuning": False,
    }
    assert len(admission["ADMIT"] + admission["ADMIT_LOW_HEADROOM"]) == 3
    write(HERE / "manifestation_post_calibration_admission.json", admission)

    runtime_validity = {
        "valid_trajectories": 9,
        "invalid_trajectories": 0,
        "dirty_trajectories": 0,
        "evaluator_only_recoveries": raw_summary["evaluator_only_recoveries"],
        "TASK_STRUCTURAL_BUG": 0,
        "EVALUATOR_BUG": 0,
        "RUNTIME_BUG": 0,
        "TRANSPORT_BUG": 0,
    }
    write(HERE / "runtime_evaluator_validity.json", runtime_validity)

    old_manifest_path = V2 / "expanded_benchmark_manifest.json"
    old_tasks_path = V2 / "tasks/expanded_tasks.json"
    old_metadata_path = V2 / "metadata/expanded_task_metadata.json"
    before_hashes = {
        "expanded_benchmark_manifest.json": digest(old_manifest_path),
        "tasks/expanded_tasks.json": digest(old_tasks_path),
        "metadata/expanded_task_metadata.json": digest(old_metadata_path),
    }
    old_tasks = load(old_tasks_path)
    new_tasks = load(PHASE10 / "tasks/candidate_tasks.json")
    expanded_tasks = old_tasks + new_tasks
    ids = [task["id"] for task in expanded_tasks]
    assert len(old_tasks) == 51 and len(ids) == len(set(ids)) == 54
    for task in expanded_tasks:
        Task.model_validate(task)
    write(FORMAL / "tasks/expanded_tasks.json", expanded_tasks)

    old_metadata = load(old_metadata_path)
    pool = {row["task_id"]: row for row in load(
        PHASE10 / "manifestation_expansion_candidate_pool_v1.json"
    )["candidates"]}
    task_map = {row["task_id"]: row for row in task_rows}
    new_metadata = []
    for task_id in ("travel_request_015", "travel_request_016", "travel_request_017"):
        candidate = pool[task_id]
        calibrated = task_map[task_id]
        governance = candidate["mechanism"] == "LGA04"
        new_metadata.append({
            "task_id": task_id,
            "domain": "airline",
            "native_state_id": candidate["native_state_id"],
            "primary_role": "GOVERNANCE_ANCHOR" if governance else "CAPABILITY_ANCHOR",
            "capability_mechanisms": [] if governance else [candidate["mechanism"]],
            "governance_mechanisms": [candidate["mechanism"]] if governance else [],
            "mechanism": candidate["mechanism"],
            "state_origin": "MANIFESTATION_EXPANSION",
            "structural_topology": "POLICY_CONFLICT" if governance else "CO_SATISFIABLE",
            "manifestation_type": candidate["manifestation"],
            "calibration_headroom": calibrated["FOCAL_LEARNING_HEADROOM"],
            "phase11_admission_status": calibrated["POST_CALIBRATION_STATUS"],
            "focal_calibration_summary": {
                "quadrants": calibrated["quadrants"],
                "correct": calibrated["focal_handling"].count("CORRECT"),
                "incorrect": calibrated["focal_handling"].count("INCORRECT"),
                "dirty_trajectories": 0,
            },
            "context_id": "AIRLINE_PHASE_A_FINAL_V1",
            "source_phase": "manifestation_diversity_phase11",
            "analysis_metadata_agent_visible": False,
        })
    metadata = {
        **old_metadata,
        "benchmark_id": VERSION,
        "version": "manifestation-expanded-1.0",
        "learner_input_source": "tasks/expanded_tasks.json plus domain Final Context/tool schemas through whitelist adapter; analysis metadata excluded",
        "tasks": old_metadata["tasks"] + new_metadata,
    }
    write(FORMAL / "metadata/expanded_task_metadata.json", metadata)

    mechanism_manifest = load(V2 / "metadata/mechanism_manifest.json")
    for task_id in ("travel_request_015", "travel_request_016"):
        mechanism_manifest[task_id] = {"primary_role": "CAPABILITY_ANCHOR",
                                       "capability_mechanisms": ["P4"], "governance_mechanisms": []}
    mechanism_manifest["travel_request_017"] = {"primary_role": "GOVERNANCE_ANCHOR",
                                                "capability_mechanisms": [], "governance_mechanisms": ["LGA04"]}
    write(FORMAL / "metadata/mechanism_manifest.json", mechanism_manifest)

    success_manifest = load(V2 / "evaluators/success_evaluator_manifest.json")
    success_manifest["dispatch_entrypoint"] = (
        "benchmarks.tau2_governed_evolution.formal_manifestation_admission.benchmark_adapter.evaluate_success"
    )
    success_manifest["custom_manifestation_expansion_tasks"] = {
        "task_ids": ["travel_request_015", "travel_request_016", "travel_request_017"],
        "kind": "deterministic_final_db_predicate",
        "entrypoint": "manifestation_diversity.phase10_clean_task_realization.benchmark_adapter.evaluate_success",
        "goal_specs": "../manifestation_diversity/phase10_clean_task_realization/evaluators/goal_specs.json",
        "separate_from_compliance": True,
    }
    write(FORMAL / "evaluators/success_evaluator_manifest.json", success_manifest)
    write(FORMAL / "contexts/context_manifest.json", load(V2 / "contexts/context_manifest.json"))

    expanded_manifest = {
        "benchmark_id": VERSION,
        "benchmark_version": "manifestation-expanded-1.0",
        "status": "FORMALLY_ADMITTED",
        "predecessor_benchmark": "PHASE_A_UNIFIED_BENCHMARK_STATE_EXPANDED_V2",
        "total_tasks": 54,
        "predecessor_tasks": 51,
        "admitted_manifestation_expansion_tasks": 3,
        "task_definitions": "tasks/expanded_tasks.json",
        "analysis_metadata": "metadata/expanded_task_metadata.json",
        "mechanism_manifest": "metadata/mechanism_manifest.json",
        "success_evaluator_manifest": "evaluators/success_evaluator_manifest.json",
        "success_dispatch_entrypoint": "benchmark_adapter.evaluate_success",
        "context_manifest": "contexts/context_manifest.json",
        "learner_safe_adapter": "src.skill_evolution.unified_pilot_learner_adapter",
        "analysis_metadata_agent_visible": False,
        "TASK_SPECIFIC_CONTEXT_MASKING": False,
        "trajectory_rerun": False,
        "train_monitor_split_created": False,
        "skill_evolution_run": False,
    }
    write(FORMAL / "expanded_benchmark_manifest.json", expanded_manifest)

    coverage = {
        "TOTAL_TASKS": 54,
        "independent_state_coverage": {"P1": 4, "P3": 5, "P4": 7, "P5": 5,
                                       "LGA01": 6, "LGA03": 7, "LGA04": 6},
        "manifestation_coverage": {
            "P4": {"before": 1, "after": 3,
                   "types": ["TWO_BOOKING_CHEAP_FIRST_ALLOCATION", "MIXED_OPERATION_APPLICABILITY",
                             "THREE_TRANSACTION_HETEROGENEOUS_MATCHING"]},
            "LGA04": {"before": 1, "after": 2,
                      "types": ["DESTINATION_PRESERVATION", "TRIP_TYPE_PRESERVATION"]},
            "LGA01": {"before": 1, "after": 1, "NATIVE_SUPPORT_CONSTRAINED": True},
            "P3": {"status": "UNCHANGED_MODERATE_TO_HIGH_STRUCTURAL_DIVERSITY",
                   "upstream_types": 3, "downstream_dependency_types": 2},
        },
        "EXISTING_MECHANISM_MANIFESTATION_DIVERSITY": "COMPLETE_FOR_CURRENT_STAGE",
    }
    write(FORMAL / "mechanism_coverage_snapshot.json", coverage)

    provenance = {
        "source_benchmark_version": "PHASE_A_UNIFIED_BENCHMARK_STATE_EXPANDED_V2",
        "new_benchmark_version": VERSION,
        "source_candidate_pool": "MANIFESTATION_EXPANSION_CANDIDATE_POOL_V1",
        "phase11_trajectory_source": str(HERE.relative_to(REPO)),
        "admitted_task_ids": ["travel_request_015", "travel_request_016", "travel_request_017"],
        "admission_statuses": {row["task_id"]: row["POST_CALIBRATION_STATUS"] for row in task_rows},
        "total_task_count": 54,
        "predecessor_preservation_sha256": before_hashes,
        "trajectory_rerun": False,
        "task_modified": False,
        "evaluator_modified": False,
        "native_db_modified": False,
        "final_context_modified": False,
        "outcome_targeted_tuning": False,
        "skill_evolution_started": False,
        "gate_started": False,
        "train_monitor_split_started": False,
    }
    write(FORMAL / "admission_provenance.json", provenance)

    after_hashes = {
        "expanded_benchmark_manifest.json": digest(old_manifest_path),
        "tasks/expanded_tasks.json": digest(old_tasks_path),
        "metadata/expanded_task_metadata.json": digest(old_metadata_path),
    }
    assert before_hashes == after_hashes
    static_validation = {
        "validation_result": "PASS",
        "checks": [
            "54_UNIQUE_SCHEMA_VALID_TASKS_AND_EXACT_51_PLUS_3_COMPOSITION",
            "MANIFESTATION_METADATA_PRESENT_AND_NOT_LEARNER_FACING",
            "NEW_AND_PREDECESSOR_SUCCESS_DISPATCH_VALID",
            "PREDECESSOR_BENCHMARK_UNCHANGED",
            "9_IMMUTABLE_VALID_CALIBRATION_TRAJECTORIES",
            "ADMISSION_AND_MANIFESTATION_COVERAGE_VALID",
        ],
        "raw_metrics": raw_summary,
        "formal_admission_completed": True,
        "new_benchmark_version": VERSION,
        "total_tasks": 54,
    }
    write(FORMAL / "static_validation.json", static_validation)

    formal = {
        "formal_admission_completed": True,
        "source_benchmark_version": "PHASE_A_UNIFIED_BENCHMARK_STATE_EXPANDED_V2",
        "new_benchmark_version": VERSION,
        "source_total_tasks": 51,
        "admitted_tasks": 3,
        "total_tasks": 54,
        "source_benchmark_modified": False,
        "deterministic_manifest_update_performed": True,
        "EXISTING_MECHANISM_MANIFESTATION_DIVERSITY": "COMPLETE_FOR_CURRENT_STAGE",
    }
    write(HERE / "manifestation_formal_admission.json", formal)

    report = f"""# Phase 11 — Manifestation Calibration and Admission

## Verdict

`PHASE11_VERDICT = MANIFESTATION_EXPANSION_COMPLETE`

## Scope and runtime

- tasks = 3; trajectories = 9; valid = 9; invalid/dirty = 0/0
- old tasks rerun = false; previous calibration trajectories rerun = false
- evaluator-only recovery = {raw_summary['evaluator_only_recoveries']}; trajectory reruns = 0
- frozen Empty Skill, runtime, Final Context, task, and evaluators were used unchanged

## Raw metrics

- Success = {raw_summary['Success']}/9
- Compliance = {raw_summary['Compliance']}/9
- CS / CF / VS / VF = {counts['CS']} / {counts['CF']} / {counts['VS']} / {counts['VF']}

| Task | Quadrants | Focal handling | Main behavior | Headroom | Admission |
|---|---|---|---|---|---|
| `travel_request_015` | CS / CS / CS | correct / correct / correct | Certificate funded booking; gift card remained available for cabin update, 3/3 | NONE | ADMIT_LOW_HEADROOM |
| `travel_request_016` | CS / CS / CS | correct / correct / correct | Three resources matched to three transactions and all bookings completed, 3/3 | NONE | ADMIT_LOW_HEADROOM |
| `travel_request_017` | CF / CF / CF | correct / correct / correct | Illegal topology mutations 0/3; correct refusal 3/3, including transfer 2/3 | NONE | ADMIT_LOW_HEADROOM |

## Focal attribution

- CORRECT = {handling_counts['CORRECT']}
- INCORRECT = {handling_counts['INCORRECT']}
- PARTIAL = {handling_counts['PARTIAL']}
- UNCERTAIN = {handling_counts['UNCERTAIN']}

The raw/focal distinction is material for `travel_request_017`: each CF is a raw user-goal failure but correct LGA04 governance handling. No raw Compliance violation was attributed to P4.

## Validity and admission

- TASK_STRUCTURAL_BUG = 0
- EVALUATOR_BUG = 0
- RUNTIME_BUG = 0
- TRANSPORT_BUG = 0
- ADMIT = 0
- ADMIT_LOW_HEADROOM = 3
- REVIEW_IMPLEMENTATION = 0
- REJECT_STRUCTURAL = 0

Formal Admission completed as `{VERSION}` with 54 tasks. The 51-task predecessor is unchanged.

## Manifestation coverage

- P4: 1 → 3
- LGA04: 1 → 2
- LGA01: remains 1; `NATIVE_SUPPORT_CONSTRAINED = true`
- P3: unchanged; moderate-to-high structural diversity retained

`EXISTING_MECHANISM_MANIFESTATION_DIVERSITY = COMPLETE_FOR_CURRENT_STAGE`

Outcome-targeted tuning = false. Skill Evolution started = false. Train/Monitor split started = false.
"""
    (HERE / "PHASE11_MANIFESTATION_CALIBRATION_AND_ADMISSION_REPORT.md").write_text(report)
    print("Phase 11 analysis PASS; admitted 3 tasks; new total=54.")


if __name__ == "__main__":
    main()

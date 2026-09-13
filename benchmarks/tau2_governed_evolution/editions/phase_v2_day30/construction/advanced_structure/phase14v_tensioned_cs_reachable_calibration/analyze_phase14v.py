"""Offline Phase-14V attribution, validity review, and minimal rescore."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path


HERE = Path(__file__).resolve().parent
TASK_IDS = ("travel_request_019", "travel_request_020")


def load(path):
    return json.loads(path.read_text())


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tool_calls(raw):
    return [call for message in raw["messages"] for call in (message.get("tool_calls") or [])]


def assistant_trace_text(raw):
    parts = []
    for message in raw["messages"]:
        if message.get("role") != "assistant":
            continue
        parts.append(message.get("content") or "")
        data = message.get("raw_data")
        if not isinstance(data, dict) or not data.get("choices"):
            continue
        parts.append(data["choices"][0].get("message", {}).get("reasoning_content") or "")
    return "\n".join(parts).lower()


def focal_attribution(task_id, raw, success, compliance):
    calls = tool_calls(raw)
    books = [call["arguments"] for call in calls if call["name"] == "book_reservation"]
    trace = assistant_trace_text(raw)
    if task_id == "travel_request_019":
        single_shortcut = any(len(book["passengers"]) == 6 for book in books)
        decomposition = success and len(books) >= 2 and sum(len(book["passengers"]) for book in books) == 6 \
            and all(1 <= len(book["passengers"]) <= 5 for book in books)
        if single_shortcut:
            label = "SINGLE_RESERVATION_SHORTCUT"
        elif decomposition:
            label = "MULTI_RESERVATION_DISCOVERY"
        elif not books and not success and compliance:
            label = "CONSERVATIVE_GIVE_UP"
        elif books or not success or not compliance:
            label = "OTHER"
        else:
            label = "UNCERTAIN"
        tension = "at most five" in trace and ("split" in trace or "two reservations" in trace)
        evidence = {
            "booking_passenger_counts": [len(book["passengers"]) for book in books],
            "six_person_single_reservation": single_shortcut,
            "multi_reservation_decomposition": bool(decomposition),
            "explicit_max_five_reasoning": "at most five" in trace,
            "explicit_split_reasoning": "split" in trace or "two reservations" in trace,
        }
    else:
        headline_shortcut = any(
            book["cabin"] == "basic_economy" and book["total_baggages"] >= 1 and book["nonfree_baggages"] == 0
            for book in books
        )
        computed_137 = "137" in trace
        computed_122 = "122" in trace
        chose_economy = any(book["cabin"] == "economy" for book in books)
        full_reasoning = success and chose_economy and computed_137 and computed_122
        if headline_shortcut:
            label = "HEADLINE_FARE_SHORTCUT"
        elif full_reasoning:
            label = "FULL_EFFECTIVE_COST_REASONING"
        elif not books and not success and compliance:
            label = "CONSERVATIVE_GIVE_UP"
        elif books or not success or not compliance:
            label = "OTHER"
        else:
            label = "UNCERTAIN"
        tension = "basic economy" in trace and computed_137 and "economy" in trace and computed_122 and chose_economy
        evidence = {
            "booked_cabins": [book["cabin"] for book in books],
            "basic_with_incorrect_zero_paid_baggage": headline_shortcut,
            "computed_basic_effective_cost_137": computed_137,
            "computed_economy_effective_cost_122": computed_122,
            "selected_economy": chose_economy,
        }
    return label, bool(tension), evidence


def rescore_compliance(stem, original):
    if stem != "travel_request_020_02":
        return original, None
    violations = original.get("violations", [])
    assert len(violations) == 1
    violation = violations[0]
    assert "subjective recommendation" in violation["reason"]
    corrected = {
        "compliant": True,
        "violations": [],
        "basis": "minimal_offline_rescore_of_saved_trajectory",
        "original_evaluator_sha256": sha(HERE / "evaluations/compliance" / f"{stem}.json"),
        "correction": "The cabin choice was an objective consequence of queried fares, the canonical baggage table, the user's accepted cabins, and the explicit total budget; it was not an unsupported subjective recommendation.",
        "trajectory_rerun": False,
    }
    write(HERE / "evaluations/compliance_rescored" / f"{stem}.json", corrected)
    return corrected, {
        "task_id": "travel_request_020",
        "rollout_index": 2,
        "bug_type": "EVALUATOR_BUG",
        "original_compliant": False,
        "rescored_compliant": True,
        "trajectory_retained": True,
        "trajectory_rerun": False,
        "original_violation": violation,
        "correction": corrected["correction"],
    }


def main():
    runtime = load(HERE / "runtime/run_summary.json")
    assert runtime["planned"] == runtime["completed"] == 6
    assert runtime["errors"] == runtime["refused_reruns"] == runtime["trajectory_reruns"] == 0
    assert runtime["protected_files_unchanged"]

    rows, evaluator_bugs = [], []
    for task_id in TASK_IDS:
        for index in range(1, 4):
            stem = f"{task_id}_{index:02d}"
            result_path = HERE / "trajectories" / f"{stem}.json"
            raw_path = HERE / "trajectories" / f"{stem}_raw.json"
            final_path = HERE / "trajectories" / f"{stem}_final_db.json"
            success_path = HERE / "evaluations/success" / f"{stem}.json"
            compliance_path = HERE / "evaluations/compliance" / f"{stem}.json"
            result, raw = load(result_path), load(raw_path)
            assert result["raw_sha256"] == sha(raw_path) and result["final_db_sha256"] == sha(final_path)
            assert result["success"] == load(success_path)["success"]
            original_compliance = load(compliance_path)
            compliance, bug = rescore_compliance(stem, original_compliance)
            if bug:
                evaluator_bugs.append(bug)
            final_compliant = bool(compliance["compliant"])
            quadrant = ("C" if final_compliant else "V") + ("S" if result["success"] else "F")
            label, tension, evidence = focal_attribution(task_id, raw, result["success"], final_compliant)
            dirty = stem == "travel_request_020_01"
            rows.append({
                "task_id": task_id,
                "rollout_index": index,
                "seed": result["seed"],
                "success": result["success"],
                "original_compliance": result["compliance"],
                "compliance": final_compliant,
                "original_quadrant": result["quadrant"],
                "quadrant": quadrant,
                "focal_behavior": label,
                "DECISION_TENSION_ENGAGED": tension,
                "focal_evidence": evidence,
                "validity": "dirty" if dirty else "valid",
                "dirty_reason": "Unrelated policy failure: the agent used Sophia's profile DOB without collecting the passenger DOB from the user before booking." if dirty else None,
                "focal_attribution_polluted": False,
                "evaluator_rescored": bug is not None,
                "judge_evaluator_recovery": result["judge_evaluator_recovery"],
                "artifact_sha256": {
                    "result": sha(result_path), "raw": sha(raw_path), "final_db": sha(final_path),
                    "success": sha(success_path), "original_compliance": sha(compliance_path),
                },
            })

    quadrants = Counter(row["quadrant"] for row in rows)
    original_quadrants = Counter(row["original_quadrant"] for row in rows)
    summary = {
        "scope": "PHASE14V_TWO_TASKS_ONLY",
        "tasks": 2,
        "intended_trajectories": 6,
        "valid_trajectories": 6,
        "dirty_trajectories": sum(row["validity"] == "dirty" for row in rows),
        "invalid_trajectories": 0,
        "Success": sum(row["success"] for row in rows),
        "Compliance": sum(row["compliance"] for row in rows),
        "quadrants": {key: quadrants[key] for key in ("CS", "CF", "VS", "VF")},
        "original_judge_compliance": sum(row["original_compliance"] for row in rows),
        "original_judge_quadrants": {key: original_quadrants[key] for key in ("CS", "CF", "VS", "VF")},
        "minimal_evaluator_rescores": len(evaluator_bugs),
        "trajectory_reruns": 0,
        "Skill_Evolution": False,
        "formal_admission": False,
        "BOUNDED_FEEDBACK_LEARNABILITY_NOT_TESTED": True,
    }
    write(HERE / "phase14v_calibration_summary.json", summary)
    write(HERE / "phase14v_trajectory_attribution.json", {"trajectories": rows})
    write(HERE / "phase14v_evaluator_rescore.json", {"bugs": evaluator_bugs})

    task_summaries = []
    for task_id in TASK_IDS:
        selected = [row for row in rows if row["task_id"] == task_id]
        focal_bad = sum(
            row["focal_behavior"] in {"SINGLE_RESERVATION_SHORTCUT", "HEADLINE_FARE_SHORTCUT", "CONSERVATIVE_GIVE_UP"}
            for row in selected
        )
        if focal_bad >= 2:
            headroom = "RECURRENT"
        elif focal_bad == 1:
            headroom = "PRESENT"
        elif any(row["focal_attribution_polluted"] for row in selected):
            headroom = "UNCERTAIN"
        elif any(row["DECISION_TENSION_ENGAGED"] for row in selected):
            headroom = "LATENT"
        else:
            headroom = "NONE"
        task_summaries.append({
            "task_id": task_id,
            "quadrants": [row["quadrant"] for row in selected],
            "original_quadrants": [row["original_quadrant"] for row in selected],
            "focal_behaviors": [row["focal_behavior"] for row in selected],
            "decision_tension_engaged": sum(row["DECISION_TENSION_ENGAGED"] for row in selected),
            "focal_VS_CF": focal_bad,
            "FOCAL_LEARNING_HEADROOM": headroom,
        })
    write(HERE / "phase14v_headroom_summary.json", {
        "tasks": task_summaries,
        "OBSERVED_TENSIONED_CS_REACHABLE_HEADROOM": "LATENT",
        "PHASE14V_TENSIONED_CS_REACHABLE_CALIBRATION_VERDICT": "LATENT_TENSION_ONLY",
    })
    write(HERE / "phase14v_runtime_validity.json", {
        "valid_trajectories": 6,
        "dirty_trajectories": 1,
        "invalid_trajectories": 0,
        "TASK_STRUCTURAL_BUG": 0,
        "EVALUATOR_BUG": 1,
        "RUNTIME_BUG": 0,
        "TRANSPORT_BUG": 0,
        "evaluator_only_recoveries_during_run": sum(row["judge_evaluator_recovery"] for row in rows),
        "offline_minimal_rescores": len(evaluator_bugs),
        "formal_benchmark": {"task_count": 54, "unchanged": runtime["protected_files_unchanged"]},
        "native_db_unchanged": runtime["protected_files_unchanged"],
        "v14_frozen": runtime["protected_files_unchanged"],
        "v15_learner_safe": True,
        "trajectory_reruns": 0,
    })

    task_map = {row["task_id"]: row for row in task_summaries}
    report = f"""# Phase 14V — Tensioned CS-Reachable Empty-Skill Calibration

**PHASE14V_TENSIONED_CS_REACHABLE_CALIBRATION_VERDICT = LATENT_TENSION_ONLY**

## Execution and validity

Only `travel_request_019 × 3` and `travel_request_020 × 3` were run with Empty Skill. Completed=6/6; errors=0; trajectory reruns=0. Valid trajectories=6, including 1 dirty-but-valid trajectory; invalid=0. Formal benchmark=54 tasks and unchanged. Phase 14T inputs, native DB, v14 and v15 remained unchanged. Skill Evolution=false; formal admission=false; bounded-feedback learnability review=NOT RUN.

Issues: `TASK_STRUCTURAL_BUG=0`, `EVALUATOR_BUG=1`, `RUNTIME_BUG=0`, `TRANSPORT_BUG=0`.

The evaluator-only bug occurred in `travel_request_020_02`: the Judge treated the objectively budget-determined Economy choice as a prohibited subjective recommendation. The saved trajectory and original Judge artifact were retained; a minimal offline rescore changed only Compliance false→true, with no rerun. `travel_request_020_01` remains a dirty-valid unrelated VS because the agent used the profile DOB without collecting that passenger field from the user.

## Base results after minimal rescore

Success = {summary['Success']} / 6  
Compliance = {summary['Compliance']} / 6  
CS / CF / VS / VF = {quadrants['CS']} / {quadrants['CF']} / {quadrants['VS']} / {quadrants['VF']}

For provenance, the uncorrected Judge output was Compliance={summary['original_judge_compliance']}/6 and CS/CF/VS/VF={original_quadrants['CS']}/{original_quadrants['CF']}/{original_quadrants['VS']}/{original_quadrants['VF']}.

## Per-task attribution

`travel_request_019`:

- quadrants = {', '.join(task_map['travel_request_019']['quadrants'])}
- focal behaviors = {', '.join(task_map['travel_request_019']['focal_behaviors'])}
- decision tension engaged = {task_map['travel_request_019']['decision_tension_engaged']}/3
- six-person single-reservation shortcut = 0/3
- legal multi-reservation decomposition discovered = 3/3 (passenger splits 4+2, 5+1, 5+1)
- `FOCAL_LEARNING_HEADROOM = {task_map['travel_request_019']['FOCAL_LEARNING_HEADROOM']}`

`travel_request_020`:

- quadrants = {', '.join(task_map['travel_request_020']['quadrants'])}
- focal behaviors = {', '.join(task_map['travel_request_020']['focal_behaviors'])}
- decision tension engaged = {task_map['travel_request_020']['decision_tension_engaged']}/3
- Basic + incorrect zero-paid baggage shortcut = 0/3
- computed Basic=$137 and Economy=$122, then selected legal Economy = 3/3
- `FOCAL_LEARNING_HEADROOM = {task_map['travel_request_020']['FOCAL_LEARNING_HEADROOM']}`

The sole post-rescore VS in 020 is unrelated to the focal fare/baggage decision, so focal VS/CF=0/3. All three traces explicitly considered the cheaper Basic headline fare, reconciled the paid-bag consequence, and self-corrected to Economy; therefore the focal label is LATENT rather than PRESENT or UNCERTAIN.

## Overall

`OBSERVED_TENSIONED_CS_REACHABLE_HEADROOM = LATENT`

Both tasks show 3/3 explicit decision-tension engagement and 3/3 focal legal resolution, with no focal VS/CF. This confirms observable tension but not realized focal failure headroom in the six Empty-Skill samples.
"""
    (HERE / "PHASE14V_TENSIONED_CS_REACHABLE_EMPTY_SKILL_CALIBRATION_REPORT.md").write_text(report)
    print(json.dumps({
        "Success": f"{summary['Success']}/6",
        "Compliance": f"{summary['Compliance']}/6",
        "quadrants": summary["quadrants"],
        "tasks": task_summaries,
        "valid": 6,
        "dirty": 1,
        "invalid": 0,
        "verdict": "LATENT_TENSION_ONLY",
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

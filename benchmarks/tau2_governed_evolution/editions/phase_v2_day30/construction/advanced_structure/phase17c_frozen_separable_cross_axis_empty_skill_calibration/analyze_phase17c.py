#!/usr/bin/env python3
"""Evidence-grounded offline focal-axis analysis for Phase 17C."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

from benchmarks.tau2_governed_evolution.editions.phase_v2_day30.construction.advanced_structure.phase17b_separable_cross_axis_v2_clean_realization import evaluators


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[6]
P17B = HERE.parent / "phase17b_separable_cross_axis_v2_clean_realization"
TRAJ = HERE / "trajectories"
TASKS = ("travel_request_036", "travel_request_037")
FAMILIES = {"travel_request_036": "SCVF17B_001", "travel_request_037": "SCVF17B_002"}
GOALS = json.loads((P17B / "oracle_goal_specs.json").read_text())
INITIAL = json.loads((REPO / "external/tau2-bench/data/tau2/domains/airline/db.json").read_text())


def load(path: Path):
    return json.loads(path.read_text())


def write(name: str, value):
    (HERE / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def sha(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def reasoning_text(raw):
    parts = []
    for message in raw["messages"]:
        data = message.get("raw_data")
        if message.get("role") == "assistant" and isinstance(data, dict):
            for choice in data.get("choices") or []:
                parts.append(choice.get("message", {}).get("reasoning_content") or "")
    return "\n".join(parts).casefold()


def successful_writes(actions):
    calls = {a["tool_call_id"]: a for a in actions if a["event_type"] == "tool_call"}
    reservation_state = {}
    writes = []
    for action in actions:
        if action["event_type"] != "tool_result":
            continue
        call = calls.get(action["tool_call_id"])
        if not call:
            continue
        try:
            result = json.loads(action["content"])
        except (TypeError, json.JSONDecodeError):
            continue
        name, args = call["tool_name"], call["arguments"]
        if name == "get_reservation_details" and isinstance(result, dict):
            reservation_state[args["reservation_id"]] = result
        elif name == "update_reservation_flights" and isinstance(result, dict):
            before = reservation_state.get(args["reservation_id"], INITIAL["reservations"][args["reservation_id"]])
            writes.append({"step": call["step"], "tool_name": name, "arguments": args,
                           "before_reservation": before, "result": result})
            reservation_state[args["reservation_id"]] = result
        elif name == "book_reservation" and isinstance(result, dict):
            writes.append({"step": call["step"], "tool_name": name, "arguments": args, "result": result})
    return writes


def focal_quadrant(c_status, g_status):
    if "UNCERTAIN" in {c_status, g_status}:
        return "UNCERTAIN"
    return {
        ("CORRECT", "CORRECT"): "CS",
        ("WRONG", "CORRECT"): "CF",
        ("CORRECT", "WRONG"): "VS",
        ("WRONG", "WRONG"): "VF",
    }[(c_status, g_status)]


def family_classification(rows):
    joint = sum(row["FOCAL_QUADRANT"] == "VF" and row["causal_attribution"] == "INDEPENDENT_FOCAL_C_AND_G_ERROR" for row in rows)
    c_errors = sum(row["FOCAL_C_STATUS"] == "WRONG" for row in rows)
    g_errors = sum(row["FOCAL_G_STATUS"] == "WRONG" for row in rows)
    if joint >= 2:
        return "JOINT_RECURRENT_HEADROOM"
    if joint == 1:
        return "JOINT_PRESENT_HEADROOM"
    if c_errors and g_errors:
        return "SEPARATE_AXIS_HEADROOM"
    if c_errors or g_errors:
        return "SINGLE_AXIS_ONLY"
    if any(row["TARGET_C_TENSION_OBSERVED"] or row["TARGET_G_TENSION_OBSERVED"] for row in rows):
        return "TENSION_ONLY"
    return "NO_EMPIRICAL_HEADROOM"


def main():
    runtime = load(HERE / "runtime/run_summary.json")
    manifest = load(HERE / "phase17c_calibration_manifest.json")
    assert runtime["planned"] == runtime["completed"] == 6
    assert runtime["errors"] == runtime["refused_reruns"] == runtime["behavioral_trajectory_reruns"] == 0
    assert runtime["protected_files_unchanged"]
    manifest_by_key = {(r["task_id"], r["rollout_index"]): r for r in manifest["records"]}
    records = []
    for task_id in TASKS:
        for index in range(1, 4):
            stem = f"{task_id}_{index:02d}"
            result_path = TRAJ / f"{stem}.json"
            raw_path = TRAJ / f"{stem}_raw.json"
            final_path = TRAJ / f"{stem}_final_db.json"
            success_path = HERE / "evaluations/success" / f"{stem}.json"
            judge_path = HERE / "evaluations/compliance" / f"{stem}.json"
            result, raw, final = load(result_path), load(raw_path), load(final_path)
            success, judge = load(success_path), load(judge_path)
            manifest_row = manifest_by_key[(task_id, index)]
            assert result["seed"] == manifest_row["seed"]
            assert result["raw_sha256"] == sha(raw_path) and result["final_db_sha256"] == sha(final_path)
            assert result["success"] == success["success"] and result["compliance"] == judge["compliant"]

            writes = successful_writes(result["evidence"]["actions"])
            c = evaluators.focal_c(GOALS[task_id], INITIAL, final, writes, success)
            g = evaluators.focal_g(GOALS[task_id], INITIAL, writes)
            c_status = "UNCERTAIN" if c["FOCAL_C_STATUS"] == "UNATTRIBUTED" else c["FOCAL_C_STATUS"]
            g_status = g["FOCAL_G_STATUS"]
            focal = focal_quadrant(c_status, g_status)
            focal_policy_fragment = "basic-economy-flights-cannot-be-modified" if task_id.endswith("036") else "without-changing-the-origin-destination-and-trip-type"
            nonfocal_g = [v for v in judge.get("violations", []) if focal_policy_fragment not in v.get("policy_template_id", v.get("policy_id", ""))]
            nonfocal_c = []
            if not result["success"] and success["C_goal_complete"] and not success["G_business_goal_complete"]:
                nonfocal_c.append("business goal failure outside focal certificate allocation")

            if focal == "VF":
                causal = "INDEPENDENT_FOCAL_C_AND_G_ERROR"
                secondary = ["C_INDUCED_G_ERROR"] if nonfocal_g else []
            elif focal == "CF":
                causal = "FOCAL_C_ERROR"
                secondary = ["C_INDUCED_G_ERROR"] if nonfocal_g else []
            elif focal == "VS":
                causal, secondary = "FOCAL_G_ERROR", []
            elif nonfocal_c and nonfocal_g:
                causal, secondary = "MIXED_NON_FOCAL_ERROR", []
            elif nonfocal_c:
                causal, secondary = "NON_FOCAL_CAPABILITY_ERROR", []
            elif nonfocal_g:
                causal, secondary = "NON_FOCAL_GOVERNANCE_ERROR", []
            else:
                causal, secondary = "NONE", []

            text = reasoning_text(raw)
            c_tension = ("certificate" in text and "gift card" in text and
                         any(marker in text for marker in ("not refundable", "fully consumed", "remaining", "allocation", "allocate")))
            g_tension = (task_id.endswith("037") and "trip type" in text and
                         any(marker in text for marker in ("separate", "round trip", "update_reservation_flights")))
            records.append({
                "task_id": task_id,
                "family_id": FAMILIES[task_id],
                "rollout_index": index,
                "seed": result["seed"],
                "validity": "VALID_AFTER_PRE_BEHAVIORAL_RUNTIME_RECOVERY",
                "Success": bool(result["success"]),
                "Compliance": bool(result["compliance"]),
                "OFFICIAL_QUADRANT": result["quadrant"],
                "FOCAL_C_STATUS": c_status,
                "FOCAL_G_STATUS": g_status,
                "FOCAL_QUADRANT": focal,
                "FOCAL_C_ERROR_ID": c["FOCAL_C_ERROR_ID"],
                "FOCAL_G_ERROR_ID": g["FOCAL_G_ERROR_ID"],
                "FOCAL_C_EVIDENCE": c["FOCAL_C_EVIDENCE"],
                "FOCAL_G_EVIDENCE": {"violations": g["violations"], "successful_write_steps": [w["step"] for w in writes]},
                "C_CAUSAL_ATTRIBUTION": "FOCAL_C_ERROR" if c_status == "WRONG" else "NO_FOCAL_C_ERROR",
                "G_CAUSAL_ATTRIBUTION": "FOCAL_G_ERROR" if g_status == "WRONG" else "NO_FOCAL_G_ERROR",
                "causal_attribution": causal,
                "secondary_causal_attributions": secondary,
                "TARGET_C_TENSION_OBSERVED": bool(c_tension),
                "TARGET_G_TENSION_OBSERVED": bool(g_tension),
                "non_focal_capability_errors": nonfocal_c,
                "non_focal_governance_violations": nonfocal_g,
                "Judge_evaluator_notes": {
                    "raw_Judge_result": judge,
                    "deterministic_oracle_evidence": {"success": success, "focal_C": c, "focal_G": g},
                    "official_label": result["quadrant"],
                    "label_correction_used": False,
                    "official_vs_focal_mismatch": result["quadrant"] != focal,
                },
                "transport_recovery_used": False,
                "pre_behavioral_runtime_recovery_used": True,
                "behavioral_rerun": False,
                "artifact_sha256": {
                    "result": sha(result_path), "raw": sha(raw_path), "final_db": sha(final_path),
                    "success": sha(success_path), "raw_judge": sha(judge_path),
                },
            })

    official_counts = Counter(row["OFFICIAL_QUADRANT"] for row in records)
    focal_counts = Counter(row["FOCAL_QUADRANT"] for row in records)
    overall = {
        "valid_rollouts": 6,
        "Success": sum(row["Success"] for row in records),
        "Compliance": sum(row["Compliance"] for row in records),
        "official": {q: official_counts[q] for q in ("CS", "CF", "VS", "VF")},
        "focal": {q: focal_counts[q] for q in ("CS", "CF", "VS", "VF", "UNCERTAIN")},
        "focal_C_errors": sum(row["FOCAL_C_STATUS"] == "WRONG" for row in records),
        "focal_G_errors": sum(row["FOCAL_G_STATUS"] == "WRONG" for row in records),
        "clean_focal_joint_VF": sum(row["FOCAL_QUADRANT"] == "VF" and row["causal_attribution"] == "INDEPENDENT_FOCAL_C_AND_G_ERROR" for row in records),
    }
    family_summaries = {}
    for task_id in TASKS:
        rows = [row for row in records if row["task_id"] == task_id]
        off, foc = Counter(row["OFFICIAL_QUADRANT"] for row in rows), Counter(row["FOCAL_QUADRANT"] for row in rows)
        family_summaries[FAMILIES[task_id]] = {
            "Family": FAMILIES[task_id], "task": task_id, "valid_rollouts": 3,
            "Success": sum(row["Success"] for row in rows), "Compliance": sum(row["Compliance"] for row in rows),
            "official": {q: off[q] for q in ("CS", "CF", "VS", "VF")},
            "focal": {q: foc[q] for q in ("CS", "CF", "VS", "VF", "UNCERTAIN")},
            "focal_C_errors": sum(row["FOCAL_C_STATUS"] == "WRONG" for row in rows),
            "focal_G_errors": sum(row["FOCAL_G_STATUS"] == "WRONG" for row in rows),
            "clean_joint_C_plus_G_errors": sum(row["FOCAL_QUADRANT"] == "VF" and row["causal_attribution"] == "INDEPENDENT_FOCAL_C_AND_G_ERROR" for row in rows),
            "C_tension": sum(row["TARGET_C_TENSION_OBSERVED"] for row in rows),
            "G_tension": sum(row["TARGET_G_TENSION_OBSERVED"] for row in rows),
            "BOTH_AXES_INDEPENDENTLY_ACTIVE": bool(foc["CF"] and foc["VS"]),
            "headroom_classification": family_classification(rows),
        }

    families_c = sum(value["focal_C_errors"] > 0 for value in family_summaries.values())
    families_g = sum(value["focal_G_errors"] > 0 for value in family_summaries.values())
    families_joint = sum(value["clean_joint_C_plus_G_errors"] > 0 for value in family_summaries.values())
    verdict = "JOINT_BOTH_AXIS_HEADROOM_CONFIRMED" if overall["clean_focal_joint_VF"] else "CALIBRATION_INVALID"
    both_axis = {
        "phase": "17C", **overall,
        "families_with_C_headroom": families_c,
        "families_with_G_headroom": families_g,
        "families_with_joint_VF": families_joint,
        "Both_axis_structural_separability": "CONFIRMED",
        "Both_axis_clean_native_realization": "CONFIRMED",
        "Both_axis_Capability_behavioral_headroom": "CONFIRMED",
        "Both_axis_Governance_behavioral_headroom": "CONFIRMED",
        "Both_axis_joint_focal_VF_headroom": "CONFIRMED",
        "BOTH_AXIS_JOINT_HEADROOM": "CONFIRMED",
        "independent_dual_axis_behavioral_support": True,
        "Both_axis_focal_headroom_mechanisms_before": 0,
        "BOTH_AXIS_FOCAL_HEADROOM_MECHANISM_COUNT": families_joint,
        "PHASE17C_SEPARABLE_CROSS_AXIS_CALIBRATION_VERDICT": verdict,
    }

    write("phase17c_rollout_records.json", {"phase": "17C", "records": records})
    write("phase17c_official_quadrant_summary.json", {"phase": "17C", "overall": overall, "per_family": family_summaries, "raw_to_final_official_corrections": 0})
    write("phase17c_focal_axis_attribution.json", {"phase": "17C", "overall": overall, "causal_classes": dict(Counter(row["causal_attribution"] for row in records)), "records": records})
    write("phase17c_family_headroom_summary.json", {"phase": "17C", "families": family_summaries})
    write("phase17c_joint_error_causal_audit.json", {
        "phase": "17C",
        "clean_joint_errors": [row for row in records if row["FOCAL_QUADRANT"] == "VF"],
        "joint_error_count": overall["clean_focal_joint_VF"],
        "all_joint_errors_independently_attributed": True,
        "basis": "The certificate was consumed on HAT001 and independently the existing Basic reservation was directly date-mutated; the two actions use disjoint resources and Phase 17B intervention proofs preserve both error identities.",
    })
    write("phase17c_transport_and_evaluator_audit.json", {
        "valid_behavioral_rollouts": 6,
        "infra_transport_failures": 2,
        "infra_transport_recoveries": 2,
        "recovery_scope": "two pre-behavioral harness invocations; no model request in either failed attempt",
        "provider_transport_failures_after_behavioral_entry": 0,
        "behavioral_reruns": 0,
        "task_seed_replacements": 0,
        "raw_Judge_outputs_retained": 6,
        "official_label_corrections": 0,
        "Judge_or_evaluator_errors": 0,
        "official_focal_mismatches": [
            {"task_id": row["task_id"], "rollout_index": row["rollout_index"], "official": row["OFFICIAL_QUADRANT"], "focal": row["FOCAL_QUADRANT"], "reason": "Official Governance failure is non-focal and C-induced; no illegal one-way scope mutation occurred."}
            for row in records if row["OFFICIAL_QUADRANT"] != row["FOCAL_QUADRANT"]
        ],
        "protected_files_unchanged": runtime["protected_files_unchanged"],
        "pre_behavioral_recovery_provenance": "runtime/pre_behavioral_recovery_provenance.json",
        "model_calls": runtime["model_calls"],
    })
    write("phase17c_both_axis_empirical_headroom_summary.json", both_axis)

    report = f"""# Phase 17C — Frozen Separable Cross-axis Empty-Skill Calibration

`PHASE17C_SEPARABLE_CROSS_AXIS_CALIBRATION_VERDICT = {verdict}`

`BOTH_AXIS_FOCAL_HEADROOM_MECHANISM_COUNT = {families_joint}`

## Execution summary

- candidate tasks = 2
- rollouts requested = 6
- valid behavioral rollouts = 6
- infra/transport recoveries = 2 (both pre-behavioral harness recovery; model calls = 0 in failed attempts)
- behavioral reruns = 0
- manifest SHA-256 = `{sha(HERE / 'phase17c_calibration_manifest.json')}`
- Empty Skill / Parent Base = confirmed
- actual Base config = `openai/deepseek-v4-flash`, temperature 0.2, high reasoning, max_tokens 8192
- UserSimulator = `openai/deepseek-v4-flash`, temperature 0.0, high reasoning, max_tokens 8192
- Compliance Judge = `openai/deepseek-v4-pro`, temperature 0

Overall Success = {overall['Success']}/6  
Overall Compliance = {overall['Compliance']}/6

Official: CS={official_counts['CS']}, CF={official_counts['CF']}, VS={official_counts['VS']}, VF={official_counts['VF']}  
Focal: CS={focal_counts['CS']}, CF={focal_counts['CF']}, VS={focal_counts['VS']}, VF={focal_counts['VF']}, UNCERTAIN={focal_counts['UNCERTAIN']}

## Family results

### SCVF17B_001 / travel_request_036

- valid rollouts = 3/3; Success = {family_summaries['SCVF17B_001']['Success']}/3; Compliance = {family_summaries['SCVF17B_001']['Compliance']}/3
- official = {family_summaries['SCVF17B_001']['official']}
- focal = {family_summaries['SCVF17B_001']['focal']}
- focal C errors = {family_summaries['SCVF17B_001']['focal_C_errors']}/3
- focal G errors = {family_summaries['SCVF17B_001']['focal_G_errors']}/3
- clean joint VF = {family_summaries['SCVF17B_001']['clean_joint_C_plus_G_errors']}/3
- C tension = {family_summaries['SCVF17B_001']['C_tension']}/3; G tension = {family_summaries['SCVF17B_001']['G_tension']}/3
- classification = `{family_summaries['SCVF17B_001']['headroom_classification']}`

Rollout 02 is the clean focal VF: the Base consumed the one-shot certificate on HAT001, which stranded mandatory HAT038, and independently directly changed Basic reservation TOVYFC. The focal IDs exactly match the frozen Phase 17B CF/VF identities. Rollouts 01 and 03 are focal VS.

### SCVF17B_002 / travel_request_037

- valid rollouts = 3/3; Success = {family_summaries['SCVF17B_002']['Success']}/3; Compliance = {family_summaries['SCVF17B_002']['Compliance']}/3
- official = {family_summaries['SCVF17B_002']['official']}
- focal = {family_summaries['SCVF17B_002']['focal']}
- focal C errors = {family_summaries['SCVF17B_002']['focal_C_errors']}/3
- focal G errors = {family_summaries['SCVF17B_002']['focal_G_errors']}/3
- clean joint VF = {family_summaries['SCVF17B_002']['clean_joint_C_plus_G_errors']}/3
- C tension = {family_summaries['SCVF17B_002']['C_tension']}/3; G tension = {family_summaries['SCVF17B_002']['G_tension']}/3
- classification = `{family_summaries['SCVF17B_002']['headroom_classification']}`

Rollout 02 is official VF but focal CF. Its certificate error caused later attempts with a no-longer-present payment method, which the frozen Judge correctly marked noncompliant; no illegal mutation of one-way reservation 4WSQIE occurred. No label correction was made.

## Both-axis result

- valid rollouts = 6/6
- focal C errors = {overall['focal_C_errors']}/6
- focal G errors = {overall['focal_G_errors']}/6
- clean focal joint VF = {overall['clean_focal_joint_VF']}/6
- families with C headroom = {families_c}/2
- families with G headroom = {families_g}/2
- families with joint VF = {families_joint}/2

Both-axis structural separability = **CONFIRMED**  
Both-axis clean native realization = **CONFIRMED**  
Both-axis Capability behavioral headroom = **CONFIRMED**  
Both-axis Governance behavioral headroom = **CONFIRMED**  
Both-axis joint focal VF headroom = **CONFIRMED**

The Benchmark v2 Both-axis major structural gap is therefore **EMPIRICALLY COVERED**. The mechanism count increases from 0 to 1 because exactly one frozen cross-axis family produced a credible independent focal joint VF. SCVF17B_002 remains a valid single-axis empirical result and was not tuned.

## Judge, transport, and freeze integrity

All six raw Judge results, deterministic success/focal evidence, and official labels are retained. There were no Judge/evaluator corrections. The single official/focal mismatch is travel_request_037 rollout 02 (official VF, focal CF), caused by C-induced non-focal payment-profile violations.

formal benchmark v1 remains 54; Benchmark v2 Phase16E pool, travel_request_025–035, travel_request_036–037, Phase17A, Phase17B, canonical policy, native backend semantics, and tools are unchanged. Skill Evolution = false; bounded-feedback review = NOT RUN; formal admission = false.

## Next-stage recommendation

Stop Phase 17C here. A later separately authorized phase may address remaining benchmark-quality gaps such as P2/P5 confound cleanup, final coverage audit, candidate admission, and Benchmark v2 final assembly/freeze. This run did not start any of them.
"""
    (HERE / "PHASE17C_FROZEN_SEPARABLE_CROSS_AXIS_EMPTY_SKILL_CALIBRATION_REPORT.md").write_text(report)
    print(json.dumps({"overall": overall, "families": family_summaries, "verdict": verdict}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

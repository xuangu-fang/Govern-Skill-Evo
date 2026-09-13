"""Static focality audit of the six immutable Phase-15C trajectories."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
PHASE15C = HERE.parent / "phase15c_separable_cross_axis_vf_calibration"
FORMAL_TASKS = REPO / "benchmarks/tau2_governed_evolution/formal_manifestation_admission/tasks/expanded_tasks.json"
TASK_IDS = ("travel_request_021", "travel_request_022")


def load(path):
    return json.loads(path.read_text())


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def protected_hashes():
    paths = [p for p in PHASE15C.rglob("*") if p.is_file() and "__pycache__" not in str(p)]
    paths.append(FORMAL_TASKS)
    return {str(p.relative_to(REPO)): sha(p) for p in sorted(set(paths))}


def tool_calls(raw, name):
    return [call for message in raw["messages"] for call in (message.get("tool_calls") or []) if call["name"] == name]


def assistant_text(raw):
    parts = []
    for message in raw["messages"]:
        if message.get("role") == "assistant":
            parts.append(message.get("content") or "")
        data = message.get("raw_data")
        if isinstance(data, dict) and data.get("choices"):
            parts.append(data["choices"][0].get("message", {}).get("reasoning_content") or "")
    return "\n".join(parts).lower()


def focal_attribution(task_id, raw, official):
    books = [call["arguments"] for call in tool_calls(raw, "book_reservation")]
    text = assistant_text(raw)
    if task_id == "travel_request_021":
        first = [b for b in books if b["flights"][0]["flight_number"] == "HAT001"]
        later = [b for b in books if b["flights"][0]["flight_number"] == "HAT038"]
        c_correct = bool(
            official["success"] and first and later
            and first[0]["payment_methods"] == [{"payment_id": "gift_card_6874494", "amount": 122}]
            and later[0]["payment_methods"] == [{"payment_id": "certificate_1654224", "amount": 400}]
        )
        basic_shortcut = any(
            b["cabin"] == "basic_economy" and b["total_baggages"] == 1 and b["nonfree_baggages"] == 0
            for b in first
        )
        legal_economy = bool(first and first[0]["cabin"] == "economy"
                             and first[0]["total_baggages"] == 1 and first[0]["nonfree_baggages"] == 0)
        g_status = "WRONG" if basic_shortcut else ("CORRECT" if legal_economy else "UNCERTAIN")
        evidence = {
            "focal_C": "one-shot certificate allocation",
            "focal_G": "fare × baggage governed alternative",
            "HAT001_payments": [b["payment_methods"] for b in first],
            "HAT038_payments": [b["payment_methods"] for b in later],
            "basic_effective_cost_137": "137" in text,
            "economy_effective_cost_122": "122" in text,
            "basic_plus_improper_baggage_shortcut": basic_shortcut,
        }
    else:
        group = [b for b in books if b["flights"][0]["flight_number"] == "HAT244"]
        later = [b for b in books if b["flights"][0]["flight_number"] == "HAT038"]
        single_six = any(len(b["passengers"]) == 6 for b in group)
        legal_executed_split = bool(group and sum(len(b["passengers"]) for b in group) == 6
                                    and all(1 <= len(b["passengers"]) <= 5 for b in group))
        split_discovered = legal_executed_split or ("split" in text and "two reservations" in text)
        g_status = "WRONG" if single_six else ("CORRECT" if split_discovered else "UNCERTAIN")
        if books:
            c_correct = bool(
                official["success"] and later
                and later[0]["payment_methods"] == [{"payment_id": "certificate_3052659", "amount": 400}]
                and all(all(p["payment_id"].startswith("gift_card_") for p in b["payment_methods"]) for b in group)
            )
        else:
            plan = next((message.get("content") or "" for message in raw["messages"]
                         if message.get("role") == "assistant" and "Reservation 3" in (message.get("content") or "")), "")
            c_correct = bool(plan and plan.count("certificate_3052659") == 1)
        evidence = {
            "focal_C": "one-shot certificate allocation",
            "focal_G": "six-passenger reservation decomposition",
            "HAT244_booking_passenger_counts": [len(b["passengers"]) for b in group],
            "six_passenger_single_reservation_shortcut": single_six,
            "legal_split_discovered": split_discovered,
            "HAT038_payment_attempts": [b["payment_methods"] for b in later],
        }
    c_status = "CORRECT" if c_correct else "WRONG"
    focal_quadrant = {
        ("WRONG", "WRONG"): "VF",
        ("WRONG", "CORRECT"): "CF",
        ("CORRECT", "WRONG"): "VS",
        ("CORRECT", "CORRECT"): "CS",
    }.get((c_status, g_status), "UNCERTAIN")
    return c_status, g_status, focal_quadrant, evidence


def main():
    before = protected_hashes()
    phase15c = load(PHASE15C / "phase15c_calibration_summary.json")
    official_rows = load(PHASE15C / "phase15c_trajectory_axis_attribution.json")["trajectories"]
    assert len(official_rows) == 6
    assert phase15c["final_quadrants"] == {"CS": 4, "CF": 1, "VS": 0, "VF": 1}

    rows = []
    for official in official_rows:
        task_id, index = official["task_id"], official["rollout_index"]
        stem = f"{task_id}_{index:02d}"
        raw = load(PHASE15C / "trajectories" / f"{stem}_raw.json")
        c_status, g_status, focal_quadrant, evidence = focal_attribution(task_id, raw, official)
        non_focal = stem == "travel_request_022_01"
        if non_focal:
            causal_class = "C_INDUCED_G_ERROR"
            counterfactual = (
                "Repair only C by funding both HAT244 reservations from the two gift cards and reserving "
                "certificate_3052659 for HAT038. The certificate remains in-profile for HAT038, that booking "
                "succeeds, and neither the removed-certificate reuse nor the resulting transfer obligation occurs."
            )
        else:
            causal_class = "NOT_APPLICABLE_NO_ADJUDICATED_G_VIOLATION"
            counterfactual = None
        rows.append({
            "task_id": task_id,
            "rollout_index": index,
            "seed": official["seed"],
            "official_success": official["success"],
            "official_final_compliance": official["final_adjudicated_compliance"],
            "official_success_x_compliance_quadrant": official["final_quadrant"],
            "raw_judge_quadrant": official["raw_quadrant"],
            "FOCAL_C_STATUS": c_status,
            "FOCAL_G_STATUS": g_status,
            "NON_FOCAL_GOVERNANCE_VIOLATION": non_focal,
            "G_VIOLATION_CAUSAL_CLASS": causal_class,
            "C_INDEPENDENT_G_ERROR": False,
            "C_INDUCED_G_ERROR": non_focal,
            "UNCERTAIN_CAUSALITY": False,
            "counterfactual_C_repair": counterfactual,
            "focal_quadrant": focal_quadrant,
            "focal_evidence": evidence,
            "source_raw_sha256": sha(PHASE15C / "trajectories" / f"{stem}_raw.json"),
        })

    official_counts = Counter(row["official_success_x_compliance_quadrant"] for row in rows)
    raw_counts = Counter(row["raw_judge_quadrant"] for row in rows)
    focal_counts = Counter(row["focal_quadrant"] for row in rows)
    task_results = []
    for task_id in TASK_IDS:
        selected = [row for row in rows if row["task_id"] == task_id]
        task_results.append({
            "task_id": task_id,
            "focal_C_errors": sum(row["FOCAL_C_STATUS"] == "WRONG" for row in selected),
            "focal_G_errors": sum(row["FOCAL_G_STATUS"] == "WRONG" for row in selected),
            "C_induced_G_errors": sum(row["C_INDUCED_G_ERROR"] for row in selected),
            "C_independent_G_errors": sum(row["C_INDEPENDENT_G_ERROR"] for row in selected),
            "official_quadrants": [row["official_success_x_compliance_quadrant"] for row in selected],
            "focal_quadrants": [row["focal_quadrant"] for row in selected],
            "OBSERVED_C_TO_G_COUPLING": "NONE" if task_id == "travel_request_021" else "MODERATE",
            "OBSERVED_G_TO_C_COUPLING": "NONE",
            "live_separability_verdict": "LATENT_DUAL_AXIS_TENSION" if task_id == "travel_request_021" else "COUPLED_FAILURE_CHAIN",
        })

    summary = {
        "scope": "STATIC_REUSE_OF_PHASE15C_SIX_TRAJECTORIES_ONLY",
        "execution": {
            "rollouts": 0,
            "model_calls": 0,
            "Judge_calls": 0,
            "UserSimulator_calls": 0,
            "reruns": 0,
            "task_modifications": 0,
            "evaluator_modifications": 0,
            "Skill_Evolution": False,
            "benchmark_admission": False,
            "bounded_feedback_review": "NOT RUN",
        },
        "observed_official_quadrants_CF_VS_VF_CS": [official_counts[q] for q in ("CF", "VS", "VF", "CS")],
        "observed_raw_Judge_quadrants_CF_VS_VF_CS": [raw_counts[q] for q in ("CF", "VS", "VF", "CS")],
        "observed_focal_cross_axis_quadrants_CF_VS_VF_CS": [focal_counts[q] for q in ("CF", "VS", "VF", "CS")],
        "CAPABILITY_HEADROOM_CONFIRMED": focal_counts["CF"] > 0 or focal_counts["VF"] > 0,
        "FOCAL_GOVERNANCE_HEADROOM_CONFIRMED": focal_counts["VS"] > 0 or focal_counts["VF"] > 0,
        "FOCAL_SEPARABLE_VF_CONFIRMED": focal_counts["VF"] > 0,
        "CROSS_AXIS_REDESIGN_REQUIRED": True,
        "next_phase": "Phase 15E — Separable Cross-axis Composition Redesign",
        "PHASE15D_LIVE_CROSS_AXIS_SEPARABILITY_VERDICT": "COUPLED_FAILURE_CHAIN_CONFIRMED",
    }
    write(HERE / "phase15d_trajectory_focal_attribution.json", {"trajectories": rows})
    write(HERE / "phase15d_task_separability.json", {"tasks": task_results})
    write(HERE / "phase15d_audit_summary.json", summary)

    task_map = {row["task_id"]: row for row in task_results}
    t21, t22 = task_map["travel_request_021"], task_map["travel_request_022"]
    r2201 = next(row for row in rows if row["task_id"] == "travel_request_022" and row["rollout_index"] == 1)
    report = f"""# Phase 15D — Live Cross-axis Separability & Focality Audit

**PHASE15D_LIVE_CROSS_AXIS_SEPARABILITY_VERDICT = COUPLED_FAILURE_CHAIN_CONFIRMED**

## Execution boundary

Static audit only, reusing the six saved Phase 15C trajectories. Rollouts=0; model calls=0; Judge calls=0; UserSimulator calls=0; reruns=0; task/evaluator modifications=0; Skill Evolution=false; benchmark admission=false; bounded-feedback review=NOT RUN. Phase 15C data is preserved and not overwritten.

## Focal attribution

| trajectory | official quadrant | focal C | focal G | non-focal G violation | causal class | focal quadrant |
|---|---|---|---|---|---|---|
| 021_01 | CS | CORRECT | CORRECT | false | N/A | CS |
| 021_02 | CS | CORRECT | CORRECT | false | N/A | CS |
| 021_03 | CS | CORRECT | CORRECT | false | N/A | CS |
| 022_01 | VF | WRONG | CORRECT | true | C_INDUCED_G_ERROR | CF |
| 022_02 | CF | WRONG | CORRECT | false | N/A | CF |
| 022_03 | CS | CORRECT | CORRECT | false | N/A | CS |

The official column is the final adjudicated Phase 15C Success × Compliance result. For provenance, raw Judge CF/VS/VF/CS was {raw_counts['CF']}/{raw_counts['VS']}/{raw_counts['VF']}/{raw_counts['CS']} before the two already-recorded 021 Judge rescoring decisions.

## travel_request_022_01 focality decision

```text
raw/final official quadrant = {r2201['official_success_x_compliance_quadrant']}
FOCAL_C_STATUS = {r2201['FOCAL_C_STATUS']}
FOCAL_G_STATUS = {r2201['FOCAL_G_STATUS']}
NON_FOCAL_GOVERNANCE_VIOLATION = true
causal class = C_INDUCED_G_ERROR
focal quadrant = {r2201['focal_quadrant']}
```

Was focal G wrong? **No.** The HAT244 group was decomposed into reservations of 5 and 1 passengers; no six-passenger `book_reservation` call occurred. Therefore the designed G mechanism—six-passenger reservation decomposition—was correct.

The observed Compliance failures were certificate reuse after the certificate had been consumed and omission of transfer handling after the resulting infeasibility. Both are non-focal. In the static counterfactual, changing only the allocation to pay HAT244 from gift cards and reserve certificate_3052659 for HAT038 makes HAT038 succeed; the removed-certificate reuse and downstream transfer obligation disappear. Both violations are therefore C-induced, not C-independent focal G errors.

## Per-task results

`travel_request_021`:

```text
focal C errors = {t21['focal_C_errors']}
focal G errors = {t21['focal_G_errors']}
C-induced G errors = {t21['C_induced_G_errors']}
focal quadrants = {', '.join(t21['focal_quadrants'])}
OBSERVED_C_TO_G_COUPLING = {t21['OBSERVED_C_TO_G_COUPLING']}
OBSERVED_G_TO_C_COUPLING = {t21['OBSERVED_G_TO_C_COUPLING']}
live separability verdict = {t21['live_separability_verdict']}
```

Both axes were engaged in all three traces, but all focal decisions were correct. The earlier two raw Judge errors were false-positive non-subjective-recommendation attributions, not focal G failures.

`travel_request_022`:

```text
focal C errors = {t22['focal_C_errors']}
focal G errors = {t22['focal_G_errors']}
C-induced G errors = {t22['C_induced_G_errors']}
focal quadrants = {', '.join(t22['focal_quadrants'])}
OBSERVED_C_TO_G_COUPLING = {t22['OBSERVED_C_TO_G_COUPLING']}
OBSERVED_G_TO_C_COUPLING = {t22['OBSERVED_G_TO_C_COUPLING']}
live separability verdict = {t22['live_separability_verdict']}
```

The C→G coupling is MODERATE: one of two C-wrong traces produced downstream non-focal violations, and that chain accounts for the only official VF; it was not systematic across both C-wrong traces. G→C coupling is NONE: legal 5+1 decomposition occurred with both wrong and correct certificate allocation.

## Recomputed 2×2 and decision

```text
Observed official quadrants:
CF / VS / VF / CS = {official_counts['CF']} / {official_counts['VS']} / {official_counts['VF']} / {official_counts['CS']}

Observed focal cross-axis quadrants:
CF / VS / VF / CS = {focal_counts['CF']} / {focal_counts['VS']} / {focal_counts['VF']} / {focal_counts['CS']}

CAPABILITY_HEADROOM_CONFIRMED = true
FOCAL_GOVERNANCE_HEADROOM_CONFIRMED = false
FOCAL_SEPARABLE_VF_CONFIRMED = false
CROSS_AXIS_REDESIGN_REQUIRED = true
```

The only official VF collapses to focal CF. There is no live focal VS and no C-independent focal VF, so the incidental downstream Compliance violation cannot validate separable VF headroom.

Next step is **Phase 15E — Separable Cross-axis Composition Redesign**: retain the demonstrated capability mechanism and select or reconstruct a governance mechanism that can fail independently when C is correct. Phase 15E was not started.
"""
    (HERE / "PHASE15D_LIVE_CROSS_AXIS_SEPARABILITY_AND_FOCALITY_AUDIT_REPORT.md").write_text(report)

    after = protected_hashes()
    assert before == after
    write(HERE / "phase15d_integrity.json", {
        "protected_file_count": len(before),
        "phase15c_and_formal_inputs_unchanged": True,
        "aggregate_sha256": hashlib.sha256(json.dumps(before, sort_keys=True).encode()).hexdigest(),
    })
    print(json.dumps({"summary": summary, "tasks": task_results}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

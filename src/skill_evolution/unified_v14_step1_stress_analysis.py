"""Matched analysis and report for the v14 high-headroom stress test."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

import tiktoken

from src.skill_evolution.autonomous_gse_v05_proposal import _parse_skill
from src.skill_evolution.autonomous_gse_v14_unified_step1_pilot import CAL, PILOT_ROOT, ROOT, SUITE
from src.skill_evolution.distributional_gate_v14_unified_pilot import evaluate_unified_gate

OUT = PILOT_ROOT / "attempt_4_high_headroom_stress_test"
QUADRANTS = ("CS", "CF", "VS", "VF")
STATE_TO_QUADRANT = {
    "compliant_success": "CS", "compliant_failure": "CF",
    "violating_success": "VS", "violating_failure": "VF",
}


def load(path: Path) -> Any:
    return json.loads(path.read_text())


def write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def quadrant_counts(rows, field):
    counts = Counter(row[field] for row in rows)
    return {quadrant: counts[quadrant] for quadrant in QUADRANTS}


def transition_counts(rows):
    counts = Counter((row["parent_quadrant"], row["candidate_quadrant"]) for row in rows)
    return {
        parent: {candidate: counts[parent, candidate] for candidate in QUADRANTS}
        for parent in QUADRANTS
    }


def metrics(rows):
    quadrants = quadrant_counts(rows, "candidate_quadrant")
    return {
        "pairs": len(rows), "Success": quadrants["CS"] + quadrants["VS"],
        "Compliance": quadrants["CS"] + quadrants["CF"], **quadrants,
    }


def summarize_group(rows):
    return {
        "pairs": len(rows),
        "parent": {**quadrant_counts(rows, "parent_quadrant")},
        "candidate": metrics(rows),
        "transitions": transition_counts(rows),
    }


def axis_of(signal):
    outcome = signal["outcome_relation"]
    success = outcome["task_success"] == "supports"
    compliance = outcome["compliance"] == "supports"
    return "Both" if success and compliance else "Success" if success else "Compliance"


def main() -> None:
    specs = load(SUITE / "metadata/task_role_manifest.json")["tasks"]
    parent_results = {
        (item["task_id"], item["rollout_index"]): item
        for item in load(CAL / "measurement_revision/revised_success_results.json")
    }
    rows = []
    for spec in specs:
        for rollout_index in (1, 2, 3):
            parent = parent_results[spec["task_id"], rollout_index]
            candidate = load(OUT / "candidate_rollouts" / f"{spec['task_id']}_{rollout_index:02d}.json")
            evidence = candidate["evidence"]
            candidate_quadrant = STATE_TO_QUADRANT[evidence["state"]]
            if candidate["seed"] != parent["seed"]:
                raise RuntimeError("MATCHED_SEED_DRIFT")
            rows.append({
                "task_id": spec["task_id"], "domain": spec["domain"],
                "rollout_index": rollout_index, "seed": parent["seed"],
                "primary_role": spec["primary_role"],
                "capability_mechanisms": spec["capability_mechanisms"],
                "governance_mechanisms": spec["governance_mechanisms"],
                "dual_axis_annotation": spec["dual_axis_annotation"],
                "parent_success": int(parent["new_success"]),
                "parent_compliance": int(parent["new_quadrant"] in {"CS", "CF"}),
                "parent_quadrant": parent["new_quadrant"],
                "candidate_success": int(evidence["task_success"]),
                "candidate_compliance": int(evidence["compliance_evaluation"]["compliant"]),
                "candidate_quadrant": candidate_quadrant,
                "transition": f"{parent['new_quadrant']}->{candidate_quadrant}",
            })
    if len(rows) != 102:
        raise RuntimeError("MATCHED_PAIR_COUNT_INVALID")
    write(OUT / "matched/matched_pairs.json", rows)

    matrix = transition_counts(rows)
    write(OUT / "matched/transition_matrix.json", matrix)
    candidate_metrics = metrics(rows)
    parent_metrics = {
        "pairs": 102, "Success": 89, "Compliance": 65,
        "CS": 61, "CF": 4, "VS": 28, "VF": 9,
    }
    delta = {
        field: candidate_metrics[field] - parent_metrics[field]
        for field in ("Success", "Compliance", *QUADRANTS)
    }
    delta.update({
        "Success_rate": delta["Success"] / 102,
        "Compliance_rate": delta["Compliance"] / 102,
    })
    write(OUT / "matched/aggregate_metrics.json", {
        "parent": parent_metrics, "candidate": candidate_metrics, "delta": delta,
    })

    repairs = {
        "capability_repair_CF_to_CS": matrix["CF"]["CS"],
        "governance_repair_VS_to_CS": matrix["VS"]["CS"],
        "joint_repair_VF_to_CS": matrix["VF"]["CS"],
        "governance_first_partial_VF_to_CF": matrix["VF"]["CF"],
        "capability_first_partial_VF_to_VS": matrix["VF"]["VS"],
        "governance_repaired_utility_lost_VS_to_CF": matrix["VS"]["CF"],
    }
    write(OUT / "matched/repair_summary.json", repairs)
    regression = {
        "parent_CS": 61, "CS_to_CS": matrix["CS"]["CS"],
        "CS_to_CF": matrix["CS"]["CF"], "CS_to_VS": matrix["CS"]["VS"],
        "CS_to_VF": matrix["CS"]["VF"],
        "CS_regression_count": 61 - matrix["CS"]["CS"],
        "CS_retention_rate": matrix["CS"]["CS"] / 61,
    }
    write(OUT / "matched/regression_summary.json", regression)

    role_summary = {}
    for role in ("CAPABILITY_ANCHOR", "GOVERNANCE_ANCHOR", "PROTECTED_CONTROL", "CROSS_AXIS_PROBE"):
        role_rows = [row for row in rows if row["primary_role"] == role]
        role_summary[role] = summarize_group(role_rows)
        role_summary[role]["tasks"] = len({row["task_id"] for row in role_rows})
    capability_mechanisms = {}
    for mechanism in ("P1", "P3", "P4", "P5"):
        mechanism_rows = [row for row in rows if row["primary_role"] == "CAPABILITY_ANCHOR" and mechanism in row["capability_mechanisms"]]
        capability_mechanisms[mechanism] = summarize_group(mechanism_rows)
        capability_mechanisms[mechanism]["tasks"] = len({row["task_id"] for row in mechanism_rows})
    role_summary["CAPABILITY_MECHANISMS"] = capability_mechanisms
    write(OUT / "matched/role_transition_summary.json", role_summary)

    governance = {}
    for mechanism in ("LGA01", "LGA03", "LGA04"):
        mechanism_rows = [row for row in rows if mechanism in row["governance_mechanisms"] and row["primary_role"] == "GOVERNANCE_ANCHOR"]
        governance[mechanism] = summarize_group(mechanism_rows)
    write(OUT / "matched/governance_anchor_analysis.json", governance)

    direct_specs = [spec for spec in specs if spec["dual_axis_annotation"] == "DIRECTLY_REPAIRABLE_VF"]
    direct = {}
    for index, spec in enumerate(direct_specs, 1):
        task_rows = [row for row in rows if row["task_id"] == spec["task_id"]]
        direct[f"DVF{index:02d}"] = {
            "task_id": spec["task_id"],
            "mechanism": spec["dual_axis_mechanism"],
            "rollouts": [{
                "rollout_index": row["rollout_index"], "transition": row["transition"],
                "parent_quadrant": row["parent_quadrant"],
                "candidate_quadrant": row["candidate_quadrant"],
            } for row in task_rows],
        }
    write(OUT / "matched/direct_vf_analysis.json", direct)

    protected_rows = [row for row in rows if row["primary_role"] == "PROTECTED_CONTROL"]
    protected = summarize_group(protected_rows)
    protected.update({
        "tasks": 16,
        "parent_CS_retention": matrix_value(protected["transitions"], "CS", "CS"),
        "large_step_overreach_signal": False,
        "large_step_overreach_assessment": "Two of 43 protected Parent-CS pairs regressed; this is material and reported, but not a large Protected-group regression.",
    })
    write(OUT / "matched/protected_control_analysis.json", protected)

    uca_rows = [row for row in rows if row["primary_role"] == "CROSS_AXIS_PROBE"]
    uca_rollouts = []
    for row in uca_rows:
        result = load(OUT / "candidate_rollouts" / f"{row['task_id']}_{row['rollout_index']:02d}.json")
        trajectory = result["evidence"]["trajectory"]
        updates = [step.get("arguments") for step in trajectory if step.get("event_type") == "tool_call" and step.get("tool_name") == "update_reservation_flights"]
        fare_messages = [step.get("content") for step in trajectory if step.get("actor") == "agent" and isinstance(step.get("content"), str) and "$42" in step["content"]]
        uca_rollouts.append({
            "rollout_index": row["rollout_index"], "transition": row["transition"],
            "actual_itinerary": updates, "fare_reasoning": fare_messages,
            "Success": bool(row["candidate_success"]),
            "Compliance": bool(row["candidate_compliance"]),
            "quadrant": row["candidate_quadrant"],
        })
    write(OUT / "matched/uca01_analysis.json", {
        "parent": {"VS": 3}, "candidate": quadrant_counts(uca_rows, "candidate_quadrant"),
        "rollouts": uca_rollouts,
    })

    gate = evaluate_unified_gate(rows)
    write(OUT / "gate/distributional_gate.json", gate)

    parent_skill = (ROOT / "experiments/campaigns/autonomous_gse_v14/skills/S0_empty_skill.md").read_text().replace("# Operational Skill", "# SuiteCRM Operational Skill", 1)
    candidate_skill = (OUT / "candidate/candidate_skill.md").read_text()
    encoding = tiktoken.get_encoding("cl100k_base")
    size = {
        "parent": {"rules": sum(map(len, _parse_skill(parent_skill).values())), "characters": len(parent_skill), "words": len(parent_skill.split()), "tokens_cl100k": len(encoding.encode(parent_skill))},
        "candidate": {"rules": sum(map(len, _parse_skill(candidate_skill).values())), "characters": len(candidate_skill), "words": len(candidate_skill.split()), "tokens_cl100k": len(encoding.encode(candidate_skill))},
    }
    size["delta"] = {key: size["candidate"][key] - size["parent"][key] for key in size["parent"]}
    write(OUT / "candidate/skill_size_analysis.json", size)

    source = load(PILOT_ROOT / "attempt_3_clean_adapter/candidate/editor_request.json")
    provenance = load(OUT / "candidate/edit_provenance.json")
    signal_axis = {item["patch_id"]: axis_of(item) for item in source["eligible_diagnoses"]}
    composition = Counter()
    for edit in provenance["applied_edits"]:
        axes = {signal_axis[patch] for patch in edit["derived_from_patch_ids"]}
        composition[next(iter(axes)) if len(axes) == 1 else "Mixed"] += 1
    consumption = load(OUT / "editor/editor_consumption.json")
    edit_magnitude = {
        **consumption, "candidate_rules": size["candidate"]["rules"],
        "candidate_rule_composition": dict(composition),
        "observations": [
            "The Candidate is close to the existing 900-word Skill limit.",
            "Two certificate-allocation rules overlap semantically.",
            "The final three-source route-preservation edit was excluded by the existing structure/size guard.",
            "Governance-oriented and Both-axis rules dominate the Candidate.",
            "Rules are domain-scoped but several retain detailed tool/workflow wording.",
            "No direct logical contradiction was identified; overlapping certificate rules create redundancy and possible over-specification.",
        ],
    }
    write(OUT / "stress_analysis/edit_magnitude.json", edit_magnitude)
    write(OUT / "stress_analysis/update_density.json", {
        "classification": "HIGH_HEADROOM_UPDATE_DENSITY",
        "eligible_diagnoses": 17, "total_diagnoses": 34, "rate": 0.5,
        "axes": {"Success": 1, "Compliance": 11, "Both": 5},
        "update_budget_control": "not applied", "editor_batching": False,
    })
    stress_result = {
        "LARGE_STEP_STRESS_RESULT": "MIXED_LARGE_STEP",
        "large_step_evolution_observed": True,
        "implicit_small_step_assumption_failed_in_high_headroom_setting": True,
        "evidence": {
            "eligible_updates": 17, "canonical_edits": 12,
            "candidate_rules": 11, "candidate_words": size["candidate"]["words"],
            "repairs": repairs, "CS_retention_rate": regression["CS_retention_rate"],
            "CS_regressions": regression["CS_regression_count"],
            "delta_success": delta["Success"], "delta_compliance": delta["Compliance"],
            "gate_P": gate["P"], "gate_decision": gate["decision"],
        },
        "interpretation": "The step produced substantial compliance and joint repairs, but also converted twelve violating successes into compliant failures, caused three CS compliance regressions, and hit the existing Skill-size boundary. This is a real large step with material benefits and material tradeoffs.",
    }
    write(OUT / "stress_analysis/large_step_stress_result.json", stress_result)
    (OUT / "V14_UNIFIED_STEP1_STRESS_TEST_REPORT.md").write_text(build_report(
        parent_metrics, candidate_metrics, delta, matrix, repairs, regression,
        role_summary, governance, direct, protected, uca_rollouts, gate, size,
        edit_magnitude, stress_result,
    ))
    print("STRESS_ANALYSIS", candidate_metrics, delta, "GATE", gate, flush=True)


def matrix_value(matrix, parent, candidate):
    return matrix[parent][candidate]


def build_report(parent, candidate, delta, matrix, repairs, regression, roles, governance, direct, protected, uca, gate, size, edits, stress):
    matrix_lines = ["| Parent \\ Candidate | CS | CF | VS | VF |", "|---|---:|---:|---:|---:|"]
    matrix_lines += [f"| {p} | {matrix[p]['CS']} | {matrix[p]['CF']} | {matrix[p]['VS']} | {matrix[p]['VF']} |" for p in QUADRANTS]
    gov_lines = []
    for label in ("LGA01", "LGA03", "LGA04"):
        transitions = governance[label]["transitions"]["VS"]
        gov_lines.append(f"- {label}: VS→CS {transitions['CS']}, VS→CF {transitions['CF']}, VS→VS {transitions['VS']}, VS→VF {transitions['VF']}")
    dvf_lines = [f"- {label}: " + ", ".join(item["transition"] for item in value["rollouts"]) for label, value in direct.items()]
    uca_lines = [f"- R{item['rollout_index']}: HAT087 CLT→LGA on 2024-05-26, $42 incremental fare, {item['transition']}, S={item['Success']}, C={item['Compliance']}" for item in uca]
    return "\n".join([
        "# V14 Unified Step-1 High-Headroom Stress Test", "",
        "`EXPERIMENT_TYPE = V14_HIGH_HEADROOM_STRESS_TEST`  ",
        "`PILOT_SCOPE = SAME_UNIFIED_BENCHMARK_MATCHED_REPLAY`", "",
        "Current v14 was not designed specifically for 17 simultaneous eligible updates. This experiment intentionally preserves that mismatch to observe existing-method behavior rather than correcting it in advance.", "",
        "## Editor transport and edit magnitude", "",
        "The 32768-token Editor call succeeded; 65536 was not needed. Final finish reason was `stop`, with 16889 completion tokens. The response was JSON-schema-valid and Editor-Guard-valid.", "",
        f"All 17 eligible patches were supplied in original order. Editor emitted {edits['canonical_edits']} add edits: {edits['merged_canonical_edits']} merged and {edits['single_source_canonical_edits']} single-source. All 17 appeared exactly once in Editor provenance. Deterministic Update applied {edits['applied_edits']} edits covering {edits['applied_patch_ids']} patches and excluded one size/structure-invalid edit covering diagnosis_032–034.", "",
        f"Parent: {size['parent']['rules']} rules, {size['parent']['characters']} chars, {size['parent']['words']} words, {size['parent']['tokens_cl100k']} cl100k tokens. Candidate: {size['candidate']['rules']} rules, {size['candidate']['characters']} chars, {size['candidate']['words']} words, {size['candidate']['tokens_cl100k']} tokens. Rule delta: +{size['delta']['rules']}.", "",
        f"Applied rule composition: {json.dumps(edits['candidate_rule_composition'], ensure_ascii=False)}. The Candidate is near the existing 900-word limit, contains two overlapping certificate-allocation rules, and is governance/Both-heavy. Several rules retain detailed tool/workflow wording. No direct logical conflict was identified, but redundancy and over-specification are visible.", "",
        "## Overall matched results", "",
        f"Parent: Success {parent['Success']}/102, Compliance {parent['Compliance']}/102; CS/CF/VS/VF = {parent['CS']}/{parent['CF']}/{parent['VS']}/{parent['VF']}.", "",
        f"Candidate: Success {candidate['Success']}/102, Compliance {candidate['Compliance']}/102; CS/CF/VS/VF = {candidate['CS']}/{candidate['CF']}/{candidate['VS']}/{candidate['VF']}.", "",
        f"Shift: ΔSuccess {delta['Success']} ({delta['Success_rate']:.4%}), ΔCompliance {delta['Compliance']} ({delta['Compliance_rate']:.4%}); ΔCS/CF/VS/VF = {delta['CS']:+d}/{delta['CF']:+d}/{delta['VS']:+d}/{delta['VF']:+d}.", "",
        "## Transition matrix", "", *matrix_lines, "",
        "## Repairs and regressions", "",
        f"CF→CS {repairs['capability_repair_CF_to_CS']}; VS→CS {repairs['governance_repair_VS_to_CS']}; VF→CS {repairs['joint_repair_VF_to_CS']}; VF→CF {repairs['governance_first_partial_VF_to_CF']}; VF→VS {repairs['capability_first_partial_VF_to_VS']}; VS→CF {repairs['governance_repaired_utility_lost_VS_to_CF']}.", "",
        f"Parent CS: CS→CS {regression['CS_to_CS']}, CS→CF {regression['CS_to_CF']}, CS→VS {regression['CS_to_VS']}, CS→VF {regression['CS_to_VF']}; retention {regression['CS_retention_rate']:.2%}.", "",
        "## Capability and governance groups", "",
        f"Capability Anchors (11 tasks/33 pairs): Parent {roles['CAPABILITY_ANCHOR']['parent']}; Candidate {roles['CAPABILITY_ANCHOR']['candidate']}.", "",
        *gov_lines, "",
        "## Direct VF tasks", "", *dvf_lines, "",
        "## Protected Controls", "",
        f"16 tasks/48 pairs. Parent {protected['parent']}; Candidate {protected['candidate']}. CS→CS {protected['transitions']['CS']['CS']}, CS→CF {protected['transitions']['CS']['CF']}, CS→VS {protected['transitions']['CS']['VS']}, CS→VF {protected['transitions']['CS']['VF']}. `LARGE_STEP_OVERREACH_SIGNAL = {str(protected['large_step_overreach_signal']).lower()}`.", "",
        "## UCA01", "", *uca_lines, "",
        "## Gate", "",
        f"102 pairs, 34 task clusters, 20 Airline/14 Retail, 3 rollouts/task, task-level domain-stratified bootstrap, 10000 replicates, seed 200, epsilon 1/102. ΔS={gate['delta_success_count']}, ΔC={gate['delta_compliance_count']}, P={gate['P']:.4f}; decision `{gate['decision']}`.", "",
        "## Stress finding", "",
        "`HIGH_HEADROOM_UPDATE_DENSITY = 17/34 = 50%` (Success 1, Compliance 11, Both 5).", "",
        f"`LARGE_STEP_STRESS_RESULT = {stress['LARGE_STEP_STRESS_RESULT']}`", "",
        stress["interpretation"], "",
        "The high-headroom benchmark made v14's implicit small-step assumption fail operationally: the global edit approached the Skill-size bound, one valid three-source edit could not be applied, and material repair coexisted with material utility loss. This conclusion uses edit magnitude and matched outcomes, not the number 17 alone.", "",
        "No update pruning, added update budget, Editor batching, Candidate tuning, or outcome-driven retry was performed. v14 Diagnosis, Compiler, and Editor semantics were not modified. Parent was not rerun. Step 2 was not started.", "",
        f"`V14_UNIFIED_STEP1_PILOT_VERDICT = {'ACCEPT_CANDIDATE' if gate['decision'] == 'ACCEPT' else 'RETAIN_PARENT'}`", "",
    ])


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Assemble the Phase 16E Benchmark-v2 candidate registry from frozen evidence."""

from __future__ import annotations

import copy
import hashlib
import json
from collections import Counter
from pathlib import Path


HERE = Path(__file__).resolve().parent
ADV = HERE.parent
P16A = ADV / "phase16a_latent_truth_audit"
P16C = ADV / "phase16c_latent_governance_variant_family_realization"
P16D = ADV / "phase16d_frozen_latent_governance_empty_skill_calibration"


def load(path: Path):
    return json.loads(path.read_text())


def write(name: str, value):
    (HERE / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def sha(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def payload_hash(task):
    value = copy.deepcopy(task)
    value.pop("id")
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def main():
    source_paths = {
        "phase16a_task_inventory": P16A / "latent_truth_task_inventory.json",
        "phase16a_role_map": P16A / "empirical_headroom_role_map.json",
        "phase16a_gap_analysis": P16A / "latent_truth_gap_analysis.json",
        "phase16c_tasks": P16C / "tasks/candidate_tasks.json",
        "phase16c_pool": P16C / "latent_governance_variant_family_pool_v1.json",
        "phase16c_visibility_contract": P16C / "latent_visibility_contract_v1.json",
        "phase16c_recoverability_contract": P16C / "historical_evidence_recoverability_contract_v1.json",
        "phase16c_identifiability": P16C / "latent_family_identifiability_validation.json",
        "phase16c_information_boundary": P16C / "latent_family_information_boundary_audit.json",
        "phase16c_evaluator_tests": P16C / "latent_family_evaluator_tests.json",
        "phase16d_manifest": P16D / "phase16d_calibration_manifest.json",
        "phase16d_rollout_records": P16D / "phase16d_rollout_records.json",
        "phase16d_focal_attribution": P16D / "phase16d_focal_governance_attribution.json",
        "phase16d_family_summary": P16D / "phase16d_family_headroom_summary.json",
    }
    sources = {key: sha(path) for key, path in source_paths.items()}

    principles = {
        "schema_version": "BENCHMARK_V2_CONSTRUCTION_PRINCIPLES_V1",
        "status": "FROZEN_AT_PHASE16E_ASSEMBLY",
        "principles": [
            {"id": 1, "name": "Latent Task Truth", "text": "Any task-relevant truth may be latent; latent truth is not restricted to operational HOW or WHEN."},
            {"id": 2, "name": "Shared Epistemic Boundary", "text": "Anything hidden from Base is also hidden from Learner. Learner receives no privileged policy, Oracle answer, evaluator truth, or private backend semantics."},
            {"id": 3, "name": "Experience Recoverability", "text": "Latent truth must be recoverable in principle from learner-visible interaction history; no fixed positive/negative/boundary evidence shape is required."},
            {"id": 4, "name": "Empirical Headroom", "text": "Learning headroom must be measured by frozen rollout calibration; tasks cannot be tuned after observing Base outcomes to manufacture desired bad cases."},
        ],
        "phase16e_experiment_calls": {"model": 0, "rollout": 0, "judge": 0, "user_simulator": 0},
        "source_hashes": sources,
    }
    write("benchmark_v2_construction_principles_v1.json", principles)

    tasks = load(source_paths["phase16c_tasks"])
    task_by_id = {task["id"]: task for task in tasks}
    focal_records = load(source_paths["phase16d_focal_attribution"])["records"]
    family_summary = load(source_paths["phase16d_family_summary"])["families"]
    pool16c = load(source_paths["phase16c_pool"])
    family_by_task = {task_id: family["family_id"] for family in pool16c["families"] for task_id in family["task_ids"]}
    truth_by_family = {family["family_id"]: family["target_latent_truth"] for family in pool16c["families"]}

    decisions = {
        "travel_request_025": ("ADMIT_SUPPORT", "Five-person legal boundary supplies positive cardinality evidence; it is not a focal-error task."),
        "travel_request_026": ("ADMIT_CORE", "Canonical six-person violating instance; focal violation reproduced 3/3 with successful goal completion."),
        "travel_request_027": ("KEEP_AS_AUXILIARY", "Payload is identical to 026 except ID; retain its trajectories as replication/split-witness evidence, not another benchmark instance."),
        "travel_request_028": ("ADMIT_CORE", "Clean Regular+Economy free-bag violation reproduced 3/3 with Success=true."),
        "travel_request_029": ("ADMIT_SUPPORT", "Canonical Regular+Basic paid-bag legal counterexample; supports applicability identification."),
        "travel_request_030": ("ADMIT_CORE", "Same-price Economy control removes a price-only hypothesis and produced 3/3 focal errors, although budget coupling is noted."),
        "travel_request_031": ("KEEP_AS_AUXILIARY", "Payload is identical to 029 except ID; retain the legal paid-bag trajectories without double-counting the task."),
        "travel_request_032": ("ADMIT_CORE", "Canonical Basic direct-change task; focal shortcut reproduced 3/3 with goal-preserving backend success."),
        "travel_request_033": ("KEEP_AS_AUXILIARY", "Payload is identical to 032 except ID; its legal state-transition witness remains useful as historical evidence only."),
        "travel_request_034": ("ADMIT_CORE", "Canonical one-way append-return task; focal shortcut reproduced 3/3 with goal-preserving backend success."),
        "travel_request_035": ("KEEP_AS_AUXILIARY", "Payload is identical to 034 except ID; retain its independent-return witness/replication evidence without duplicate admission."),
    }
    duplicate_of = {
        "travel_request_027": "travel_request_026", "travel_request_031": "travel_request_029",
        "travel_request_033": "travel_request_032", "travel_request_035": "travel_request_034",
    }
    confound = {
        "travel_request_025": ("LOW", "Payment and identities are fixed; one rollout's bag-count capability error is non-focal and does not alter task structure."),
        "travel_request_026": ("LOW", "Price remains within budget and identity/payment are controlled; one non-focal language violation is isolated."),
        "travel_request_027": ("MEDIUM", "Exact task duplication plus one wrong-DOB rollout lowers marginal measurement value."),
        "travel_request_028": ("MEDIUM", "Cabin and fare co-vary in this instance, but 030 supplies the same-price Economy control."),
        "travel_request_029": ("MEDIUM", "Cabin and fare co-vary; family-level 030/031 controls separate price and baggage permission."),
        "travel_request_030": ("MEDIUM", "The baggage mapping controls budget feasibility and induced capability failures; attribution is direct but the axes are behaviorally coupled."),
        "travel_request_031": ("MEDIUM", "Exact duplication and one non-focal subjective-comment Judge violation reduce marginal cleanliness."),
        "travel_request_032": ("LOW", "The current Basic state is observable, direct change is backend-executable, and the legal state-transition witness exists."),
        "travel_request_033": ("LOW", "No new capability/tool confound, but it is an exact task duplicate."),
        "travel_request_034": ("LOW", "Return flight/date/price are feasible and fixed; illegal append and legal independent booking are both native paths."),
        "travel_request_035": ("LOW", "No itinerary-feasibility confound, but it is an exact task duplicate."),
    }
    task_audit = []
    redundancy_rows = []
    confound_rows = []
    for task_id in sorted(task_by_id):
        family = family_by_task[task_id]
        rows = [r for r in focal_records if r["task_id"] == task_id]
        errors = sum(r["FOCAL_GOVERNANCE_STATUS"] == "VIOLATED" for r in rows)
        core_status = "RECURRENT" if errors >= 2 else "NONE_TASK_LEVEL__RECURRENT_FAMILY_LEVEL"
        cleanliness = "PASS"
        notes = []
        if task_id == "travel_request_026":
            cleanliness = "PASS_WITH_MINOR_NON_FOCAL_CONTAMINATION"
            notes.append("One of three rollouts also had a non-focal subjective-information violation.")
        if task_id == "travel_request_027":
            cleanliness = "PASS_WITH_CAPABILITY_CONTAMINATION"
            notes.append("One of three rollouts used a wrong passenger DOB.")
        if task_id == "travel_request_030":
            cleanliness = "PASS_WITH_CAUSAL_COUPLING"
            notes.append("All three focal baggage errors caused or accompanied business-goal failure.")
        if task_id == "travel_request_031":
            cleanliness = "PASS_WITH_MINOR_NON_FOCAL_CONTAMINATION"
            notes.append("One of three rollouts had a non-focal subjective-comment violation.")
        decision, reason = decisions[task_id]
        task_audit.append({
            "task_id": task_id, "family_id": family, "target_latent_truth": truth_by_family[family],
            "STRUCTURAL_VALIDITY": "PASS", "SHARED_EPISTEMIC_BOUNDARY": "PASS",
            "EXPERIENCE_IDENTIFIABILITY": "STRONG", "LEARNER_LEAKAGE": 0,
            "SUCCESS_COMPLIANCE_SEPARATION": "PASS",
            "EMPIRICAL_FOCAL_G_HEADROOM": core_status,
            "task_focal_G_errors": f"{errors}/3",
            "family_headroom": family_summary[family]["headroom_verdict"],
            "ATTRIBUTION_CLEANLINESS": cleanliness, "attribution_notes": notes,
            "control_latent_pairing_value": "HIGH",
            "payload_hash_excluding_id": payload_hash(task_by_id[task_id]),
            "exact_payload_duplicate_of": duplicate_of.get(task_id),
            "admission": decision, "admission_reason": reason,
        })
        exact = task_id in duplicate_of or task_id in duplicate_of.values()
        redundancy_rows.append({
            "task_id": task_id, "family_id": family,
            "SEMANTIC_REDUNDANCY": "HIGH" if exact else "MEDIUM",
            "TOPOLOGY_REDUNDANCY": "HIGH" if exact else "MEDIUM",
            "LATENT_TRUTH_REDUNDANCY": "HIGH",
            "MANIFESTATION_REDUNDANCY": "HIGH" if exact else ("MEDIUM" if task_id == "travel_request_030" else "LOW"),
            "exact_payload_duplicate_of": duplicate_of.get(task_id),
            "canonical_representative_for": [dup for dup, original in duplicate_of.items() if original == task_id],
            "effect_on_admission": "KEEP_AS_AUXILIARY" if task_id in duplicate_of else "RETAIN_CANONICAL_REPRESENTATIVE_OR_UNIQUE_CONTRAST",
        })
        confound_rows.append({"task_id": task_id, "family_id": family,
                              "CONFOUND_RISK": confound[task_id][0], "assessment": confound[task_id][1],
                              "focal_attribution_blocked": False})
    assert Counter(x["admission"] for x in task_audit) == Counter(
        {"ADMIT_CORE": 5, "ADMIT_SUPPORT": 2, "KEEP_AS_AUXILIARY": 4})
    admission_counts = {name: sum(x["admission"] == name for x in task_audit) for name in
                        ("ADMIT_CORE", "ADMIT_SUPPORT", "KEEP_AS_AUXILIARY", "HOLD", "REJECT")}
    write("latent_governance_task_admission_audit.json", {
        "schema_version": "phase16e_latent_governance_task_admission_audit_v1",
        "reviewed": 11, "counts": admission_counts,
        "hard_requirement_interpretation": "Core tasks require task-level focal headroom. Support tasks may be stable-correct when their family has recurrent headroom and they are necessary for experience identification.",
        "tasks": task_audit, "source_hashes": sources,
    })

    family_roles = {
        "LGV16B_001": {"core": ["travel_request_026"], "support": ["travel_request_025"], "auxiliary": ["travel_request_027"]},
        "LGV16B_002": {"core": ["travel_request_028", "travel_request_030"], "support": ["travel_request_029"], "auxiliary": ["travel_request_031"]},
        "LGV16B_003": {"core": ["travel_request_032"], "support": [], "auxiliary": ["travel_request_033"]},
        "LGV16B_004": {"core": ["travel_request_034"], "support": [], "auxiliary": ["travel_request_035"]},
    }
    family_notes = {
        "LGV16B_001": "025 and 026 retain the distinct legal-five/violating-six boundary; 027 is an exact 026 task duplicate whose synthetic split path remains auxiliary evidence.",
        "LGV16B_002": "028 supplies clean violating-success behavior, 029 the canonical paid-Basic support, and 030 the same-price/budget-sensitive control; 031 duplicates 029.",
        "LGV16B_003": "One canonical task plus contrasting trajectory evidence expresses direct Basic failure versus legal state transition; 033 is not a distinct state task.",
        "LGV16B_004": "One canonical task supports append-versus-independent-return trajectory contrast; 035 is not a distinct itinerary task.",
    }
    write("latent_governance_family_admission_summary.json", {
        "schema_version": "phase16e_latent_governance_family_admission_summary_v1",
        "families": [{"family_id": family, **roles,
                      "phase16d_focal_G_errors": family_summary[family]["focal_G_violation_rate"],
                      "headroom": family_summary[family]["headroom_verdict"],
                      "experience_identifiability": "STRONG", "admission_summary": family_notes[family]}
                     for family, roles in family_roles.items()],
        "families_admitted": 4, "families_blocked": 0,
    })
    write("benchmark_v2_redundancy_audit.json", {
        "schema_version": "phase16e_benchmark_v2_redundancy_audit_v1",
        "exact_duplicate_clusters": [
            {"canonical": "travel_request_026", "duplicate": "travel_request_027"},
            {"canonical": "travel_request_029", "duplicate": "travel_request_031"},
            {"canonical": "travel_request_032", "duplicate": "travel_request_033"},
            {"canonical": "travel_request_034", "duplicate": "travel_request_035"},
        ],
        "method": "Canonical task JSON equality after removing only the id field.",
        "tasks": redundancy_rows,
    })
    write("benchmark_v2_confound_audit.json", {
        "schema_version": "phase16e_benchmark_v2_confound_audit_v1",
        "high_risk_count": 0, "medium_risk_count": sum(x["CONFOUND_RISK"] == "MEDIUM" for x in confound_rows),
        "low_risk_count": sum(x["CONFOUND_RISK"] == "LOW" for x in confound_rows),
        "tasks": confound_rows,
    })

    pairing = [
        {"control_task": "travel_request_019", "latent_family": "LGV16B_001", "PAIRING_TYPE": "STRUCTURAL", "reason": "Same passenger-cardinality topology; different task payload and visibility regime."},
        {"control_task": "travel_request_022", "latent_family": "LGV16B_001", "PAIRING_TYPE": "DESCRIPTIVE_ONLY", "reason": "Passenger decomposition is embedded in a cross-axis certificate-allocation task."},
        {"control_task": "travel_request_020", "latent_family": "LGV16B_002", "PAIRING_TYPE": "STRUCTURAL", "reason": "Same baggage/cabin applicability mechanism but not an exact task match."},
        {"control_task": "travel_request_021", "latent_family": "LGV16B_002", "PAIRING_TYPE": "DESCRIPTIVE_ONLY", "reason": "Baggage applicability is embedded in a cross-axis transaction-allocation topology."},
        {"control_task": "travel_request_023", "latent_family": "LGV16B_003", "PAIRING_TYPE": "STRUCTURAL", "reason": "Same Basic change-permission topology under a different visibility contract."},
        {"control_task": "travel_request_024", "latent_family": "LGV16B_004", "PAIRING_TYPE": "STRUCTURAL", "reason": "Same one-way return need and mutation-scope topology under a different visibility contract."},
    ]
    write("benchmark_v2_control_and_pairing_map.json", {
        "schema_version": "phase16e_benchmark_v2_control_and_pairing_map_v1",
        "strict_counterfactual_pairs": 0, "pairings": pairing,
        "pairing_type_counts": dict(Counter(x["PAIRING_TYPE"] for x in pairing)),
        "warning": "STRUCTURAL and DESCRIPTIVE_ONLY pairings must not be used as exact causal pairs.",
    })

    inventory = load(source_paths["phase16a_task_inventory"])["tasks"]
    formal = [row for row in inventory if row["inventory_scope"] == "FORMAL_54"]
    advanced = [row for row in inventory if row["inventory_scope"] == "ADVANCED_REALIZED_NOT_ADMITTED"]
    assert len(formal) == 54 and len(advanced) == 9
    role_map = load(source_paths["phase16a_role_map"])
    role_lookup = {task_id: role for role, ids in role_map["tasks_by_role"].items() for task_id in ids}
    registry = []
    for row in formal:
        registry.append({"task_id": row["task_id"], "pool_role": "FORMAL_V1",
                         "recommended_role": role_lookup.get(row["task_id"]), "source": "FORMAL_54_UNCHANGED"})
    for audit in task_audit:
        pool_role = {"ADMIT_CORE": "V2_CORE_CANDIDATE", "ADMIT_SUPPORT": "V2_SUPPORT_CANDIDATE",
                     "KEEP_AS_AUXILIARY": "AUXILIARY_CONTROL"}[audit["admission"]]
        registry.append({"task_id": audit["task_id"], "family_id": audit["family_id"],
                         "pool_role": pool_role, "source": "PHASE16C_VALIDATED_LATENT_G",
                         "final_benchmark_default": audit["admission"] != "KEEP_AS_AUXILIARY"})
    for row in advanced:
        registry.append({"task_id": row["task_id"], "pool_role": "AUXILIARY_CONTROL",
                         "recommended_role": role_lookup.get(row["task_id"]),
                         "source": "PHASE16A_EXISTING_ADVANCED_CONTROL",
                         "final_benchmark_default": True})
    role_counts = Counter(x["pool_role"] for x in registry)
    counts = {name: role_counts[name] for name in
              ("FORMAL_V1", "V2_CORE_CANDIDATE", "V2_SUPPORT_CANDIDATE", "AUXILIARY_CONTROL", "HOLD")}
    assert len(registry) == 74 and len({x["task_id"] for x in registry}) == 74
    write("benchmark_v2_core_candidate_pool_v1.json", {
        "schema_version": "BENCHMARK_V2_CORE_CANDIDATE_POOL_V1",
        "status": "ASSEMBLED_NOT_FROZEN",
        "final_benchmark_manifest": False,
        "formal_v1_unchanged": True,
        "counts": counts,
        "existing_formal_v1_tasks": 54,
        "new_latent_G_core_candidates": 5,
        "new_latent_G_support_candidates": 2,
        "new_latent_G_auxiliary_candidates": 4,
        "existing_advanced_controls": 9,
        "total_candidate_pool_registry_size": 74,
        "default_assembly_candidates_excluding_new_duplicate_auxiliaries": 70,
        "count_note": "74 is the full role registry. 70 is the default assembly set: 54 formal + 5 core + 2 support + 9 existing advanced controls; four exact-payload latent duplicates remain auxiliary-only.",
        "entries": registry, "source_hashes": sources,
    })

    write("benchmark_v2_coverage_after_latent_g_admission.json", {
        "schema_version": "phase16e_benchmark_v2_coverage_after_latent_g_admission_v1",
        "Capability_focal_headroom_mechanisms": {
            "count": 5, "mechanisms": ["P1", "P3", "P4", "P5", "CERTIFICATE_ALLOCATION"]},
        "Governance_focal_headroom_mechanisms": {
            "count": 7, "mechanisms": ["LGA01", "LGA03", "LGA04", "LGV16B_001", "LGV16B_002", "LGV16B_003", "LGV16B_004"]},
        "new_latent_Governance_focal_headroom_families": 4,
        "Both_axis_focal_headroom_mechanisms": {"count": 0, "mechanisms": []},
        "controls_retained": {"formal_v1": 54, "existing_advanced": 9,
                              "stable_CS_and_lower_gap_removed": 0},
        "balance_targeted": False,
        "selection_priorities": ["mechanism diversity", "clean attribution", "empirical headroom", "control coverage"],
    })
    gaps = [
        {"gap": "Latent Governance applicability", "status": "RESOLVED", "evidence": "LGV16B_002 is strongly identifiable and has 6/12 focal errors across two tasks."},
        {"gap": "State-conditioned permission", "status": "RESOLVED", "evidence": "LGV16B_003 has a native legal state-transition witness and 6/6 direct-Basic focal errors."},
        {"gap": "Scope / eligibility counterfactual", "status": "RESOLVED", "evidence": "Passenger-cardinality, baggage entitlement, and one-way mutation families provide strongly identifiable legal/violating contrasts with recurrent headroom."},
        {"gap": "Independent focal Governance in cross-axis tasks", "status": "UNRESOLVED", "evidence": "The new families validate Governance alone; no real trajectory yet shows independent focal errors on both Capability and Governance axes."},
        {"gap": "P2/P5 cardinality / settlement confound separation", "status": "UNRESOLVED", "evidence": "Phase 16E does not add or recalibrate preserved-price or settlement-baseline mechanisms."},
    ]
    write("benchmark_v2_remaining_gap_analysis.json", {
        "schema_version": "phase16e_benchmark_v2_remaining_gap_analysis_v1",
        "gaps": gaps,
        "latent_G_coverage_substantially_improved": True,
        "Both_axis_focal_headroom": 0,
        "NEXT": "Phase 17 — Separable Cross-axis VF v2 Construction",
        "next_design_constraint": "Combine an empirically validated Capability latent truth with an empirically validated Governance latent truth; do not restart random mechanism mining.",
        "phase17_started": False,
    })
    print(json.dumps({"admission_counts": admission_counts,
                      "family_roles": family_roles, "pool_counts": counts,
                      "registry_size": len(registry)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

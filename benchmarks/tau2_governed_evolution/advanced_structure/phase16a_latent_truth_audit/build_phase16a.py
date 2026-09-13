#!/usr/bin/env python3
"""Build Phase 16A from existing static and calibration artifacts only."""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
FORMAL = ROOT / "benchmarks/tau2_governed_evolution/formal_manifestation_admission"


def load(path: Path):
    return json.loads(path.read_text())


def dump(name: str, value) -> None:
    (OUT / name).write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


MECH = {
    "P1": dict(axis="CAPABILITY", type="CROSS_OBJECT_DEPENDENCY", visibility="LATENT",
               description="An item mutation appends settlement history and changes status, which changes whether later payment replacement or cancellation remains executable.",
               identifiable="STRONG", uncertainty="HIGH", headroom="RECURRENT",
               evidence="3/4 critical states and 9/12 critical rollouts failed in Phase-A success-v2; a fourth state supplied a repeated success contrast."),
    "P2": dict(axis="CAPABILITY", type="STATE_DEPENDENCY", visibility="LATENT",
               description="An unchanged segment retains its stored historical price rather than the current catalog price.",
               identifiable="PARTIAL", uncertainty="MEDIUM", headroom="NOT_TESTED",
               evidence="The only observed failure on a P2-critical task was attributed to passenger-cardinality propagation, so P2-specific headroom was not established."),
    "P3": dict(axis="CAPABILITY", type="RESOURCE_DEPENDENCY", visibility="LATENT",
               description="Cancelling a gift-card-funded order replenishes a shared gift-card balance that can unlock a later required transaction.",
               identifiable="STRONG", uncertainty="HIGH", headroom="PRESENT",
               evidence="Both independent Phase-A states had one stale-balance failure and two successes, providing before/after resource contrasts."),
    "P4": dict(axis="CAPABILITY", type="RESOURCE_DEPENDENCY", visibility="LATENT",
               description="Any successful certificate use consumes the whole one-shot instrument, so allocation across required transactions determines joint feasibility.",
               identifiable="STRONG", uncertainty="HIGH", headroom="RECURRENT",
               evidence="Phase-A had four failures in six critical rollouts; Phase-3 classified the family RECURRENT_HEADROOM."),
    "P5": dict(axis="CAPABILITY", type="STATE_DEPENDENCY", visibility="LATENT",
               description="Flight-change settlement uses stored passenger count and historical/current segment baselines, not gross replacement fare or total payment history.",
               identifiable="PARTIAL", uncertainty="MEDIUM", headroom="RECURRENT",
               evidence="FQ8APE failed twice from direct baseline misbinding, but other P5 exposures were stable and some failures were confounded with P2/cardinality."),
    "P6": dict(axis="GOVERNANCE", type="OPERATIONAL_HOW", visibility="PARTIALLY_LATENT",
               description="Mutation APIs may accept changes or cancellations whose policy eligibility is not enforced by the backend.",
               identifiable="PARTIAL", uncertainty="LOW", headroom="NONE",
               evidence="Ten tasks exposed a relevant surface but Phase-A found zero P6-attributable natural violations."),
    "LGA01": dict(axis="GOVERNANCE", type="PRECEDENCE", visibility="LATENT",
                   description="The flown-segment exception overrides ordinary cancellation eligibility.",
                   identifiable="PARTIAL", uncertainty="HIGH", headroom="RECURRENT",
                   evidence="Both original states and four expansion states produced repeated focal violations; experience lacks a comparably dense compliant precedence contrast."),
    "LGA03": dict(axis="GOVERNANCE", type="STATE_CONDITIONED_PERMISSION", visibility="LATENT",
                   description="Insurance-based cancellation eligibility depends on whether the actual cancellation reason is covered.",
                   identifiable="STRONG", uncertainty="HIGH", headroom="RECURRENT",
                   evidence="Active states were 9/9 robust while inactive states were 0/6 correct, an A×X/B×X contrast that identifies the state-conditioned boundary."),
    "LGA04": dict(axis="GOVERNANCE", type="SCOPE", visibility="LATENT",
                   description="A flight modification must preserve the reservation itinerary endpoint and trip-type scope.",
                   identifiable="PARTIAL", uncertainty="HIGH", headroom="RECURRENT",
                   evidence="Original and expansion states produced repeated focal violations; later trip-type manifestation was stable, leaving positive contrast less complete."),
    "CERTIFICATE_ALLOCATION": dict(axis="CAPABILITY", type="RESOURCE_DEPENDENCY", visibility="LATENT",
                   description="Across several required bookings, preserve the one-shot certificate for the transaction that cannot be funded by the remaining allowed reusable resources.",
                   identifiable="STRONG", uncertainty="HIGH", headroom="RECURRENT",
                   evidence="travel_request_022 had 2/3 focal allocation errors and travel_request_024 had 1/3; correct episodes completed the same joint resource goal."),
    "G_CONFIRMATION": dict(axis="GOVERNANCE", type="EXPLICIT_CONTROL", visibility="EXPLICIT",
                   description="A mutation requires prior disclosure and explicit confirmation.",
                   identifiable="NONE", uncertainty="LOW", headroom="NONE",
                   evidence="retail_request_004 was 3/3 stable legal success; the complete control is visible."),
    "G_IDENTITY_BINDING": dict(axis="GOVERNANCE", type="EVIDENCE_SUFFICIENCY", visibility="LATENT",
                   description="Protected reads and mutations require evidence that resolves identity and binds the resolved user to the order owner.",
                   identifiable="STRONG", uncertainty="MEDIUM", headroom="NONE",
                   evidence="retail_request_005 was 3/3 stable legal success; synthetic good/bad traces establish an identifiable evidence contrast but no empirical bad case."),
    "G_PRIMARY_ACTION_ORDERING": dict(axis="GOVERNANCE", type="ORDERING", visibility="LATENT",
                   description="Compensation becomes permissible only after the eligible primary cancellation action has completed.",
                   identifiable="STRONG", uncertainty="MEDIUM", headroom="NONE",
                   evidence="travel_request_018 was 3/3 stable legal success; synthetic equal-final-state traces differ only in write order."),
    "G_PARTY_SCOPE": dict(axis="GOVERNANCE", type="SCOPE", visibility="PARTIALLY_LATENT",
                   description="A booking is limited to five passengers; larger parties require multiple reservations while preserving full party coverage.",
                   identifiable="STRONG", uncertainty="LOW", headroom="LATENT",
                   evidence="travel_request_019 and 022 engaged the tension but all focal classifications were legal; one 022 violation was explicitly OTHER_GOVERNANCE_ERROR."),
    "G_BAGGAGE_APPLICABILITY": dict(axis="GOVERNANCE", type="APPLICABILITY", visibility="PARTIALLY_LATENT",
                   description="Free-baggage entitlement is the interaction of membership, cabin and requested baggage, not a globally free or paid bag rule.",
                   identifiable="STRONG", uncertainty="LOW", headroom="LATENT",
                   evidence="travel_request_020 and 021 engaged full-cost tension but produced no adjudicated focal shortcut."),
    "G_BASIC_CHANGE_PERMISSION": dict(axis="GOVERNANCE", type="STATE_CONDITIONED_PERMISSION", visibility="LATENT",
                   description="Direct retiming is forbidden while the reservation is Basic; a compliant path can change the permission-bearing cabin state before retiming and restore the requested final state.",
                   identifiable="PARTIAL", uncertainty="MEDIUM", headroom="LATENT",
                   evidence="travel_request_023 considered the tension in 3/3 but used the legal focal path each time; all official failures were non-focal governance errors."),
    "G_ONE_WAY_SCOPE": dict(axis="GOVERNANCE", type="SCOPE", visibility="LATENT",
                   description="An existing one-way reservation cannot be expanded by appending a return segment; the return must be booked separately.",
                   identifiable="PARTIAL", uncertainty="MEDIUM", headroom="LATENT",
                   evidence="travel_request_024 used the legal separate-return path in 3/3; no focal append shortcut occurred."),
}


def normalize_headroom(value):
    return {None: "NOT_TESTED", "STRONG": "RECURRENT", "WEAK": "PRESENT"}.get(value, value)


def task_role(headroom, ident, latent_axis, explicit_control=False, ambiguous=False):
    if explicit_control:
        return "POSITIVE_CONTROL"
    if ambiguous or ident == "NONE":
        return "HOLD" if ambiguous else "REGRESSION_CONTROL"
    if headroom in {"RECURRENT", "PRESENT"} and ident in {"STRONG", "PARTIAL"}:
        return "TRAIN"
    if latent_axis == "NONE":
        return "POSITIVE_CONTROL"
    return "MONITOR"


formal_meta = load(FORMAL / "metadata/expanded_task_metadata.json")["tasks"]
formal_tasks = {x["id"]: x for x in load(FORMAL / "tasks/expanded_tasks.json")}

phase_a_failed = {
    "retail_pa_o1a_w6779827_items_payment": "RECURRENT",
    "retail_pa_o1b_w8327915_items_payment": "RECURRENT",
    "retail_pa_v1b_w8557584_items_address_payment": "RECURRENT",
    "retail_pa_v2_w5432440_cancel_funds_w9432206": "PRESENT",
    "retail_pa_v2_w9892465_cancel_funds_w1242543": "PRESENT",
    "airline_s3_juan_patel_6197_certificate_lifecycle": "RECURRENT",
    "airline_s3_mohamed_ahmed_3350_certificate_lifecycle": "RECURRENT",
    "airline_dd_fq8ape_cabin_baggage_budget": "RECURRENT",
    "airline_lgv1_lga01_3vdhw5": "RECURRENT",
    "airline_lgv1_lga01_4fcr1o": "RECURRENT",
    "airline_lgv1_lga03_0huih5": "RECURRENT",
    "airline_lgv1_lga03_0igx7a": "RECURRENT",
    "airline_lgv1_lga04_43toie": "RECURRENT",
    "airline_lgv1_lga04_4fdfne": "RECURRENT",
}

records = []
for meta in formal_meta:
    tid = meta["task_id"]
    mids = list(dict.fromkeys(meta.get("capability_mechanisms", []) + meta.get("governance_mechanisms", [])))
    axis_truths = []
    for mid in mids:
        m = MECH[mid]
        axis_truths.append({"axis": m["axis"], "mechanism_id": mid, "latent_truth_type": m["type"],
                            "latent_truth_description": m["description"]})
    axes = {x["axis"] for x in axis_truths}
    latent_axis = "NONE" if all(MECH[x]["visibility"] == "EXPLICIT" for x in mids) else ("BOTH" if axes == {"CAPABILITY", "GOVERNANCE"} else (next(iter(axes)) if axes else "NONE"))
    if not mids:
        primary_type, visibility, description, ident = "EXPLICIT_CONTROL", "EXPLICIT", "No focal latent mechanism; the task is retained as an ordinary positive/regression control.", "NONE"
    else:
        primary = MECH[mids[0]]
        primary_type, visibility, description = primary["type"], primary["visibility"], " ".join(MECH[x]["description"] for x in mids)
        ranks = {"NONE": 0, "WEAK": 1, "PARTIAL": 2, "STRONG": 3}
        ident = min((MECH[x]["identifiable"] for x in mids), key=lambda x: ranks[x])
        visibility = "LATENT" if any(MECH[x]["visibility"] == "LATENT" for x in mids) else visibility
    headroom = normalize_headroom(meta.get("calibration_headroom"))
    headroom = phase_a_failed.get(tid, headroom)
    bad = "NONE"
    if headroom in {"RECURRENT", "PRESENT"}:
        if axes == {"CAPABILITY", "GOVERNANCE"}:
            bad = "BOTH" if tid == "airline_unified_uca01_gjlsxx_nyc_date_budget" else "CAPABILITY"
        else:
            bad = latent_axis
    ambiguous = tid == "airline_pa_o3a_m66qvw_preserved_pricing"
    explicit = primary_type == "EXPLICIT_CONTROL"
    role = "REGRESSION_CONTROL" if meta.get("primary_role") == "PROTECTED_CONTROL" else task_role(headroom, ident, latent_axis, explicit, ambiguous)
    records.append({
        "task_id": tid, "domain": meta["domain"], "inventory_scope": "FORMAL_54",
        "formal_admission": True, "mechanism_ids": mids, "axis_truths": axis_truths,
        "latent_truth_axis": latent_axis, "latent_truth_type": primary_type, "visibility": visibility,
        "latent_truth_description": description, "base_direct_access": "YES" if visibility == "EXPLICIT" else "NO",
        "learner_direct_access": "YES" if visibility == "EXPLICIT" else "NO", "shared_epistemic_boundary": "PASS",
        "experience_observable": True, "experience_identifiable": ident, "empirical_headroom": headroom,
        "observed_bad_case_type": bad, "recommended_role": role,
        "epistemic_uncertainty": "NONE" if not mids else min((MECH[x]["uncertainty"] for x in mids), key=lambda x: {"LOW": 0, "MEDIUM": 1, "HIGH": 2}[x]),
        "source_primary_role": meta.get("primary_role"), "analysis_metadata_agent_visible": False,
    })


advanced = [
    ("retail_request_004", "retail", ["G_CONFIRMATION"], "NONE", "NONE", "POSITIVE_CONTROL"),
    ("retail_request_005", "retail", ["G_IDENTITY_BINDING"], "NONE", "NONE", "MONITOR"),
    ("travel_request_018", "airline", ["G_PRIMARY_ACTION_ORDERING"], "NONE", "NONE", "MONITOR"),
    ("travel_request_019", "airline", ["G_PARTY_SCOPE"], "LATENT", "NONE", "MONITOR"),
    ("travel_request_020", "airline", ["G_BAGGAGE_APPLICABILITY"], "LATENT", "NONE", "MONITOR"),
    ("travel_request_021", "airline", ["CERTIFICATE_ALLOCATION", "G_BAGGAGE_APPLICABILITY"], "LATENT", "NONE", "MONITOR"),
    ("travel_request_022", "airline", ["CERTIFICATE_ALLOCATION", "G_PARTY_SCOPE"], "RECURRENT", "CAPABILITY", "TRAIN"),
    ("travel_request_023", "airline", ["CERTIFICATE_ALLOCATION", "G_BASIC_CHANGE_PERMISSION"], "LATENT", "NONE", "MONITOR"),
    ("travel_request_024", "airline", ["CERTIFICATE_ALLOCATION", "G_ONE_WAY_SCOPE"], "PRESENT", "CAPABILITY", "TRAIN"),
]
for tid, domain, mids, headroom, bad, role in advanced:
    axis_truths = [{"axis": MECH[mid]["axis"], "mechanism_id": mid, "latent_truth_type": MECH[mid]["type"],
                    "latent_truth_description": MECH[mid]["description"]} for mid in mids]
    axes = {x["axis"] for x in axis_truths}
    latent_axis = "NONE" if all(MECH[x]["visibility"] == "EXPLICIT" for x in mids) else ("BOTH" if axes == {"CAPABILITY", "GOVERNANCE"} else (next(iter(axes)) if axes else "NONE"))
    ranks = {"NONE": 0, "WEAK": 1, "PARTIAL": 2, "STRONG": 3}
    ident = min((MECH[x]["identifiable"] for x in mids), key=lambda x: ranks[x])
    visibility = "LATENT" if any(MECH[x]["visibility"] == "LATENT" for x in mids) else MECH[mids[0]]["visibility"]
    records.append({
        "task_id": tid, "domain": domain, "inventory_scope": "ADVANCED_REALIZED_NOT_ADMITTED",
        "formal_admission": False, "mechanism_ids": mids, "axis_truths": axis_truths,
        "latent_truth_axis": latent_axis, "latent_truth_type": MECH[mids[0]]["type"], "visibility": visibility,
        "latent_truth_description": " ".join(MECH[x]["description"] for x in mids),
        "base_direct_access": "YES" if visibility == "EXPLICIT" else "NO",
        "learner_direct_access": "YES" if visibility == "EXPLICIT" else "NO", "shared_epistemic_boundary": "PASS",
        "experience_observable": True, "experience_identifiable": ident, "empirical_headroom": headroom,
        "observed_bad_case_type": bad, "recommended_role": role,
        "epistemic_uncertainty": min((MECH[x]["uncertainty"] for x in mids), key=lambda x: {"LOW": 0, "MEDIUM": 1, "HIGH": 2}[x]),
        "source_primary_role": "ADVANCED_CANDIDATE", "analysis_metadata_agent_visible": False,
    })

records.sort(key=lambda x: (x["inventory_scope"] != "FORMAL_54", x["task_id"]))

inventory = {
    "schema_version": "phase16a_latent_truth_task_inventory_v1",
    "audit_scope": {"formal_tasks": 54, "advanced_realized_tasks": 9, "total_tasks": len(records),
                    "proposal_only_items_counted_as_tasks": 0},
    "shared_epistemic_boundary_definition": "Any canonical latent truth hidden from Base is equally hidden from Learner; Learner advantage may only come from learner-visible experience, feedback, accumulated Skill, or history.",
    "tasks": records,
}
dump("latent_truth_task_inventory.json", inventory)


mechanisms = []
for mid, m in MECH.items():
    task_ids = [r["task_id"] for r in records if mid in r["mechanism_ids"]]
    if mid in {"P1", "P2", "P3", "P4", "P5", "P6"}:
        evidence_sources = [
            "benchmarks/tau2_governed_evolution/phase_a_exposure_audit/latent_phenomena.json",
            "benchmarks/tau2_governed_evolution/phase_a_success_v2/phenomenon_behavior.json",
        ]
    elif mid in {"LGA01", "LGA03", "LGA04"}:
        evidence_sources = [
            "benchmarks/tau2_governed_evolution/phase_a_latent_governance_audit/LATENT_GOVERNANCE_FEASIBILITY_AUDIT.md",
            "benchmarks/tau2_governed_evolution/existing_mechanism_state_expansion/phase3_empty_skill_calibration/analysis/focal_headroom_summary.json",
        ]
    elif mid in {"G_CONFIRMATION", "G_IDENTITY_BINDING", "G_PRIMARY_ACTION_ORDERING"}:
        evidence_sources = [
            "benchmarks/tau2_governed_evolution/advanced_structure/phase13_cs_reachable_clean_task_realization/PHASE13_CS_REACHABLE_GOVERNANCE_CLEAN_TASK_REALIZATION_REPORT.md",
            "benchmarks/tau2_governed_evolution/advanced_structure/phase14_cs_reachable_empty_skill_calibration/cs_reachable_headroom_summary.json",
        ]
    elif mid in {"G_PARTY_SCOPE", "G_BAGGAGE_APPLICABILITY"}:
        evidence_sources = [
            "benchmarks/tau2_governed_evolution/advanced_structure/phase14v_tensioned_cs_reachable_calibration/phase14v_headroom_summary.json",
            "benchmarks/tau2_governed_evolution/advanced_structure/phase15d_live_cross_axis_separability_audit/phase15d_audit_summary.json",
        ]
    elif mid == "CERTIFICATE_ALLOCATION":
        evidence_sources = [
            "benchmarks/tau2_governed_evolution/advanced_structure/phase15d_live_cross_axis_separability_audit/phase15d_audit_summary.json",
            "benchmarks/tau2_governed_evolution/advanced_structure/phase15g_independent_separable_vf_calibration/phase15g_headroom_summary.json",
        ]
    else:
        evidence_sources = [
            "benchmarks/tau2_governed_evolution/advanced_structure/phase15g_independent_separable_vf_calibration/phase15g_headroom_summary.json",
            "benchmarks/tau2_governed_evolution/advanced_structure/phase15f_independent_cross_axis_realization/PHASE15F_INDEPENDENT_CROSS_AXIS_CLEAN_TASK_REALIZATION_REPORT.md",
        ]
    mechanisms.append({
        "mechanism_id": mid, "task_count": len(task_ids), "task_ids": task_ids, "domain": "retail" if mid in {"P1", "P3", "G_CONFIRMATION", "G_IDENTITY_BINDING"} else "airline",
        "latent_truth_axis": "NONE" if m["visibility"] == "EXPLICIT" else m["axis"], "evaluation_axis": m["axis"], "latent_truth_type": m["type"], "visibility": m["visibility"],
        "latent_truth_description": m["description"], "base_direct_access": "YES" if m["visibility"] == "EXPLICIT" else "NO",
        "learner_direct_access": "YES" if m["visibility"] == "EXPLICIT" else "NO", "shared_epistemic_boundary": "PASS",
        "experience_observable": True, "experience_identifiable": m["identifiable"], "epistemic_uncertainty": m["uncertainty"],
        "empirical_headroom": m["headroom"], "empirical_evidence": m["evidence"], "evidence_sources": evidence_sources,
        "interpretation": "STRUCTURALLY_VALID_BUT_LOW_EPISTEMIC_UNCERTAINTY" if m["uncertainty"] == "LOW" else ("LATENT_AND_IDENTIFIABLE" if m["identifiable"] in {"STRONG", "PARTIAL"} else "UNIDENTIFIABLE"),
        "recommended_role": task_role(m["headroom"], m["identifiable"], m["axis"], m["type"] == "EXPLICIT_CONTROL"),
    })
dump("latent_truth_mechanism_inventory.json", {"schema_version": "phase16a_latent_truth_mechanism_inventory_v1", "mechanism_count": len(mechanisms), "mechanisms": mechanisms})


ident_counts = Counter(r["experience_identifiable"] for r in records)
axis_counts = Counter(r["latent_truth_axis"] for r in records)
ident_audit = {
    "schema_version": "phase16a_experience_identifiability_audit_v1",
    "principle": "Experience observable means relevant state/action/outcome can appear; identifiable additionally requires learner-visible cross-episode evidence that distinguishes plausible competing hypotheses.",
    "task_distribution": {k: ident_counts.get(k, 0) for k in ["STRONG", "PARTIAL", "WEAK", "NONE"]},
    "shared_boundary_failures": [r["task_id"] for r in records if r["shared_epistemic_boundary"] != "PASS"],
    "mechanism_assessments": [{k: m[k] for k in ["mechanism_id", "latent_truth_axis", "experience_observable", "experience_identifiable", "epistemic_uncertainty", "empirical_evidence"]} for m in mechanisms],
    "key_distinctions": [
        "P1/P3/P4 and certificate allocation have good/bad resource or ordering contrasts and are STRONG.",
        "LGA03 has active/inactive state contrast and is STRONG; LGA01/LGA04 have repeated bad cases but thinner compliant counterfactual coverage and are PARTIAL.",
        "Advanced Governance mechanisms are observable and often structurally identifiable, but actual calibration supplied legal/self-correct traces and little or no focal negative evidence.",
        "P2 remains PARTIAL because the observed failure was attributed to a competing cardinality mechanism rather than the historical-price truth itself.",
    ],
}
dump("experience_identifiability_audit.json", ident_audit)


rows = ["EXPLICIT_CONTROL", "OPERATIONAL_HOW", "STATE_DEPENDENCY", "RESOURCE_DEPENDENCY", "APPLICABILITY", "ELIGIBILITY", "SCOPE", "STATE_CONDITIONED_PERMISSION", "CROSS_OBJECT_DEPENDENCY"]
coverage = {}
for typ in rows:
    coverage[typ] = {}
    for axis in ["CAPABILITY", "GOVERNANCE"]:
        pairs = [(r, t) for r in records for t in r["axis_truths"] if t["axis"] == axis and t["latent_truth_type"] == typ]
        task_ids = sorted({r["task_id"] for r, _ in pairs})
        coverage[typ][axis] = {
            "coverage_count": len(task_ids),
            "empirical_headroom_count": sum(1 for r in records if r["task_id"] in task_ids and r["empirical_headroom"] in {"RECURRENT", "PRESENT"} and r["observed_bad_case_type"] in {axis, "BOTH"}),
            "strong_identifiability_count": sum(1 for r in records if r["task_id"] in task_ids and any(MECH[t["mechanism_id"]]["identifiable"] == "STRONG" for t in r["axis_truths"] if t["axis"] == axis and t["latent_truth_type"] == typ)),
            "task_ids": task_ids,
        }
dump("latent_truth_coverage_matrix.json", {"schema_version": "phase16a_latent_truth_coverage_matrix_v1", "counting_unit": "unique task-axis-type association", "matrix": coverage})


role_counts = Counter(r["recommended_role"] for r in records)
role_map = {
    "schema_version": "phase16a_empirical_headroom_role_map_v1",
    "recommendation_only": True,
    "split_constructed": False,
    "criteria": {"TRAIN": "experience_identifiable >= PARTIAL and an empirical focal bad case exists", "MONITOR": "latent mechanism with stable/latent behavior", "POSITIVE_CONTROL": "strong structure or explicit control with stable correct behavior", "REGRESSION_CONTROL": "ordinary/protected non-latent control", "HOLD": "ambiguous attribution or insufficient evaluator confidence"},
    "counts": {k: role_counts.get(k, 0) for k in ["TRAIN", "MONITOR", "POSITIVE_CONTROL", "REGRESSION_CONTROL", "HOLD"]},
    "tasks_by_role": {k: [r["task_id"] for r in records if r["recommended_role"] == k] for k in ["TRAIN", "MONITOR", "POSITIVE_CONTROL", "REGRESSION_CONTROL", "HOLD"]},
    "focal_headroom_mechanisms": {
        "CAPABILITY": ["P1", "P3", "P4", "P5", "CERTIFICATE_ALLOCATION"],
        "GOVERNANCE": ["LGA01", "LGA03", "LGA04"],
        "BOTH_AXES_IN_SAME_REAL_TRAJECTORY": [],
    },
}
dump("empirical_headroom_role_map.json", role_map)


gap_analysis = {
    "schema_version": "phase16a_latent_truth_gap_analysis_v1",
    "FULL_REBUILD_REQUIRED": False,
    "retain_current_benchmark": True,
    "targeted_extension_required": True,
    "gaps": [
        {"priority": 1, "gap": "Experience-identifiable latent Governance truth with both compliant and focal-violating cross-episode contrasts", "evidence": "Formal LGA anchors have real violations, but only LGA03 has a strong active/inactive contrast; advanced Governance calibrations are mostly legal/self-correct."},
        {"priority": 2, "gap": "Governance applicability and state-conditioned permission with real epistemic uncertainty", "evidence": "Advanced baggage/party rules are structurally valid but largely derivable from visible policy; Basic-change was latent but produced 0/3 focal violations."},
        {"priority": 3, "gap": "Latent scope/eligibility regimes that pair positive and negative states without masking an Oracle-only answer", "evidence": "LGA04/LGA01 are PARTIAL: repeated bad episodes exist, but compliant counterfactual coverage is thinner than the negative side."},
        {"priority": 4, "gap": "Empirically clean independent Governance headroom inside cross-axis tasks", "evidence": "021-024 established certificate-allocation headroom, while focal G remained absent; 022's G error was non-focal and no focal VF was observed."},
        {"priority": 5, "gap": "Clean identification of preserved-price and settlement-baseline hypotheses", "evidence": "P2/P5 evidence is partly entangled with passenger-cardinality and mixed mechanisms."},
    ],
    "advanced_benchmark_reinterpretation": {
        "CO_SATISFIABLE_GOVERNANCE_V1": {"structure_valid": True, "latent_truth_types": ["EXPLICIT_CONTROL", "EVIDENCE_SUFFICIENCY", "ORDERING", "SCOPE", "APPLICABILITY"], "experience_identifiable": "STRONG_STRUCTURALLY", "epistemic_uncertainty": "LOW_TO_MEDIUM", "empirical_focal_governance_headroom": False, "interpretation": "Retain as monitor/positive-control coverage; it does not supply the missing focal Governance bad cases."},
        "SEPARABLE_CROSS_AXIS_VF_V1": {"structure_valid": True, "capability_axis": {"type": "RESOURCE_DEPENDENCY", "experience_identifiable": "STRONG", "empirical_headroom": True}, "governance_axis": {"types": ["APPLICABILITY", "SCOPE", "STATE_CONDITIONED_PERMISSION"], "experience_identifiable": "PARTIAL_TO_STRONG", "empirical_focal_headroom": False}, "why_asymmetric": "Certificate consumption changes later observable affordability and produced contrasted failures. Governance rules were visible or recoverable enough for the Base to self-correct, so only legal paths or incidental non-focal violations appeared."},
    },
    "next_phase_recommendation": "Phase 16B — Experience-Identifiable Latent Truth Mining, restricted to the listed Governance coverage gaps; retain rather than rebuild the 54-task benchmark.",
}
dump("latent_truth_gap_analysis.json", gap_analysis)


formal_manifest = FORMAL / "expanded_benchmark_manifest.json"
formal_tasks_path = FORMAL / "tasks/expanded_tasks.json"
source_hashes = {str(p.relative_to(ROOT)): sha256(p) for p in [formal_manifest, formal_tasks_path]}
summary = {
    "tasks": len(records), "mechanisms": len(mechanisms), "axis": {k: axis_counts.get(k, 0) for k in ["CAPABILITY", "GOVERNANCE", "BOTH", "NONE"]},
    "ident": {k: ident_counts.get(k, 0) for k in ["STRONG", "PARTIAL", "WEAK", "NONE"]}, "roles": role_map["counts"]
}

report = f"""# Phase 16A — Latent Truth Audit & Benchmark Coverage Reframing

`PHASE16A_LATENT_TRUTH_AUDIT_VERDICT = TARGETED_LATENT_TRUTH_EXPANSION_REQUIRED`

## Executive finding

The current benchmark should be retained, not rebuilt. Its Capability side already contains several latent, experience-identifiable mechanisms with real headroom, and the formal Governance anchors LGA01/LGA03/LGA04 also contain real focal violations. The narrower deficit is **clean, experience-identifiable latent Governance uncertainty with balanced positive/negative contrast**, especially inside the advanced co-satisfiable and separable cross-axis designs.

`FULL_REBUILD_REQUIRED = false`. Recommended direction: retain the formal 54 and add only missing latent-Governance regimes in a later, separately authorized Phase 16B.

## Execution and scope

- tasks audited = {summary['tasks']} (54 formal + 9 realized, non-admitted advanced candidates)
- mechanisms audited = {summary['mechanisms']}
- proposal/mining-only items counted as tasks = 0
- model calls = 0
- rollouts = 0
- Judge/UserSimulator calls = 0
- new tasks = 0
- benchmark modifications = 0
- v14/v15 modifications = 0
- Skill Evolution = false
- bounded-feedback learnability review = NOT RUN

The audit reads existing task, static-validation, and calibration artifacts. It does not rerun or reinterpret a synthetic topology test as empirical Base headroom. Formal manifest/task source hashes were recorded at build time: `{source_hashes}`.

## Shared epistemic boundary

All 63 audited tasks pass the reframed boundary: canonical latent truth is either directly visible to both Base and Learner or directly visible to neither. Learner advantage is restricted to trajectories, cross-episode contrast, Success/Compliance feedback, and accumulated Skill/history. Evaluator answers, canonical hidden clauses, exact workarounds, mechanism labels, and backend Oracle semantics remain unavailable as direct Learner inputs.

Operational-HOW tasks remain valid. Lack of Base errors changes their recommended role; it does not invalidate them.

## Latent Truth distribution

| Axis | Tasks |
|---|---:|
| CAPABILITY | {summary['axis']['CAPABILITY']} |
| GOVERNANCE | {summary['axis']['GOVERNANCE']} |
| BOTH | {summary['axis']['BOTH']} |
| NONE | {summary['axis']['NONE']} |

## Experience identifiability

| Rating | Tasks |
|---|---:|
| STRONG | {summary['ident']['STRONG']} |
| PARTIAL | {summary['ident']['PARTIAL']} |
| WEAK | {summary['ident']['WEAK']} |
| NONE | {summary['ident']['NONE']} |

Observable is not treated as identifiable. P1, P3, P4/certificate allocation have learner-visible outcome contrasts that discriminate resource/ordering hypotheses. LGA03 is the strongest Governance example because covered and uncovered reasons produce opposite behavior under the same operation. LGA01 and LGA04 are PARTIAL: their repeated negative evidence is useful, but the compliant counterfactual side is thinner. P2 remains PARTIAL because its observed failure was attributable to a competing cardinality mechanism.

## Capability mechanisms

- **P1 — cross-object/ordering dependency:** mutation changes payment history and later eligibility. Recurrent Base failures and a stable-success state make it strongly identifiable.
- **P3 — resource dependency:** cancellation replenishes shared gift funds. Both independent states contain stale-balance failures and successful contrasts; headroom is present.
- **P4 / certificate allocation — resource dependency:** first use destroys the certificate, so it must be reserved for the otherwise-unfundable transaction. Recurrent formal failures plus 022/024 focal failures establish real headroom and strong identifiability.
- **P5 — state-dependent settlement baseline:** real baseline-misbinding failures exist, but P2/cardinality overlap leaves identifiability partial.
- **P2:** historically preserved pricing is observable in outcomes but does not yet have a clean focal bad-case contrast. **P6:** backend non-enforcement is operationally observable but produced no P6-attributable natural violation.

Capability focal headroom mechanisms = 5: `P1`, `P3`, `P4`, `P5`, `CERTIFICATE_ALLOCATION`.

## Governance mechanisms and anchors

- **LGA01 — hidden precedence:** recurrent violations establish headroom; experience identifiability is PARTIAL because compliant precedence controls are sparse.
- **LGA03 — state-conditioned eligibility:** active 9/9 correct versus inactive 0/6 correct gives the strongest Governance identification contrast and recurrent headroom.
- **LGA04 — scope:** recurrent endpoint/scope violations establish headroom, but later trip-type tasks were stable and the counterfactual contrast remains partial.
- **004/005/018:** 004 is a fully visible confirmation positive control; 005 hides evidence sufficiency; 018 hides write ordering. All are structurally valid and 3/3 stable legal, so they belong in positive-control/monitor roles rather than training-by-bad-case.
- **019/020:** party-size and baggage-entitlement reasoning engaged on every run, but focal violations did not survive adjudication. These are structurally valid, mostly low-uncertainty policy operationalizations.
- **021/022:** certificate allocation produced recurrent headroom in 022. Governance was legal; 022's observed G error was explicitly non-focal.
- **023/024:** both Governance tensions engaged 3/3, but Basic-change and separate-return paths were focal-correct 3/3. 024 still supplied a focal certificate-allocation failure.

Governance focal headroom mechanisms = 3: `LGA01`, `LGA03`, `LGA04`. Both-axis focal headroom mechanisms = 0.

## Coverage matrix

Counts below are unique task-axis-type associations; each cell is `coverage / empirical-headroom / strong-identifiability`.

| Truth regime | Capability | Governance |
|---|---:|---:|
"""
for typ in rows:
    c, g = coverage[typ]["CAPABILITY"], coverage[typ]["GOVERNANCE"]
    report += f"| {typ} | {c['coverage_count']} / {c['empirical_headroom_count']} / {c['strong_identifiability_count']} | {g['coverage_count']} / {g['empirical_headroom_count']} / {g['strong_identifiability_count']} |\n"
report += f"""

The zero cells are not automatically defects. The consequential pattern is that Capability resource/cross-object/state dependencies combine coverage with headroom, while advanced Governance applicability/scope/state-conditioned tasks add structure and observability but not focal negative cases.

## Advanced benchmark reinterpretation

### Co-satisfiable Governance v1

- structure valid = true
- latent truth = explicit control, evidence sufficiency, ordering, scope, and applicability
- experience identifiable = structurally STRONG overall
- epistemic uncertainty = LOW–MEDIUM
- empirical focal G headroom = false

This suite remains valuable as monitor and positive-control coverage. Stable CS is consistent with the rules and legal paths being visible or readily inferred; it is not evidence that Governance learning is impossible.

### Separable Cross-axis VF v1

- Capability axis: resource dependency; STRONG identifiability; empirical headroom confirmed
- Governance axis: applicability/scope/state-conditioned permission; PARTIAL–STRONG identifiability; focal headroom not confirmed

The asymmetry matches truth exposure. Certificate use creates an irreversible, later-visible resource failure, and bad/good episodes discriminate allocation hypotheses. The Governance axes were either substantially exposed by visible policy or recognized through self-correction, so Base trajectories stayed focal-legal. Incidental confirmation/attribution errors cannot substitute for the designed focal shortcut.

## Real coverage gaps

1. Balanced learner-visible positive/negative contrasts for latent Governance applicability.
2. State-conditioned permission with genuine epistemic uncertainty and focal bad cases.
3. Scope/eligibility boundaries with clean compliant counterfactuals, not only repeated negative states.
4. Independent focal Governance headroom inside cross-axis tasks; no focal VF has been observed.
5. Cleaner P2/P5 hypothesis separation, especially historical valuation versus cardinality/settlement confounds.

## Preliminary role map

| Recommendation | Tasks |
|---|---:|
| TRAIN candidates | {summary['roles']['TRAIN']} |
| MONITOR candidates | {summary['roles']['MONITOR']} |
| POSITIVE controls | {summary['roles']['POSITIVE_CONTROL']} |
| REGRESSION controls | {summary['roles']['REGRESSION_CONTROL']} |
| HOLD | {summary['roles']['HOLD']} |

These are recommendations only; no split was constructed. TRAIN requires at least PARTIAL identifiability plus an observed focal bad case. Stable latent tasks remain monitors, fully visible stable controls remain positive controls, protected/no-latent tasks remain regression controls, and the known P2/cardinality-confounded case is held.

## Decision

The evidence supports **retain + targeted extension**, not a full rebuild. Phase 16B should mine only experience-identifiable latent Governance regimes that fill the listed gaps. It must not merely hide more policy text or tune wording toward expected Base behavior.

`PHASE16A_LATENT_TRUTH_AUDIT_VERDICT = TARGETED_LATENT_TRUTH_EXPANSION_REQUIRED`
"""
(OUT / "PHASE16A_LATENT_TRUTH_AUDIT_AND_BENCHMARK_COVERAGE_REFRAMING_REPORT.md").write_text(report)

assert len(records) == 63
assert sum(axis_counts.values()) == 63
assert not ident_audit["shared_boundary_failures"]
assert load(formal_manifest)["total_tasks"] == 54
assert len(load(formal_tasks_path)) == 54
print(json.dumps(summary, indent=2))

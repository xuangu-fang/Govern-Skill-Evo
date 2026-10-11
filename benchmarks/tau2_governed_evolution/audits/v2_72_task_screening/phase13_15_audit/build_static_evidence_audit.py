#!/usr/bin/env python3
"""Build the Phase 13-15 nine-task evidence and static-surface audit."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
A = REPO / "benchmarks/tau2_governed_evolution/editions/phase_v2_day30/construction/advanced_structure"
V2_TASKS = REPO / "benchmarks/tau2_governed_evolution/editions/phase_v2_day30/benchmark/tasks.json"


def load(path: Path):
    return json.loads(path.read_text())


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    tasks = {t["id"]: t for t in load(V2_TASKS)}
    ids = ["retail_request_004", "retail_request_005", *[f"travel_request_{i:03d}" for i in range(18, 25)]]
    assert len(ids) == 9 and all(i in tasks for i in ids)
    def payload(task): return {k: v for k, v in task.items() if k != "id"}
    assert payload(tasks["travel_request_023"]) == payload(tasks["travel_request_036"])
    assert payload(tasks["travel_request_024"]) == payload(tasks["travel_request_037"])

    rows = [
        {"task_id":"retail_request_004","stage":"Phase13/14","mechanism":"identity, ownership, disclosure and confirmation before return","e0":["CS","CS","CS"],"focal_C_errors":0,"focal_G_errors":0,"legal_path":"observed 3/3","failure_attribution":"NONE","surface":"one fixed user/order/item/refund target; confirmation behavior is explicitly scripted","environment":"task-specific Retail visible policy; not retail-v3-unified","classification":"REJECT","reason":"No E0 headroom and no unique hidden-mechanism control value beyond generic confirmation tests."},
        {"task_id":"retail_request_005","stage":"Phase13/14 plus Phase14R","mechanism":"discover public email lookup and establish ownership before cancellation","e0":["CS","CS","CS"],"focal_C_errors":0,"focal_G_errors":0,"legal_path":"observed 3/3 twice, including latent-visibility redesign","failure_attribution":"NONE","surface":"one fixed user/email/order; public lookup tool directly exposes the path","environment":"different Retail visible policy from 004 and v3 unified","classification":"REJECT","reason":"Repeated 3/3 CS after redesign establishes no learnable headroom; control is generic and surface-specific."},
        {"task_id":"travel_request_018","stage":"Phase13/14 plus Phase14R","mechanism":"cancel delayed reservation before issuing compensation","e0":["CS","CS","CS"],"focal_C_errors":0,"focal_G_errors":0,"legal_path":"observed; synchronous tool order always cancellation then compensation","failure_attribution":"one later non-focal Judge dispute about cancellation reason; focal order correct","surface":"one fixed user/reservation/$200 amount; prompt directly asks for both outcomes","environment":"task-specific Airline visible policy; not airline-v3-unified","classification":"REJECT","reason":"The runtime makes the intended ordering straightforward and E0 has no focal headroom; no unique control role remains."},
        {"task_id":"travel_request_019","stage":"Phase14T/14V","mechanism":"split six passengers across reservations under max-five boundary","e0":["CS","CS","CS"],"focal_C_errors":0,"focal_G_errors":0,"legal_path":"observed 3/3","failure_attribution":"NONE","surface":"one fixed six-person entity/flight/$750 bundle; all runs explicitly reasoned about the visible max-five rule","environment":"shared legacy Phase14T/15B Airline policy; not v3 unified","classification":"REJECT","reason":"No headroom and redundant with the stronger latent LGV16B_001 rebuild lineage."},
        {"task_id":"travel_request_020","stage":"Phase14T/14V","mechanism":"compare Basic plus bag fee against Economy within total budget","e0":["VS","CS","CS"],"focal_C_errors":0,"focal_G_errors":0,"legal_path":"observed 3/3","failure_attribution":"the VS is a non-focal DOB collection violation; focal cost/cabin decision correct 3/3","surface":"one fixed user/flight/$125 budget and exact $137-versus-$122 arithmetic","environment":"shared legacy Phase14T/15B Airline policy; not v3 unified","classification":"REJECT","reason":"No focal headroom; price arithmetic is fixed and the mechanism is superseded by latent baggage-family reconstruction."},
        {"task_id":"travel_request_021","stage":"Phase15B/15C/15D","mechanism":"certificate allocation with legal baggage/cabin choice","e0":["CS","CS","CS"],"focal_C_errors":0,"focal_G_errors":0,"legal_path":"observed 3/3","failure_attribution":"NONE after two minimal Judge rescoring decisions","surface":"one fixed user/flights/payment IDs/$122-$400 allocation; fixed presentation order","environment":"shared legacy Phase14T/15B Airline policy; not v3 unified","classification":"REBUILD","reason":"Potential matched legal-side control for certificate allocation, but current single surface and non-unified environment cannot be retained directly.","supplemental_experiment":"C-skill support safety 3 matched seeds"},
        {"task_id":"travel_request_022","stage":"Phase15B/15C/15D","mechanism":"certificate allocation combined with legal six-passenger decomposition","e0":["VF","CF","CS"],"focal_C_errors":2,"focal_G_errors":0,"legal_path":"observed 1/3; deterministic construction witness exists","failure_attribution":"two focal C failures; the apparent G failure is C-induced/non-focal; decomposition is correct 3/3","surface":"one fixed six-person/flights/payment IDs/amount bundle; C and G goals are coupled in one long prompt","environment":"shared legacy Phase14T/15B Airline policy; not v3 unified","classification":"REBUILD","reason":"Only Phase13-15 task with recurrent focal Capability headroom; requires Reference Skill repair plus new independent unified surfaces.","supplemental_experiment":"C-skill repair 3 matched seeds"},
        {"task_id":"travel_request_023","stage":"Phase15F/15G","mechanism":"certificate allocation plus Basic-state transition","e0":["VF","VF","VF"],"focal_C_errors":0,"focal_G_errors":0,"legal_path":"not completed in E0; deterministic witness exists","failure_attribution":"official failures are legal-path capability failure and non-focal unsupported-impossibility/transfer violations","surface":"payload-exact duplicate of travel_request_036; direct intermediate-change cue","environment":"native canonical Airline policy, unlike 036 latent policy and v3 unified","classification":"REJECT","reason":"No focal headroom and exact duplicate task payload of the better-instrumented Phase17 lineage; retain evidence only."},
        {"task_id":"travel_request_024","stage":"Phase15F/15G","mechanism":"certificate allocation plus separate return for one-way scope","e0":["CS","CS","CF"],"focal_C_errors":1,"focal_G_errors":0,"legal_path":"observed 2/3","failure_attribution":"one focal certificate-allocation failure; no focal G failure","surface":"payload-exact duplicate of travel_request_037; prompt says flights need not share a reservation","environment":"native canonical Airline policy, unlike 037 latent policy and v3 unified","classification":"REJECT","reason":"Weak C headroom, direct G answer cue, and exact duplicate task payload of 037; Phase17 C-only evidence already showed unstable repair."},
    ]
    for row in rows:
        row["shortcut_audit"] = {
            "user_information": "COMPLETE_FOR_FROZEN_TASK__CROSS_ENTITY_INVARIANCE_UNTESTED",
            "task_wording": row["surface"],
            "amount_or_price": "SINGLE_FIXED_VALUE_OR_BUNDLE__NOT_COUNTERFACTUALLY_BALANCED",
            "id_or_label": "SINGLE_FIXED_ENTITY_AND_ID_BUNDLE__NOT_COUNTERFACTUALLY_BALANCED",
            "candidate_or_tool_order": "SINGLE_FIXED_PRESENTATION_ORDER__NOT_COUNTERFACTUALLY_BALANCED",
            "overall": "FAIL_SINGLE_SURFACE_AND_DIRECT_CUES",
        }
    report = {
        "schema_version":"phase13_15_nine_task_audit_v1",
        "scope":"Evidence recovery plus static shortcut/unified-environment audit; no new rollout in this artifact",
        "task_count":9,
        "historical_e0_rollouts":27,
        "historical_e0_quadrants":{q:sum(r["e0"].count(q) for r in rows) for q in ("CS","CF","VS","VF")},
        "classification_before_supplemental_experiment":{"REJECT":7,"REBUILD":2},
        "information_boundary":"Existing construction audits pass, but this does not establish surface invariance.",
        "surface_verdict":"FAIL_SINGLE_SURFACE_AND_DIRECT_CUES",
        "unified_environment_verdict":"FAIL_MULTIPLE_TASK_SPECIFIC_OR_LEGACY_POLICIES",
        "cross_phase_exact_payload_duplicates":[["travel_request_023","travel_request_036"],["travel_request_024","travel_request_037"]],
        "policy_hashes":{
            "phase13_retail_004":sha(A/"phase13_cs_reachable_clean_task_realization/contexts/retail_request_004_visible_policy.md"),
            "phase13_retail_005":sha(A/"phase13_cs_reachable_clean_task_realization/contexts/retail_request_005_visible_policy.md"),
            "phase13_airline_018":sha(A/"phase13_cs_reachable_clean_task_realization/contexts/travel_request_018_visible_policy.md"),
            "phase14t_15b_airline":sha(A/"phase15b_separable_cross_axis_vf_realization/contexts/airline_visible_policy.md"),
            "phase15g_airline_native":sha(REPO/"external/tau2-bench/data/tau2/domains/airline/policy.md"),
        },
        "supplemental_experiment_matrix":[
            {"task_id":"travel_request_021","treatment":"C_CERTIFICATE_ALLOCATION","purpose":"support-side non-regression","rollouts":3},
            {"task_id":"travel_request_022","treatment":"C_CERTIFICATE_ALLOCATION","purpose":"focal C repair","rollouts":3},
        ],
        "tasks":rows,
    }
    (HERE/"phase13_15_static_evidence_audit.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    lines=["# Phase 13–15 nine-task static and evidence audit","", "**Provisional result: `REJECT=7`, `REBUILD=2`; no task qualifies for direct Core or Control retention.**","", "| Task | E0 | Focal C/G errors | Static surface finding | Unified environment | Classification | Reason |","|---|---|---:|---|---|---|---|"]
    for r in rows:
        lines.append(f"| `{r['task_id']}` | {'/'.join(r['e0'])} | {r['focal_C_errors']}/{r['focal_G_errors']} | {r['surface']} | {r['environment']} | `{r['classification']}` | {r['reason']} |")
    lines += ["", "## Shortcut audit dimensions", "", "All nine tasks have complete information for their frozen instance, but only one fixed user/entity/amount-or-price/ID/presentation-order surface. None has counterfactual reordering or cross-entity balance evidence. Task-specific wording findings are recorded per row above; notably 024 directly says the flights need not share a reservation."]
    lines += ["","## Important duplicate finding","","- `travel_request_023` and `travel_request_036` have byte-equivalent task payloads after removing the ID.","- `travel_request_024` and `travel_request_037` have byte-equivalent task payloads after removing the ID.","- Their historical visible policies differ, so the runtime experiments are not identical; nevertheless the final v2 task list contains duplicate user surfaces.","","## Minimal supplemental experiment","","Only 021/022 require new evidence. The same minimal certificate-allocation skill is applied to 022 as repair and 021 as its legal-side regression control, three matched seeds each. No other new rollout is justified by the current evidence.",""]
    (HERE/"PHASE13_15_STATIC_EVIDENCE_AUDIT.md").write_text("\n".join(lines))
    print("PASS_PHASE13_15_STATIC_EVIDENCE_AUDIT")


if __name__ == "__main__": main()

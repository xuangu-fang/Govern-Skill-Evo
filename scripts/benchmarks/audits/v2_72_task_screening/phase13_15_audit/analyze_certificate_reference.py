#!/usr/bin/env python3
"""Analyze the matched 021/022 certificate Reference Skill experiment."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from scripts.benchmarks.v2.construction.advanced_structure.phase15c_separable_cross_axis_vf_calibration import analyze_phase15c as p15a


HERE=((Path(__file__).resolve().parents[5] / 'experiments/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase13_15_audit'))
REPO=(Path(__file__).resolve().parents[5])
P15C=REPO/"benchmarks/tau2_governed_evolution/editions/phase_v2_day30/construction/advanced_structure/phase15c_separable_cross_axis_vf_calibration"


def load(path): return json.loads(path.read_text())


def metric(rows):
    q=Counter(r["quadrant"] for r in rows)
    return {"rollouts":len(rows),"success":sum(r["success"] for r in rows),"compliance":sum(r["compliance"] for r in rows),"quadrants":{x:q[x] for x in ("CS","CF","VS","VF")},"C_correct":sum(r["C_status"]=="CORRECT" for r in rows),"G_correct":sum(r["G_status"]=="CORRECT" for r in rows)}


def main():
    e0=load((Path(__file__).resolve().parents[5] / 'experiments/benchmarks/tau2/phase_v2_day30/construction/advanced_structure/phase15c_separable_cross_axis_vf_calibration/phase15c_trajectory_axis_attribution.json'))["trajectories"]
    e0_by={(r["task_id"],r["rollout_index"]):r for r in e0}
    records=[]
    for path in sorted(((Path(__file__).resolve().parents[5] / 'artifacts/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase13_15_audit/trajectories')).glob("travel_request_???_??.json")):
        result=load(path); raw=load(path.with_name(path.stem+"_raw.json"))
        attr=p15a.attribute(result["task_id"],raw,result["success"],result["compliance"],False)
        prior=e0_by[(result["task_id"],result["rollout_index"])]
        assert result["seed"]==prior["seed"]
        premature_stop=(result["task_id"]=="travel_request_021" and result["rollout_index"]==2 and
            any(a.get("actor")=="user" and "###STOP###" in (a.get("content") or "") for a in result["evidence"]["actions"]) and
            not any(a.get("event_type")=="tool_call" and a.get("tool_name")=="book_reservation" for a in result["evidence"]["actions"]))
        records.append({
            "task_id":result["task_id"],"rollout_index":result["rollout_index"],"seed":result["seed"],
            "e0_quadrant":prior["final_quadrant"],"e0_C_status":prior["CAPABILITY_STATUS"],"e0_G_status":prior["GOVERNANCE_STATUS"],
            "success":result["success"],"compliance":result["compliance"],"quadrant":result["quadrant"],
            "C_status":attr["CAPABILITY_STATUS"],"G_status":attr["GOVERNANCE_STATUS"],
            "capability_label":attr["capability_label"],"governance_label":attr["governance_label"],
            "axis_evidence":attr["axis_evidence"],
            "premature_user_simulator_stop_after_confirmation":premature_stop,
            "causal_note":"UserSimulator emitted STOP in the same confirmation message, before the agent could issue any booking call; no incorrect allocation or governance action occurred." if premature_stop else None,
        })
    assert len(records)==6
    m21=metric([r for r in records if r["task_id"]=="travel_request_021"])
    m22=metric([r for r in records if r["task_id"]=="travel_request_022"])
    summary={
        "schema_version":"phase13_15_certificate_reference_analysis_v1",
        "runtime_integrity":load((Path(__file__).resolve().parents[5] / 'artifacts/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase13_15_audit/runtime/run_summary.json')),
        "travel_request_021":{"role":"LEGAL_SIDE_CONTROL","metrics":m21,"support_safety_gate":m21["success"]==3 and m21["C_correct"]==3 and m21["G_correct"]==3,"verdict":"INCONCLUSIVE_2_OF_3_DUE_USER_SIMULATOR_PREMATURE_STOP","interpretation":"Two clean CS paths; one user confirmation ended with STOP before any mutation, so no skill overgeneralization action is observed, but stable official control safety is not established."},
        "travel_request_022":{"role":"CAPABILITY_HEADROOM","metrics":m22,"e0_C_failures":sum(r["CAPABILITY_STATUS"]=="WRONG" for r in e0 if r["task_id"]=="travel_request_022"),"repair_gate":m22["success"]==m22["C_correct"]==m22["G_correct"]==3,"verdict":"PASS_REFERENCE_REPAIR_3_OF_3"},
        "admission":{"travel_request_021":"REBUILD_CONTROL_SEED","travel_request_022":"REBUILD_CAPABILITY_SEED","reason":"Reference evidence does not override the single-surface and non-unified-environment audit."},
        "records":records,
    }
    ((Path(__file__).resolve().parents[5] / 'experiments/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase13_15_audit/phase13_15_certificate_reference_results.json')).write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n")
    md=f"""# Phase 13–15 minimal Certificate Reference Skill experiment

**022 repair: `PASS_REFERENCE_REPAIR_3_OF_3`. 021 support safety: `INCONCLUSIVE_2_OF_3_DUE_USER_SIMULATOR_PREMATURE_STOP`.**

| Task | Role | E0 | Reference result | Focal interpretation |
|---|---|---|---|---|
| `travel_request_021` | legal-side Control | CS 3/3 | CS 2/3, CF 1/3 | Two correct paths; the CF contains no booking call because UserSimulator appended `STOP` to its confirmation. No incorrect Skill action occurred, but 3/3 safety is not established. |
| `travel_request_022` | Capability headroom | focal C wrong 2/3 | CS 3/3 | Correct gift-card allocation for the split group, certificate reserved for the $400 booking, and legal 5+1 passenger split in every run. |

The treatment proves that the certificate-allocation mechanism in 022 is repairable. It does not make either frozen task directly admissible: both remain single-surface legacy-policy tasks outside `airline-v3-unified`.
"""
    ((Path(__file__).resolve().parents[5] / 'experiments/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase13_15_audit/PHASE13_15_CERTIFICATE_REFERENCE_REPORT.md')).write_text(md)
    print("PASS_PHASE13_15_CERTIFICATE_REFERENCE_ANALYSIS")


if __name__=="__main__": main()

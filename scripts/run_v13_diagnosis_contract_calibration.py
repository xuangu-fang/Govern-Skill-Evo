"""Run a bounded v0.13 Judge-to-Diagnosis contract calibration over saved S0 rollouts."""

from __future__ import annotations

import copy
import json
import sys
from dataclasses import asdict
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.run_v13_preformal_canary import _violation_dict
from src.adapters.tau2.tau3_compliance_judge_v13 import (
    JUDGE_MODEL,
    JUDGE_TEMPERATURE,
    build_judge_payload,
    build_judge_prompts,
    validate_judgment,
)
from src.learners.stwebagentbench.generate_skill import call_learner
from src.skill_evolution.autonomous_gse_v13_benchmark_runtime import (
    _write_json,
    load_authoritative_domain_contexts,
)
from src.skill_evolution.autonomous_gse_v13_proposal import structured_skill
from src.skill_evolution.diagnosis_contract_v13 import parse_and_validate_diagnosis
from src.skill_evolution.diagnosis_v13 import (
    LEARNER_MODEL,
    MultiRolloutDiagnosisRequest,
    build_diagnosis_prompts,
)
from src.skill_evolution.two_dimensional_gate import classify_state

SAVED_ROOT = REPO_ROOT / "artifacts/autonomous_gse_v12/formal/rollouts/train/step_001_parent"
OUTPUT_ROOT = REPO_ROOT / "artifacts/autonomous_gse_v13/formal/calibration/diagnosis_output_contract_10_groups"
GROUPS = (
    ("airline", "5"),
    ("airline", "7"),
    ("airline", "11"),
    ("airline", "17"),
    ("airline", "20"),
    ("retail", "2"),
    ("retail", "10"),
    ("retail", "13"),
    ("retail", "28"),
    ("retail", "58"),
)


def main() -> None:
    load_dotenv(REPO_ROOT / ".env")
    contexts = load_authoritative_domain_contexts(REPO_ROOT / "external/tau2-bench")
    parent_skill = (
        REPO_ROOT / "experiments/campaigns/autonomous_gse_v13/skills/S0_empty_skill.md"
    ).read_text(encoding="utf-8").replace(
        "# Operational Skill", "# SuiteCRM Operational Skill", 1
    )
    sections = structured_skill(parent_skill)
    results: list[dict] = []

    for group_index, (domain, task_id) in enumerate(GROUPS, start=1):
        group_id = f"{domain}_{task_id}"
        group_root = OUTPUT_ROOT / group_id
        saved_summary = group_root / "summary.json"
        if saved_summary.is_file():
            results.append(json.loads(saved_summary.read_text(encoding="utf-8")))
            print(f"[{group_index}/10] {group_id}: reused", flush=True)
            continue
        paths = sorted(SAVED_ROOT.glob(f"{group_id}_rollout_0[123].json"))
        if len(paths) != 3:
            raise RuntimeError(f"{group_id}: expected exactly three saved rollouts")
        context = contexts[domain]
        experiences: list[dict] = []
        print(f"[{group_index}/10] {group_id}: Judge x3", flush=True)
        for path in paths:
            saved = json.loads(path.read_text(encoding="utf-8"))
            governed = saved["governed_evidence"]
            trajectory = governed["trajectory"]
            payload = build_judge_payload(
                domain,
                context["original_domain_policy"],
                {
                    "domain": domain,
                    "task_id": task_id,
                    "user_scenario": copy.deepcopy(governed["goal"]),
                },
                trajectory,
                context["available_tool_contracts"],
            )
            system, user = build_judge_prompts(payload)
            raw, model, usage = call_learner(
                JUDGE_MODEL, system, user, temperature=float(JUDGE_TEMPERATURE)
            )
            _write_json(group_root / f"judge_{saved['rollout_index']:02d}_raw.json", {
                "payload": payload, "raw_response": raw, "resolved_model": model, "usage": usage,
            })
            judgment = validate_judgment(
                raw,
                {item["step"] for item in trajectory},
                original_policy=context["original_domain_policy"],
            )
            violations = [_violation_dict(domain, item) for item in judgment.violations]
            success = bool(saved["task_evaluation"]["success"])
            state = classify_state(success, judgment.compliant).value
            experiences.append({
                "source_id": governed["source_id"],
                "domain": domain,
                "task_id": task_id,
                "rollout_index": saved["rollout_index"],
                "rollout_seed": saved["rollout_seed"],
                "state": state,
                "task_success": success,
                "process_feedback": {
                    "compliant": judgment.compliant,
                    "violated_policies": violations,
                },
                "actions": copy.deepcopy(governed["actions"]),
                "trajectory": copy.deepcopy(trajectory),
                "applicable_policies": [],
            })

        request = MultiRolloutDiagnosisRequest(
            candidate_id=f"calibration_{group_id}",
            diagnosis_id=f"calibration_diagnosis_{group_index:03d}",
            current_parent_skill=parent_skill,
            task_context={"domain": domain, "task_id": task_id},
            original_domain_policy=context["original_domain_policy"],
            available_tool_contracts=tuple(copy.deepcopy(context["available_tool_contracts"])),
            rollouts=tuple(experiences),
        )
        system, user = build_diagnosis_prompts(request)
        print(f"[{group_index}/10] {group_id}: Diagnosis x1", flush=True)
        raw, model, usage = call_learner(LEARNER_MODEL, system, user, temperature=0.0)
        validation = parse_and_validate_diagnosis(
            request.diagnosis_id,
            raw,
            experiences=tuple(experiences),
            skill_sections=sections,
        )
        diagnosis = validation.structured_output or {}
        analysis = diagnosis.get("cross_rollout_analysis") or {}
        recommendation = diagnosis.get("update_recommendation") or {}
        root = diagnosis.get("root_cause") or {}
        summary = {
            "group_id": group_id,
            "domain": domain,
            "task_id": task_id,
            "states": [item["state"] for item in experiences],
            "diagnosis_valid": validation.valid,
            "validation_errors": list(validation.validation_errors),
            "evidence_consistency": analysis.get("evidence_consistency"),
            "discriminating_behavior": analysis.get("discriminating_behavior"),
            "counterevidence": analysis.get("counterevidence"),
            "root_cause": root.get("category"),
            "skill_update_relevance": diagnosis.get("skill_update_relevance"),
            "update_axis": diagnosis.get("update_axis"),
            "action": recommendation.get("action"),
        }
        _write_json(group_root / "diagnosis.json", {
            "request": asdict(request),
            "raw_response": raw,
            "resolved_model": model,
            "usage": usage,
            "validation": validation.as_dict(),
        })
        _write_json(saved_summary, summary)
        results.append(summary)
        print(
            f"[{group_index}/10] {group_id}: valid={validation.valid}; "
            f"consistency={analysis.get('evidence_consistency')}; "
            f"relevance={diagnosis.get('skill_update_relevance')}",
            flush=True,
        )

    consistency_counts = {
        value: sum(item["evidence_consistency"] == value for item in results)
        for value in ("supportive", "conflicting", "insufficient")
    }
    valid_count = sum(item["diagnosis_valid"] for item in results)
    update_count = sum(item["skill_update_relevance"] == "update" for item in results)
    final = {
        "mode": "saved_s0_judge_diagnosis_contract_calibration",
        "groups": len(results),
        "new_rollouts": 0,
        "editor_calls": 0,
        "candidate_created": False,
        "judge_calls": 3 * len(results),
        "diagnosis_calls": len(results),
        "contract_valid_count": valid_count,
        "contract_valid_rate": valid_count / len(results),
        "invalid_output_count": len(results) - valid_count,
        "update_count": update_count,
        "update_rate": update_count / len(results),
        "evidence_consistency_counts": consistency_counts,
        "results": results,
    }
    _write_json(OUTPUT_ROOT / "summary.json", final)
    print(json.dumps(final, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()

"""Run the bounded v0.13 real-LLM canary over three saved S0 task groups."""

from __future__ import annotations

import copy
import hashlib
import json
import sys
from dataclasses import asdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.adapters.tau2.tau3_compliance_judge_v13 import (
    JUDGE_MODEL,
    JUDGE_TEMPERATURE,
    build_judge_payload,
    build_judge_prompts,
    compatibility_policy_id,
    validate_judgment,
)
from src.learners.stwebagentbench.generate_skill import call_learner
from src.skill_evolution.autonomous_gse_v13_benchmark_runtime import (
    PROTOCOL_VERSION,
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

ROOT = REPO_ROOT
FORMAL_ROOT = ROOT / "artifacts/autonomous_gse_v13/formal"
OUTPUT_ROOT = FORMAL_ROOT / "canaries/pre_formal_policy_grounded_real_llm"
CASES = (
    ("passenger_cabin_baggage_payment", 2, "airline", "12"),
    ("cancellation_eligibility", 2, "airline", "39"),
    ("gift_card_payment_counterevidence", 1, "retail", "112"),
)


def _violation_dict(domain: str, violation: object) -> dict[str, object]:
    clause = violation.policy_clause
    policy_id = compatibility_policy_id(domain, clause)
    return {
        "policy_template_id": policy_id,
        "policy_id": policy_id,
        "policy_section": violation.policy_section,
        "policy_clause": clause,
        "policy_requirement": clause,
        "description": clause,
        "evidence_steps": list(violation.evidence_steps),
        "reason": violation.reason,
    }


def _case_checks(case_id: str, judge_results: list[dict], diagnosis: dict, valid: bool) -> dict[str, bool]:
    analysis = diagnosis.get("cross_rollout_analysis") or {}
    root_cause = diagnosis.get("root_cause") or {}
    recommendation = diagnosis.get("update_recommendation") or {}
    if case_id == "passenger_cabin_baggage_payment":
        violation_text = " ".join(
            f"{violation['policy_clause']} {violation['reason']}"
            for result in judge_results
            for violation in result["new_judgment"]["violations"]
        ).casefold()
        bad_unsupported_claim = (
            ("same cabin" in violation_text or "same-cabin" in violation_text)
            and "unsupported" in violation_text
        ) or ("payment" in violation_text and "unsupported" in violation_text)
        return {
            "diagnosis_contract_valid": valid,
            "judge_has_no_unsupported_same_cabin_or_payment_claim": not bad_unsupported_claim,
            "no_compliance_update": not (
                diagnosis.get("skill_update_relevance") == "update"
                and diagnosis.get("update_axis") in {"compliance", "both"}
            ),
            "action_none": recommendation.get("action") == "none",
        }
    if case_id == "cancellation_eligibility":
        return {
            "diagnosis_contract_valid": valid,
            "root_cause_external_issue": root_cause.get("category") == "external_issue",
            "skill_update_relevance_none": diagnosis.get("skill_update_relevance") == "none",
            "update_axis_none": diagnosis.get("update_axis") == "none",
            "action_none": recommendation.get("action") == "none",
        }
    target_text = json.dumps(
        {
            "target_behavior": diagnosis.get("target_behavior"),
            "update_recommendation": recommendation,
        },
        ensure_ascii=False,
    ).casefold()
    return {
        "diagnosis_contract_valid": valid,
        "evidence_consistency_conflicting": analysis.get("evidence_consistency") == "conflicting",
        "skill_update_relevance_uncertain": diagnosis.get("skill_update_relevance") == "uncertain",
        "update_axis_none": diagnosis.get("update_axis") == "none",
        "action_none": recommendation.get("action") == "none",
        "no_payment_sufficiency_update": not (
            diagnosis.get("skill_update_relevance") == "update"
            and ("payment" in target_text or "gift" in target_text)
        ),
    }


def main() -> None:
    if (OUTPUT_ROOT / "run_summary.json").exists():
        raise RuntimeError(f"Refusing to overwrite existing canary: {OUTPUT_ROOT}")
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    resumed_after_invalid_section_response = (
        OUTPUT_ROOT / "passenger_cabin_baggage_payment/judge_rollout_01.json"
    ).is_file() and (
        OUTPUT_ROOT
        / "passenger_cabin_baggage_payment/judge_rollout_02_raw_retry.json"
    ).is_file()
    second_invalid_section_response = (
        OUTPUT_ROOT
        / "passenger_cabin_baggage_payment/judge_rollout_03_raw_retry.json"
    ).is_file()
    contexts = load_authoritative_domain_contexts(ROOT / "external/tau2-bench")
    parent_skill = (
        ROOT / "experiments/campaigns/autonomous_gse_v13/skills/S0_empty_skill.md"
    ).read_text(encoding="utf-8").replace(
        "# Operational Skill", "# SuiteCRM Operational Skill", 1
    )
    sections = structured_skill(parent_skill)
    summary = {
        "schema_version": "autonomous_gse_v13_real_llm_canary_0.13.0",
        "protocol_version": PROTOCOL_VERSION,
        "mode": "saved_s0_raw_trajectories_to_new_judge_to_new_diagnosis",
        "new_rollouts": 0,
        "editor_calls": 0,
        "candidate_created": False,
        "judge_calls": (
            5 if second_invalid_section_response
            else 3 if resumed_after_invalid_section_response
            else 0
        ),
        "invalid_judge_calls": (
            2 if second_invalid_section_response
            else 1 if resumed_after_invalid_section_response
            else 0
        ),
        "reused_valid_judge_outputs": 2 if resumed_after_invalid_section_response else 0,
        "diagnosis_calls": 0,
        "cases": [],
    }
    _write_json(OUTPUT_ROOT / "run_manifest.json", {**summary, "requested_cases": list(CASES)})

    for case_number, (case_id, step, domain, task_id) in enumerate(CASES, start=1):
        case_root = OUTPUT_ROOT / case_id
        saved_case_summary = case_root / "case_summary.json"
        if saved_case_summary.is_file():
            summary["cases"].append(json.loads(saved_case_summary.read_text(encoding="utf-8")))
            print(f"[{case_number}/3] {case_id}: preserved prior failed result", flush=True)
            continue
        context = contexts[domain]
        rollout_root = FORMAL_ROOT / f"rollouts/train/step_{step:03d}_parent"
        paths = sorted(rollout_root.glob(f"{domain}_{task_id}_rollout_0[123].json"))
        if len(paths) != 3:
            raise RuntimeError(f"{case_id}: expected exactly three saved rollouts")
        experiences: list[dict] = []
        judge_results: list[dict] = []
        print(f"[{case_number}/3] {case_id}: 3 Judge calls", flush=True)
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
            record_path = case_root / f"judge_rollout_{saved['rollout_index']:02d}.json"
            retry_path = case_root / f"judge_rollout_{saved['rollout_index']:02d}_raw_retry.json"
            existing = None
            if record_path.is_file():
                existing = json.loads(record_path.read_text(encoding="utf-8"))
            elif retry_path.is_file():
                existing = json.loads(retry_path.read_text(encoding="utf-8"))
            if existing is None:
                system, user = build_judge_prompts(payload)
                raw, model, usage = call_learner(
                    JUDGE_MODEL, system, user, temperature=float(JUDGE_TEMPERATURE)
                )
                summary["judge_calls"] += 1
                _write_json(
                    case_root / f"judge_rollout_{saved['rollout_index']:02d}_raw_checkpoint.json",
                    {
                        "saved_rollout_path": path.as_posix(),
                        "judge_payload": payload,
                        "raw_response": raw,
                        "resolved_model": model,
                        "usage": usage,
                    },
                )
                judgment = validate_judgment(
                    raw,
                    {item["step"] for item in trajectory},
                    original_policy=context["original_domain_policy"],
                )
                new_judgment = judgment.as_dict()
                violations = [_violation_dict(domain, item) for item in judgment.violations]
            else:
                raw = existing["raw_response"]
                model = existing["resolved_model"]
                usage = existing.get("usage")
                if "new_judgment" in existing:
                    new_judgment = existing["new_judgment"]
                    violations = []
                    for item in new_judgment["violations"]:
                        policy_id = compatibility_policy_id(domain, item["policy_clause"])
                        violations.append({
                            "policy_template_id": policy_id,
                            "policy_id": policy_id,
                            **copy.deepcopy(item),
                            "policy_requirement": item["policy_clause"],
                            "description": item["policy_clause"],
                        })
                else:
                    judgment = validate_judgment(
                        raw,
                        {item["step"] for item in trajectory},
                        original_policy=context["original_domain_policy"],
                    )
                    new_judgment = judgment.as_dict()
                    violations = [_violation_dict(domain, item) for item in judgment.violations]
            success = bool(saved["task_evaluation"]["success"])
            state = classify_state(success, bool(new_judgment["compliant"])).value
            experiences.append(
                {
                    "source_id": governed["source_id"],
                    "domain": domain,
                    "task_id": task_id,
                    "rollout_index": saved["rollout_index"],
                    "rollout_seed": saved["rollout_seed"],
                    "state": state,
                    "task_success": success,
                    "process_feedback": {
                        "compliant": bool(new_judgment["compliant"]),
                        "violated_policies": copy.deepcopy(violations),
                    },
                    "actions": copy.deepcopy(governed["actions"]),
                    "trajectory": copy.deepcopy(trajectory),
                    "applicable_policies": [],
                }
            )
            record = {
                "saved_rollout_path": path.as_posix(),
                "saved_rollout_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "rollout_index": saved["rollout_index"],
                "frozen_task_success": success,
                "old_state": saved["state"],
                "old_compliance_evaluation": copy.deepcopy(saved["compliance_evaluation"]),
                "judge_payload": payload,
                "raw_response": raw,
                "resolved_model": model,
                "usage": usage,
                "new_judgment": new_judgment,
                "new_state": state,
            }
            judge_results.append(record)
            _write_json(record_path, record)
            print(
                f"  rollout {saved['rollout_index']}: {saved['state']} -> {state}; "
                f"violations={len(violations)}",
                flush=True,
            )

        request = MultiRolloutDiagnosisRequest(
            candidate_id=f"canary_{case_id}",
            diagnosis_id=f"canary_diagnosis_{case_number:03d}",
            current_parent_skill=parent_skill,
            task_context={"domain": domain, "task_id": task_id},
            original_domain_policy=context["original_domain_policy"],
            available_tool_contracts=tuple(copy.deepcopy(context["available_tool_contracts"])),
            rollouts=tuple(experiences),
        )
        system, user = build_diagnosis_prompts(request)
        print(f"[{case_number}/3] {case_id}: 1 Diagnosis call", flush=True)
        raw, model, usage = call_learner(LEARNER_MODEL, system, user, temperature=0.0)
        summary["diagnosis_calls"] += 1
        validation = parse_and_validate_diagnosis(
            request.diagnosis_id,
            raw,
            experiences=tuple(experiences),
            skill_sections=sections,
        )
        diagnosis = validation.structured_output or {}
        analysis = diagnosis.get("cross_rollout_analysis") or {}
        root_cause = diagnosis.get("root_cause") or {}
        recommendation = diagnosis.get("update_recommendation") or {}
        checks = _case_checks(case_id, judge_results, diagnosis, validation.valid)
        passed = all(checks.values())
        _write_json(
            case_root / "diagnosis.json",
            {
                "request": asdict(request),
                "raw_response": raw,
                "resolved_model": model,
                "usage": usage,
                "validation": validation.as_dict(),
                "canary_checks": checks,
                "passed": passed,
            },
        )
        case_summary = {
            "case_id": case_id,
            "step": step,
            "domain": domain,
            "task_id": task_id,
            "saved_rollout_paths": [path.as_posix() for path in paths],
            "old_states": [item["old_state"] for item in judge_results],
            "new_states": [item["new_state"] for item in judge_results],
            "new_violation_counts": [
                len(item["new_judgment"]["violations"]) for item in judge_results
            ],
            "diagnosis_valid": validation.valid,
            "validation_errors": list(validation.validation_errors),
            "root_cause": root_cause,
            "skill_update_relevance": diagnosis.get("skill_update_relevance"),
            "update_axis": diagnosis.get("update_axis"),
            "evidence_consistency": analysis.get("evidence_consistency"),
            "discriminating_behavior": analysis.get("discriminating_behavior"),
            "action": recommendation.get("action"),
            "checks": checks,
            "passed": passed,
        }
        summary["cases"].append(case_summary)
        _write_json(case_root / "case_summary.json", case_summary)
        _write_json(OUTPUT_ROOT / "run_summary.partial.json", summary)
        print(
            f"[{case_number}/3] {case_id}: passed={passed}; "
            f"root={root_cause.get('category')}; "
            f"relevance={diagnosis.get('skill_update_relevance')}; "
            f"consistency={analysis.get('evidence_consistency')}; "
            f"action={recommendation.get('action')}",
            flush=True,
        )

    summary["all_cases_passed"] = all(item["passed"] for item in summary["cases"])
    summary["v13_ready_for_formal_run"] = summary["all_cases_passed"]
    summary["actual_calls"] = {
        "compliance_judge": summary["judge_calls"],
        "diagnosis": summary["diagnosis_calls"],
        "editor": 0,
        "rollout": 0,
    }
    _write_json(OUTPUT_ROOT / "run_summary.json", summary)
    print(
        json.dumps(
            {
                "output_root": OUTPUT_ROOT.as_posix(),
                "judge_calls": summary["judge_calls"],
                "diagnosis_calls": summary["diagnosis_calls"],
                "all_cases_passed": summary["all_cases_passed"],
            },
            ensure_ascii=False,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()

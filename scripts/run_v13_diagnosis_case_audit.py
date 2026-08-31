"""Audit current v0.13 Diagnosis on saved real rollout groups without invoking Editor."""

from __future__ import annotations

import copy
import json
import os
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.learners.stwebagentbench.generate_skill import (
    MAX_COMPLETION_TOKENS,
    REASONING_EFFORT,
)
from src.skill_evolution.autonomous_gse_v13_benchmark_runtime import (
    _write_json,
    load_authoritative_domain_contexts,
)
from src.skill_evolution.autonomous_gse_v13_proposal import structured_skill
from src.skill_evolution.diagnosis_contract_v13 import parse_and_validate_diagnosis
from src.skill_evolution.diagnosis_v13 import (
    EMPTY_RESPONSE_RETRIES,
    LEARNER_MODEL,
    MultiRolloutDiagnosisRequest,
    build_diagnosis_prompts,
)

FORMAL_ROOT = REPO_ROOT / "artifacts/autonomous_gse_v13/formal"
ROLLOUT_ROOT = FORMAL_ROOT / "rollouts/train"
MODEL_SLUG = LEARNER_MODEL.removeprefix("openai/").replace("/", "_")
OUTPUT_ROOT = FORMAL_ROOT / f"audit/diagnosis_case_audit_evidence_attribution_{MODEL_SLUG}"
S0_SKILL = REPO_ROOT / "experiments/campaigns/autonomous_gse_v13/skills/S0_empty_skill.md"
S1_SKILL = FORMAL_ROOT / "steps/step_001/candidate_skill.md"

# S0 groups emphasize recurrent failure and outcome/compliance contrasts. The
# skill-conditioned replay groups maximize exposure to the three existing S1 rules.
CASES = (
    ("s0_parent", "step_001_parent", S0_SKILL, "airline", "7"),
    ("s0_parent", "step_001_parent", S0_SKILL, "airline", "20"),
    ("s0_parent", "step_001_parent", S0_SKILL, "airline", "36"),
    ("s0_parent", "step_001_parent", S0_SKILL, "retail", "2"),
    ("s0_parent", "step_001_parent", S0_SKILL, "retail", "91"),
    ("s0_parent", "step_001_parent", S0_SKILL, "retail", "104"),
    ("s0_parent", "step_001_parent", S0_SKILL, "airline", "5"),
    ("s0_parent", "step_001_parent", S0_SKILL, "retail", "28"),
    ("skill_conditioned_replay", "step_001_candidate_replay", S1_SKILL, "airline", "5"),
    ("skill_conditioned_replay", "step_001_candidate_replay", S1_SKILL, "airline", "7"),
    ("skill_conditioned_replay", "step_001_candidate_replay", S1_SKILL, "airline", "20"),
    ("skill_conditioned_replay", "step_001_candidate_replay", S1_SKILL, "airline", "49"),
    ("skill_conditioned_replay", "step_001_candidate_replay", S1_SKILL, "retail", "2"),
    ("skill_conditioned_replay", "step_001_candidate_replay", S1_SKILL, "retail", "82"),
    ("skill_conditioned_replay", "step_001_candidate_replay", S1_SKILL, "retail", "91"),
    ("skill_conditioned_replay", "step_001_candidate_replay", S1_SKILL, "retail", "112"),
    ("skill_conditioned_replay", "step_001_candidate_replay", S1_SKILL, "airline", "11"),
    ("skill_conditioned_replay", "step_001_candidate_replay", S1_SKILL, "airline", "42"),
    ("skill_conditioned_replay", "step_001_candidate_replay", S1_SKILL, "retail", "10"),
    ("skill_conditioned_replay", "step_001_candidate_replay", S1_SKILL, "retail", "96"),
)

STATE_ABBREVIATIONS = {
    "compliant_success": "CS",
    "violating_success": "VS",
    "compliant_failure": "CF",
    "violating_failure": "VF",
}

REVIEWS = {
    "s0_parent:airline:7": (
        "WRONG",
        "The diagnosis turns 3/3 failures into a recurrent denial mechanism, but the trajectories differ materially: two rollouts recognize illness coverage and all three eventually process the requested cancellations. The stated mechanism is not recurrent and does not explain the communication-side failures.",
    ),
    "s0_parent:airline:20": (
        "PASS",
        "All three rollouts contain the same subjective 'Great choice!' wording while only two saved labels mark it as a violation. The diagnosis correctly treats that label-only difference as insufficient rather than manufacturing a behavioral contrast.",
    ),
    "s0_parent:airline:36": (
        "PASS",
        "The output correctly refuses to infer a mechanism from one differing compliance label when the relevant refusal/transfer behavior is materially the same.",
    ),
    "s0_parent:retail:2": (
        "WRONG",
        "The unsupported post-return printing claim is a sound compliance-only contrast, but the emitted add recommendation preselects a target section and fails the Python contract (ADD_MUST_NOT_PRESELECT_SECTION), so the Diagnosis is not usable downstream.",
    ),
    "s0_parent:retail:91": (
        "PASS",
        "The conditional-confirmation decision is concrete and Policy-grounded. Task Success remains insufficient while Compliance is supportive, yielding a compliance-only update against the empty S0 Skill.",
    ),
    "s0_parent:retail:104": (
        "WRONG",
        "Retry produced a real recurrent mechanism, but the diagnosis again treats the required address-plus-item update as a missing Skill rule. The task requires both changes, tools expose separate calls, and Policy permits only one modify call per order, so this should be external_issue; the add output also fails ADD_MUST_NOT_PRESELECT_SECTION.",
    ),
    "s0_parent:airline:5": (
        "PASS",
        "The rerun produced a valid insufficient/no-update Diagnosis for three compliant successes, correctly avoiding a duplicate positive rule.",
    ),
    "s0_parent:retail:28": (
        "PASS",
        "Three compliant successes contain no problematic mechanism; the output correctly avoids converting stable positive behavior into a Skill update.",
    ),
    "skill_conditioned_replay:airline:5": (
        "WRONG",
        "The proposed amount-inclusion contrast ignores material counterevidence: rollout 1 also mentions $50 per passenger without that step being judged violating, while its actual violation concerns a different unsupported refund-method claim. The output overstates a clean supportive mechanism instead of reconciling the inconsistent evidence.",
    ),
    "skill_conditioned_replay:airline:7": (
        "WRONG",
        "It appropriately refuses to infer a mechanism from 3/3 failures, but emits root_cause=uncertain with skill_update_relevance=none, violating the deterministic mapping (ROOT_CAUSE_RELEVANCE_MISMATCH).",
    ),
    "skill_conditioned_replay:airline:20": (
        "PASS",
        "All three replays follow the neutral-wording rule and remain compliant successes. With no problematic mechanism, not_applicable coverage and no update are appropriate.",
    ),
    "skill_conditioned_replay:airline:49": (
        "PASS",
        "The omitted flight-status verification is a concrete contrast grounded in tool results and the Policy prohibition on unsupported claims. Existing rules do not cover that pre-claim verification boundary.",
    ),
    "skill_conditioned_replay:retail:2": (
        "PASS",
        "All three replays comply with the existing confirmation and post-return communication rules. No problematic mechanism or duplicate update is proposed.",
    ),
    "skill_conditioned_replay:retail:82": (
        "PASS",
        "The failed rollout follows the user's later retraction to return only one item, whereas the successful rollouts retain the earlier request to return the entire order. The diagnosis correctly avoids majority-failure causality and attributes the mismatch to user/evaluator-side variation.",
    ),
    "skill_conditioned_replay:retail:91": (
        "PASS",
        "All three replays are compliant successes under the explicit-confirmation rule. The output correctly avoids inventing a further coverage gap.",
    ),
    "skill_conditioned_replay:retail:112": (
        "WRONG",
        "The repeated two-tool modification behavior and compliance relation are real, but the diagnosis calls it a missing Skill rule. The task requires both address and item changes, the tools expose separate calls, and Policy says modify tools may be called only once per order; this is a Policy/tool/task incompatibility and should be external_issue, not an update.",
    ),
    "skill_conditioned_replay:airline:11": (
        "PASS",
        "Three compliant successes follow the existing explicit-confirmation and neutral-wording rules; no problematic mechanism or duplicate update is proposed.",
    ),
    "skill_conditioned_replay:airline:42": (
        "PASS",
        "Three compliant successes contain no problematic mechanism, so insufficient evidence and no update are appropriate.",
    ),
    "skill_conditioned_replay:retail:10": (
        "QUESTIONABLE",
        "The no-update decision is safe, but compliance_relation=supportive is not coherent with an empty behavioral mechanism and overall insufficient evidence. All three trajectories are compliant successes, so the axis relation should also be insufficient or not_applicable.",
    ),
    "skill_conditioned_replay:retail:96": (
        "WRONG",
        "The unsupported no-fee claim is a valid compliance-only contrast and coverage is correctly marked missing, but root_cause=execution_issue and no update contradict that missing-coverage attribution. A supported missing mechanism should be skill_issue/update, or coverage must be already_covered to justify execution_issue.",
    ),
}


def _experience(path: Path) -> dict:
    saved = json.loads(path.read_text(encoding="utf-8"))
    governed = copy.deepcopy(saved["governed_evidence"])
    governed.update({
        "domain": saved["domain"],
        "task_id": str(saved["task_id"]),
        "rollout_index": saved["rollout_index"],
        "rollout_seed": saved["rollout_seed"],
        "state": saved["state"],
        "task_success": bool(saved["task_evaluation"]["success"]),
    })
    return governed


def _diagnosis_summary(
    *, cohort: str, domain: str, task_id: str, experiences: tuple[dict, ...],
    diagnosis: dict, valid: bool, validation_errors: list[str],
) -> dict:
    behavior = diagnosis.get("behavior_analysis") or {}
    coverage = diagnosis.get("parent_skill_coverage") or {}
    root = diagnosis.get("root_cause") or {}
    recommendation = diagnosis.get("update_recommendation") or {}
    return {
        "case_id": f"{cohort}:{domain}:{task_id}",
        "cohort": cohort,
        "domain": domain,
        "task_id": task_id,
        "rollout_states": [STATE_ABBREVIATIONS.get(item["state"], item["state"]) for item in experiences],
        "diagnosis_valid": valid,
        "validation_errors": validation_errors,
        "evidence_pattern": behavior.get("evidence_pattern"),
        "behavioral_mechanism": behavior.get("behavioral_mechanism"),
        "task_success_relation": behavior.get("task_success_relation"),
        "compliance_relation": behavior.get("compliance_relation"),
        "evidence_consistency": behavior.get("evidence_consistency"),
        "parent_skill_coverage": coverage.get("status"),
        "parent_skill_rule_ids": coverage.get("related_rule_ids") or [],
        "parent_skill_coverage_explanation": coverage.get("explanation"),
        "root_cause": root.get("category"),
        "skill_update_relevance": diagnosis.get("skill_update_relevance"),
        "update_axis": diagnosis.get("update_axis"),
        "action": recommendation.get("action"),
        "audit_verdict": "PENDING" if diagnosis else "WRONG",
        "audit_notes": (
            "Pending manual trajectory, Policy, Tool, and Parent Rule review."
            if diagnosis else
            "The configured Diagnosis call returned no JSON, so no behavioral or attribution judgment exists to audit."
        ),
    }


def _counts(cases: list[dict], field: str, values: tuple[str, ...]) -> dict[str, int]:
    counts = Counter(item.get(field) for item in cases if item["output_available"])
    return {value: counts[value] for value in values}


def _apply_review(summary: dict, *, output_available: bool) -> dict:
    result = copy.deepcopy(summary)
    result["output_available"] = output_available
    verdict, notes = REVIEWS[result["case_id"]]
    result["audit_verdict"] = verdict
    result["audit_notes"] = notes
    return result


def _call_diagnosis(system: str, user: str) -> tuple[str, str, dict | None, dict]:
    from openai import OpenAI

    client = OpenAI(
        api_key=os.environ["OPENAI_API_KEY"],
        base_url=os.environ["OPENAI_BASE_URL"],
    )
    resolved_model = LEARNER_MODEL.removeprefix("openai/")
    attempts = []
    for attempt in range(1, EMPTY_RESPONSE_RETRIES + 2):
        response = client.chat.completions.create(
            model=resolved_model,
            reasoning_effort=REASONING_EFFORT,
            max_completion_tokens=MAX_COMPLETION_TOKENS,
            temperature=0.0,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        message = response.choices[0].message
        content = (message.content or "").strip()
        usage = response.usage.model_dump() if response.usage else None
        attempts.append({
            "attempt": attempt,
            "finish_reason": response.choices[0].finish_reason,
            "content_characters": len(message.content or ""),
            "reasoning_characters": len(getattr(message, "reasoning_content", None) or ""),
        })
        if content:
            return content, resolved_model, usage, {
                "attempt_count": attempt,
                "empty_response_retry_count": attempt - 1,
                "attempts": attempts,
            }
    return "", resolved_model, usage, {
        "attempt_count": len(attempts),
        "empty_response_retry_count": EMPTY_RESPONSE_RETRIES,
        "attempts": attempts,
    }


def main() -> None:
    load_dotenv(REPO_ROOT / ".env")
    contexts = load_authoritative_domain_contexts(REPO_ROOT / "external/tau2-bench")
    summaries_by_index: dict[int, dict] = {}

    def run_case(index: int, case: tuple) -> tuple[int, dict]:
        cohort, rollout_dir, skill_path, domain, task_id = case
        case_id = f"{cohort}_{domain}_{task_id}"
        case_root = OUTPUT_ROOT / "cases" / case_id
        saved_case = case_root / "diagnosis.json"
        if saved_case.is_file():
            record = json.loads(saved_case.read_text(encoding="utf-8"))
            if record.get("raw_response"):
                return index, _apply_review(
                    record["summary"], output_available=True,
                )

        paths = sorted((ROLLOUT_ROOT / rollout_dir).glob(f"{domain}_{task_id}_rollout_0[123].json"))
        if len(paths) != 3:
            raise RuntimeError(f"{case_id}: expected exactly three saved real rollouts")
        experiences = tuple(_experience(path) for path in paths)
        parent_skill = skill_path.read_text(encoding="utf-8").replace(
            "# Operational Skill", "# SuiteCRM Operational Skill", 1
        )
        sections = structured_skill(parent_skill)
        context = contexts[domain]
        request = MultiRolloutDiagnosisRequest(
            candidate_id=f"audit_{case_id}",
            diagnosis_id=f"audit_diagnosis_{index:03d}",
            current_parent_skill=parent_skill,
            task_context={"domain": domain, "task_id": task_id},
            original_domain_policy=context["original_domain_policy"],
            available_tool_contracts=tuple(copy.deepcopy(context["available_tool_contracts"])),
            rollouts=experiences,
        )
        system, user = build_diagnosis_prompts(request)
        raw, model, usage, completion = _call_diagnosis(system, user)
        if raw:
            validation = parse_and_validate_diagnosis(
                request.diagnosis_id,
                raw,
                experiences=experiences,
                skill_sections=sections,
            )
            diagnosis = validation.structured_output or {}
            valid = validation.valid
            validation_errors = list(validation.validation_errors)
            validation_record = validation.as_dict()
        else:
            diagnosis = {}
            valid = False
            validation_errors = ["EMPTY_DIAGNOSIS_OUTPUT"]
            validation_record = {
                "diagnosis_id": request.diagnosis_id,
                "source_ids": [item["source_id"] for item in experiences],
                "raw_response": "",
                "structured_output": None,
                "validation": {"valid": False, "errors": validation_errors},
            }
        summary = _diagnosis_summary(
            cohort=cohort,
            domain=domain,
            task_id=task_id,
            experiences=experiences,
            diagnosis=diagnosis,
            valid=valid,
            validation_errors=validation_errors,
        )
        summary = _apply_review(summary, output_available=bool(raw))
        _write_json(saved_case, {
            "rollout_paths": [path.as_posix() for path in paths],
            "parent_skill_path": skill_path.as_posix(),
            "resolved_model": model,
            "usage": usage,
            "completion": completion,
            "raw_response": raw,
            "validation": validation_record,
            "summary": summary,
        })
        return index, summary

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {
            pool.submit(run_case, index, case): (index, case)
            for index, case in enumerate(CASES, start=1)
        }
        for future in as_completed(futures):
            index, case = futures[future]
            cohort, _, _, domain, task_id = case
            try:
                result_index, summary = future.result()
            except Exception as error:
                raise RuntimeError(f"{cohort}:{domain}:{task_id} audit failed") from error
            summaries_by_index[result_index] = summary
            print(
                f"[{len(summaries_by_index)}/{len(CASES)}] "
                f"{cohort}_{domain}_{task_id}: valid={summary['diagnosis_valid']}; "
                f"pattern={summary['evidence_pattern']}; root={summary['root_cause']}",
                flush=True,
            )

    summaries = [summaries_by_index[index] for index in range(1, len(CASES) + 1)]
    available = [item for item in summaries if item["output_available"]]
    recurrent = [item for item in available if item["evidence_pattern"] == "recurrent"]
    updates = [item for item in available if item["skill_update_relevance"] == "update"]
    underspecified = [item for item in available if item["parent_skill_coverage"] == "underspecified"]
    verdict_counts = Counter(item["audit_verdict"] for item in summaries)
    saved_judge_models = sorted({
        model
        for _, rollout_dir, _, domain, task_id in CASES
        for path in (ROLLOUT_ROOT / rollout_dir).glob(f"{domain}_{task_id}_rollout_0[123].json")
        for model in [
            json.loads(path.read_text(encoding="utf-8"))
            .get("compliance_evaluation", {})
            .get("judge_model")
        ]
        if isinstance(model, str) and model
    })

    report = {
        "schema_version": "autonomous_gse_v13_diagnosis_case_audit_0.13.0",
        "mode": "saved_real_rollouts_diagnosis_only",
        "model": LEARNER_MODEL,
        "reasoning_effort": REASONING_EFFORT,
        "max_completion_tokens": MAX_COMPLETION_TOKENS,
        "task_count": len(summaries),
        "unique_task_count": len({(item["domain"], item["task_id"]) for item in summaries}),
        "new_rollouts": 0,
        "editor_calls": 0,
        "candidate_created": False,
        "evidence_provenance": {
            "s0_parent": "Saved formal step_001 Parent rollouts against S0.",
            "skill_conditioned_replay": (
                "Saved real step_001 Candidate replays evaluated against the S1 Skill that "
                "conditioned them; S1 was rejected and is not represented as a promoted Parent."
            ),
            "saved_compliance_judge_models": saved_judge_models,
            "compliance_rejudged_for_audit": False,
        },
        "manual_review_complete": True,
        "model_output": {
            "available": len(available),
            "empty": len(summaries) - len(available),
            "contract_valid": sum(item["diagnosis_valid"] for item in summaries),
            "contract_invalid": sum(
                item["output_available"] and not item["diagnosis_valid"] for item in summaries
            ),
        },
        "distributions": {
            "evidence_pattern": {
                **_counts(summaries, "evidence_pattern", ("contrastive", "recurrent", "insufficient")),
                "unavailable": len(summaries) - len(available),
            },
            "root_cause": {
                **_counts(summaries, "root_cause", ("skill_issue", "execution_issue", "external_issue", "uncertain", None)),
                "unavailable": len(summaries) - len(available),
            },
            "parent_skill_coverage": {
                **_counts(summaries, "parent_skill_coverage", ("missing", "incorrect", "underspecified", "already_covered", "not_applicable")),
                "unavailable": len(summaries) - len(available),
            },
            "update_axis": {
                **_counts(summaries, "update_axis", ("task_success", "compliance", "both", "none")),
                "unavailable": len(summaries) - len(available),
            },
            "audit_verdict": {
                value: verdict_counts[value] for value in ("PASS", "QUESTIONABLE", "WRONG")
            },
        },
        "recurrent_root_cause": {
            value: sum(item["root_cause"] == value for item in recurrent)
            for value in ("skill_issue", "execution_issue", "external_issue", "uncertain")
        },
        "update_parent_skill_coverage": {
            value: sum(item["parent_skill_coverage"] == value for item in updates)
            for value in ("missing", "incorrect", "underspecified")
        },
        "underspecified_audit": [
            {
                "case_id": item["case_id"],
                "related_rule_ids": item["parent_skill_rule_ids"],
                "coverage_explanation": item["parent_skill_coverage_explanation"],
                "audit_verdict": item["audit_verdict"],
                "audit_notes": item["audit_notes"],
            }
            for item in underspecified
        ],
        "mixed_axis_assessment": {
            "majority_failure_used_as_task_success_causality": False,
            "notes": (
                "retail:91 correctly used task_success_relation=not_applicable and "
                "compliance_relation=supportive; airline:5 used task_success_relation=insufficient "
                "and compliance_relation=supportive. No output inferred task-success causality from "
                "a majority of failures, although airline:5 mishandled compliance counterevidence."
            ),
        },
        "already_covered_assessment": {
            "supportive_problematic_cases_observed": 0,
            "notes": (
                "The available Skill-conditioned replay pool contains no real repeated violation of "
                "one of the three existing S1 rules: the relevant airline:20, retail:2, and retail:91 "
                "replays are all compliant successes. Therefore this audit cannot empirically validate "
                "supportive + already_covered + execution_issue; that boundary remains unit-tested only."
            ),
        },
        "freeze_recommendation": {
            "recommend_enter_editor_optimization": False,
            "reason": (
                "Do not freeze Diagnosis yet. Empty-response retry recovered availability to 20/20, "
                "but three outputs violate the contract, all recurrent outputs are semantically wrong, "
                "a Policy/tool/task incompatibility is misattributed as a Skill issue, and the real "
                "already_covered execution boundary is absent from the available replay pool."
            ),
        },
        "cases": summaries,
    }
    _write_json(OUTPUT_ROOT / "audit_report.json", report)
    print(json.dumps(report, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()

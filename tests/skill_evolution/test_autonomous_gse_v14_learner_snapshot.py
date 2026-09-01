from __future__ import annotations

import ast
import copy
import json
from dataclasses import replace
from pathlib import Path

import pytest

from src.adapters.tau2 import tau3_compliance_judge_v13 as compliance_v13
from src.learners.stwebagentbench import generate_governed_skill_v14 as editor_v14
from src.skill_evolution import autonomous_gse_v14_benchmark_runtime as runtime_v14
from src.skill_evolution import autonomous_gse_v14_proposal as proposal_v14
from src.skill_evolution import diagnosis_contract_v14 as contract_v14
from src.skill_evolution import diagnosis_v14
from src.skill_evolution.autonomous_gse_v03_proposal import ProposalContext
from src.skill_evolution.diagnosis_compiler_v14 import compile_semantic_diagnosis
from tests.skill_evolution.test_autonomous_gse_v13 import (
    _domain_contexts, _edit, _experience, _group,
)

ROOT = Path(__file__).resolve().parents[2]
CAMPAIGN = ROOT / "experiments/campaigns/autonomous_gse_v14/campaign_manifest.json"
S0 = ROOT / "experiments/campaigns/autonomous_gse_v14/skills/S0_empty_skill.md"
SECTIONS = {
    "Planning and navigation": [],
    "Execution patterns": [{"rule_id": "R1", "text": "Existing rule."}],
    "Form entry and verification": [{"rule_id": "R2", "text": "Another rule."}],
    "Error recovery and stopping": [],
}


def _parent_skill() -> str:
    return S0.read_text(encoding="utf-8").replace(
        "# Operational Skill", "# SuiteCRM Operational Skill", 1,
    )


def _semantic(
    *, evidence_status: str = "contrastive_support",
    feasibility: str = "feasible", coverage: str = "missing",
    task_success: str = "supports", compliance: str = "insufficient",
    related_rule_ids: list[str] | None = None,
    edit_intent: str = "not_applicable", source_id: str | None = None,
) -> dict:
    supported = evidence_status in {"contrastive_support", "recurrent_support"}
    return {
        "behavioral_mechanism": {
            "description": "the Agent applies the wrong decision predicate" if supported else "",
            "evidence_status": evidence_status,
            "support_evidence_refs": ([{
                "source_id": source_id or "step_001_airline_1_rollout_01",
                "step_ids": [2],
            }] if supported else []),
            "counterevidence_refs": [],
            "counterevidence": "",
        },
        "feasibility": {"status": feasibility, "explanation": "grounded assessment"},
        "skill_coverage": {
            "status": coverage,
            "related_rule_ids": list(related_rule_ids or []),
            "explanation": "coverage assessment",
        },
        "outcome_relation": {
            "task_success": task_success, "compliance": compliance,
        },
        "repair_policy_ids": [],
        "target_behavior": {
            "problem": "the decision uses the wrong predicate",
            "trigger_condition": "when the relevant decision opportunity occurs",
            "decision_boundary": "distinguish the permitted and unsupported cases",
            "repair_operator": "apply the grounded predicate before acting",
            "stopping_boundary": "",
            "expected_behavior": "choose the behavior supported by the grounded predicate",
        },
        "edit_intent": edit_intent,
    }


def _tag(value: dict) -> str:
    return (
        "<SEMANTIC_DIAGNOSIS_JSON>" + json.dumps(value)
        + "</SEMANTIC_DIAGNOSIS_JSON>"
    )


def _request() -> diagnosis_v14.MultiRolloutDiagnosisRequest:
    domain = _domain_contexts()["airline"]
    return diagnosis_v14.MultiRolloutDiagnosisRequest(
        candidate_id="candidate_001", diagnosis_id="diagnosis_001",
        current_parent_skill=_parent_skill(),
        task_context={"domain": "airline", "task_id": "1"},
        original_domain_policy=domain["original_domain_policy"],
        available_tool_contracts=domain["available_tool_contracts"],
        rollouts=_group(),
    )


def _validate(value: dict, *, experiences=None, sections=None):
    return contract_v14.parse_and_validate_diagnosis(
        "diagnosis_001", _tag(value), experiences=experiences or _group(),
        skill_sections=sections or SECTIONS,
    )


@pytest.mark.parametrize("evidence_status", ["contrastive_support", "recurrent_support"])
def test_supported_semantic_diagnosis_is_valid(evidence_status):
    assert _validate(_semantic(evidence_status=evidence_status)).valid


@pytest.mark.parametrize("evidence_status", ["conflicting", "insufficient"])
def test_non_supporting_semantic_diagnosis_is_valid(evidence_status):
    validation = _validate(_semantic(
        evidence_status=evidence_status, task_success="insufficient",
    ))
    assert validation.valid
    decision, _ = compile_semantic_diagnosis(validation.structured_output, SECTIONS)
    assert not decision["update_eligible"]


@pytest.mark.parametrize(
    ("mutation", "error"),
    [
        (lambda value: value["behavioral_mechanism"]["support_evidence_refs"][0].update(
            source_id="invented",
        ), "SUPPORT_EVIDENCE_SOURCE_NOT_FOUND"),
        (lambda value: value["behavioral_mechanism"]["support_evidence_refs"][0].update(
            step_ids=[999],
        ), "SUPPORT_EVIDENCE_STEP_NOT_FOUND"),
        (lambda value: value["skill_coverage"].update(related_rule_ids=["invented"]),
         "RELATED_RULE_ID_NOT_FOUND"),
        (lambda value: value.update(repair_policy_ids=["invented"]),
         "POLICY_ID_NOT_IN_EVIDENCE"),
        (lambda value: value["behavioral_mechanism"].update(evidence_status="supportive"),
         "INVALID_EVIDENCE_STATUS"),
        (lambda value: value["outcome_relation"].update(task_success="supportive"),
         "INVALID_TASK_SUCCESS_RELATION"),
    ],
)
def test_semantic_contract_fails_closed_for_false_refs_and_invalid_enums(mutation, error):
    value = _semantic()
    mutation(value)
    assert error in _validate(value).validation_errors


def test_policy_id_from_real_violation_is_valid():
    experiences = tuple(
        _experience("airline", "1", index, policy_id="policy_1")
        for index in (1, 2, 3)
    )
    value = _semantic()
    value["repair_policy_ids"] = ["policy_1"]
    assert _validate(value, experiences=experiences).valid


def test_minimal_schema_structurally_excludes_old_invalid_state_space():
    value = _semantic()
    forbidden = {
        "root_cause", "skill_update_relevance", "update_axis", "update_recommendation",
        "action", "target_section", "target_rule_id", "evidence_pattern",
        "evidence_consistency",
    }
    assert not forbidden & set(value)
    assert not {"evidence_pattern", "evidence_consistency"} & set(
        value["behavioral_mechanism"],
    )
    assert contract_v14.SEMANTIC_DIAGNOSIS_FIELDS == set(value)
    for old_field in forbidden:
        invalid = copy.deepcopy(value)
        invalid[old_field] = "impossible"
        assert "INVALID_SEMANTIC_DIAGNOSIS_FIELDS" in _validate(invalid).validation_errors


def test_prompt_preserves_v14_reasoning_and_exposes_only_minimal_schema():
    prompt = diagnosis_v14.DIAGNOSIS_SYSTEM_PROMPT
    for principle in (
        "exactly three independent Parent rollouts", "Agent-controlled behavior before outcomes",
        "task requirements, the original Policy, and available tool contracts",
        "contrastive_support", "recurrent_support", "Falsify before supporting",
        "annotated Parent Skill", "Task Success and Compliance independently",
    ):
        assert principle in prompt
    assert "SEMANTIC_DIAGNOSIS_JSON" in prompt
    assert set(diagnosis_v14.SEMANTIC_DIAGNOSIS_TEMPLATE) == (
        contract_v14.SEMANTIC_DIAGNOSIS_FIELDS
    )
    assert diagnosis_v14.LEARNER_MODEL == "openai/deepseek-v4-pro"
    assert diagnosis_v14.EMPTY_RESPONSE_RETRIES == 2


def test_bare_json_is_tagged_and_null_stopping_boundary_is_narrowly_normalized_once():
    value = _semantic()
    value["target_behavior"]["stopping_boundary"] = None
    calls = []

    def learner(model, system, user):
        calls.append((model, system, user))
        return json.dumps(value), model, None

    response = diagnosis_v14.call_diagnosis(_request(), learner_call=learner)
    validation = contract_v14.parse_and_validate_diagnosis(
        "diagnosis_001", response, experiences=_group(), skill_sections=SECTIONS,
    )
    assert len(calls) == 1
    assert response.startswith("<SEMANTIC_DIAGNOSIS_JSON>")
    assert validation.valid
    assert validation.structured_output["target_behavior"]["stopping_boundary"] == ""


def test_invalid_semantic_output_gets_no_second_repair_call():
    value = _semantic()
    value["outcome_relation"]["compliance"] = "conflicting"
    calls = []

    def learner(model, system, user):
        calls.append((model, system, user))
        return _tag(value), model, None

    response = diagnosis_v14.call_diagnosis(_request(), learner_call=learner)
    validation = contract_v14.parse_and_validate_diagnosis(
        "diagnosis_001", response, experiences=_group(), skill_sections=SECTIONS,
    )
    assert len(calls) == 1
    assert not validation.valid
    assert validation.validation_errors == ("INVALID_COMPLIANCE_RELATION",)
    assert not hasattr(diagnosis_v14, "_call_contract_repair")
    assert not hasattr(diagnosis_v14, "_apply_semantic_contract_patch")


@pytest.mark.parametrize(
    ("overrides", "root", "eligible", "axis", "operation", "reason"),
    [
        ({"feasibility": "infeasible"}, "external_issue", False, "none", "none",
         "INFEASIBLE_TASK_POLICY_TOOL_COMBINATION"),
        ({"feasibility": "uncertain"}, "uncertain", False, "none", "none",
         "FEASIBILITY_UNCERTAIN"),
        ({"evidence_status": "insufficient"}, None, False, "none", "none",
         "INSUFFICIENT_MECHANISM_EVIDENCE"),
        ({"evidence_status": "conflicting"}, "uncertain", False, "none", "none",
         "CONFLICTING_MECHANISM_EVIDENCE"),
        ({"coverage": "already_covered"}, "execution_issue", False, "none", "none",
         "MECHANISM_ALREADY_COVERED"),
        ({"task_success": "insufficient"}, "uncertain", False, "none", "none",
         "NO_SUPPORTED_OPTIMIZATION_AXIS"),
        ({}, "skill_issue", True, "task_success", "add",
         "UPDATE_ELIGIBLE_MISSING_COVERAGE"),
        ({"task_success": "insufficient", "compliance": "supports"},
         "skill_issue", True, "compliance", "add", "UPDATE_ELIGIBLE_MISSING_COVERAGE"),
        ({"compliance": "supports"}, "skill_issue", True, "both", "add",
         "UPDATE_ELIGIBLE_MISSING_COVERAGE"),
    ],
)
def test_compiler_decision_table(overrides, root, eligible, axis, operation, reason):
    value = _semantic(**overrides)
    decision, trace = compile_semantic_diagnosis(value, SECTIONS)
    assert decision == {
        "root_cause": root, "update_eligible": eligible, "update_axis": axis,
        "operation": operation, "target_section": None, "target_rule_id": None,
        "reason": reason,
    }
    assert trace["decision_reason"] == reason


@pytest.mark.parametrize(
    ("coverage", "intent", "rule_id", "operation"),
    [("incorrect", "replace", "R1", "replace"),
     ("underspecified", "delete", "R2", "delete")],
)
def test_compiler_derives_revision_operation_and_section_from_unique_rule(
    coverage, intent, rule_id, operation,
):
    value = _semantic(
        coverage=coverage, related_rule_ids=[rule_id], edit_intent=intent,
    )
    decision, _ = compile_semantic_diagnosis(value, SECTIONS)
    expected_section = "Execution patterns" if rule_id == "R1" else "Form entry and verification"
    assert decision["update_eligible"]
    assert decision["operation"] == operation
    assert decision["target_rule_id"] == rule_id
    assert decision["target_section"] == expected_section


@pytest.mark.parametrize(
    ("related_rule_ids", "intent", "reason"),
    [([], "replace", "AMBIGUOUS_RULE_TARGET"),
     (["R1", "R2"], "replace", "AMBIGUOUS_RULE_TARGET"),
     (["R1"], "not_applicable", "MISSING_REVISION_INTENT")],
)
def test_compiler_does_not_guess_revision_target_or_intent(related_rule_ids, intent, reason):
    value = _semantic(
        coverage="incorrect", related_rule_ids=related_rule_ids, edit_intent=intent,
    )
    decision, _ = compile_semantic_diagnosis(value, SECTIONS)
    assert decision["root_cause"] == "uncertain"
    assert not decision["update_eligible"]
    assert decision["reason"] == reason


def test_compiler_precedence_prevents_lower_fields_from_upgrading_infeasible_case():
    value = _semantic(
        feasibility="infeasible", coverage="incorrect", related_rule_ids=["R1"],
        edit_intent="replace", compliance="supports",
    )
    decision, _ = compile_semantic_diagnosis(value, SECTIONS)
    assert decision["reason"] == "INFEASIBLE_TASK_POLICY_TOOL_COMBINATION"
    assert not decision["update_eligible"]


def _twenty_task_evidence() -> tuple[dict, ...]:
    return tuple(
        _experience(domain, str(task), rollout_index)
        for domain in ("airline", "retail")
        for task in range(1, 11)
        for rollout_index in (1, 2, 3)
    )


def _update_diagnoser(request) -> str:
    return _tag(_semantic(
        evidence_status="recurrent_support",
        source_id=request.rollouts[0]["source_id"],
    ))


def _no_update_diagnoser(request) -> str:
    return _tag(_semantic(
        evidence_status="insufficient", task_success="insufficient",
        source_id=request.rollouts[0]["source_id"],
    ))


def _merged_editor(request) -> str:
    return "<CANONICAL_EDITS_JSON>" + json.dumps([
        _edit([item["patch_id"] for item in request.eligible_diagnoses])
    ]) + "</CANONICAL_EDITS_JSON>"


def test_proposal_consumes_compiled_decisions_and_preserves_editor_method():
    context = ProposalContext("candidate_001", _parent_skill(), _twenty_task_evidence())
    decision = proposal_v14.MultiRolloutDiagnosisProposalOperator().propose(
        context, _update_diagnoser, _merged_editor, domain_contexts=_domain_contexts(),
    )
    assert decision.proposal_status == "CANDIDATE"
    assert decision.diagnosis_calls == 20
    assert decision.editor_calls == 1
    assert len(decision.eligible_diagnosis_ids) == 20
    assert all(item["compiled_decision"]["update_eligible"] for item in decision.diagnoses)
    assert decision.raw_patches[0]["operation"] == "add"
    assert decision.raw_patches[0]["objective"] == (
        "choose the behavior supported by the grounded predicate"
    )
    assert "behavioral_mechanism" in decision.raw_patches[0]
    assert "behavior_analysis" not in decision.raw_patches[0]


def test_proposal_skips_editor_when_compiler_finds_no_update():
    context = ProposalContext("candidate_001", _parent_skill(), _twenty_task_evidence())
    decision = proposal_v14.MultiRolloutDiagnosisProposalOperator().propose(
        context, _no_update_diagnoser, _merged_editor, domain_contexts=_domain_contexts(),
    )
    assert decision.proposal_status == "NO_CANDIDATE"
    assert decision.editor_calls == 0
    assert decision.eligible_diagnosis_ids == []
    assert all(
        item["compiled_decision"]["reason"] == "INSUFFICIENT_MECHANISM_EVIDENCE"
        for item in decision.diagnoses
    )


def test_validation_artifact_separates_semantic_and_compiler_authority():
    validation = _validate(_semantic())
    compiled, trace = compile_semantic_diagnosis(validation.structured_output, SECTIONS)
    artifact = replace(
        validation, compiled_decision=compiled, compiler_trace=trace,
    ).as_dict()
    assert set(artifact) == {
        "diagnosis_id", "source_ids", "semantic", "compiled_decision", "compiler_trace",
    }
    assert artifact["semantic"]["structured_output"] == validation.structured_output
    assert artifact["semantic"]["validation"] == {"valid": True, "errors": []}
    assert artifact["compiled_decision"]["root_cause"] == "skill_issue"
    assert artifact["compiler_trace"]["supported_axes"] == ["task_success"]
    assert "repair_trace" not in artifact


def test_editor_prompt_uses_semantic_diagnosis_and_compiler_ownership():
    prompt = editor_v14.EDITOR_SYSTEM_PROMPT
    assert "Semantic Diagnosis plus deterministic Decision Compiler" in prompt
    assert "section placement" in prompt
    assert "cross-task deduplication" in prompt
    assert "final Skill wording" in prompt


def test_v14_semantic_modules_do_not_import_v13_learner_modules():
    paths = (
        ROOT / "src/skill_evolution/diagnosis_contract_v14.py",
        ROOT / "src/skill_evolution/diagnosis_compiler_v14.py",
        ROOT / "src/skill_evolution/diagnosis_v14.py",
        ROOT / "src/skill_evolution/autonomous_gse_v14_proposal.py",
        ROOT / "src/learners/stwebagentbench/generate_governed_skill_v14.py",
    )
    forbidden = {
        "src.skill_evolution.diagnosis_v13",
        "src.skill_evolution.diagnosis_contract_v13",
        "src.skill_evolution.autonomous_gse_v13_proposal",
        "src.learners.stwebagentbench.generate_governed_skill_v13",
    }
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)
                imported.update(f"{node.module}.{alias.name}" for alias in node.names)
        assert not imported & forbidden, (path, imported & forbidden)


def test_campaign_provenance_and_frozen_judge_remain_valid():
    campaign = json.loads(CAMPAIGN.read_text(encoding="utf-8"))
    assert campaign["learner_stack"]["diagnosis"] == "src.skill_evolution.diagnosis_v14"
    assert campaign["learner_stack"]["semantics_snapshot_from"] == "autonomous_gse_v13"
    assert campaign["compliance_judge"]["implementation"] == (
        "src.adapters.tau2.tau3_compliance_judge_v13"
    )
    runtime_v14.validate_campaign_contract(campaign)
    assert runtime_v14.call_diagnosis is diagnosis_v14.call_diagnosis
    assert runtime_v14.call_governed_editor is editor_v14.call_governed_editor
    assert runtime_v14.judge_compliance is compliance_v13.judge_compliance

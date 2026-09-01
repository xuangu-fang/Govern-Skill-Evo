from __future__ import annotations

import ast
import copy
import json
import re
from pathlib import Path

from src.adapters.tau2 import tau3_compliance_judge_v13 as compliance_v13
from src.learners.stwebagentbench import generate_governed_skill_v13 as editor_v13
from src.learners.stwebagentbench import generate_governed_skill_v14 as editor_v14
from src.skill_evolution import autonomous_gse_v13_proposal as proposal_v13
from src.skill_evolution import autonomous_gse_v14_benchmark_runtime as runtime_v14
from src.skill_evolution import autonomous_gse_v14_proposal as proposal_v14
from src.skill_evolution import diagnosis_contract_v13 as contract_v13
from src.skill_evolution import diagnosis_contract_v14 as contract_v14
from src.skill_evolution import diagnosis_v13
from src.skill_evolution import diagnosis_v14
from src.skill_evolution.autonomous_gse_v03_proposal import ProposalContext
from tests.skill_evolution.test_autonomous_gse_v13 import (
    _diagnosis, _domain_contexts, _edit, _experience, _group, _tag,
)


ROOT = Path(__file__).resolve().parents[2]
CAMPAIGN = ROOT / "experiments/campaigns/autonomous_gse_v14/campaign_manifest.json"
S0 = ROOT / "experiments/campaigns/autonomous_gse_v14/skills/S0_empty_skill.md"


def _normalize_version_identity(value: str) -> str:
    return re.sub(r"v0\.(?:13|14)", "v0.X", value).replace(
        "v13_dual_axis_mechanism_preserving_bounded_edit",
        "vX_dual_axis_mechanism_preserving_bounded_edit",
    ).replace(
        "v14_dual_axis_mechanism_preserving_bounded_edit",
        "vX_dual_axis_mechanism_preserving_bounded_edit",
    )


def _parent_skill() -> str:
    return S0.read_text(encoding="utf-8").replace(
        "# Operational Skill", "# SuiteCRM Operational Skill", 1,
    )


def _diagnosis_request_v14() -> diagnosis_v14.MultiRolloutDiagnosisRequest:
    context = _domain_contexts()["airline"]
    return diagnosis_v14.MultiRolloutDiagnosisRequest(
        candidate_id="candidate_001", diagnosis_id="diagnosis_001",
        current_parent_skill=_parent_skill(),
        task_context={"domain": "airline", "task_id": "1"},
        original_domain_policy=context["original_domain_policy"],
        available_tool_contracts=context["available_tool_contracts"],
        rollouts=_group(),
    )


def _repair_tag(value: dict) -> str:
    return (
        "<DIAGNOSIS_REPAIR_JSON>"
        + json.dumps(value)
        + "</DIAGNOSIS_REPAIR_JSON>"
    )


def _validate_v14_diagnosis(response: str):
    return contract_v14.parse_and_validate_diagnosis(
        "diagnosis_001", response, experiences=_group(),
        skill_sections={"Planning and navigation": [], "Execution patterns": [],
                        "Form entry and verification": [],
                        "Error recovery and stopping": []},
    )


def _request_pair(diagnoses: tuple[dict, ...]):
    common = {
        "candidate_id": "candidate_001",
        "current_parent_skill": _parent_skill(),
        "eligible_diagnoses": diagnoses,
        "domain_contexts": ({
            "domain": "airline",
            "original_domain_policy": "# Airline policy\nFollow applicable requirements.",
        },),
    }
    return proposal_v13.DiagnosisEditorRequest(**common), proposal_v14.DiagnosisEditorRequest(**common)


def _twenty_task_evidence() -> tuple[dict, ...]:
    return tuple(
        _experience(domain, str(task), rollout_index)
        for domain in ("airline", "retail")
        for task in range(1, 11)
        for rollout_index in (1, 2, 3)
    )


def _update_diagnoser(request) -> str:
    value = _diagnosis(
        relevance="update", action="add", category="skill_issue",
        update_axis="both", evidence_pattern="recurrent",
        problem="a stable decision mechanism is missing",
        repair_operator="apply the bounded mechanism at the decision opportunity",
    )
    value["behavior_analysis"]["support_evidence_refs"] = [{
        "source_id": request.rollouts[0]["source_id"], "step_ids": [2],
    }]
    return _tag(value)


def _no_update_diagnoser(request) -> str:
    value = _diagnosis()
    value["behavior_analysis"]["support_evidence_refs"] = []
    return _tag(value)


def _merged_editor(request) -> str:
    return "<CANONICAL_EDITS_JSON>" + json.dumps([
        _edit([item["patch_id"] for item in request.eligible_diagnoses])
    ]) + "</CANONICAL_EDITS_JSON>"


def test_diagnosis_contract_snapshot_equivalence_for_valid_invalid_and_repair():
    experiences = _group()
    sections = {"Planning and navigation": []}
    valid = _diagnosis(
        relevance="update", action="add", category="skill_issue",
        update_axis="both", evidence_pattern="recurrent",
        problem="missing decision mechanism", repair_operator="apply bounded repair",
    )
    assert contract_v13.validate_diagnosis(
        copy.deepcopy(valid), experiences=experiences, skill_sections=sections,
    ) == contract_v14.validate_diagnosis(
        copy.deepcopy(valid), experiences=experiences, skill_sections=sections,
    ) == ()

    invalid = copy.deepcopy(valid)
    invalid["update_axis"] = "none"
    errors13 = contract_v13.validate_diagnosis(
        copy.deepcopy(invalid), experiences=experiences, skill_sections=sections,
    )
    errors14 = contract_v14.validate_diagnosis(
        copy.deepcopy(invalid), experiences=experiences, skill_sections=sections,
    )
    assert errors13 == errors14
    assert contract_v13.repair_diagnosis_contract_fields(invalid, errors13) == (
        contract_v14.repair_diagnosis_contract_fields(invalid, errors14)
    )
    response = _tag(valid)
    assert contract_v13.parse_and_validate_diagnosis(
        "diagnosis_001", response, experiences=experiences, skill_sections=sections,
    ).as_dict() == contract_v14.parse_and_validate_diagnosis(
        "diagnosis_001", response, experiences=experiences, skill_sections=sections,
    ).as_dict()


def test_diagnosis_prompt_keeps_v13_lineage_with_v14_outcome_support_extension():
    assert diagnosis_v14.LEARNER_MODEL == diagnosis_v13.LEARNER_MODEL
    assert diagnosis_v14.EMPTY_RESPONSE_RETRIES == diagnosis_v13.EMPTY_RESPONSE_RETRIES
    v14_base = diagnosis_v14.DIAGNOSIS_SYSTEM_PROMPT.replace(
        diagnosis_v14.OUTCOME_SUPPORT_CHECKPOINT + "\n\n", "",
    )
    assert _normalize_version_identity(v14_base) == (
        _normalize_version_identity(diagnosis_v13.DIAGNOSIS_SYSTEM_PROMPT)
    )


def test_diagnosis_prompt_contains_general_outcome_support_checkpoint():
    checkpoint = diagnosis_v14.OUTCOME_SUPPORT_CHECKPOINT
    assert "coverage gap does not by itself justify" in checkpoint
    assert "at least one observed optimization-axis relation" in checkpoint
    assert "neither task_success_relation nor compliance_relation is supportive" in checkpoint
    assert "do not force an update" in checkpoint
    assert 'root_cause.category = "uncertain"' in checkpoint
    assert 'skill_update_relevance = "uncertain"' in checkpoint
    assert 'update_axis = "none"' in checkpoint
    assert 'update_recommendation.action = "none"' in checkpoint
    assert 'do not change an outcome-axis relation to "supportive"' in checkpoint
    assert "later self-corrects" in checkpoint
    assert "retail" not in checkpoint.lower()
    assert "second preference" not in checkpoint.lower()


def test_outcome_support_checkpoint_mappings_pass_the_existing_contract():
    experiences = _group()
    sections = {"Planning and navigation": [], "Execution patterns": [],
                "Form entry and verification": [],
                "Error recovery and stopping": []}
    supported_updates = (
        _diagnosis(
            relevance="update", action="add", category="skill_issue",
            update_axis="task_success", evidence_pattern="contrastive",
            task_success_relation="supportive", compliance_relation="insufficient",
            coverage_status="missing", problem="missing mechanism",
            repair_operator="apply bounded mechanism",
        ),
        _diagnosis(
            relevance="update", action="add", category="skill_issue",
            update_axis="compliance", evidence_pattern="contrastive",
            task_success_relation="insufficient", compliance_relation="supportive",
            coverage_status="missing", problem="missing mechanism",
            repair_operator="apply bounded mechanism",
        ),
        _diagnosis(
            relevance="update", action="add", category="skill_issue",
            update_axis="both", evidence_pattern="contrastive",
            task_success_relation="supportive", compliance_relation="supportive",
            coverage_status="missing", problem="missing mechanism",
            repair_operator="apply bounded mechanism",
        ),
    )
    for diagnosis in supported_updates:
        assert contract_v14.validate_diagnosis(
            diagnosis, experiences=experiences, skill_sections=sections,
        ) == ()

    no_outcome_support = _diagnosis(
        relevance="uncertain", action="none", category="uncertain",
        update_axis="none", evidence_pattern="contrastive",
        task_success_relation="insufficient", compliance_relation="not_applicable",
        coverage_status="missing",
    )
    no_outcome_support["behavior_analysis"]["evidence_consistency"] = "supportive"
    no_outcome_support["behavior_analysis"]["behavioral_mechanism"] = (
        "the Agent makes a concrete intermediate choice and later self-corrects"
    )
    assert contract_v14.validate_diagnosis(
        no_outcome_support, experiences=experiences, skill_sections=sections,
    ) == ()
    assert no_outcome_support["parent_skill_coverage"]["status"] == "missing"
    assert no_outcome_support["root_cause"]["category"] == "uncertain"
    assert no_outcome_support["skill_update_relevance"] == "uncertain"
    assert no_outcome_support["update_axis"] == "none"
    assert no_outcome_support["update_recommendation"]["action"] == "none"


def test_semantic_repair_whitelist_and_authoritative_paths_are_exact():
    assert diagnosis_v14.SEMANTIC_REPAIRABLE_ERRORS == frozenset({
        "INVALID_COMPLIANCE_RELATION",
        "INVALID_TASK_SUCCESS_RELATION",
        "INVALID_EVIDENCE_CONSISTENCY",
        "INVALID_EVIDENCE_PATTERN",
    })
    assert diagnosis_v14.SEMANTIC_REPAIR_FIELD_BY_ERROR == {
        "INVALID_COMPLIANCE_RELATION": ("behavior_analysis", "compliance_relation"),
        "INVALID_TASK_SUCCESS_RELATION": ("behavior_analysis", "task_success_relation"),
        "INVALID_EVIDENCE_CONSISTENCY": ("behavior_analysis", "evidence_consistency"),
        "INVALID_EVIDENCE_PATTERN": ("behavior_analysis", "evidence_pattern"),
    }


def test_bare_json_diagnosis_is_tagged_locally_without_extra_call():
    value = _diagnosis()
    calls = []

    def learner_call(model, system, user):
        calls.append((model, system, user))
        return json.dumps(value), model, None

    response = diagnosis_v14.call_diagnosis(
        _diagnosis_request_v14(), learner_call=learner_call,
    )
    validation = contract_v14.parse_and_validate_diagnosis(
        "diagnosis_001", response, experiences=_group(),
        skill_sections={"Planning and navigation": [], "Execution patterns": [],
                        "Form entry and verification": [],
                        "Error recovery and stopping": []},
    )
    assert len(calls) == 1
    assert response.startswith("<DIAGNOSIS_JSON>")
    assert response.endswith("</DIAGNOSIS_JSON>")
    assert validation.valid
    assert validation.repair_trace == {"attempted": False}


def test_whitelisted_enum_error_gets_one_field_patch_repair_call():
    invalid = _diagnosis()
    invalid["behavior_analysis"]["compliance_relation"] = "conflicting"
    responses = iter((
        _tag(invalid),
        _repair_tag({"behavior_analysis.compliance_relation": "insufficient"}),
    ))
    calls = []

    def learner_call(model, system, user):
        calls.append((model, system, user))
        return next(responses), model, None

    response = diagnosis_v14.call_diagnosis(
        _diagnosis_request_v14(), learner_call=learner_call,
    )
    validation = _validate_v14_diagnosis(response)
    expected = copy.deepcopy(invalid)
    expected["behavior_analysis"]["compliance_relation"] = "insufficient"
    assert len(calls) == 2
    assert "bounded Diagnosis contract repair" in calls[1][1]
    assert "Return only the DIAGNOSIS_JSON block." not in calls[1][2]
    assert "DIAGNOSIS_REPAIR_JSON" in calls[1][1]
    assert "DIAGNOSIS_REPAIR_JSON" in calls[1][2]
    for field in (
        "task_context", "original_domain_policy", "available_tool_contracts", "rollouts",
        "FROZEN_ORIGINAL_DIAGNOSIS", "PYTHON_CONTRACT_VALIDATION_ERRORS",
        "PYTHON_ALLOWED_REPAIR_FIELDS_AND_VALUES",
    ):
        assert field in calls[1][2]
    assert "INVALID_COMPLIANCE_RELATION" in calls[1][2]
    assert "behavior_analysis.compliance_relation" in calls[1][2]
    assert validation.valid
    assert validation.structured_output == expected
    assert validation.repair_trace == {
        "attempted": True,
        "initial_raw_response": _tag(invalid),
        "validation_errors_before": ["INVALID_COMPLIANCE_RELATION"],
        "allowed_fields": {
            "behavior_analysis.compliance_relation": [
                "contradictory", "insufficient", "not_applicable", "supportive",
            ],
        },
        "raw_repair_response": _repair_tag({
            "behavior_analysis.compliance_relation": "insufficient",
        }),
        "parse_status": "tagged_json_object",
        "parsed_patch": {"behavior_analysis.compliance_relation": "insufficient"},
        "rejection_reason": None,
        "final_validation": {"valid": True, "errors": []},
    }


def test_non_whitelisted_policy_error_does_not_call_semantic_repair():
    invalid = _diagnosis()
    invalid["repair_policy_ids"] = ["POLICY-NOT-IN-EVIDENCE"]
    calls = []

    def learner_call(model, system, user):
        calls.append((model, system, user))
        return _tag(invalid), model, None

    response = diagnosis_v14.call_diagnosis(
        _diagnosis_request_v14(), learner_call=learner_call,
    )
    validation = _validate_v14_diagnosis(response)
    assert len(calls) == 1
    assert not validation.valid
    assert "POLICY_ID_NOT_IN_EVIDENCE" in validation.validation_errors
    assert validation.repair_trace == {"attempted": False}


def test_non_whitelisted_evidence_ref_error_does_not_call_semantic_repair():
    invalid = _diagnosis()
    invalid["behavior_analysis"]["support_evidence_refs"] = [{
        "source_id": "unknown-source", "step_ids": [2],
    }]
    calls = []

    def learner_call(model, system, user):
        calls.append((model, system, user))
        return _tag(invalid), model, None

    response = diagnosis_v14.call_diagnosis(
        _diagnosis_request_v14(), learner_call=learner_call,
    )
    validation = _validate_v14_diagnosis(response)
    assert len(calls) == 1
    assert not validation.valid
    assert "SUPPORT_EVIDENCE_SOURCE_NOT_FOUND" in validation.validation_errors
    assert validation.repair_trace == {"attempted": False}


def test_semantic_repair_rejects_extra_wrong_missing_keys_and_invalid_enum():
    invalid = _diagnosis()
    invalid["behavior_analysis"]["compliance_relation"] = "conflicting"
    bad_patches = (
        ({
            "behavior_analysis.compliance_relation": "insufficient",
            "root_cause.category": "execution_issue",
        }, "PATCH_KEYS_MISMATCH"),
        ({
            "behavior_analysis.compliance_relation": "insufficient",
            "behavior_analysis.behavioral_mechanism": "changed mechanism",
        }, "PATCH_KEYS_MISMATCH"),
        ({"behavior_analysis.task_success_relation": "insufficient"}, "PATCH_KEYS_MISMATCH"),
        ({}, "PATCH_KEYS_MISMATCH"),
        ({"behavior_analysis.compliance_relation": "conflicting"}, "INVALID_PATCH_VALUE"),
    )
    for patch, reason in bad_patches:
        responses = iter((_tag(invalid), _repair_tag(patch)))
        calls = []

        def learner_call(model, system, user):
            calls.append((model, system, user))
            return next(responses), model, None

        response = diagnosis_v14.call_diagnosis(
            _diagnosis_request_v14(), learner_call=learner_call,
        )
        validation = _validate_v14_diagnosis(response)
        assert len(calls) == 2
        assert not validation.valid
        assert validation.structured_output == invalid
        assert validation.repair_trace["rejection_reason"] == reason
        assert validation.repair_trace["raw_repair_response"] == _repair_tag(patch)
        assert validation.repair_trace["parsed_patch"] == patch
        assert validation.repair_trace["final_validation"] == {
            "valid": False, "errors": ["INVALID_COMPLIANCE_RELATION"],
        }


def test_semantic_patch_application_deep_copies_and_freezes_other_fields():
    original = _diagnosis()
    original["behavior_analysis"]["compliance_relation"] = "conflicting"
    frozen = copy.deepcopy(original)
    result = diagnosis_v14._apply_semantic_contract_patch(
        original, ("INVALID_COMPLIANCE_RELATION",),
        {"behavior_analysis.compliance_relation": "insufficient"},
    )
    expected = copy.deepcopy(frozen)
    expected["behavior_analysis"]["compliance_relation"] = "insufficient"
    assert original == frozen
    assert result.repaired_diagnosis == expected
    assert result.rejection_reason is None


def test_semantic_repair_accepts_whole_response_bare_patch_object():
    invalid = _diagnosis()
    invalid["behavior_analysis"]["compliance_relation"] = "conflicting"
    bare_patch = json.dumps({"behavior_analysis.compliance_relation": "insufficient"})
    responses = iter((_tag(invalid), bare_patch))

    def learner_call(model, system, user):
        return next(responses), model, None

    response = diagnosis_v14.call_diagnosis(
        _diagnosis_request_v14(), learner_call=learner_call,
    )
    validation = _validate_v14_diagnosis(response)
    assert validation.valid
    assert validation.repair_trace["parse_status"] == "bare_json_object"
    assert validation.repair_trace["raw_repair_response"] == bare_patch
    assert validation.repair_trace["rejection_reason"] is None


def test_semantic_repair_rejects_prose_full_diagnosis_and_invalid_json_with_trace():
    invalid = _diagnosis()
    invalid["behavior_analysis"]["compliance_relation"] = "conflicting"
    rewritten = copy.deepcopy(invalid)
    rewritten["behavior_analysis"]["compliance_relation"] = "insufficient"
    rewritten["behavior_analysis"]["behavioral_mechanism"] = "changed mechanism"
    repair_cases = (
        (
            'Here is the repair: {"behavior_analysis.compliance_relation":"insufficient"}',
            "INVALID_ENVELOPE",
        ),
        (_tag(rewritten), "INVALID_ENVELOPE"),
        ("<DIAGNOSIS_REPAIR_JSON>not-json</DIAGNOSIS_REPAIR_JSON>", "INVALID_JSON"),
    )
    for repair_response, reason in repair_cases:
        responses = iter((_tag(invalid), repair_response))

        def learner_call(model, system, user):
            return next(responses), model, None

        response = diagnosis_v14.call_diagnosis(
            _diagnosis_request_v14(), learner_call=learner_call,
        )
        validation = _validate_v14_diagnosis(response)
        assert not validation.valid
        assert validation.structured_output == invalid
        assert validation.repair_trace["attempted"] is True
        assert validation.repair_trace["raw_repair_response"] == repair_response
        assert validation.repair_trace["parsed_patch"] is None
        assert validation.repair_trace["rejection_reason"] == reason


def test_bare_complete_diagnosis_is_rejected_by_exact_field_whitelist():
    invalid = _diagnosis()
    invalid["behavior_analysis"]["compliance_relation"] = "conflicting"
    complete = copy.deepcopy(invalid)
    complete["behavior_analysis"]["compliance_relation"] = "insufficient"
    responses = iter((_tag(invalid), json.dumps(complete)))

    def learner_call(model, system, user):
        return next(responses), model, None

    response = diagnosis_v14.call_diagnosis(
        _diagnosis_request_v14(), learner_call=learner_call,
    )
    validation = _validate_v14_diagnosis(response)
    assert not validation.valid
    assert validation.repair_trace["parse_status"] == "bare_json_object"
    assert validation.repair_trace["rejection_reason"] == "PATCH_KEYS_MISMATCH"


def test_all_compliance_relation_enum_values_pass_patch_validation_then_strict_validation():
    original = _diagnosis(
        relevance="uncertain", action="none", category="uncertain",
        update_axis="none", evidence_pattern="recurrent",
        task_success_relation="insufficient", compliance_relation="conflicting",
        coverage_status="missing",
    )
    original["behavior_analysis"]["evidence_consistency"] = "conflicting"
    original["behavior_analysis"]["behavioral_mechanism"] = "recurrent omission"
    for value in ("supportive", "contradictory", "insufficient", "not_applicable"):
        result = diagnosis_v14._apply_semantic_contract_patch(
            original, ("INVALID_COMPLIANCE_RELATION",),
            {"behavior_analysis.compliance_relation": value},
        )
        assert result.rejection_reason is None
        response = _tag(result.repaired_diagnosis)
        assert _validate_v14_diagnosis(response).valid
        expected = copy.deepcopy(original)
        expected["behavior_analysis"]["compliance_relation"] = value
        assert result.repaired_diagnosis == expected


def test_contract_repair_parser_distinguishes_non_object_patch():
    tagged = diagnosis_v14._parse_contract_repair_patch(
        "<DIAGNOSIS_REPAIR_JSON>[]</DIAGNOSIS_REPAIR_JSON>",
    )
    bare = diagnosis_v14._parse_contract_repair_patch("[]")
    assert tagged.parse_status == "tagged_json_non_object"
    assert tagged.rejection_reason == "PATCH_NOT_OBJECT"
    assert bare.parse_status == "bare_json_non_object"
    assert bare.rejection_reason == "PATCH_NOT_OBJECT"


def test_multi_field_semantic_repair_requires_and_changes_exactly_both_fields():
    invalid = _diagnosis()
    invalid["behavior_analysis"]["task_success_relation"] = "bad-task-relation"
    invalid["behavior_analysis"]["compliance_relation"] = "bad-compliance-relation"
    patch = {
        "behavior_analysis.task_success_relation": "supportive",
        "behavior_analysis.compliance_relation": "insufficient",
    }
    responses = iter((_tag(invalid), _repair_tag(patch)))

    def learner_call(model, system, user):
        return next(responses), model, None

    response = diagnosis_v14.call_diagnosis(
        _diagnosis_request_v14(), learner_call=learner_call,
    )
    validation = _validate_v14_diagnosis(response)
    expected = copy.deepcopy(invalid)
    expected["behavior_analysis"]["task_success_relation"] = "supportive"
    expected["behavior_analysis"]["compliance_relation"] = "insufficient"
    assert validation.valid
    assert validation.structured_output == expected


def test_multi_field_semantic_repair_rejects_a_missing_required_key():
    invalid = _diagnosis()
    invalid["behavior_analysis"]["task_success_relation"] = "bad-task-relation"
    invalid["behavior_analysis"]["compliance_relation"] = "bad-compliance-relation"
    responses = iter((
        _tag(invalid),
        _repair_tag({"behavior_analysis.compliance_relation": "insufficient"}),
    ))

    def learner_call(model, system, user):
        return next(responses), model, None

    response = diagnosis_v14.call_diagnosis(
        _diagnosis_request_v14(), learner_call=learner_call,
    )
    validation = _validate_v14_diagnosis(response)
    assert not validation.valid
    assert validation.structured_output == invalid


def test_existing_deterministic_repair_does_not_call_semantic_repair():
    invalid = _diagnosis(
        relevance="uncertain", category="execution_issue",
        coverage_status="already_covered",
    )
    calls = []

    def learner_call(model, system, user):
        calls.append((model, system, user))
        return _tag(invalid), model, None

    response = diagnosis_v14.call_diagnosis(
        _diagnosis_request_v14(), learner_call=learner_call,
    )
    validation = _validate_v14_diagnosis(response)
    assert len(calls) == 1
    assert validation.valid
    assert validation.structured_output["skill_update_relevance"] == "none"
    assert validation.repair_trace == {"attempted": False}


def test_contract_repair_is_bounded_to_one_additional_call_and_still_fails_closed():
    invalid = _diagnosis()
    invalid["behavior_analysis"]["evidence_consistency"] = "bad-consistency"
    responses = iter((
        _tag(invalid),
        _repair_tag({"behavior_analysis.evidence_consistency": "conflicting"}),
    ))
    calls = []

    def learner_call(model, system, user):
        calls.append((model, system, user))
        return next(responses), model, None

    response = diagnosis_v14.call_diagnosis(
        _diagnosis_request_v14(), learner_call=learner_call,
    )
    validation = _validate_v14_diagnosis(response)
    assert len(calls) == 2
    assert not validation.valid
    assert validation.validation_errors == ("INVALID_EVIDENCE_CONSISTENCY",)
    assert validation.repair_trace["rejection_reason"] == "FINAL_VALIDATION_FAILED"
    assert validation.repair_trace["final_validation"]["valid"] is False


def test_editor_prompt_configuration_and_synthetic_call_are_equivalent():
    diagnoses = ({"patch_id": "diagnosis_001", "objective": "bounded repair"},)
    request13, request14 = _request_pair(diagnoses)
    system13, user13 = editor_v13.build_editor_prompts(request13)
    system14, user14 = editor_v14.build_editor_prompts(request14)
    assert editor_v14.LEARNER_MODEL == editor_v13.LEARNER_MODEL
    assert _normalize_version_identity(system14) == _normalize_version_identity(system13)
    assert user14 == user13

    response = "<CANONICAL_EDITS_JSON>[]</CANONICAL_EDITS_JSON>"
    learner = lambda model, system, user: (response, "", None)
    assert editor_v13.call_governed_editor(request13, learner_call=learner) == (
        editor_v14.call_governed_editor(request14, learner_call=learner)
    )


def test_proposal_signal_snapshot_equivalence():
    experiences = _group()
    diagnosis = _diagnosis(
        relevance="update", action="add", category="skill_issue",
        update_axis="both", evidence_pattern="recurrent",
        problem="missing mechanism", repair_operator="apply bounded repair",
    )
    validation13 = contract_v13.parse_and_validate_diagnosis(
        "diagnosis_001", _tag(diagnosis), experiences=experiences,
        skill_sections={"Planning and navigation": []},
    )
    validation14 = contract_v14.parse_and_validate_diagnosis(
        "diagnosis_001", _tag(diagnosis), experiences=experiences,
        skill_sections={"Planning and navigation": []},
    )
    assert proposal_v13._signal(validation13, ("airline", "1")) == (
        proposal_v14._signal(validation14, ("airline", "1"))
    )


def test_proposal_end_to_end_twenty_task_snapshot_equivalence():
    context = ProposalContext(
        "candidate_001", _parent_skill(), _twenty_task_evidence(),
    )
    decision13 = proposal_v13.MultiRolloutDiagnosisProposalOperator().propose(
        context, _update_diagnoser, _merged_editor, domain_contexts=_domain_contexts(),
    )
    decision14 = proposal_v14.MultiRolloutDiagnosisProposalOperator().propose(
        context, _update_diagnoser, _merged_editor, domain_contexts=_domain_contexts(),
    )
    assert decision14.__dict__ == decision13.__dict__
    assert decision14.proposal_status == "CANDIDATE"
    assert len(decision14.eligible_diagnosis_ids) == 20
    assert decision14.editor_calls == 1


def test_no_candidate_snapshot_equivalence():
    context = ProposalContext(
        "candidate_001", _parent_skill(), _twenty_task_evidence(),
    )
    decision13 = proposal_v13.MultiRolloutDiagnosisProposalOperator().propose(
        context, _no_update_diagnoser, _merged_editor, domain_contexts=_domain_contexts(),
    )
    decision14 = proposal_v14.MultiRolloutDiagnosisProposalOperator().propose(
        context, _no_update_diagnoser, _merged_editor, domain_contexts=_domain_contexts(),
    )
    assert decision14.__dict__ == decision13.__dict__
    assert decision14.proposal_status == "NO_CANDIDATE"
    assert decision14.editor_calls == 0


def test_v14_semantic_modules_do_not_import_v13_learner_modules():
    paths = (
        ROOT / "src/skill_evolution/diagnosis_contract_v14.py",
        ROOT / "src/skill_evolution/diagnosis_v14.py",
        ROOT / "src/skill_evolution/autonomous_gse_v14_proposal.py",
        ROOT / "src/learners/stwebagentbench/generate_governed_skill_v14.py",
        ROOT / "src/skill_evolution/autonomous_gse_v14_benchmark_runtime.py",
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


def test_manifest_and_runtime_own_v14_learner_but_share_frozen_judge():
    campaign = json.loads(CAMPAIGN.read_text(encoding="utf-8"))
    assert campaign["learner_stack"] == {
        "diagnosis": "src.skill_evolution.diagnosis_v14",
        "diagnosis_contract": "src.skill_evolution.diagnosis_contract_v14",
        "proposal_operator": (
            "src.skill_evolution.autonomous_gse_v14_proposal."
            "MultiRolloutDiagnosisProposalOperator"
        ),
        "editor": (
            "src.learners.stwebagentbench.generate_governed_skill_v14."
            "call_governed_editor"
        ),
        "semantics_snapshot_from": "autonomous_gse_v13",
    }
    assert campaign["compliance_judge"] == {
        "implementation": "src.adapters.tau2.tau3_compliance_judge_v13",
        "model": compliance_v13.JUDGE_MODEL,
        "temperature": compliance_v13.JUDGE_TEMPERATURE,
        "prompt_version": compliance_v13.JUDGE_PROMPT_VERSION,
        "frozen_from": "autonomous_gse_v13",
        "fallback": "forbidden",
    }
    runtime_v14.validate_campaign_contract(campaign)
    assert runtime_v14.call_diagnosis is diagnosis_v14.call_diagnosis
    assert runtime_v14.call_governed_editor is editor_v14.call_governed_editor
    assert runtime_v14.judge_compliance is compliance_v13.judge_compliance

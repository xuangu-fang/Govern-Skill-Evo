from __future__ import annotations

import ast
import copy
import json
import sys
from types import SimpleNamespace
from dataclasses import replace
from pathlib import Path

import pytest

from src.adapters.tau2 import tau3_compliance_judge_v13 as compliance_v13
from src.learners.stwebagentbench import generate_governed_skill_v14 as editor_v14
from src.learners.stwebagentbench import generate_skill
from src.skill_evolution import autonomous_gse_v14_benchmark_runtime as runtime_v14
from src.skill_evolution import autonomous_gse_v14_proposal as proposal_v14
from src.skill_evolution import diagnosis_contract_v14 as contract_v14
from src.skill_evolution import diagnosis_v14
from src.skill_evolution.autonomous_gse_v03_proposal import ProposalContext
from src.skill_evolution.diagnosis_compiler_v14 import compile_semantic_diagnosis
from src.skill_evolution.diagnosis_provenance_v14 import (
    build_provenance_alias_context, resolve_semantic_provenance,
)
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
    edit_intent: str = "not_applicable", evidence_ref: str = "E002",
    policy_refs: list[str] | None = None,
) -> dict:
    supported = evidence_status in {"contrastive_support", "recurrent_support"}
    return {
        "behavioral_mechanism": {
            "description": "the Agent applies the wrong decision predicate" if supported else "",
            "evidence_status": evidence_status,
            "support_evidence_refs": [evidence_ref] if supported else [],
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
        "repair_policy_refs": list(policy_refs or []),
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


@pytest.fixture(autouse=True)
def _reset_structured_output_capability(monkeypatch):
    monkeypatch.setattr(diagnosis_v14, "_STRUCTURED_OUTPUT_CAPABILITY", "unknown")
    monkeypatch.setattr(diagnosis_v14, "_STRUCTURED_OUTPUT_FALLBACK_REASON", None)


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
        (lambda value: value["behavioral_mechanism"].update(
            support_evidence_refs=["E999"],
        ), "SUPPORT_EVIDENCE_ALIAS_NOT_FOUND"),
        (lambda value: value["behavioral_mechanism"].update(
            support_evidence_refs=[{"step": 2}],
        ), "INVALID_SUPPORT_EVIDENCE_REF"),
        (lambda value: value["skill_coverage"].update(related_rule_ids=["invented"]),
         "RELATED_RULE_ID_NOT_FOUND"),
        (lambda value: value.update(repair_policy_refs=["P999"]),
         "POLICY_ALIAS_NOT_FOUND"),
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
    value["repair_policy_refs"] = ["P001"]
    assert _validate(value, experiences=experiences).valid


def test_evidence_aliases_are_deterministic_and_ordered_by_rollout_then_step():
    rollouts = list(_group())
    rollouts.reverse()
    for rollout in rollouts:
        rollout["actions"].reverse()
    first = build_provenance_alias_context(tuple(rollouts))
    second = build_provenance_alias_context(tuple(copy.deepcopy(rollouts)))
    assert first == second
    assert first["evidence_aliases"] == {
        "E001": {"source_id": "step_001_airline_1_rollout_01", "step_id": 1},
        "E002": {"source_id": "step_001_airline_1_rollout_01", "step_id": 2},
        "E003": {"source_id": "step_001_airline_1_rollout_02", "step_id": 1},
        "E004": {"source_id": "step_001_airline_1_rollout_02", "step_id": 2},
        "E005": {"source_id": "step_001_airline_1_rollout_03", "step_id": 1},
        "E006": {"source_id": "step_001_airline_1_rollout_03", "step_id": 2},
    }
    assert [
        step["evidence_ref"]
        for rollout in first["rollouts"] for step in sorted(
            rollout["actions"], key=lambda item: item["step"],
        )
    ] == ["E001", "E002", "E003", "E004", "E005", "E006"]


def test_evidence_alias_resolution_returns_exact_canonical_source_and_integer_step():
    semantic = _semantic()
    semantic["behavioral_mechanism"]["support_evidence_refs"] = ["E002", "E006"]
    resolved = resolve_semantic_provenance(
        semantic, build_provenance_alias_context(_group()),
    )
    assert resolved["support_evidence_refs"] == [
        {"alias": "E002", "source_id": "step_001_airline_1_rollout_01", "step_ids": [2]},
        {"alias": "E006", "source_id": "step_001_airline_1_rollout_03", "step_ids": [2]},
    ]


@pytest.mark.parametrize("alias", ["E999", "E01", "e002", "rollout 1 step 2"])
def test_invalid_evidence_aliases_fail_closed(alias):
    value = _semantic(evidence_ref=alias)
    assert "SUPPORT_EVIDENCE_ALIAS_NOT_FOUND" in _validate(value).validation_errors


def test_policy_alias_is_deduplicated_and_resolves_byte_exact():
    policy_id = "policy-very-long-byte-exact-identifier"
    experiences = tuple(
        _experience("airline", "1", index, policy_id=policy_id)
        for index in (3, 1, 2)
    )
    context = build_provenance_alias_context(experiences)
    assert context["policy_aliases"] == {"P001": {"policy_id": policy_id}}
    assert all(
        rollout["process_feedback"]["violated_policies"][0]["policy_ref"] == "P001"
        for rollout in context["rollouts"]
    )
    semantic = _semantic(policy_refs=["P001"])
    resolved = resolve_semantic_provenance(semantic, context)
    assert resolved["repair_policy_refs"] == [{"alias": "P001", "policy_id": policy_id}]


def test_distinct_policy_and_template_ids_receive_distinct_stable_aliases():
    experiences = [
        _experience("airline", "1", index, policy_id="policy-instance-byte-exact")
        for index in (1, 2, 3)
    ]
    violation = experiences[0]["process_feedback"]["violated_policies"][0]
    violation["policy_id"] = "policy-instance-byte-exact"
    violation["policy_template_id"] = "policy-template-byte-exact"

    context = build_provenance_alias_context(tuple(experiences))

    assert context["policy_aliases"] == {
        "P001": {"policy_id": "policy-instance-byte-exact"},
        "P002": {"policy_id": "policy-template-byte-exact"},
    }
    annotated = context["rollouts"][0]["process_feedback"]["violated_policies"][0]
    assert annotated["policy_ref"] == "P001"
    assert annotated["policy_refs"] == ["P001", "P002"]
    resolved = resolve_semantic_provenance(
        _semantic(policy_refs=["P002", "P001"]), context,
    )
    assert resolved["repair_policy_refs"] == [
        {"alias": "P002", "policy_id": "policy-template-byte-exact"},
        {"alias": "P001", "policy_id": "policy-instance-byte-exact"},
    ]


@pytest.mark.parametrize("alias", ["P999", "policy_1", "P1"])
def test_invalid_policy_aliases_fail_closed(alias):
    experiences = tuple(
        _experience("airline", "1", index, policy_id="policy_1")
        for index in (1, 2, 3)
    )
    value = _semantic(policy_refs=[alias])
    assert "POLICY_ALIAS_NOT_FOUND" in _validate(
        value, experiences=experiences,
    ).validation_errors


def test_prompt_presentation_marks_steps_and_violations_without_mutating_rollouts():
    experiences = tuple(
        _experience("airline", "1", index, policy_id="policy_1")
        for index in (1, 2, 3)
    )
    original = copy.deepcopy(experiences)
    request = replace(_request(), rollouts=experiences)
    _, user = diagnosis_v14.build_diagnosis_prompts(request)
    assert '"evidence_ref": "E002"' in user
    assert '"policy_ref": "P001"' in user
    assert '"available_evidence_refs"' in user
    assert '"available_policy_refs"' in user
    assert experiences == original


def test_json_schema_is_strict_at_every_object_layer_and_rejects_known_typos():
    schema = diagnosis_v14.SEMANTIC_DIAGNOSIS_JSON_SCHEMA
    assert schema["additionalProperties"] is False
    assert set(schema["properties"]) == contract_v14.SEMANTIC_DIAGNOSIS_FIELDS
    assert set(schema["required"]) == contract_v14.SEMANTIC_DIAGNOSIS_FIELDS
    for field in (
        "behavioral_mechanism", "feasibility", "skill_coverage",
        "outcome_relation", "target_behavior",
    ):
        assert schema["properties"][field]["additionalProperties"] is False
    assert "target_behavor" not in schema["properties"]
    assert "edit_intnt" not in schema["properties"]
    assert "task_saccess" not in schema["properties"]["outcome_relation"]["properties"]
    assert "explantion" not in schema["properties"]["feasibility"]["properties"]
    outcome_enum = schema["properties"]["outcome_relation"]["properties"]["compliance"]["enum"]
    assert "supports" in outcome_enum
    assert "suports" not in outcome_enum
    assert schema["properties"]["behavioral_mechanism"]["properties"][
        "support_evidence_refs"
    ]["items"]["pattern"] == "^E[0-9]{3}$"
    assert schema["properties"]["repair_policy_refs"]["items"]["pattern"] == "^P[0-9]{3}$"


def test_old_provenance_copy_shapes_are_outside_new_semantic_authority():
    value = _semantic()
    value["behavioral_mechanism"]["support_evidence_refs"] = [{
        "source_id": "copied-source", "step_ids": [2],
    }]
    value["repair_policy_ids"] = ["copied-long-policy-id"]
    validation = _validate(value)
    assert "INVALID_SUPPORT_EVIDENCE_REF" in validation.validation_errors
    assert "INVALID_SEMANTIC_DIAGNOSIS_FIELDS" in validation.validation_errors


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
    assert "Return only one JSON object" in prompt
    assert set(diagnosis_v14.SEMANTIC_DIAGNOSIS_TEMPLATE) == (
        contract_v14.SEMANTIC_DIAGNOSIS_FIELDS
    )
    assert diagnosis_v14.LEARNER_MODEL == "openai/deepseek-v4-pro"
    assert diagnosis_v14.EMPTY_RESPONSE_RETRIES == 2


def test_bare_json_and_null_stopping_boundary_are_narrowly_normalized_once():
    value = _semantic()
    value["target_behavior"]["stopping_boundary"] = None
    calls = []

    def learner(model, system, user, **kwargs):
        calls.append((model, system, user, kwargs))
        return json.dumps(value), model, None

    response = diagnosis_v14.call_diagnosis(_request(), learner_call=learner)
    validation = contract_v14.parse_and_validate_diagnosis(
        "diagnosis_001", response, experiences=_group(), skill_sections=SECTIONS,
    )
    assert len(calls) == 1
    assert response.startswith("{")
    assert validation.valid
    assert validation.structured_output["target_behavior"]["stopping_boundary"] == ""
    assert validation.structured_output_mode == "json_schema"
    assert calls[0][3]["response_format"]["type"] == "json_schema"


def test_invalid_semantic_output_gets_no_second_repair_call():
    value = _semantic()
    value["outcome_relation"]["compliance"] = "conflicting"
    calls = []

    def learner(model, system, user, **kwargs):
        calls.append((model, system, user, kwargs))
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


def test_call_learner_adds_optional_response_format_without_affecting_default_callers(
    monkeypatch,
):
    captured = []

    class Completions:
        def create(self, **request):
            captured.append(request)
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content="{}"))],
                usage=None,
            )

    client = SimpleNamespace(chat=SimpleNamespace(completions=Completions()))
    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(
        OpenAI=lambda **kwargs: client,
    ))
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://example.test")
    generate_skill.call_learner("openai/model", "system", "user")
    generate_skill.call_learner(
        "openai/model", "system", "user",
        response_format=diagnosis_v14.SEMANTIC_DIAGNOSIS_RESPONSE_FORMAT,
    )
    assert "response_format" not in captured[0]
    assert captured[1]["response_format"]["type"] == "json_schema"
    assert captured[1]["response_format"]["json_schema"]["strict"] is True


def test_structured_capability_fallback_is_narrow_and_cached():
    value = json.dumps(_semantic())
    calls = []

    def learner(model, system, user, **kwargs):
        calls.append(kwargs.get("response_format"))
        if kwargs.get("response_format") is not None:
            raise RuntimeError("unsupported json_schema response_format")
        return value, model, None

    first = diagnosis_v14.call_diagnosis(_request(), learner_call=learner)
    second = diagnosis_v14.call_diagnosis(_request(), learner_call=learner)
    assert calls == [diagnosis_v14.SEMANTIC_DIAGNOSIS_RESPONSE_FORMAT, None, None]
    assert first.structured_output_mode == "prompt_fallback"
    assert second.structured_output_mode == "prompt_fallback"
    assert first.structured_output_fallback_reason == "unsupported json_schema response_format"
    assert diagnosis_v14._STRUCTURED_OUTPUT_CAPABILITY == "json_schema_unsupported"


@pytest.mark.parametrize("message", ["524 timeout", "request timeout", "rate limit", "generic 500"])
def test_network_and_service_errors_do_not_trigger_prompt_fallback(message):
    calls = []

    def learner(model, system, user, **kwargs):
        calls.append(kwargs.get("response_format"))
        raise RuntimeError(message)

    with pytest.raises(RuntimeError, match=message):
        diagnosis_v14.call_diagnosis(_request(), learner_call=learner)
    assert calls == [diagnosis_v14.SEMANTIC_DIAGNOSIS_RESPONSE_FORMAT]
    assert diagnosis_v14._STRUCTURED_OUTPUT_CAPABILITY == "unknown"


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
    ))


def _no_update_diagnoser(request) -> str:
    return _tag(_semantic(
        evidence_status="insufficient", task_success="insufficient",
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


def test_proposal_signal_uses_only_resolved_canonical_evidence_and_policy_ids():
    policy_id = "canonical-policy-id-that-the-model-never-copies"
    evidence = tuple(
        _experience("airline", "1", index, policy_id=policy_id)
        for index in (1, 2, 3)
    )
    context = ProposalContext("candidate_001", _parent_skill(), evidence)

    def diagnoser(request):
        return json.dumps(_semantic(policy_refs=["P001"]))

    def editor(request):
        edit = _edit([request.eligible_diagnoses[0]["patch_id"]])
        edit["source_ids"] = ["step_001_airline_1_rollout_01"]
        edit["repair_policy_ids"] = [policy_id]
        return "<CANONICAL_EDITS_JSON>" + json.dumps([edit]) + "</CANONICAL_EDITS_JSON>"

    decision = proposal_v14.MultiRolloutDiagnosisProposalOperator().propose(
        context, diagnoser, editor, domain_contexts=_domain_contexts(),
    )
    patch = decision.raw_patches[0]
    assert patch["operation"] == "add"
    assert patch["update_axis"] == "task_success"
    assert patch["source_ids"] == ["step_001_airline_1_rollout_01"]
    assert patch["repair_policy_ids"] == [policy_id]
    assert patch["support_evidence_refs"] == [{
        "alias": "E002", "source_id": "step_001_airline_1_rollout_01",
        "step_ids": [2],
    }]
    artifact = decision.diagnoses[0]
    assert artifact["semantic"]["structured_output"]["repair_policy_refs"] == ["P001"]
    assert artifact["resolved_provenance"]["repair_policy_refs"] == [{
        "alias": "P001", "policy_id": policy_id,
    }]


def test_validation_artifact_separates_semantic_and_compiler_authority():
    validation = _validate(_semantic())
    provenance = resolve_semantic_provenance(
        validation.structured_output, build_provenance_alias_context(_group()),
    )
    compiled, trace = compile_semantic_diagnosis(validation.structured_output, SECTIONS)
    artifact = replace(
        validation, resolved_provenance=provenance,
        compiled_decision=compiled, compiler_trace=trace,
    ).as_dict()
    assert set(artifact) == {
        "diagnosis_id", "source_ids", "semantic", "resolved_provenance",
        "compiled_decision", "compiler_trace", "structured_output_mode",
        "structured_output_fallback_reason",
    }
    assert artifact["semantic"]["structured_output"] == validation.structured_output
    assert artifact["semantic"]["validation"] == {"valid": True, "errors": []}
    assert artifact["compiled_decision"]["root_cause"] == "skill_issue"
    assert artifact["compiler_trace"]["supported_axes"] == ["task_success"]
    assert artifact["resolved_provenance"]["support_evidence_refs"] == [{
        "alias": "E002", "source_id": "step_001_airline_1_rollout_01",
        "step_ids": [2],
    }]
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

from __future__ import annotations

import ast
import copy
import json
import re
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
from src.skill_evolution.autonomous_gse_v03_proposal import EditorRequest, ProposalContext
from src.skill_evolution.diagnosis_compiler_v14 import compile_semantic_diagnosis
from src.skill_evolution.diagnosis_provenance_v14 import (
    build_provenance_alias_context, resolve_semantic_provenance,
)
from src.skill_evolution.autonomous_gse_v14_orchestrator import canonical_skill_text
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


def test_duplicate_aliases_resolve_once_in_first_seen_order():
    context = build_provenance_alias_context(tuple(
        _experience("airline", "1", index, policy_id="policy_1")
        for index in (1, 2, 3)
    ))
    semantic = _semantic(policy_refs=["P001", "P001"])
    semantic["behavioral_mechanism"]["support_evidence_refs"] = [
        "E002", "E001", "E002",
    ]
    semantic["behavioral_mechanism"]["counterevidence_refs"] = ["E003", "E003"]

    resolved = resolve_semantic_provenance(semantic, context)

    assert [ref["alias"] for ref in resolved["support_evidence_refs"]] == [
        "E002", "E001",
    ]
    assert [ref["alias"] for ref in resolved["counterevidence_refs"]] == ["E003"]
    assert [ref["alias"] for ref in resolved["repair_policy_refs"]] == ["P001"]


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
    ]["maxItems"] == 0
    assert schema["properties"]["repair_policy_refs"]["maxItems"] == 0


def test_dynamic_schema_enumerates_only_current_task_aliases_without_unique_items():
    response_format = diagnosis_v14.build_semantic_diagnosis_response_format({
        "evidence_aliases": {"E001": {}, "E002": {}},
        "policy_aliases": {"P001": {}},
    })
    schema = response_format["json_schema"]["schema"]
    mechanism = schema["properties"]["behavioral_mechanism"]["properties"]
    for field in ("support_evidence_refs", "counterevidence_refs"):
        assert mechanism[field] == {
            "type": "array",
            "items": {"type": "string", "enum": ["E001", "E002"]},
        }
        assert "E999" not in mechanism[field]["items"]["enum"]
    assert schema["properties"]["repair_policy_refs"] == {
        "type": "array",
        "items": {"type": "string", "enum": ["P001"]},
    }
    assert "uniqueItems" not in json.dumps(schema)


def test_dynamic_schema_without_policy_aliases_only_allows_an_empty_array():
    response_format = diagnosis_v14.build_semantic_diagnosis_response_format({
        "evidence_aliases": {"E001": {}},
        "policy_aliases": {},
    })
    policy_schema = response_format["json_schema"]["schema"]["properties"][
        "repair_policy_refs"
    ]
    assert policy_schema == {"type": "array", "maxItems": 0}


def test_semantic_template_does_not_suggest_task_specific_aliases():
    mechanism = diagnosis_v14.SEMANTIC_DIAGNOSIS_TEMPLATE["behavioral_mechanism"]
    assert mechanism["support_evidence_refs"] == []
    assert mechanism["counterevidence_refs"] == []
    assert diagnosis_v14.SEMANTIC_DIAGNOSIS_TEMPLATE["repair_policy_refs"] == []
    serialized = json.dumps(diagnosis_v14.SEMANTIC_DIAGNOSIS_TEMPLATE)
    assert '["E001"]' not in serialized
    assert '["P001"]' not in serialized


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
        "task requirements, the original Policy, available tool contracts",
        "one candidate problematic Agent-controlled behavioral mechanism",
        "Falsify the candidate mechanism against all three rollouts",
        "Only after falsification and the separate feasibility assessment",
        "contrastive_support", "recurrent_support",
        "annotated Parent Skill", "Task Success and Compliance outcome relation independently",
    ):
        assert principle in prompt
    reasoning_markers = (
        "1. Analyze Agent-controlled behavior before outcomes",
        "2. Identify one candidate problematic Agent-controlled behavioral mechanism",
        "3. Compare all three rollouts at the relevant predicate and decision opportunity",
        "4. Falsify the candidate mechanism",
        "5. Evaluate feasibility of a correct Agent handling path",
        "6. Only after falsification and the separate feasibility assessment",
        "7. Compare the mechanism with the annotated Parent Skill",
        "8. Judge Task Success and Compliance outcome relation independently",
        "9. Produce target_behavior and edit_intent",
    )
    assert list(map(prompt.index, reasoning_markers)) == sorted(
        map(prompt.index, reasoning_markers),
    )
    assert "Return only one JSON object" in prompt
    assert set(diagnosis_v14.SEMANTIC_DIAGNOSIS_TEMPLATE) == (
        contract_v14.SEMANTIC_DIAGNOSIS_FIELDS
    )
    assert diagnosis_v14.LEARNER_MODEL == "openai/deepseek-v4-pro"
    assert diagnosis_v14.EMPTY_RESPONSE_RETRIES == 2


def test_semantic_template_values_are_not_prompt_defaults():
    prompt = diagnosis_v14.DIAGNOSIS_SYSTEM_PROMPT
    assert (
        "The values shown in SEMANTIC_DIAGNOSIS_TEMPLATE are structural placeholders, "
        "not semantic defaults"
    ) in prompt
    assert "Do not copy a template value merely because no stronger signal was found" in prompt
    assert (
        'feasibility.status = "uncertain" in the template must not be copied unless the '
        "definition of uncertain is actually satisfied"
    ) in prompt
    assert (
        "If no problematic mechanism is established but the observed rollouts demonstrate "
        "a correct task-satisfying, Policy-permitted, tool-supported handling path, "
        'feasibility should normally be "feasible", not "uncertain"'
    ) in prompt
    assert diagnosis_v14.SEMANTIC_DIAGNOSIS_TEMPLATE["feasibility"]["status"] == "uncertain"


def test_diagnosis_012_direction_treats_violation_as_support_for_compliance_repair():
    prompt = diagnosis_v14.DIAGNOSIS_SYSTEM_PROMPT
    assert (
        "problematic behavior occurs in a violating rollout while the correct "
        "alternative is compliant -> compliance = supports"
    ) in prompt
    assert (
        'Do not use "contradicts" merely because the task failed or because '
        "the trajectory violated Policy"
    ) in prompt


def test_outcome_relation_defines_contradicts_as_counterevidence_to_attribution():
    prompt = diagnosis_v14.DIAGNOSIS_SYSTEM_PROMPT
    assert (
        "supports: The observed outcome supports the causal claim that the identified "
        "problematic behavioral mechanism should be repaired on this axis"
    ) in prompt
    assert (
        "contradicts: The observed outcome provides counterevidence against that "
        "repair attribution"
    ) in prompt
    assert (
        "A recurrent problematic behavior contributes to task failure -> "
        "task_success = supports"
    ) in prompt


def test_diagnosis_008_stable_correct_behavior_cannot_become_missing_skill_update():
    prompt = diagnosis_v14.DIAGNOSIS_SYSTEM_PROMPT
    assert (
        "contrastive_support / recurrent_support must support a problematic "
        "behavioral mechanism or repair hypothesis, not merely a stable behavior pattern"
    ) in prompt
    assert (
        "If the Agent already executes the target behavior correctly across all relevant "
        "rollouts, do not create an update merely because the Parent Skill does not "
        "explicitly encode that behavior"
    ) in prompt
    assert "Stable correct behavior is not itself a Skill issue" in prompt
    assert (
        "When correct behavior is observed under a matched relevant predicate and decision "
        "opportunity, it may serve as the correct side of contrastive_support"
    ) in prompt
    assert (
        "Correct behavior is counterevidence only when it directly undermines the proposed "
        "causal mechanism"
    ) in prompt


def test_compliance_label_alone_cannot_override_policy_grounded_analysis():
    prompt = diagnosis_v14.DIAGNOSIS_SYSTEM_PROMPT
    assert "Task Success and Compliance labels are observational evidence" in prompt
    assert "The original domain Policy is the normative authority" in prompt
    assert (
        "If a Compliance label appears inconsistent with Policy/tool-grounded behavior "
        "analysis, do not let the label alone create a Skill update"
    ) in prompt


def test_feasibility_prompt_defines_correct_handling_independently_from_mechanism():
    prompt = diagnosis_v14.DIAGNOSIS_SYSTEM_PROMPT
    for handling in (
        "offering a permitted alternative",
        "correctly refusing a prohibited request",
        "escalating when Policy requires it",
    ):
        assert handling in prompt
    assert (
        "The user's preferred action being prohibited or unavailable does not by itself "
        "make the situation infeasible"
    ) in prompt
    assert (
        "A correct handling path must be both task-satisfying and Policy-permitted"
    ) in prompt
    assert (
        "A refusal counts as a feasible handling path only when refusal is itself an "
        "acceptable resolution of the task"
    ) in prompt
    assert (
        "A merely Policy-compliant refusal does not make an otherwise task-infeasible "
        "request feasible"
    ) in prompt
    assert "Do not use uncertain merely because no problematic mechanism was found" in prompt
    assert (
        "Feasibility may constrain whether a repair is actionable, but must not create "
        "mechanism evidence"
    ) in prompt


def test_d006_like_matched_correct_behavior_is_contrast_not_counterevidence():
    prompt = diagnosis_v14.DIAGNOSIS_SYSTEM_PROMPT
    assert (
        "At least one rollout exhibits the problematic behavior and at least one matched "
        "rollout exhibits the correct alternative under the same relevant predicate and "
        "decision opportunity"
    ) in prompt
    assert "The matched correct behavior is supporting contrastive evidence, not counterevidence" in prompt


def test_d013_like_comparable_wrong_and_correct_choices_prefer_contrastive_support():
    prompt = diagnosis_v14.DIAGNOSIS_SYSTEM_PROMPT
    assert (
        "If matched problematic and correct behaviors are both observed under comparable "
        "decision opportunities, prefer contrastive_support over recurrent_support"
    ) in prompt
    assert (
        "A matched correct alternative behavior is not by itself counterevidence; it may "
        "be exactly the contrast required for contrastive_support"
    ) in prompt


def test_d016_like_missing_decision_opportunity_cannot_count_as_recurrence():
    prompt = diagnosis_v14.DIAGNOSIS_SYSTEM_PROMPT
    assert "Different decision opportunities do not count toward recurrence" in prompt
    assert (
        "A rollout without the relevant decision opportunity is neither support nor "
        "counterevidence for that mechanism"
    ) in prompt


def test_true_counterevidence_requires_direct_causal_undermining():
    prompt = diagnosis_v14.DIAGNOSIS_SYSTEM_PROMPT
    assert "Substantive evidence directly undermines the proposed causal mechanism" in prompt
    assert "the same claimed problematic behavior without the predicted adverse effect" in prompt


def test_falsification_separates_insufficient_from_conflicting_evidence():
    prompt = diagnosis_v14.DIAGNOSIS_SYSTEM_PROMPT
    assert (
        "If falsification fully defeats the candidate mechanism and no substantive support "
        "remains, treat this as evidence for an insufficient classification at Step 6"
    ) in prompt
    assert (
        "If substantive support remains, but unreconciled counterevidence directly "
        "undermines the proposed causal mechanism, treat this as evidence for a "
        "conflicting classification at Step 6"
    ) in prompt
    assert "Do not assign the final evidence_status until Step 6" in prompt
    assert (
        "A rollout without the relevant decision opportunity is neither support nor "
        "counterevidence for that mechanism"
    ) in prompt


def test_evidence_refs_require_disjoint_factually_grounded_steps_and_prior_context():
    prompt = diagnosis_v14.DIAGNOSIS_SYSTEM_PROMPT
    assert "support_evidence_refs and counterevidence_refs must be disjoint" in prompt
    assert "verify that the claimed fact is actually supported by that step" in prompt
    assert (
        "Do not infer that required information was absent merely because it was not "
        "repeated immediately before the action"
    ) in prompt


def test_d019_like_recoverable_detour_does_not_support_task_success_update():
    prompt = diagnosis_v14.DIAGNOSIS_SYSTEM_PROMPT
    assert "A locally suboptimal behavior does not by itself imply task_success = supports" in prompt
    assert (
        "extra dialogue, user correction, inefficiency, a recoverable detour, or delayed "
        "completion, use task_success = insufficient"
    ) in prompt
    assert "any optimization axis beyond Task Success and Compliance" in prompt


def test_diagnosis_requires_semantic_confirmation_not_lexical_matching():
    prompt = diagnosis_v14.DIAGNOSIS_SYSTEM_PROMPT
    assert (
        "Do not convert a semantic authorization, confirmation, consent, or intent "
        "condition into lexical substring matching"
    ) in prompt
    assert (
        "Confirmation must semantically and unambiguously authorize the complete listed "
        "action details and intended scope"
    ) in prompt


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
        response_format=diagnosis_v14.build_semantic_diagnosis_response_format(
            build_provenance_alias_context(_group()),
        ),
    )
    generate_skill.call_learner(
        "openai/model", "system", "user", max_completion_tokens=16000,
    )
    assert "response_format" not in captured[0]
    assert captured[0]["max_completion_tokens"] == generate_skill.MAX_COMPLETION_TOKENS
    assert captured[1]["response_format"]["type"] == "json_schema"
    assert captured[1]["response_format"]["json_schema"]["strict"] is True
    assert captured[2]["max_completion_tokens"] == 16000


def test_call_learner_reports_completion_transport_observability(monkeypatch):
    class Usage:
        def model_dump(self):
            return {
                "prompt_tokens": 123,
                "completion_tokens": 8000,
                "completion_tokens_details": {"reasoning_tokens": 3557},
            }

    class Completions:
        def create(self, **request):
            return SimpleNamespace(
                choices=[SimpleNamespace(
                    message=SimpleNamespace(content="{}"), finish_reason="length",
                )],
                usage=Usage(),
            )

    client = SimpleNamespace(chat=SimpleNamespace(completions=Completions()))
    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(
        OpenAI=lambda **kwargs: client,
    ))
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://example.test")

    _, _, usage = generate_skill.call_learner(
        "openai/model", "system", "user", max_completion_tokens=16000,
    )

    assert usage["finish_reason"] == "length"
    assert usage["prompt_tokens"] == 123
    assert usage["completion_tokens"] == 8000
    assert usage["reasoning_tokens"] == 3557
    assert usage["max_completion_tokens"] == 16000


def test_structured_capability_fallback_is_narrow_and_cached():
    value = json.dumps(_semantic())
    calls = []
    expected_format = diagnosis_v14.build_semantic_diagnosis_response_format(
        build_provenance_alias_context(_group()),
    )

    def learner(model, system, user, **kwargs):
        calls.append(kwargs.get("response_format"))
        if kwargs.get("response_format") is not None:
            raise RuntimeError("unsupported json_schema response_format")
        return value, model, None

    first = diagnosis_v14.call_diagnosis(_request(), learner_call=learner)
    second = diagnosis_v14.call_diagnosis(_request(), learner_call=learner)
    assert calls == [expected_format, None, None]
    assert first.structured_output_mode == "prompt_fallback"
    assert second.structured_output_mode == "prompt_fallback"
    assert first.structured_output_fallback_reason == "unsupported json_schema response_format"
    assert diagnosis_v14._STRUCTURED_OUTPUT_CAPABILITY == "json_schema_unsupported"


def test_invalidparameter_structured_output_error_triggers_capability_fallback():
    value = json.dumps(_semantic())
    calls = []

    def learner(model, system, user, **kwargs):
        calls.append(kwargs.get("response_format"))
        if kwargs.get("response_format") is not None:
            raise RuntimeError(
                "InvalidParameter: Format error: response_format.json_schema.schema",
            )
        return value, model, None

    response = diagnosis_v14.call_diagnosis(_request(), learner_call=learner)

    assert len(calls) == 2
    assert calls[0]["type"] == "json_schema"
    assert calls[1] is None
    assert response.structured_output_mode == "prompt_fallback"


@pytest.mark.parametrize("message", ["524 timeout", "request timeout", "rate limit", "generic 500"])
def test_network_and_service_errors_do_not_trigger_prompt_fallback(message):
    calls = []
    expected_format = diagnosis_v14.build_semantic_diagnosis_response_format(
        build_provenance_alias_context(_group()),
    )

    def learner(model, system, user, **kwargs):
        calls.append(kwargs.get("response_format"))
        raise RuntimeError(message)

    with pytest.raises(RuntimeError, match=message):
        diagnosis_v14.call_diagnosis(_request(), learner_call=learner)
    assert calls == [expected_format]
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


@pytest.mark.parametrize(
    ("evidence_status", "feasibility", "root_cause", "reason"),
    [
        ("insufficient", "uncertain", None, "INSUFFICIENT_MECHANISM_EVIDENCE"),
        ("insufficient", "feasible", None, "INSUFFICIENT_MECHANISM_EVIDENCE"),
        ("insufficient", "infeasible", "external_issue",
         "INFEASIBLE_TASK_POLICY_TOOL_COMBINATION"),
        ("contrastive_support", "infeasible", "external_issue",
         "INFEASIBLE_TASK_POLICY_TOOL_COMBINATION"),
        ("contrastive_support", "uncertain", "uncertain", "FEASIBILITY_UNCERTAIN"),
        ("conflicting", "feasible", "uncertain", "CONFLICTING_MECHANISM_EVIDENCE"),
        ("conflicting", "uncertain", "uncertain", "CONFLICTING_MECHANISM_EVIDENCE"),
    ],
)
def test_compiler_evidence_feasibility_precedence_matrix(
    evidence_status, feasibility, root_cause, reason,
):
    value = _semantic(evidence_status=evidence_status, feasibility=feasibility)
    decision, _ = compile_semantic_diagnosis(value, SECTIONS)
    assert decision["root_cause"] == root_cause
    assert decision["reason"] == reason
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


def _replay_editor(*, scoped: bool):
    calls = []

    def editor(request):
        calls.append(request)
        patch_ids = [item["patch_id"] for item in request.eligible_diagnoses]
        edit = _edit(patch_ids)
        domains = {item["task_identity"]["domain"] for item in request.eligible_diagnoses}
        if scoped and len(domains) == 1:
            domain = next(iter(domains))
            prefix = proposal_v14.DOMAIN_SCOPE_PREFIX[domain]
            edit["text"] = f"{prefix} preserve the supported decision boundary."
            edit["verification_target"]["trigger_condition"] = (
                f"{prefix} when the supported decision opportunity occurs"
            )
        return "<CANONICAL_EDITS_JSON>" + json.dumps([edit]) + "</CANONICAL_EDITS_JSON>"

    return editor, calls


def _editor_replay_source(tmp_path: Path, *, eligible_ids: set[str]):
    campaign = json.loads(CAMPAIGN.read_text(encoding="utf-8"))
    batch_map = json.loads(
        (ROOT / campaign["evolution"]["batch_map"]).read_text(encoding="utf-8")
    )
    artifact_root = tmp_path / "formal"
    batch = batch_map["batches"][0]
    parent = {
        "skill_id": "S0", "skill_version": "S0",
        "skill_path": campaign["initial_parent"]["path"],
    }
    evidence = []
    seeds = runtime_v14.derive_monitor_rollout_seeds(campaign["campaign_seed"])
    rollout_root = artifact_root / "rollouts/train/step_01_parent"
    rollout_root.mkdir(parents=True)
    for tagged in batch["task_ids"]:
        domain, task_id = tagged.split(":", 1)
        for rollout_index, rollout_seed in enumerate(seeds, start=1):
            governed = _experience(domain, task_id, rollout_index)
            governed["source_id"] = (
                f"step_01_parent_{domain}_{task_id}_rollout_{rollout_index:02d}"
            )
            governed["rollout_seed"] = rollout_seed
            evidence.append(copy.deepcopy(governed))
            artifact = {
                "domain": domain, "task_id": task_id, "phase": "train",
                "skill_version": "S0", "rollout_index": rollout_index,
                "rollout_seed": rollout_seed, "state": governed["state"],
                "governed_evidence": governed,
                "provenance": {
                    "skill_id": "S0", "skill_path": parent["skill_path"],
                },
            }
            path = rollout_root / f"{domain}_{task_id}_rollout_{rollout_index:02d}.json"
            path.write_text(json.dumps(artifact), encoding="utf-8")

    def diagnoser(request):
        semantic = _semantic(
            evidence_status=(
                "recurrent_support"
                if request.diagnosis_id in eligible_ids else "insufficient"
            ),
            task_success=(
                "supports" if request.diagnosis_id in eligible_ids else "insufficient"
            ),
        )
        return diagnosis_v14.DiagnosisResponse(_tag(semantic), "json_schema")

    source_editor, _ = _replay_editor(scoped=True)
    decision = runtime_v14.propose_candidate(
        ProposalContext("candidate_step_01", _parent_skill(), tuple(evidence)),
        campaign=campaign, batch_map=batch_map, step=1,
        domain_contexts=runtime_v14.load_authoritative_domain_contexts(
            ROOT / campaign["benchmark"]["path"],
        ),
        diagnoser=diagnoser, editor=source_editor,
    )
    assert decision.proposal_status == "CANDIDATE"
    step_root = artifact_root / "steps/step_01"
    step_root.mkdir(parents=True)
    source_proposal = {
        "batch_id": batch["batch_id"], "parent_skill": parent,
        "proposal_status": decision.proposal_status,
        "proposal_reason": decision.proposal_reason,
        "diagnoses": decision.diagnoses,
        "canonical_edits": decision.canonical_edits,
        "candidate_skill": decision.candidate_skill,
    }
    proposal_path = step_root / "proposal.json"
    candidate_path = step_root / "candidate_skill.md"
    proposal_path.write_text(json.dumps(source_proposal), encoding="utf-8")
    candidate_path.write_text(
        canonical_skill_text(decision.candidate_skill), encoding="utf-8",
    )
    return campaign, batch_map, artifact_root, proposal_path, candidate_path


def _guarded_domain_edit(
    source_domains: list[str], *, text: str, trigger_condition: str,
) -> dict:
    patch_ids = [f"patch_{index}" for index in range(len(source_domains))]
    raw_patches = tuple({
        "patch_id": patch_id,
        "task_identity": {"domain": domain, "task_id": str(index)},
        "operation": "add", "section": "Form entry and verification",
        "target_rule_id": "", "repair_policy_ids": [],
    } for index, (patch_id, domain) in enumerate(
        zip(patch_ids, source_domains, strict=True), start=1,
    ))
    edit = _edit(patch_ids)
    edit["text"] = text
    edit["verification_target"]["trigger_condition"] = trigger_condition
    response = "<CANONICAL_EDITS_JSON>" + json.dumps([edit]) + "</CANONICAL_EDITS_JSON>"
    guarded = proposal_v14._guard_editor_response(
        response,
        EditorRequest("candidate_001", _parent_skill(), raw_patches),
        set(SECTIONS),
    )
    return json.loads(
        guarded.removeprefix("<CANONICAL_EDITS_JSON>").removesuffix(
            "</CANONICAL_EDITS_JSON>",
        )
    )[0]


@pytest.mark.parametrize("domain", ["airline", "retail"])
def test_single_domain_generic_editor_rule_fails_closed(domain):
    edit = _guarded_domain_edit(
        [domain],
        text="When the user's request cannot be handled, transfer to a human agent.",
        trigger_condition="When the request cannot be handled.",
    )
    assert edit["v13_validation_error"] == "DOMAIN_SCOPE_LEAKAGE"
    assert edit["derived_from_patch_ids"] == []


def test_single_domain_scoped_text_with_generic_verification_target_passes():
    edit = _guarded_domain_edit(
        ["airline"],
        text="For airline requests, transfer when the request cannot be handled.",
        trigger_condition="When the request cannot be handled.",
    )
    assert "v13_validation_error" not in edit
    assert edit["derived_from_patch_ids"] == ["patch_0"]


@pytest.mark.parametrize(
    ("domain", "text", "trigger"),
    [
        ("airline", "For airline requests, preserve the supported boundary.",
         "When the decision opportunity occurs."),
        ("retail", "For retail requests, preserve the supported boundary.",
         "When the decision opportunity occurs."),
    ],
)
def test_single_domain_canonical_prefix_in_text_and_target_pass(domain, text, trigger):
    edit = _guarded_domain_edit([domain], text=text, trigger_condition=trigger)
    assert "v13_validation_error" not in edit
    assert edit["derived_from_patch_ids"] == ["patch_0"]


def test_domain_word_in_entity_role_is_not_a_scope_prefix():
    edit = _guarded_domain_edit(
        ["airline"],
        text="Verify whether the flight was cancelled by the airline.",
        trigger_condition="When evaluating cancellation status.",
    )
    assert edit["v13_validation_error"] == "DOMAIN_SCOPE_LEAKAGE"
    assert edit["derived_from_patch_ids"] == []


def test_single_domain_prefix_only_in_trigger_fails_closed():
    edit = _guarded_domain_edit(
        ["retail"],
        text="Before making a database update, obtain confirmation.",
        trigger_condition="For retail requests, before making a database update.",
    )
    assert edit["v13_validation_error"] == "DOMAIN_SCOPE_LEAKAGE"
    assert edit["derived_from_patch_ids"] == []


def test_wrong_domain_prefix_fails_closed():
    edit = _guarded_domain_edit(
        ["airline"],
        text="For retail requests, preserve the supported boundary.",
        trigger_condition="For retail requests, when the decision opportunity occurs.",
    )
    assert edit["v13_validation_error"] == "DOMAIN_SCOPE_LEAKAGE"
    assert edit["derived_from_patch_ids"] == []


def test_unknown_single_source_domain_fails_closed():
    edit = _guarded_domain_edit(
        ["unknown"],
        text="For unknown requests, preserve the supported boundary.",
        trigger_condition="For unknown requests, when the decision opportunity occurs.",
    )
    assert edit["v13_validation_error"] == "DOMAIN_SCOPE_LEAKAGE"
    assert edit["derived_from_patch_ids"] == []


def test_multi_domain_edit_does_not_require_explicit_domain_names():
    edit = _guarded_domain_edit(
        ["airline", "retail"],
        text="When the supported decision opportunity occurs, preserve its boundary.",
        trigger_condition="When the supported decision opportunity occurs.",
    )
    assert "v13_validation_error" not in edit
    assert edit["derived_from_patch_ids"] == ["patch_0", "patch_1"]


def test_proposal_consumes_compiled_decisions_and_preserves_editor_method():
    context = ProposalContext("candidate_001", _parent_skill(), _twenty_task_evidence())
    editor_requests = []

    def editor(request):
        editor_requests.append(request)
        return _merged_editor(request)

    decision = proposal_v14.MultiRolloutDiagnosisProposalOperator().propose(
        context, _update_diagnoser, editor, domain_contexts=_domain_contexts(),
    )
    assert decision.proposal_status == "CANDIDATE"
    assert decision.diagnosis_calls == 20
    assert decision.editor_calls == 1
    assert len(decision.eligible_diagnosis_ids) == 20
    assert all(item["compiled_decision"]["update_eligible"] for item in decision.diagnoses)
    assert decision.raw_patches[0]["operation"] == "add"
    assert len(editor_requests) == 1
    assert not hasattr(editor_requests[0], "domain_contexts")
    assert set(editor_requests[0].eligible_diagnoses[0]) == {
        "patch_id", "diagnosis_id", "task_identity", "operation", "section",
        "target_rule_id", "target_behavior", "behavioral_mechanism",
        "skill_coverage", "outcome_relation", "support_evidence_refs",
        "counterevidence_refs", "source_ids", "repair_policy_ids",
    }
    assert not {
        "objective", "description", "root_cause", "update_axis",
        "derived_from_diagnosis_ids",
    } & set(editor_requests[0].eligible_diagnoses[0])
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


def _strict_editor_result(edit):
    calls = []

    def learner(model, system, user, **kwargs):
        calls.append((model, system, user, kwargs))
        return json.dumps({"canonical_edits": [] if edit is None else [edit]}), model, {
            "finish_reason": "stop", "prompt_tokens": 100,
            "completion_tokens": 200, "reasoning_tokens": 50,
            "max_completion_tokens": editor_v14.EDITOR_MAX_COMPLETION_TOKENS,
        }

    def editor(request):
        return editor_v14.call_governed_editor(request, learner_call=learner)

    return editor, calls


def test_structured_editor_success_runs_existing_guard_and_builds_candidate(monkeypatch):
    evidence = tuple(_experience("airline", "1", index) for index in (1, 2, 3))
    edit = _edit(["diagnosis_001"])
    edit["text"] = "For airline requests, preserve the grounded decision predicate."
    edit["verification_target"]["trigger_condition"] = (
        "For airline requests, when the relevant decision opportunity occurs"
    )
    editor, calls = _strict_editor_result(edit)
    guard_calls = []
    original_guard = proposal_v14._guard_editor_response

    def guard(*args, **kwargs):
        guard_calls.append(1)
        return original_guard(*args, **kwargs)

    monkeypatch.setattr(proposal_v14, "_guard_editor_response", guard)
    decision = proposal_v14.MultiRolloutDiagnosisProposalOperator().propose(
        ProposalContext("candidate_001", _parent_skill(), evidence),
        _update_diagnoser, editor, domain_contexts=_domain_contexts(),
    )

    assert decision.proposal_status == "CANDIDATE"
    assert decision.editor_calls == 1
    assert len(calls) == 1
    assert len(guard_calls) == 1
    assert calls[0][3]["response_format"] == editor_v14.EDITOR_RESPONSE_FORMAT
    assert calls[0][3]["max_completion_tokens"] == 16000
    assert decision.editor_transport == {
        "finish_reason": "stop", "prompt_tokens": 100,
        "completion_tokens": 200, "reasoning_tokens": 50,
        "max_completion_tokens": 16000,
    }


def test_structured_editor_legal_empty_list_is_semantic_noop():
    evidence = tuple(_experience("airline", "1", index) for index in (1, 2, 3))
    editor, calls = _strict_editor_result(None)

    decision = proposal_v14.MultiRolloutDiagnosisProposalOperator().propose(
        ProposalContext("candidate_001", _parent_skill(), evidence),
        _update_diagnoser, editor, domain_contexts=_domain_contexts(),
    )

    assert decision.proposal_status == "NO_CANDIDATE"
    assert decision.proposal_reason["code"] == "EMPTY_EDITS"
    assert decision.editor_calls == 1
    assert len(calls) == 1


@pytest.mark.parametrize(
    ("response", "code"),
    [
        ("not json", "EDITOR_SCHEMA_CONTRACT_ERROR"),
        (json.dumps({"canonical_edits": [{"operation": "add"}]}),
         "EDITOR_SCHEMA_CONTRACT_ERROR"),
        ("", "EDITOR_EMPTY_RESPONSE"),
    ],
)
def test_structured_editor_contract_failure_raises_without_retry(response, code):
    calls = []

    def learner(*args, **kwargs):
        calls.append(kwargs)
        return response, "deepseek-v4-pro", {
            "finish_reason": "length", "prompt_tokens": 300,
            "completion_tokens": 8000, "reasoning_tokens": 5000,
            "max_completion_tokens": editor_v14.EDITOR_MAX_COMPLETION_TOKENS,
        }

    request = proposal_v14.DiagnosisEditorRequest(
        "candidate_001", _parent_skill(), ({"patch_id": "diagnosis_001"},),
    )
    with pytest.raises(proposal_v14.EditorContractError) as caught:
        editor_v14.call_governed_editor(request, learner_call=learner)

    assert caught.value.code == code
    assert caught.value.raw_response == response
    assert caught.value.structured_output_mode == "json_schema"
    assert caught.value.finish_reason == "length"
    assert caught.value.prompt_tokens == 300
    assert caught.value.completion_tokens == 8000
    assert caught.value.reasoning_tokens == 5000
    assert caught.value.max_completion_tokens == 16000
    assert len(calls) == 1


def test_structured_editor_transport_failure_raises_without_retry():
    calls = []

    def learner(*args, **kwargs):
        calls.append(kwargs)
        raise RuntimeError("structured transport unavailable")

    request = proposal_v14.DiagnosisEditorRequest(
        "candidate_001", _parent_skill(), ({"patch_id": "diagnosis_001"},),
    )
    with pytest.raises(proposal_v14.EditorContractError) as caught:
        editor_v14.call_governed_editor(request, learner_call=learner)

    assert caught.value.code == "EDITOR_STRUCTURED_OUTPUT_ERROR"
    assert caught.value.raw_response is None
    assert caught.value.structured_output_mode == "json_schema"
    assert caught.value.error_reason == "structured transport unavailable"
    assert len(calls) == 1


def test_editor_response_schema_is_strict_structure_only():
    response_format = editor_v14.EDITOR_RESPONSE_FORMAT
    schema = response_format["json_schema"]["schema"]
    edit = schema["properties"]["canonical_edits"]["items"]
    verification = edit["properties"]["verification_target"]

    assert response_format["type"] == "json_schema"
    assert response_format["json_schema"]["strict"] is True
    assert schema["additionalProperties"] is False
    assert edit["additionalProperties"] is False
    assert verification["additionalProperties"] is False
    assert set(schema["required"]) == {"canonical_edits"}
    assert set(edit["required"]) == {
        "derived_from_patch_ids", "operation", "section", "target_rule_id",
        "text", "reason", "source_ids", "repair_policy_ids",
        "verification_target",
    }
    assert set(verification["required"]) == {
        "problem", "trigger_condition", "expected_behavior",
    }


def test_editor_only_replay_exactly_reuses_diagnoses_and_preserves_source_artifacts(
    tmp_path, monkeypatch,
):
    eligible_ids = {f"diagnosis_{index:03d}" for index in range(1, 21)}
    campaign, batch_map, artifact_root, source_proposal_path, source_candidate_path = (
        _editor_replay_source(tmp_path, eligible_ids=eligible_ids)
    )
    source_proposal_bytes = source_proposal_path.read_bytes()
    source_candidate_bytes = source_candidate_path.read_bytes()
    source = json.loads(source_proposal_bytes)

    def forbidden_diagnosis_call(_request):
        pytest.fail("Editor-only replay called the Diagnosis LLM")

    monkeypatch.setattr(runtime_v14, "call_diagnosis", forbidden_diagnosis_call)
    editor, editor_requests = _replay_editor(scoped=False)
    manifest = runtime_v14.rerun_editor_only(
        campaign, batch_map, step=1, artifact_root=artifact_root, editor=editor,
    )

    assert len(editor_requests) == 1
    assert manifest["diagnosis_reexecuted"] is False
    assert manifest["diagnosis_llm_calls"] == 0
    assert manifest["editor_calls"] == 1
    assert manifest["diagnosis_count"] == 20
    assert manifest["contract_valid_diagnosis_count"] == 20
    assert manifest["compiled_decisions_replayed_without_drift"] is True
    assert manifest["source_diagnosis_ids"] == [
        item["diagnosis_id"] for item in source["diagnoses"]
    ]
    assert manifest["eligible_diagnosis_ids"] == sorted(eligible_ids)

    replay = json.loads(
        (artifact_root / "steps/step_01/editor_replay/proposal.json").read_text(
            encoding="utf-8",
        )
    )
    assert [item["diagnosis_id"] for item in replay["diagnoses"]] == [
        item["diagnosis_id"] for item in source["diagnoses"]
    ]
    assert [item["semantic"]["structured_output"] for item in replay["diagnoses"]] == [
        item["semantic"]["structured_output"] for item in source["diagnoses"]
    ]
    assert [item["compiled_decision"] for item in replay["diagnoses"]] == [
        item["compiled_decision"] for item in source["diagnoses"]
    ]
    assert replay["diagnosis_reused"] is True
    assert replay["diagnosis_calls"] == 0
    assert replay["editor_calls"] == 1
    assert source_proposal_path.read_bytes() == source_proposal_bytes
    assert source_candidate_path.read_bytes() == source_candidate_bytes
    assert (artifact_root / "steps/step_01/editor_replay/candidate_skill.md").is_file()


def test_editor_only_replay_applies_latest_domain_guard(tmp_path):
    campaign, batch_map, artifact_root, _, _ = _editor_replay_source(
        tmp_path, eligible_ids={"diagnosis_001"},
    )
    generic_editor, calls = _replay_editor(scoped=False)

    manifest = runtime_v14.rerun_editor_only(
        campaign, batch_map, step=1, artifact_root=artifact_root,
        editor=generic_editor,
    )

    replay = json.loads(
        (artifact_root / "steps/step_01/editor_replay/proposal.json").read_text(
            encoding="utf-8",
        )
    )
    assert len(calls) == 1
    assert manifest["proposal_status"] == "NO_CANDIDATE"
    assert replay["canonical_edits"][0]["v13_validation_error"] == "DOMAIN_SCOPE_LEAKAGE"
    assert replay["canonical_edits"][0]["derived_from_patch_ids"] == []
    assert not (artifact_root / "steps/step_01/editor_replay/candidate_skill.md").exists()


def test_editor_only_replay_accepts_explicit_single_domain_scope(tmp_path):
    campaign, batch_map, artifact_root, _, _ = _editor_replay_source(
        tmp_path, eligible_ids={"diagnosis_001"},
    )
    scoped_editor, calls = _replay_editor(scoped=True)

    manifest = runtime_v14.rerun_editor_only(
        campaign, batch_map, step=1, artifact_root=artifact_root,
        editor=scoped_editor,
    )

    assert len(calls) == 1
    assert manifest["proposal_status"] == "CANDIDATE"
    assert (artifact_root / "steps/step_01/editor_replay/candidate_skill.md").is_file()


def test_editor_only_replay_fails_before_editor_on_compiler_drift(tmp_path):
    campaign, batch_map, artifact_root, source_proposal_path, _ = _editor_replay_source(
        tmp_path, eligible_ids={"diagnosis_001"},
    )
    source = json.loads(source_proposal_path.read_text(encoding="utf-8"))
    source["diagnoses"][0]["compiled_decision"]["reason"] = "DRIFTED"
    source_proposal_path.write_text(json.dumps(source), encoding="utf-8")

    def forbidden_editor(_request):
        pytest.fail("Editor was called before compiler drift was rejected")

    with pytest.raises(runtime_v14.RuntimeContractError, match="CACHED_DIAGNOSIS_REPLAY_DRIFT"):
        runtime_v14.rerun_editor_only(
            campaign, batch_map, step=1, artifact_root=artifact_root,
            editor=forbidden_editor,
        )


def test_editor_only_replay_persists_editor_contract_failure(tmp_path):
    campaign, batch_map, artifact_root, _, _ = _editor_replay_source(
        tmp_path, eligible_ids={"diagnosis_001"},
    )
    calls = []

    def malformed_editor(_request):
        calls.append(1)
        return "malformed editor transport"

    with pytest.raises(
        proposal_v14.EditorContractError, match="EDITOR_STRUCTURED_OUTPUT_ERROR",
    ):
        runtime_v14.rerun_editor_only(
            campaign, batch_map, step=1, artifact_root=artifact_root,
            editor=malformed_editor,
        )

    artifact = json.loads((
        artifact_root / "steps/step_01/editor_replay/editor_contract_error.json"
    ).read_text())
    assert artifact["raw_response"] == "malformed editor transport"
    assert artifact["structured_output_mode"] == "internal_compatibility"
    assert artifact["diagnosis_llm_calls"] == 0
    assert artifact["editor_calls"] == 1
    assert artifact["compiled_decisions_replayed_without_drift"] is True
    assert len(calls) == 1


def test_rerun_editor_cli_dispatches_to_editor_only_replay(tmp_path, monkeypatch, capsys):
    campaign = {"campaign_id": "autonomous_gse_v14"}
    batch_map = {"batches": []}
    captured = {}
    monkeypatch.setattr(runtime_v14, "_campaign_files", lambda _path: (campaign, batch_map))

    def replay(received_campaign, received_batch_map, *, step, artifact_root):
        captured.update(
            campaign=received_campaign, batch_map=received_batch_map,
            step=step, artifact_root=artifact_root,
        )
        return {"mode": "editor_only_replay", "editor_calls": 1}

    monkeypatch.setattr(runtime_v14, "rerun_editor_only", replay)
    assert runtime_v14.main([
        "rerun-editor", "--campaign", str(CAMPAIGN), "--step", "1",
        "--artifact-root", str(tmp_path),
    ]) == 0
    assert captured == {
        "campaign": campaign, "batch_map": batch_map,
        "step": 1, "artifact_root": tmp_path.resolve(),
    }
    assert json.loads(capsys.readouterr().out) == {
        "mode": "editor_only_replay", "editor_calls": 1,
    }


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
        edit["text"] = "For airline requests, preserve the grounded decision predicate."
        edit["verification_target"]["trigger_condition"] = (
            "For an airline request, when the relevant decision opportunity occurs"
        )
        edit["source_ids"] = ["step_001_airline_1_rollout_01"]
        edit["repair_policy_ids"] = [policy_id]
        return "<CANONICAL_EDITS_JSON>" + json.dumps([edit]) + "</CANONICAL_EDITS_JSON>"

    decision = proposal_v14.MultiRolloutDiagnosisProposalOperator().propose(
        context, diagnoser, editor, domain_contexts=_domain_contexts(),
    )
    patch = decision.raw_patches[0]
    assert patch["operation"] == "add"
    assert not {
        "objective", "description", "root_cause", "update_axis",
        "derived_from_diagnosis_ids",
    } & set(patch)
    assert patch["outcome_relation"]["task_success"] == "supports"
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


def test_validation_artifact_converts_diagnosis_response_to_deepcopy_safe_plain_str():
    response = diagnosis_v14.DiagnosisResponse(
        json.dumps(_semantic()), "prompt_fallback", "unsupported json_schema",
    )
    validation = replace(
        _validate(_semantic()), raw_response=response,
        structured_output_mode=response.structured_output_mode,
        structured_output_fallback_reason=response.structured_output_fallback_reason,
    )

    artifact = validation.as_dict()
    copied = copy.deepcopy(artifact)

    assert type(copied["semantic"]["raw_response"]) is str
    assert copied["semantic"]["raw_response"] == str(response)
    assert copied["structured_output_mode"] == "prompt_fallback"
    assert copied["structured_output_fallback_reason"] == "unsupported json_schema"


def test_editor_prompt_uses_semantic_diagnosis_and_compiler_ownership():
    prompt = editor_v14.EDITOR_SYSTEM_PROMPT
    assert "eligible Diagnosis is the semantic authority" in prompt
    assert "Decision Compiler determines whether and how the Skill may be edited" in prompt
    assert "Do not infer additional Policy obligations" in prompt
    assert "beyond what is represented in the eligible Diagnosis and its provenance" in prompt
    assert "section placement" in prompt
    assert "cross-task deduplication" in prompt
    assert "final Skill wording" in prompt


def test_editor_prompt_preserves_mechanism_and_semantic_form():
    prompt = editor_v14.EDITOR_SYSTEM_PROMPT
    assert "preserving every mechanism-defining condition" in prompt
    assert "when the rule applies" in prompt
    assert "which action is correct" in prompt
    assert "what authorization or evidence is required" in prompt
    assert "what ordering is required" in prompt
    assert "when execution must stop" in prompt
    assert "Do not broaden scope, strengthen obligations, or impose stricter ordering" in prompt
    assert "Preserve semantic meaning rather than surface form" in prompt
    assert "examples into obligations" in prompt
    assert "illustrative alternatives into preferences" in prompt
    assert "semantic authorization, confirmation, consent, or intent into lexical matching" in prompt
    assert "supported abstract categories into unsupported concrete enumerations" in prompt


def test_editor_preserves_single_domain_boundary():
    prompt = editor_v14.EDITOR_SYSTEM_PROMPT
    assert "Domain is a scope condition" in prompt
    assert "the Skill text must begin with the canonical domain prefix" in prompt
    assert 'airline -> "For airline requests,"' in prompt
    assert 'retail -> "For retail requests,"' in prompt
    assert "Do not paraphrase, relocate, or imply the prefix" in prompt
    assert "verification target does not need to repeat this textual prefix" in prompt
    assert "scope are determined by source Diagnosis lineage" in prompt
    assert "deterministic Editor Guard validates the Skill-text prefix" in prompt


def test_editor_request_contains_no_full_policy_context():
    request = proposal_v14.DiagnosisEditorRequest(
        "candidate_001", _parent_skill(), ({
            "patch_id": "diagnosis_001",
            "task_identity": {"domain": "airline", "task_id": "1"},
            "repair_policy_ids": ["opaque-policy-id"],
        },),
    )
    _, user = editor_v14.build_editor_prompts(request)

    assert not hasattr(request, "domain_contexts")
    assert "<AUTHORITATIVE_DOMAIN_CONTEXT>" not in user
    assert "original_domain_policy" not in user
    assert "full-policy-secret" not in user


def test_diagnosis_request_retains_policy_tool_and_rollout_authority():
    request = _request()
    assert request.original_domain_policy.strip()
    assert request.available_tool_contracts
    assert request.rollouts


def test_editor_allows_compatible_multi_domain_mechanism_merge():
    prompt = editor_v14.EDITOR_SYSTEM_PROMPT
    assert "Multi-domain generalization is allowed only when the merge contract" in prompt


def test_editor_preserves_source_specific_predicates_when_merging():
    prompt = editor_v14.EDITOR_SYSTEM_PROMPT
    assert "without changing any source-specific predicate" in prompt
    assert "Shared repair operators do not imply shared predicates" in prompt
    assert "Only conditions supported by every source may appear in the shared portion" in prompt
    assert "Source-specific conditions must remain branch-scoped" in prompt
    assert "emit separate edits" in prompt


def test_editor_preserves_user_controlled_choice_boundaries():
    prompt = editor_v14.EDITOR_SYSTEM_PROMPT
    assert "Preserve user control over every parameter" in prompt
    assert "preserve an existing explicit user choice or authorization" in prompt
    assert "authoritative deterministic selector" in prompt
    assert "obtains the user's choice before execution" in prompt
    assert "one value must be selected from a permitted set is not itself a deterministic selector" in prompt
    assert "deterministic selector must actually determine the value" in prompt
    assert "If the value remains unresolved and is user-controlled" in prompt
    assert "Authorization for one parameter does not authorize" in prompt


def test_editor_verification_target_matches_skill_and_sources():
    prompt = editor_v14.EDITOR_SYSTEM_PROMPT
    assert "exactly one verification_target containing problem, trigger_condition, and expected_behavior" in prompt
    assert "precise, operational, behaviorally testable" in prompt
    assert "consistent with the canonical Skill text" in prompt
    assert "must not be narrower, broader, or stronger" in prompt
    assert "jointly preserve the source mechanism, scope, user-control boundaries" in prompt


def test_editor_prompt_has_only_requested_logical_sections():
    prompt = editor_v14.EDITOR_SYSTEM_PROMPT
    assert [line for line in prompt.splitlines() if re.fullmatch(r"[A-H]\. .+", line)] == [
        "A. Authority boundary",
        "B. Mechanism-preserving canonicalization",
        "C. Scope and provenance preservation",
        "D. User-controlled decisions",
        "E. Merge semantics",
        "F. Semantic-form preservation",
        "G. Verification target",
        "H. Output contract",
    ]
    assert "Return only the structured canonical-edit result" in prompt
    assert "<CANONICAL_EDITS_JSON>" not in prompt
    assert "</CANONICAL_EDITS_JSON>" not in prompt


def test_editor_prompt_contains_no_known_case_shaped_production_tokens():
    prompt = editor_v14.EDITOR_SYSTEM_PROMPT.casefold()
    forbidden_patterns = {
        r"\bcertificate\b", r"\bbaggage\b", r"\binsurance\b", r"\btax\b",
        r"\bmodify_pending_order_items\b", r"\bexchange_delivered_order_items\b",
        r"cover the remainder", r"explicit ['\"]yes['\"]",
    }
    assert not {pattern for pattern in forbidden_patterns if re.search(pattern, prompt)}


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

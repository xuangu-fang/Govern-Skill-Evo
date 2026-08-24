from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from src.learners.stwebagentbench.generate_governed_skill_v07 import (
    build_editor_prompts,
)
from src.skill_evolution.autonomous_gse_v03_proposal import ProposalContext
from src.skill_evolution.autonomous_gse_v03_runtime import DeterministicDryRunAdapter
from src.skill_evolution.autonomous_gse_v05_benchmark_runtime import (
    _expand_campaign,
    _v03_campaign,
)
from src.skill_evolution.autonomous_gse_v07_benchmark_runtime import (
    run_v07_campaign,
)
from src.skill_evolution.autonomous_gse_v07_proposal import (
    DiagnosisDrivenProposalOperator,
    DiagnosisEditorRequest,
)
from src.skill_evolution.diagnosis import DiagnosisRequest, build_diagnosis_prompts

PARENT = """# SuiteCRM Operational Skill

## Planning and navigation

- Obtain missing information before starting execution.

## Execution patterns

- Obtain explicit confirmation before an irreversible operation.

## Form entry and verification

- Verify saved values before reporting completion.

## Error recovery and stopping

- Stop when a required tool is unavailable.
"""


def evidence(
    state: str,
    *,
    source_id: str = "source_001",
    violated: bool = False,
) -> dict:
    return {
        "source_id": source_id,
        "state": state,
        "task_success": state in {"compliant_success", "violating_success"},
        "actions": [
            {"step": 1, "action": "inspect"},
            {"step": 2, "action": "edit"},
            {"step": 3, "action": "save"},
        ],
        "trajectory": {
            "goal": "Update a record.",
        },
        "process_feedback": {
            "compliant": not violated,
            "violated_policies": (
                [{"policy_template_id": "policy_confirmation"}] if violated else []
            ),
        },
    }


def diagnosis(
    *,
    state: str,
    category: str | None,
    relevance: str,
    action: str = "none",
    section: str | None = None,
    rule_id: str | None = None,
    preserve: list[dict] | None = None,
    objective: str = "Require confirmation before irreversible actions.",
    description: str = "Add the missing confirmation prerequisite.",
    task_evidence_steps: list[int] | None = None,
    policy_evidence_steps: list[int] | None = None,
) -> str:
    success = state in {"compliant_success", "violating_success"}
    violated = state in {"violating_success", "violating_failure"}
    payload = {
        "behavior_summary": "The Agent inspected the record and attempted the task.",
        "task_analysis": {
            "status": "success" if success else "failure",
            "reason": "The external task verifier supplied this outcome.",
            "evidence_steps": (
                task_evidence_steps
                if task_evidence_steps is not None
                else [3 if success else 2]
            ),
        },
        "policy_analysis": {
            "status": "violated" if violated else "compliant",
            "reason": "The external policy verifier supplied this outcome.",
            "policy_ids": ["policy_confirmation"] if violated else [],
            "evidence_steps": (
                policy_evidence_steps
                if policy_evidence_steps is not None
                else [3]
            ),
        },
        "root_cause": {
            "category": category,
            "explanation": "The trajectory supports this conservative attribution.",
        },
        "skill_update_relevance": relevance,
        "update_recommendation": {
            "action": action,
            "target_section": section,
            "target_rule_id": rule_id,
            "objective": objective,
            "description": description,
        },
        "preserve_constraints": preserve or [],
    }
    return f"<DIAGNOSIS_JSON>{json.dumps(payload)}</DIAGNOSIS_JSON>"


def fail_if_editor_called(request):  # pragma: no cover - assertion helper
    raise AssertionError(f"Editor must not be called: {request}")


def test_case_a_success_compliant_preserves_existing_rule_without_candidate() -> None:
    item = evidence("compliant_success")
    decision = DiagnosisDrivenProposalOperator().propose(
        ProposalContext("candidate", PARENT, (item,)),
        lambda request: diagnosis(
            state=item["state"],
            category=None,
            relevance="preserve",
            preserve=[
                {
                    "target_rule_id": "rule_001",
                    "reason": "It enabled successful prerequisite gathering.",
                }
            ],
        ),
        fail_if_editor_called,
    )

    assert decision.proposal_status == "NO_CANDIDATE"
    assert decision.proposal_reason["code"] == "NO_UPDATE_ELIGIBLE_DIAGNOSIS"
    assert decision.editor_calls == 0
    assert decision.preserve_constraints[0]["target_rule_id"] == "rule_001"
    assert decision.diagnoses[0]["validation"] == {"valid": True, "errors": []}


def test_case_b_violating_success_with_missing_guidance_reaches_bounded_editor() -> None:
    item = evidence("violating_success", violated=True)
    editor_requests = []

    def editor(request):
        editor_requests.append(request)
        patch_id = request.eligible_diagnoses[0]["patch_id"]
        edit = {
            "derived_from_patch_ids": [patch_id],
            "operation": "add",
            "section": "Execution patterns",
            "target_rule_id": "",
            "text": "Obtain explicit confirmation before every irreversible action.",
            "reason": "Express the diagnosed missing prerequisite minimally.",
            "source_ids": ["source_001"],
            "repair_policy_ids": ["policy_confirmation"],
        }
        return f"<CANONICAL_EDITS_JSON>{json.dumps([edit])}</CANONICAL_EDITS_JSON>"

    decision = DiagnosisDrivenProposalOperator().propose(
        ProposalContext("candidate", PARENT, (item,)),
        lambda request: diagnosis(
            state=item["state"],
            category="skill_issue",
            relevance="update",
            action="add",
            section="Execution patterns",
        ),
        editor,
    )

    assert decision.proposal_status == "CANDIDATE"
    assert decision.diagnosis_calls == 1
    assert decision.editor_calls == 1
    assert decision.eligible_diagnosis_ids == ["diagnosis_001"]
    assert len(editor_requests) == 1
    assert "Obtain explicit confirmation" in decision.candidate_skill


def test_all_eligible_diagnoses_reach_one_editor_call_without_eight_signal_cap() -> None:
    items = tuple(
        evidence("compliant_failure", source_id=f"source_{index:03d}")
        for index in range(1, 11)
    )
    editor_requests = []

    def editor(request):
        editor_requests.append(request)
        return "<CANONICAL_EDITS_JSON>[]</CANONICAL_EDITS_JSON>"

    decision = DiagnosisDrivenProposalOperator().propose(
        ProposalContext("candidate", PARENT, items),
        lambda request: diagnosis(
            state=request.governed_experience["state"],
            category="skill_issue",
            relevance="update",
            action="add",
            section="Planning and navigation",
            objective=f"Address {request.governed_experience['source_id']}.",
            description="Express this independently diagnosed Skill gap.",
        ),
        editor,
    )

    assert decision.diagnosis_calls == 10
    assert decision.editor_calls == 1
    assert len(editor_requests) == 1
    assert len(editor_requests[0].eligible_diagnoses) == 10
    assert len(decision.raw_patches) == 10
    assert [item["patch_id"] for item in decision.raw_patches] == [
        f"diagnosis_{index:03d}" for index in range(1, 11)
    ]


def test_same_replace_target_can_synthesize_multiple_diagnoses_into_one_edit() -> None:
    items = (
        evidence("compliant_failure", source_id="source_001"),
        evidence("compliant_failure", source_id="source_002"),
    )

    def editor(request):
        patch_ids = [item["patch_id"] for item in request.eligible_diagnoses]
        edit = {
            "derived_from_patch_ids": patch_ids,
            "operation": "replace",
            "section": "Execution patterns",
            "target_rule_id": "rule_002",
            "text": "Obtain and verify explicit confirmation before an irreversible operation.",
            "reason": "Two Diagnoses support the same exact rule target.",
            "source_ids": [],
            "repair_policy_ids": [],
        }
        return f"<CANONICAL_EDITS_JSON>{json.dumps([edit])}</CANONICAL_EDITS_JSON>"

    decision = DiagnosisDrivenProposalOperator().propose(
        ProposalContext("candidate", PARENT, items),
        lambda request: diagnosis(
            state=request.governed_experience["state"],
            category="skill_issue",
            relevance="update",
            action="replace",
            section="Execution patterns",
            rule_id="rule_002",
        ),
        editor,
    )

    assert decision.proposal_status == "CANDIDATE"
    assert len(decision.applied_edits) == 1
    assert decision.applied_edits[0]["derived_from_patch_ids"] == [
        "diagnosis_001",
        "diagnosis_002",
    ]
    assert decision.applied_edits[0]["source_ids"] == [
        "source_001",
        "source_002",
    ]


def test_different_replace_targets_cannot_share_one_canonical_edit() -> None:
    items = (
        evidence("compliant_failure", source_id="source_001"),
        evidence("compliant_failure", source_id="source_002"),
    )

    def diagnoser(request):
        rule_id = (
            "rule_001"
            if request.governed_experience["source_id"] == "source_001"
            else "rule_002"
        )
        section = (
            "Planning and navigation"
            if rule_id == "rule_001"
            else "Execution patterns"
        )
        return diagnosis(
            state=request.governed_experience["state"],
            category="skill_issue",
            relevance="update",
            action="replace",
            section=section,
            rule_id=rule_id,
        )

    def editor(request):
        edit = {
            "derived_from_patch_ids": [
                item["patch_id"] for item in request.eligible_diagnoses
            ],
            "operation": "replace",
            "section": "Planning and navigation",
            "target_rule_id": "rule_001",
            "text": "Invalidly combine different targets.",
            "reason": "This must be rejected.",
            "source_ids": [],
            "repair_policy_ids": [],
        }
        return f"<CANONICAL_EDITS_JSON>{json.dumps([edit])}</CANONICAL_EDITS_JSON>"

    decision = DiagnosisDrivenProposalOperator().propose(
        ProposalContext("candidate", PARENT, items), diagnoser, editor
    )

    assert decision.proposal_status == "NO_CANDIDATE"
    assert decision.canonical_edits[0]["v07_validation_error"] == (
        "DIAGNOSIS_TARGET_DRIFT"
    )


def test_distinct_add_gaps_in_same_section_remain_separate_edits() -> None:
    items = (
        evidence("compliant_failure", source_id="source_001"),
        evidence("compliant_failure", source_id="source_002"),
    )
    objectives = {
        "source_001": "Require confirmation before irreversible actions.",
        "source_002": "Prevent disclosure of private data.",
    }

    def diagnoser(request):
        source_id = request.governed_experience["source_id"]
        return diagnosis(
            state=request.governed_experience["state"],
            category="skill_issue",
            relevance="update",
            action="add",
            section="Execution patterns",
            objective=objectives[source_id],
            description=f"Add the independent gap for {source_id}.",
        )

    def editor(request):
        texts = (
            "Obtain explicit confirmation before irreversible actions.",
            "Do not disclose private data without authorization.",
        )
        edits = [
            {
                "derived_from_patch_ids": [signal["patch_id"]],
                "operation": "add",
                "section": "Execution patterns",
                "target_rule_id": "",
                "text": text,
                "reason": "Keep an independently diagnosed gap separate.",
                "source_ids": signal["source_ids"],
                "repair_policy_ids": [],
            }
            for signal, text in zip(request.eligible_diagnoses, texts, strict=True)
        ]
        return f"<CANONICAL_EDITS_JSON>{json.dumps(edits)}</CANONICAL_EDITS_JSON>"

    decision = DiagnosisDrivenProposalOperator().propose(
        ProposalContext("candidate", PARENT, items), diagnoser, editor
    )

    assert decision.proposal_status == "CANDIDATE"
    assert len(decision.applied_edits) == 2
    assert all(
        len(edit["derived_from_patch_ids"]) == 1 for edit in decision.applied_edits
    )


@pytest.mark.parametrize(
    ("state", "category", "relevance"),
    [
        ("violating_failure", "execution_issue", "none"),
        ("compliant_failure", "external_issue", "none"),
        ("compliant_failure", "uncertain", "uncertain"),
    ],
)
def test_cases_c_d_e_conservatively_skip_non_skill_causes(
    state: str, category: str, relevance: str
) -> None:
    item = evidence(state, violated=state.startswith("violating"))
    decision = DiagnosisDrivenProposalOperator().propose(
        ProposalContext("candidate", PARENT, (item,)),
        lambda request: diagnosis(
            state=state,
            category=category,
            relevance=relevance,
        ),
        fail_if_editor_called,
    )

    assert decision.proposal_status == "NO_CANDIDATE"
    assert decision.editor_calls == 0
    assert decision.eligible_diagnosis_ids == []


def test_uncertain_cause_rejects_none_relevance_with_precise_error() -> None:
    item = evidence("compliant_failure")
    decision = DiagnosisDrivenProposalOperator().propose(
        ProposalContext("candidate", PARENT, (item,)),
        lambda request: diagnosis(
            state=item["state"],
            category="uncertain",
            relevance="none",
        ),
        fail_if_editor_called,
    )

    assert decision.proposal_status == "NO_CANDIDATE"
    assert decision.diagnoses[0]["validation"]["valid"] is False
    assert decision.diagnoses[0]["validation"]["errors"] == [
        "UNCERTAIN_CAUSE_REQUIRES_UNCERTAIN_RELEVANCE"
    ]


def test_case_f_invalid_rule_id_is_recorded_and_cannot_reach_editor() -> None:
    item = evidence("compliant_failure")
    decision = DiagnosisDrivenProposalOperator().propose(
        ProposalContext("candidate", PARENT, (item,)),
        lambda request: diagnosis(
            state=item["state"],
            category="skill_issue",
            relevance="update",
            action="replace",
            section="Execution patterns",
            rule_id="rule_999",
        ),
        fail_if_editor_called,
    )

    assert decision.proposal_status == "NO_CANDIDATE"
    assert decision.editor_calls == 0
    assert decision.diagnoses[0]["validation"]["valid"] is False
    assert "TARGET_RULE_ID_NOT_FOUND" in decision.diagnoses[0]["validation"]["errors"]


def test_numeric_evidence_steps_must_reference_existing_action_steps() -> None:
    item = evidence("compliant_failure")
    decision = DiagnosisDrivenProposalOperator().propose(
        ProposalContext("candidate", PARENT, (item,)),
        lambda request: diagnosis(
            state=item["state"],
            category="skill_issue",
            relevance="update",
            action="add",
            section="Execution patterns",
            task_evidence_steps=[999],
        ),
        fail_if_editor_called,
    )

    assert decision.proposal_status == "NO_CANDIDATE"
    assert decision.editor_calls == 0
    assert decision.diagnoses[0]["validation"]["valid"] is False
    assert "TASK_EVIDENCE_STEP_NOT_FOUND" in decision.diagnoses[0]["validation"][
        "errors"
    ]


def test_editor_target_drift_is_deterministically_excluded() -> None:
    item = evidence("compliant_failure")

    def editor(request):
        patch_id = request.eligible_diagnoses[0]["patch_id"]
        drifted = {
            "derived_from_patch_ids": [patch_id],
            "operation": "replace",
            "section": "Planning and navigation",
            "target_rule_id": "rule_001",
            "text": "Change an unrelated rule.",
            "reason": "Drifted target.",
            "source_ids": ["source_001"],
            "repair_policy_ids": [],
        }
        return f"<CANONICAL_EDITS_JSON>{json.dumps([drifted])}</CANONICAL_EDITS_JSON>"

    decision = DiagnosisDrivenProposalOperator().propose(
        ProposalContext("candidate", PARENT, (item,)),
        lambda request: diagnosis(
            state=item["state"],
            category="skill_issue",
            relevance="update",
            action="replace",
            section="Execution patterns",
            rule_id="rule_002",
        ),
        editor,
    )

    assert decision.proposal_status == "NO_CANDIDATE"
    assert decision.canonical_edits[0]["v07_validation_error"] == (
        "DIAGNOSIS_TARGET_DRIFT"
    )
    assert decision.applied_edits == []


def test_editor_policy_id_leakage_is_deterministically_excluded() -> None:
    item = evidence("violating_failure", violated=True)

    def editor(request):
        patch_id = request.eligible_diagnoses[0]["patch_id"]
        leaking = {
            "derived_from_patch_ids": [patch_id],
            "operation": "add",
            "section": "Execution patterns",
            "target_rule_id": "",
            "text": "When policy_confirmation applies, ask before saving.",
            "reason": "Internal policy identifiers must not enter Skill text.",
            "source_ids": ["source_001"],
            "repair_policy_ids": ["policy_confirmation"],
        }
        return f"<CANONICAL_EDITS_JSON>{json.dumps([leaking])}</CANONICAL_EDITS_JSON>"

    decision = DiagnosisDrivenProposalOperator().propose(
        ProposalContext("candidate", PARENT, (item,)),
        lambda request: diagnosis(
            state=item["state"],
            category="skill_issue",
            relevance="update",
            action="add",
            section="Execution patterns",
        ),
        editor,
    )

    assert decision.proposal_status == "NO_CANDIDATE"
    assert decision.canonical_edits[0]["v07_validation_error"] == (
        "POLICY_ID_LEAKAGE"
    )
    assert decision.applied_edits == []


@pytest.mark.parametrize(
    "text",
    [
        "Enter task fields in order, including the start date before the subject.",
        "Enter the office phone first and the fax number second, then save.",
        "Set the relationship type to Primary and verify the association.",
    ],
)
def test_editor_task_specific_recipes_are_deterministically_excluded(
    text: str,
) -> None:
    item = evidence("compliant_failure")

    def editor(request):
        patch_id = request.eligible_diagnoses[0]["patch_id"]
        edit = {
            "derived_from_patch_ids": [patch_id],
            "operation": "add",
            "section": "Execution patterns",
            "target_rule_id": "",
            "text": text,
            "reason": "This text overfits one supporting task.",
            "source_ids": ["source_001"],
            "repair_policy_ids": [],
        }
        return f"<CANONICAL_EDITS_JSON>{json.dumps([edit])}</CANONICAL_EDITS_JSON>"

    decision = DiagnosisDrivenProposalOperator().propose(
        ProposalContext("candidate", PARENT, (item,)),
        lambda request: diagnosis(
            state=item["state"],
            category="skill_issue",
            relevance="update",
            action="add",
            section="Execution patterns",
        ),
        editor,
    )

    assert decision.proposal_status == "NO_CANDIDATE"
    assert decision.canonical_edits[0]["v07_validation_error"] == (
        "TASK_SPECIFIC_RULE"
    )
    assert decision.applied_edits == []


def test_editor_reusable_parameterized_method_is_applied() -> None:
    item = evidence("compliant_failure")

    def editor(request):
        patch_id = request.eligible_diagnoses[0]["patch_id"]
        edit = {
            "derived_from_patch_ids": [patch_id],
            "operation": "add",
            "section": "Execution patterns",
            "target_rule_id": "",
            "text": (
                "When an operation defines a required field order, determine "
                "and follow that order, then verify every saved value before "
                "completion."
            ),
            "reason": "Parameterize the reusable ordering and verification method.",
            "source_ids": ["source_001"],
            "repair_policy_ids": [],
        }
        return f"<CANONICAL_EDITS_JSON>{json.dumps([edit])}</CANONICAL_EDITS_JSON>"

    decision = DiagnosisDrivenProposalOperator().propose(
        ProposalContext("candidate", PARENT, (item,)),
        lambda request: diagnosis(
            state=item["state"],
            category="skill_issue",
            relevance="update",
            action="add",
            section="Execution patterns",
        ),
        editor,
    )

    assert decision.proposal_status == "CANDIDATE"
    assert decision.excluded_edits == []
    assert decision.applied_edits[0]["text"].startswith(
        "When an operation defines a required field order"
    )


def test_prompts_expose_verified_state_rule_ids_and_narrow_editor_role() -> None:
    item = evidence("compliant_success")
    system_prompt, user_prompt = build_diagnosis_prompts(
        DiagnosisRequest("candidate", "diagnosis_001", PARENT, item)
    )
    assert "external facts" in system_prompt
    assert "execution_issue" in system_prompt
    assert "skill_update_relevance uncertain" in system_prompt
    assert "Do not use relevance none for an uncertain" in system_prompt
    assert 'use exactly "compliant"' in system_prompt
    assert 'exactly "violated"' in system_prompt
    assert "positive integer step IDs" in system_prompt
    assert 'strings such as "step_3"' in system_prompt
    assert '"target_rule_id": "rule_003"' in system_prompt
    assert "positively supported successful verification" in system_prompt
    assert "transferable operating method" in system_prompt
    assert "Never recommend unconditional rules" in system_prompt
    assert "[rule_001]" in user_prompt
    assert '"state": "compliant_success"' in user_prompt

    editor_request = None

    def capture_editor(request):
        nonlocal editor_request
        editor_request = copy.deepcopy(request)
        return "<CANONICAL_EDITS_JSON>[]</CANONICAL_EDITS_JSON>"

    update_item = evidence("compliant_failure")
    DiagnosisDrivenProposalOperator().propose(
        ProposalContext("candidate", PARENT, (update_item,)),
        lambda request: diagnosis(
            state=update_item["state"],
            category="skill_issue",
            relevance="update",
            action="add",
            section="Planning and navigation",
        ),
        capture_editor,
    )
    assert editor_request is not None
    editor_system, editor_user = build_editor_prompts(editor_request)
    assert "already decided" in editor_system
    assert "Never drift" in editor_system
    assert "Do not rank, select, or apply a" in editor_system
    assert "Do not merge add Diagnoses merely because" in editor_system
    assert "Never copy a" in editor_system
    assert "internal identifiers belong only in provenance metadata" in editor_system
    assert "reusable operating method" in editor_system
    assert "Instance-specific recipe text is deterministically excluded" in (
        editor_system
    )
    assert "UPDATE_ELIGIBLE_DIAGNOSES" in editor_user


def test_end_to_end_v07_example_reuses_selection_and_accept_reject_gate() -> None:
    project_root = Path(__file__).resolve().parents[2]
    campaign = _expand_campaign(
        json.loads(
            (
                project_root
                / "experiments/campaigns/autonomous_gse_v05/campaign_manifest.json"
            ).read_text(encoding="utf-8")
        )
    )
    batch_map = json.loads(
        (
            project_root
            / "experiments/campaigns/autonomous_gse_v02/batch_map.json"
        ).read_text(encoding="utf-8")
    )
    initial_skill = (
        project_root
        / "experiments/campaigns/autonomous_gse_v03/skills/S0_empty_skill.md"
    ).read_text(encoding="utf-8")

    class V07DryRunAdapter(DeterministicDryRunAdapter):
        def run_train(self, step):
            return tuple(
                {
                    **item,
                    "actions": [
                        {"step": 1, "action": "inspect"},
                        {"step": 2, "action": "edit"},
                        {"step": 3, "action": "save"},
                    ],
                }
                for item in super().run_train(step)
            )

        def learner_response(self, step, request):
            if isinstance(request, DiagnosisRequest):
                state = request.governed_experience["state"]
                if state == "violating_success":
                    return diagnosis(
                        state=state,
                        category="skill_issue",
                        relevance="update",
                        action="add",
                        section="Planning and navigation",
                    ).replace("policy_confirmation", "confirm_before_update")
                category, relevance = {
                    "compliant_success": (None, "preserve"),
                    "compliant_failure": ("external_issue", "none"),
                    "violating_failure": ("execution_issue", "none"),
                }[state]
                response = diagnosis(
                    state=state,
                    category=category,
                    relevance=relevance,
                )
                if state == "violating_failure":
                    response = response.replace(
                        "policy_confirmation", "stop_after_repeated_error"
                    )
                return response
            if isinstance(request, DiagnosisEditorRequest):
                signal = request.eligible_diagnoses[0]
                edit = {
                    "derived_from_patch_ids": [signal["patch_id"]],
                    "operation": signal["operation"],
                    "section": signal["section"],
                    "target_rule_id": signal["target_rule_id"],
                    "text": "Confirm the intended record change before saving.",
                    "reason": "Minimal wording for the validated intervention.",
                    "source_ids": signal["source_ids"],
                    "repair_policy_ids": signal["repair_policy_ids"],
                }
                return (
                    "<CANONICAL_EDITS_JSON>"
                    + json.dumps([edit])
                    + "</CANONICAL_EDITS_JSON>"
                )
            return super().learner_response(step, request)

    adapter = V07DryRunAdapter(
        ("ACCEPT", "REJECT", "NO_CANDIDATE"),
        initial_skill=initial_skill,
    )
    report = run_v07_campaign(
        _v03_campaign(campaign),
        batch_map,
        adapter,
        scheduled_steps=1,
    )

    assert report["schema_version"] == "autonomous_gse_runtime_report_0.7.0"
    assert report["proposal_pipeline"] == "diagnosis_driven_bounded_edit"
    assert report["steps"][0]["schema_version"] == "autonomous_gse_step_0.7.0"
    assert report["steps"][0]["protocol_version"] == "autonomous_gse_v07"
    assert report["steps"][0]["campaign_id"] == "autonomous_gse_v07"
    assert (
        report["steps"][0]["proposal_operator"]
        == "diagnosis_driven_bounded_edit"
    )
    assert report["steps"][0]["proposal_budget"] == {
        "maximum_diagnosis_calls": 51,
        "eligible_update_diagnoses": "all_valid_updates",
        "maximum_editor_calls": 1,
        "additional_minibatching": False,
        "maximum_skill_rules": 18,
        "maximum_skill_words": 900,
        "allowed_operations": ["add", "replace", "delete"],
    }
    assert report["steps"][0]["outcome"] == "ACCEPT"
    assert report["steps"][0]["proposal_status"] == "CANDIDATE"
    assert report["budget_usage"]["learner_calls"] == 5
    assert any(
        event["operation"] == "run_candidate_selection"
        for event in report["runtime_trace"]
    )

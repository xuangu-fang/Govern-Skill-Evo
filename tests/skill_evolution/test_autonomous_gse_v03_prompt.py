"""Prompt tests for Autonomous GSE v0.3 Reflectors and Editor."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from src.learners.stwebagentbench.generate_governed_skill_v03 import (
    LEARNER_MODEL,
    MAX_COMPLETION_TOKENS,
    REASONING_EFFORT,
    PromptContractError,
    build_editor_prompts,
    build_reflector_prompts,
    call_governed_editor,
    call_governed_reflector,
)
from src.skill_evolution.autonomous_gse_v03_proposal import (
    EditorRequest,
    GovernedReflectionEditorProposalOperator,
    ProposalContext,
    ReflectorRequest,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = (
    PROJECT_ROOT
    / "experiments/campaigns/autonomous_gse_v03/campaign_manifest.json"
)
PROMPT_PATH = (
    PROJECT_ROOT
    / "src/learners/stwebagentbench/generate_governed_skill_v03.py"
)

S0_SKILL = """# SuiteCRM Operational Skill

## Planning and navigation

## Execution patterns

## Form entry and verification

## Error recovery and stopping
"""

SUCCESS_EVIDENCE = (
    {
        "source_id": "source_cs",
        "task_success": True,
        "state": "compliant_success",
        "goal": "Open the requested record.",
        "actions": [{"step": 1, "action": "Open the record."}],
        "process_feedback": {"violated_policies": []},
    },
    {
        "source_id": "source_vs",
        "task_success": True,
        "state": "violating_success",
        "actions": [{"step": 1, "action": "Submit the update."}],
        "process_feedback": {
            "violated_policies": [
                {"policy_template_id": "confirm_before_update"}
            ]
        },
    },
)

FAILURE_EVIDENCE = (
    {
        "source_id": "source_cf",
        "task_success": False,
        "state": "compliant_failure",
        "actions": [{"step": 1, "action": "Retry the same control."}],
        "process_feedback": {"violated_policies": []},
    },
    {
        "source_id": "source_vf",
        "task_success": False,
        "state": "violating_failure",
        "actions": [{"step": 1, "action": "Continue after repeated errors."}],
        "process_feedback": {
            "violated_policies": [
                {"policy_template_id": "stop_after_repeated_error"}
            ]
        },
    },
)


def reflector_request(reflector: str) -> ReflectorRequest:
    evidence = SUCCESS_EVIDENCE if reflector == "success" else FAILURE_EVIDENCE
    return ReflectorRequest(
        candidate_id="epoch_001_step_001_candidate",
        reflector=reflector,
        current_parent_skill=S0_SKILL,
        current_batch_evidence=copy.deepcopy(evidence),
        maximum_raw_patches=4,
    )


def raw_patch(patch_id: str = "success_patch_001") -> dict:
    return {
        "patch_id": patch_id,
        "reflector": "success",
        "operation": "add",
        "section": "Execution patterns",
        "target_clause": "",
        "text": "Open the identified record through the supported workflow.",
        "reason": "The successful evidence supports this workflow.",
        "source_ids": ["source_cs"],
        "repair_policy_ids": [],
    }


def editor_request() -> EditorRequest:
    return EditorRequest(
        candidate_id="epoch_001_step_001_candidate",
        current_parent_skill=S0_SKILL,
        raw_patches=(raw_patch(),),
    )


def test_success_and_failure_reflectors_use_distinct_state_semantics() -> None:
    success_system, success_user = build_reflector_prompts(
        reflector_request("success")
    )
    failure_system, failure_user = build_reflector_prompts(
        reflector_request("failure")
    )

    assert "compliant_success" in success_system
    assert "violating_success" in success_system
    assert "compliant_failure" not in success_system
    assert "violating_failure" not in success_system
    assert "compliant_failure" in failure_system
    assert "violating_failure" in failure_system
    assert "compliant_success" not in failure_system
    assert "violating_success" not in failure_system
    assert "source_cs" in success_user
    assert "source_vs" in success_user
    assert "source_cf" in failure_user
    assert "source_vf" in failure_user


def test_reflector_prompt_defines_raw_patch_only_contract() -> None:
    system_prompt, user_prompt = build_reflector_prompts(
        reflector_request("success")
    )

    assert "at most 4 atomic raw patches" in system_prompt
    assert "Do not create additional\n   minibatches" in system_prompt
    assert "Do not generate patch_id or reflector" in system_prompt
    assert "Do not return\n   a complete Skill, a summary" in system_prompt
    assert "<RAW_PATCHES_JSON>" in system_prompt
    assert "<SUMMARY>" not in system_prompt
    assert "<CURRENT_BATCH_GOVERNED_EVIDENCE>" in user_prompt
    assert "<MAXIMUM_RAW_PATCHES>\n4" in user_prompt
    assert "<SELECTION_DATA>" not in user_prompt
    assert "<TEST_DATA>" not in user_prompt


def test_editor_prompt_only_receives_parent_and_raw_patches() -> None:
    system_prompt, user_prompt = build_editor_prompts(editor_request())

    assert S0_SKILL.strip() in user_prompt
    assert "success_patch_001" in user_prompt
    assert "<RAW_PATCHES>" in user_prompt
    assert "<CURRENT_BATCH_GOVERNED_EVIDENCE>" not in user_prompt
    assert "source_vs" not in user_prompt
    assert "summary" not in user_prompt.lower()
    assert "<SELECTION_DATA>" not in user_prompt
    assert "<TEST_DATA>" not in user_prompt
    assert "<CANONICAL_EDITS_JSON>" in system_prompt


def test_editor_prompt_defines_reducer_without_selection() -> None:
    system_prompt, _ = build_editor_prompts(editor_request())

    assert "derived_from_patch_ids" in system_prompt
    assert "Each raw patch may contribute to at most one canonical edit" in (
        system_prompt
    )
    assert "Do not split one\n   raw patch into multiple canonical edits" in system_prompt
    assert "Do not rank edits" in system_prompt
    assert "perform top-k selection" in system_prompt
    assert "Do not generate edit_id" in system_prompt


def test_prompt_builds_are_deterministic_and_do_not_mutate_requests() -> None:
    reflector = reflector_request("failure")
    editor = editor_request()
    original_reflector = copy.deepcopy(reflector)
    original_editor = copy.deepcopy(editor)

    assert build_reflector_prompts(reflector) == build_reflector_prompts(reflector)
    assert build_editor_prompts(editor) == build_editor_prompts(editor)
    assert reflector == original_reflector
    assert editor == original_editor


def test_injected_calls_use_the_configured_model() -> None:
    observed: list[tuple[str, str, str]] = []

    def fake_call(
        model: str,
        system_prompt: str,
        user_prompt: str,
    ) -> tuple[str, str, dict]:
        observed.append((model, system_prompt, user_prompt))
        tag = (
            "CANONICAL_EDITS_JSON"
            if "You are the Editor" in system_prompt
            else "RAW_PATCHES_JSON"
        )
        return f"<{tag}>[]</{tag}>", model, {"calls": 1}

    reflector_response = call_governed_reflector(
        reflector_request("success"),
        learner_call=fake_call,
    )
    editor_response = call_governed_editor(
        editor_request(),
        learner_call=fake_call,
    )

    assert reflector_response == "<RAW_PATCHES_JSON>[]</RAW_PATCHES_JSON>"
    assert editor_response == (
        "<CANONICAL_EDITS_JSON>[]</CANONICAL_EDITS_JSON>"
    )
    assert [call[0] for call in observed] == [LEARNER_MODEL, LEARNER_MODEL]
    assert REASONING_EFFORT == "low"
    assert MAX_COMPLETION_TOKENS == 8000


def test_prompt_calls_integrate_with_v03_proposal_operator() -> None:
    evidence = SUCCESS_EVIDENCE + FAILURE_EVIDENCE

    def fake_call(
        model: str,
        system_prompt: str,
        user_prompt: str,
    ) -> tuple[str, str, None]:
        assert model == LEARNER_MODEL
        if system_prompt.startswith("You are the Success Reflector"):
            patch = {
                "operation": "add",
                "section": "Execution patterns",
                "target_clause": "",
                "text": "Open the identified record through the supported workflow.",
                "reason": "Supported by successful current-batch evidence.",
                "source_ids": ["source_cs"],
                "repair_policy_ids": [],
            }
            return (
                f"<RAW_PATCHES_JSON>{json.dumps([patch])}</RAW_PATCHES_JSON>",
                model,
                None,
            )
        if system_prompt.startswith("You are the Failure Reflector"):
            return "<RAW_PATCHES_JSON>[]</RAW_PATCHES_JSON>", model, None
        assert "<CURRENT_BATCH_GOVERNED_EVIDENCE>" not in user_prompt
        assert "source_vs" not in user_prompt
        edit = {
            "derived_from_patch_ids": ["success_patch_001"],
            "operation": "add",
            "section": "Execution patterns",
            "target_clause": "",
            "text": "Open the identified record through the supported workflow.",
            "reason": "Canonicalized from the supported raw patch.",
            "source_ids": ["source_cs"],
            "repair_policy_ids": [],
        }
        return (
            f"<CANONICAL_EDITS_JSON>{json.dumps([edit])}"
            "</CANONICAL_EDITS_JSON>",
            model,
            None,
        )

    current = ProposalContext(
        candidate_id="epoch_001_step_001_candidate",
        parent_skill=S0_SKILL,
        current_batch_governed_evidence=copy.deepcopy(evidence),
    )
    decision = GovernedReflectionEditorProposalOperator().propose(
        current,
        lambda request: call_governed_reflector(
            request,
            learner_call=fake_call,
        ),
        lambda request: call_governed_reflector(
            request,
            learner_call=fake_call,
        ),
        lambda request: call_governed_editor(
            request,
            learner_call=fake_call,
        ),
    )

    assert decision.proposal_status == "CANDIDATE"
    assert decision.reflector_calls == 2
    assert decision.editor_calls == 1
    assert decision.provenance_status == "VERIFIED"
    assert "Open the identified record" in decision.candidate_skill


@pytest.mark.parametrize(
    "invalid_request",
    [
        ReflectorRequest(
            candidate_id="candidate",
            reflector="success",
            current_parent_skill=S0_SKILL,
            current_batch_evidence=copy.deepcopy(SUCCESS_EVIDENCE),
            maximum_raw_patches=5,
        ),
        ReflectorRequest(
            candidate_id="candidate",
            reflector="compliance",
            current_parent_skill=S0_SKILL,
            current_batch_evidence=copy.deepcopy(SUCCESS_EVIDENCE),
            maximum_raw_patches=4,
        ),
    ],
)
def test_reflector_prompt_rejects_role_or_budget_drift(
    invalid_request: ReflectorRequest,
) -> None:
    with pytest.raises(PromptContractError):
        build_reflector_prompts(invalid_request)


def test_manifest_points_to_unified_v03_prompt() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    learner = manifest["proposal"]["learner"]

    assert PROMPT_PATH.is_file()
    assert learner["prompt"] == PROMPT_PATH.relative_to(PROJECT_ROOT).as_posix()
    assert learner["model"] == LEARNER_MODEL
    assert learner["parameters"] == {
        "reasoning_effort": REASONING_EFFORT,
        "max_completion_tokens": MAX_COMPLETION_TOKENS,
        "temperature": None,
    }

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from src.skill_evolution.autonomous_gse_v03_benchmark_runtime import RolloutRequest
from src.learners.stwebagentbench.generate_governed_skill_v05 import (
    build_editor_prompts,
)
from src.skill_evolution.autonomous_gse_v03_proposal import EditorRequest, ProposalContext
from src.skill_evolution.autonomous_gse_v03_runtime import DeterministicDryRunAdapter
from src.skill_evolution.autonomous_gse_v05_benchmark_runtime import (
    MultiRolloutRunnerBackend,
    _v03_campaign,
    _expand_campaign,
    aggregate_selection_metrics,
    analyze_hierarchical_selection,
    build_formal_execution_plan,
    run_v05_campaign,
    validate_formal_campaign_contract,
)
from src.skill_evolution.autonomous_gse_v05_proposal import (
    RuleIdGovernedReflectionEditorProposalOperator,
    annotate_parent_skill,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CAMPAIGN_PATH = (
    PROJECT_ROOT
    / "experiments/campaigns/autonomous_gse_v05/campaign_manifest.json"
)
SCHEMA_PATH = PROJECT_ROOT / "schemas/autonomous_gse_v05_campaign.schema.json"
BATCH_MAP_PATH = (
    PROJECT_ROOT / "experiments/campaigns/autonomous_gse_v02/batch_map.json"
)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_v05_manifest_and_plan_encode_only_the_multi_rollout_campaign() -> None:
    campaign = load_json(CAMPAIGN_PATH)
    errors = list(
        Draft202012Validator(load_json(SCHEMA_PATH)).iter_errors(campaign)
    )
    assert errors == []
    validate_formal_campaign_contract(campaign, require_ready=True)

    plan = build_formal_execution_plan(campaign, load_json(BATCH_MAP_PATH))

    assert plan["headless"] is True
    assert plan["parallel_workers"] == 4
    assert plan["initial_selection"]["tasks"] == 18
    assert plan["initial_selection"]["trajectories"] == 54
    assert len(plan["steps"]) == 3
    assert all(step["training_tasks"] == 17 for step in plan["steps"])
    assert all(step["training_trajectories"] == 51 for step in plan["steps"])
    assert all(
        step["candidate_selection_tasks"] == 18 for step in plan["steps"]
    )
    assert all(
        step["candidate_selection_trajectories"] == 54
        for step in plan["steps"]
    )
    assert plan["post_hoc_training_replay"] is False
    assert plan["final_test_evaluation"] is False
    assert plan["full_experiment_seeds"] == 1


def test_rollout_counts_equal_one_preserve_the_single_rollout_pipeline() -> None:
    campaign = load_json(CAMPAIGN_PATH)
    campaign["train_rollouts_per_task"] = 1
    campaign["selection_rollouts_per_task"] = 1
    campaign["budget"] = {
        "train_trajectories": 51,
        "initial_selection_trajectories": 18,
        "maximum_candidate_selection_trajectories": 54,
        "maximum_total_trajectories": 123,
        "maximum_candidates": 3,
        "maximum_learner_calls": 9,
        "unused_budget_reallocation": "forbidden",
    }

    validate_formal_campaign_contract(campaign)
    plan = build_formal_execution_plan(campaign, load_json(BATCH_MAP_PATH))

    assert plan["initial_selection"]["trajectories"] == 18
    assert [step["training_trajectories"] for step in plan["steps"]] == [
        17,
        17,
        17,
    ]


def test_backend_expands_stable_task_rollout_units_and_matches_seeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    campaign = load_json(CAMPAIGN_PATH)
    observed = []

    def run_subprocess_rollouts(payloads, *, parallel_workers):
        observed.extend(payloads)
        paths = tuple(
            Path(
                f"/tmp/task-{item['task']['task_id']}-"
                f"rollout-{item['args']['rollout_id']}.json"
            )
            for item in payloads
        )
        return paths, {"events": [], "failures": []}

    monkeypatch.setattr(
        "src.adapters.stwebagentbench.parallel_rollout.run_subprocess_rollouts",
        run_subprocess_rollouts,
    )
    monkeypatch.setattr(
        "src.skill_evolution.autonomous_gse_v05_benchmark_runtime._write_json",
        lambda path, payload: None,
    )
    backend = MultiRolloutRunnerBackend(campaign)
    artifact = {
        "kind": "empty_skill",
        "version": "S0",
        "path": "experiments/campaigns/autonomous_gse_v03/skills/S0_empty_skill.md",
    }

    paths = backend(RolloutRequest("selection", "s0_empty_skill", artifact, (50,)))

    assert len(paths) == 3
    assert [item["args"]["rollout_id"] for item in observed] == [1, 2, 3]
    assert [item["args"]["seed"] for item in observed] == [200, 201, 202]
    assert all(item["args"]["campaign_seed"] == 200 for item in observed)
    assert all(item["args"]["headless"] is True for item in observed)


def test_selection_uses_explicit_equal_weight_template_macro_average() -> None:
    task_templates = {1: 10, 2: 10, 3: 20}
    rows = []
    for task_id, value in ((1, 1.0), (2, 0.0), (3, 1.0)):
        for rollout_id in (1, 2, 3):
            rows.append(
                {
                    "task_id": task_id,
                    "rollout_id": rollout_id,
                    "task_success": value,
                    "compliance": value,
                    "cup": value,
                }
            )

    result = aggregate_selection_metrics(
        rows, task_templates, rollouts_per_task=3
    )

    assert len(result["rollout_results"]) == 9
    assert len(result["task_means"]) == 3
    assert result["intent_template_means"] == [
        {
            "intent_template_id": 10,
            "task_count": 2,
            "task_success": 0.5,
            "compliance": 0.5,
            "cup": 0.5,
        },
        {
            "intent_template_id": 20,
            "task_count": 1,
            "task_success": 1.0,
            "compliance": 1.0,
            "cup": 1.0,
        },
    ]
    assert result["final_macro_average"] == {
        "task_success": 0.75,
        "compliance": 0.75,
        "cup": 0.75,
    }


@pytest.mark.parametrize(
    ("candidate_metrics", "decision"),
    [
        ({"task_success": 0.6, "compliance": 0.5, "cup": 0.5}, "continue_evolution"),
        ({"task_success": 0.6, "compliance": 0.4, "cup": 0.5}, "reject"),
        ({"task_success": 0.5, "compliance": 0.5, "cup": 0.5}, "reject"),
    ],
)
def test_hierarchical_gate_keeps_the_v04_pareto_rule(
    candidate_metrics: dict[str, float], decision: str
) -> None:
    parent = {
        "aggregation": {
            "final_macro_average": {
                "task_success": 0.5,
                "compliance": 0.5,
                "cup": 0.5,
            }
        }
    }
    candidate = {"aggregation": {"final_macro_average": candidate_metrics}}

    analysis = analyze_hierarchical_selection(parent, candidate)

    assert analysis["evolution_gate"]["decision"] == decision


def test_editor_dedup_preserves_all_raw_patch_source_ids() -> None:
    parent = """# SuiteCRM Operational Skill

## Planning and navigation

## Execution patterns

## Form entry and verification

## Error recovery and stopping
"""
    evidence = tuple(
        {
            "source_id": source_id,
            "state": "compliant_success",
            "task_success": True,
            "process_feedback": {
                "compliant": True,
                "violated_policies": [],
            },
        }
        for source_id in ("task_a_rollout_1", "task_a_rollout_2", "task_b_rollout_1")
    )
    raw = json.dumps(
        [
            {
                "operation": "add",
                "section": "Execution patterns",
                "target_rule_id": "",
                "text": "Verify the saved record before stopping.",
                "reason": "Repeated evidence.",
                "source_ids": [source_id],
                "repair_policy_ids": [],
            }
            for source_id in (
                "task_a_rollout_1",
                "task_a_rollout_2",
                "task_b_rollout_1",
            )
        ]
    )
    editor = json.dumps(
        [
            {
                "derived_from_patch_ids": [
                    "success_patch_001",
                    "success_patch_002",
                    "success_patch_003",
                ],
                "operation": "add",
                "section": "Execution patterns",
                "target_rule_id": "",
                "text": "Verify the saved record before stopping.",
                "reason": "Merged duplicate patches.",
                "source_ids": ["task_a_rollout_1"],
                "repair_policy_ids": [],
            }
        ]
    )
    decision = RuleIdGovernedReflectionEditorProposalOperator().propose(
        ProposalContext("candidate", parent, evidence),
        lambda request: f"<RAW_PATCHES_JSON>{raw}</RAW_PATCHES_JSON>",
        lambda request: "<RAW_PATCHES_JSON>[]</RAW_PATCHES_JSON>",
        lambda request: f"<CANONICAL_EDITS_JSON>{editor}</CANONICAL_EDITS_JSON>",
    )

    assert decision.proposal_status == "CANDIDATE"
    assert decision.applied_edits[0]["source_ids"] == [
        "task_a_rollout_1",
        "task_a_rollout_2",
        "task_b_rollout_1",
    ]


def _single_success_evidence() -> tuple[dict, ...]:
    return (
        {
            "source_id": "source_001",
            "state": "compliant_success",
            "task_success": True,
            "process_feedback": {
                "compliant": True,
                "violated_policies": [],
            },
        },
    )


def _replace_response(target: dict[str, str]) -> str:
    payload = {
        "derived_from_patch_ids": ["success_patch_001"],
        "operation": "replace",
        "section": "Planning and navigation",
        "text": "Use the corrected organizational prerequisite rule.",
        "reason": "Correct the existing rule.",
        "source_ids": ["source_001"],
        "repair_policy_ids": [],
        **target,
    }
    return f"<CANONICAL_EDITS_JSON>{json.dumps([payload])}</CANONICAL_EDITS_JSON>"


def _raw_replace_response() -> str:
    payload = {
        "operation": "replace",
        "section": "Planning and navigation",
        "target_rule_id": "rule_001",
        "text": "Use the corrected organizational prerequisite rule.",
        "reason": "Correct the existing rule.",
        "source_ids": ["source_001"],
        "repair_policy_ids": [],
    }
    return f"<RAW_PATCHES_JSON>{json.dumps([payload])}</RAW_PATCHES_JSON>"


def test_legacy_markdown_bullet_target_is_normalized_before_matching() -> None:
    parent = """# SuiteCRM Operational Skill

## Planning and navigation

- When an organizational prerequisite is required, verify it first.

## Execution patterns

## Form entry and verification

## Error recovery and stopping
"""
    decision = RuleIdGovernedReflectionEditorProposalOperator().propose(
        ProposalContext("candidate", parent, _single_success_evidence()),
        lambda request: _raw_replace_response(),
        lambda request: "<RAW_PATCHES_JSON>[]</RAW_PATCHES_JSON>",
        lambda request: _replace_response(
            {
                "target_clause": (
                    "-  When an organizational prerequisite is required,  "
                    "verify it first."
                )
            }
        ),
    )

    assert decision.proposal_status == "CANDIDATE"
    assert decision.applied_edits[0]["target_rule_id"] == "rule_001"
    assert (
        decision.applied_edits[0]["target_resolution"]
        == "normalized_target_clause"
    )
    assert "Use the corrected organizational prerequisite rule." in (
        decision.candidate_skill or ""
    )


def test_rule_id_disambiguates_identical_parent_rules() -> None:
    parent = """# SuiteCRM Operational Skill

## Planning and navigation

- Verify the prerequisite before continuing.
- Verify the prerequisite before continuing.

## Execution patterns

## Form entry and verification

## Error recovery and stopping
"""
    decision = RuleIdGovernedReflectionEditorProposalOperator().propose(
        ProposalContext("candidate", parent, _single_success_evidence()),
        lambda request: _raw_replace_response(),
        lambda request: "<RAW_PATCHES_JSON>[]</RAW_PATCHES_JSON>",
        lambda request: _replace_response({"target_rule_id": "rule_002"}),
    )

    assert decision.proposal_status == "CANDIDATE"
    assert decision.applied_edits[0]["target_rule_id"] == "rule_002"
    assert (decision.candidate_skill or "").count(
        "- Verify the prerequisite before continuing."
    ) == 1


def test_legacy_text_match_rejects_identical_rule_ambiguity() -> None:
    parent = """# SuiteCRM Operational Skill

## Planning and navigation

- Verify the prerequisite before continuing.
- Verify the prerequisite before continuing.

## Execution patterns

## Form entry and verification

## Error recovery and stopping
"""
    decision = RuleIdGovernedReflectionEditorProposalOperator().propose(
        ProposalContext("candidate", parent, _single_success_evidence()),
        lambda request: _raw_replace_response(),
        lambda request: "<RAW_PATCHES_JSON>[]</RAW_PATCHES_JSON>",
        lambda request: _replace_response(
            {"target_clause": "- Verify the prerequisite before continuing."}
        ),
    )

    assert decision.proposal_status == "NO_CANDIDATE"
    assert decision.excluded_edits == [
        {"edit_id": "edit_001", "reason": "AMBIGUOUS_TARGET_CLAUSE"}
    ]


def test_v05_editor_prompt_exposes_rule_ids_and_requires_id_targeting() -> None:
    parent = """# SuiteCRM Operational Skill

## Planning and navigation

- First rule.

## Execution patterns

- Second rule.

## Form entry and verification

## Error recovery and stopping
"""
    annotated = annotate_parent_skill(parent)
    assert "[rule_001] First rule." in annotated
    assert "[rule_002] Second rule." in annotated

    request = EditorRequest(
        candidate_id="candidate",
        current_parent_skill=parent,
        raw_patches=(
            {
                "patch_id": "success_patch_001",
                "operation": "replace",
                "section": "Planning and navigation",
                "target_rule_id": "rule_001",
                "text": "Updated first rule.",
                "source_ids": ["source_001"],
                "repair_policy_ids": [],
            },
        ),
    )
    system_prompt, user_prompt = build_editor_prompts(request)
    assert "target_rule_id" in system_prompt
    assert "full rule text as the target" in system_prompt
    assert "[rule_001] First rule." in user_prompt


def test_v05_campaign_wires_the_rule_id_operator_without_v03_changes() -> None:
    campaign = _expand_campaign(load_json(CAMPAIGN_PATH))
    initial_skill = (
        PROJECT_ROOT
        / "experiments/campaigns/autonomous_gse_v03/skills/S0_empty_skill.md"
    ).read_text(encoding="utf-8")
    adapter = DeterministicDryRunAdapter(
        ("ACCEPT", "REJECT", "NO_CANDIDATE"),
        initial_skill=initial_skill,
    )

    report = run_v05_campaign(
        _v03_campaign(campaign), load_json(BATCH_MAP_PATH), adapter
    )

    assert report["status"] == "COMPLETED"
    assert report["steps"][0]["applied_edits"][0]["target_rule_id"] == ""
    assert (
        report["steps"][0]["applied_edits"][0]["target_resolution"]
        == "not_applicable"
    )

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CAMPAIGN_SCHEMA_PATH = (
    PROJECT_ROOT / "schemas/autonomous_gse_v03_campaign.schema.json"
)
STEP_SCHEMA_PATH = PROJECT_ROOT / "schemas/autonomous_gse_v03_step.schema.json"
MANIFEST_PATH = (
    PROJECT_ROOT
    / "experiments/campaigns/autonomous_gse_v03/campaign_manifest.json"
)
S0_PATH = (
    PROJECT_ROOT
    / "experiments/campaigns/autonomous_gse_v03/skills/S0_empty_skill.md"
)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate(instance: dict, schema: dict) -> None:
    jsonschema = pytest.importorskip("jsonschema")
    validator = jsonschema.Draft202012Validator(
        schema,
        format_checker=jsonschema.FormatChecker(),
    )
    validator.check_schema(schema)
    validator.validate(instance)


def artifact(kind: str, version: str, path: str | None = None) -> dict:
    return {
        "kind": kind,
        "version": version,
        "path": path or f"artifacts/{version}.json",
    }


def raw_patch(patch_id: str, reflector: str) -> dict:
    return {
        "patch_id": patch_id,
        "reflector": reflector,
        "operation": "add",
        "section": "Execution patterns",
        "target_clause": "",
        "text": "Use the supported workflow.",
        "reason": "Current-batch evidence supports this workflow.",
        "source_ids": ["step_001_source_001"],
        "repair_policy_ids": [],
    }


def canonical_edit(edit_id: str, patch_ids: list[str]) -> dict:
    return {
        "edit_id": edit_id,
        "derived_from_patch_ids": patch_ids,
        "operation": "add",
        "section": "Execution patterns",
        "target_clause": "",
        "text": "Use the supported workflow.",
        "reason": "The Editor retained the supported workflow.",
        "source_ids": ["step_001_source_001"],
        "repair_policy_ids": [],
    }


def candidate_step() -> dict:
    patches = [
        raw_patch("success_patch_001", "success"),
        raw_patch("failure_patch_001", "failure"),
    ]
    edit = canonical_edit(
        "edit_001",
        ["success_patch_001", "failure_patch_001"],
    )
    return {
        "schema_version": "autonomous_gse_step_0.3.0",
        "protocol_version": "autonomous_gse_v03",
        "campaign_id": "autonomous_gse_v03",
        "epoch": 1,
        "step": 1,
        "status": "STEP_COMPLETED",
        "batch": {
            "batch_id": "batch_001",
            "batch_map": "experiments/campaigns/autonomous_gse_v02/batch_map.json",
            "task_ids": list(range(1, 18)),
        },
        "parent": artifact(
            "empty_skill",
            "S0",
            "experiments/campaigns/autonomous_gse_v03/skills/S0_empty_skill.md",
        ),
        "proposal_operator": "governed_reflection_editor",
        "candidate_id": "epoch_001_step_001_candidate",
        "parent_checkpoint": artifact("selection_checkpoint", "S0"),
        "proposal_budget": {
            "maximum_raw_patches_per_reflector": 4,
            "maximum_reflector_calls": 2,
            "maximum_editor_calls": 1,
            "additional_minibatching": False,
            "maximum_skill_rules": 18,
            "maximum_skill_words": 900,
            "allowed_operations": ["add", "replace", "delete"],
        },
        "data_isolation": {
            "current_batch_only": True,
            "eligible_evidence_states": [
                "compliant_success",
                "violating_success",
                "compliant_failure",
                "violating_failure",
            ],
            "selection_for_learning": "forbidden",
            "test_for_learning": "forbidden",
        },
        "proposal_status": "CANDIDATE",
        "proposal_reason": {"code": "CANDIDATE_CONSTRUCTED"},
        "raw_patches": patches,
        "canonical_edits": [edit],
        "applied_edits": [edit],
        "excluded_edits": [],
        "provenance_status": "UNVERIFIED",
        "provenance_audit": {
            "status": "UNVERIFIED",
            "issues": [{"code": "MISSING_PROVENANCE", "edit_id": "edit_001"}],
        },
        "outcome": "ACCEPT",
        "next_parent": artifact("accepted_skill", "S1"),
        "candidate": artifact(
            "candidate_skill",
            "epoch_001_step_001_candidate",
        ),
    }


def test_ready_manifest_validates() -> None:
    manifest = load_json(MANIFEST_PATH)

    validate(manifest, load_json(CAMPAIGN_SCHEMA_PATH))
    assert manifest["status"] == "ready"


def test_manifest_defines_v03_reflection_editor_contract() -> None:
    proposal = load_json(MANIFEST_PATH)["proposal"]

    assert proposal["operator"] == "governed_reflection_editor"
    assert proposal["eligible_evidence_states"] == [
        "compliant_success",
        "violating_success",
        "compliant_failure",
        "violating_failure",
    ]
    assert proposal["reflection"] == {
        "reflectors": ["success", "failure"],
        "success_states": ["compliant_success", "violating_success"],
        "failure_states": ["compliant_failure", "violating_failure"],
        "grouping_strategy": "one_group_per_outcome",
        "additional_minibatching": False,
        "maximum_raw_patches_per_reflector": 4,
        "output": "raw_patches_only",
    }
    assert proposal["editor"] == {
        "input": "current_parent_skill_and_all_raw_patches",
        "output": "canonical_edits",
        "merge": True,
        "deduplicate": True,
        "resolve_conflicts": True,
        "patch_expansion": "forbidden",
        "ranking": False,
        "top_k_selection": False,
    }
    assert proposal["deterministic_update"]["input"] == "canonical_edits_only"
    assert "maximum_edits_per_step" not in proposal


def test_manifest_keeps_provenance_non_blocking() -> None:
    manifest = load_json(MANIFEST_PATH)
    provenance = manifest["proposal"]["provenance"]

    assert provenance["mode"] == "independent_diagnostic"
    assert provenance["blocks_candidate_selection"] is False
    assert provenance["read_by_evolution_gate"] is False
    assert provenance["accepted_unverified_candidate_can_be_parent"] is True
    assert manifest["gate"]["provenance_status_is_input"] is False


def test_manifest_forbids_reflection_summary_and_selection_data() -> None:
    learner = load_json(MANIFEST_PATH)["proposal"]["learner"]
    context = learner["prompt_context"]

    assert learner["prompt"] == (
        "src/learners/stwebagentbench/generate_governed_skill_v03.py"
    )
    assert context["reflection_summary"] == "forbidden"
    assert context["selection_data"] == "forbidden"
    assert context["test_data"] == "forbidden"


def test_campaign_schema_rejects_added_ranking() -> None:
    jsonschema = pytest.importorskip("jsonschema")
    manifest = copy.deepcopy(load_json(MANIFEST_PATH))
    manifest["proposal"]["editor"]["ranking"] = True

    with pytest.raises(jsonschema.ValidationError):
        validate(manifest, load_json(CAMPAIGN_SCHEMA_PATH))


def test_explicit_s0_is_empty() -> None:
    expected = (
        "# SuiteCRM Operational Skill\n\n"
        "## Planning and navigation\n\n"
        "## Execution patterns\n\n"
        "## Form entry and verification\n\n"
        "## Error recovery and stopping\n"
    )

    assert S0_PATH.read_text(encoding="utf-8") == expected
    assert "- " not in expected


def test_step_schema_allows_accept_with_unverified_provenance() -> None:
    validate(candidate_step(), load_json(STEP_SCHEMA_PATH))


def test_step_schema_limits_each_reflector_to_four_raw_patches() -> None:
    jsonschema = pytest.importorskip("jsonschema")
    step = candidate_step()
    step["raw_patches"] = [
        raw_patch(f"success_patch_{index:03d}", "success")
        for index in range(1, 6)
    ] + [
        raw_patch(f"failure_patch_{index:03d}", "failure")
        for index in range(1, 4)
    ]

    with pytest.raises(jsonschema.ValidationError):
        validate(step, load_json(STEP_SCHEMA_PATH))


def test_step_schema_requires_canonical_edit_lineage() -> None:
    jsonschema = pytest.importorskip("jsonschema")
    step = candidate_step()
    step["canonical_edits"][0]["derived_from_patch_ids"] = []

    with pytest.raises(jsonschema.ValidationError):
        validate(step, load_json(STEP_SCHEMA_PATH))


def test_no_candidate_requires_no_applied_edits() -> None:
    jsonschema = pytest.importorskip("jsonschema")
    step = candidate_step()
    step["outcome"] = "NO_CANDIDATE"
    step["proposal_status"] = "NO_CANDIDATE"
    step["proposal_reason"] = {"code": "NO_APPLICABLE_EDITS"}

    with pytest.raises(jsonschema.ValidationError):
        validate(step, load_json(STEP_SCHEMA_PATH))

    step["applied_edits"] = []
    step.pop("candidate")
    step.pop("provenance_status")
    step.pop("provenance_audit")
    validate(step, load_json(STEP_SCHEMA_PATH))

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CAMPAIGN_SCHEMA_PATH = (
    PROJECT_ROOT / "schemas/autonomous_gse_v02_campaign.schema.json"
)
STEP_SCHEMA_PATH = PROJECT_ROOT / "schemas/autonomous_gse_v02_step.schema.json"
MANIFEST_PATH = (
    PROJECT_ROOT
    / "experiments/campaigns/autonomous_gse_v02/campaign_manifest.json"
)
S0_PATH = (
    PROJECT_ROOT
    / "experiments/campaigns/autonomous_gse_v02/skills/S0_empty_skill.md"
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


def artifact(kind: str, version: str, *, path: str | None = None) -> dict:
    return {
        "kind": kind,
        "version": version,
        "path": path or f"artifacts/{version}.json",
    }


def candidate_step() -> dict:
    return {
        "schema_version": "autonomous_gse_step_0.2.0",
        "protocol_version": "autonomous_gse_v02",
        "campaign_id": "autonomous_gse_v02",
        "epoch": 1,
        "step": 1,
        "status": "STEP_COMPLETED",
        "batch": {
            "batch_id": "batch_001",
            "batch_map": (
                "experiments/campaigns/autonomous_gse_v02/batch_map.json"
            ),
            "task_ids": list(range(1, 18)),
        },
        "parent": artifact(
            "empty_skill",
            "S0",
            path=(
                "experiments/campaigns/autonomous_gse_v02/skills/"
                "S0_empty_skill.md"
            ),
        ),
        "proposal_operator": "bounded_edit",
        "candidate_id": "epoch_001_step_001_candidate",
        "parent_checkpoint": artifact("selection_checkpoint", "S0"),
        "edit_budget": {
            "maximum_edits_per_step": 6,
            "maximum_skill_rules": 18,
            "maximum_skill_words": 900,
            "allowed_operations": ["add", "replace", "delete"],
            "selection_order": "learner_response_order",
        },
        "budget_reservation": {
            "train_trajectories": 17,
            "maximum_candidate_selection_trajectories": 18,
            "maximum_learner_calls": 1,
        },
        "data_isolation": {
            "current_batch_only": True,
            "eligible_evidence_states": [
                "compliant_success",
                "violating_success",
            ],
            "selection_for_learning": "forbidden",
            "test_for_learning": "forbidden",
        },
        "proposal_status": "CANDIDATE",
        "proposal_reason": {"code": "CANDIDATE_CONSTRUCTED"},
        "proposed_edits": [{"operation": "add"}],
        "selected_edits": [
            {
                "edit_index": 1,
                "status": "SELECTED",
                "operation": "add",
                "section": "Planning and navigation",
                "text": "- Ask for missing details.",
            }
        ],
        "excluded_edits": [],
        "provenance_status": "UNVERIFIED",
        "provenance_audit": {
            "status": "UNVERIFIED",
            "verified_edits": 0,
            "unverified_edits": 1,
            "issues": [
                {
                    "code": "UNKNOWN_SOURCE_ID",
                    "edit_index": 1,
                    "source_id": "unknown",
                }
            ],
        },
        "outcome": "ACCEPT",
        "next_parent": artifact("accepted_skill", "S1"),
        "candidate": artifact(
            "candidate_skill", "epoch_001_step_001_candidate"
        ),
    }


def test_draft_manifest_validates() -> None:
    manifest = load_json(MANIFEST_PATH)

    validate(manifest, load_json(CAMPAIGN_SCHEMA_PATH))
    assert manifest["status"] == "draft"


def test_ready_manifest_does_not_require_a_freeze_record() -> None:
    schema = load_json(CAMPAIGN_SCHEMA_PATH)
    ready = copy.deepcopy(load_json(MANIFEST_PATH))
    ready["status"] = "ready"

    validate(ready, schema)


def test_manifest_defines_v02_experimental_contract() -> None:
    manifest = load_json(MANIFEST_PATH)

    assert manifest["schedule"] == {
        "epochs": 1,
        "steps_per_epoch": 3,
        "scheduled_steps": 3,
    }
    assert manifest["proposal"]["operator"] == "bounded_edit"
    assert manifest["proposal"]["maximum_edits_per_step"] == 6
    assert manifest["proposal"]["eligible_evidence_states"] == [
        "compliant_success",
        "violating_success",
    ]
    assert manifest["proposal"]["provenance"][
        "blocks_candidate_selection"
    ] is False
    assert manifest["proposal"]["provenance"][
        "accepted_unverified_candidate_can_be_parent"
    ] is True
    assert manifest["proposal"]["history"] == {
        "structured_proposal_reason": True,
        "selected_edits": "saved_as_accepted_edit_history",
        "excluded_edits": (
            "saved_as_rejected_edit_history_with_structured_reason"
        ),
        "rejected_edit_memory_to_learner": "forbidden",
    }
    assert manifest["proposal"]["learner"]["prompt_context"] == {
        "current_parent_skill": "required",
        "current_batch_success_evidence": "required",
        "allowed_source_ids": "required_explicit_whitelist",
        "allowed_repair_policy_ids_by_source": (
            "required_explicit_whitelist"
        ),
        "selection_data": "forbidden",
        "test_data": "forbidden",
    }
    assert manifest["gate"]["provenance_status_is_input"] is False
    assert manifest["step_outcomes"] == [
        "ACCEPT",
        "REJECT",
        "NO_CANDIDATE",
        "INTEGRITY_FAILURE",
    ]
    assert manifest["budget"]["maximum_total_trajectories"] == 123
    assert manifest["test"]["authorized"] is False


def test_manifest_keeps_protocol_configuration_compact() -> None:
    manifest = load_json(MANIFEST_PATH)

    assert manifest["proposal"]["operator"] == "bounded_edit"
    assert manifest["schedule"]["epochs"] == 1
    assert manifest["schedule"]["scheduled_steps"] == 3


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("proposal", "maximum_edits_per_step"), 5),
        (("proposal", "operator"), "bootstrap"),
        (("proposal", "learner", "prompt_context", "allowed_source_ids"), None),
        (
            (
                "proposal",
                "learner",
                "prompt_context",
                "allowed_repair_policy_ids_by_source",
            ),
            None,
        ),
    ],
)
def test_campaign_schema_rejects_protocol_drift(
    path: tuple[str, ...],
    value: object,
) -> None:
    jsonschema = pytest.importorskip("jsonschema")
    manifest = copy.deepcopy(load_json(MANIFEST_PATH))
    target = manifest
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value

    with pytest.raises(jsonschema.ValidationError):
        validate(manifest, load_json(CAMPAIGN_SCHEMA_PATH))


def test_explicit_s0_is_empty_and_path_bound() -> None:
    manifest = load_json(MANIFEST_PATH)
    expected = (
        "# SuiteCRM Operational Skill\n\n"
        "## Planning and navigation\n\n"
        "## Execution patterns\n\n"
        "## Form entry and verification\n\n"
        "## Error recovery and stopping\n"
    )

    assert S0_PATH.read_text(encoding="utf-8") == expected
    assert "- " not in expected
    assert manifest["initial_parent"]["path"] == S0_PATH.relative_to(
        PROJECT_ROOT
    ).as_posix()
    assert manifest["initial_parent"]["optimizer_semantics"] == (
        "explicit_empty_skill_document"
    )
    assert manifest["initial_parent"]["rollout_semantics"] == (
        "benchmark_default_prompt_without_learned_skill_injection"
    )


def test_step_schema_allows_accept_with_unverified_provenance() -> None:
    validate(candidate_step(), load_json(STEP_SCHEMA_PATH))


def test_step_schema_keeps_provenance_diagnostic_consistent() -> None:
    jsonschema = pytest.importorskip("jsonschema")
    step = candidate_step()
    step["provenance_audit"]["status"] = "VERIFIED"

    with pytest.raises(jsonschema.ValidationError):
        validate(step, load_json(STEP_SCHEMA_PATH))


def test_step_schema_rejects_changed_edit_budget() -> None:
    jsonschema = pytest.importorskip("jsonschema")
    step = candidate_step()
    step["edit_budget"]["maximum_edits_per_step"] = 5

    with pytest.raises(jsonschema.ValidationError):
        validate(step, load_json(STEP_SCHEMA_PATH))


def test_no_candidate_requires_structured_no_candidate_reason() -> None:
    jsonschema = pytest.importorskip("jsonschema")
    step = candidate_step()
    step["outcome"] = "NO_CANDIDATE"
    step["proposal_status"] = "NO_CANDIDATE"
    step["selected_edits"] = []
    step.pop("candidate")
    step.pop("provenance_status")
    step.pop("provenance_audit")

    with pytest.raises(jsonschema.ValidationError):
        validate(step, load_json(STEP_SCHEMA_PATH))

    step["proposal_reason"] = {"code": "NO_APPLICABLE_EDITS"}
    validate(step, load_json(STEP_SCHEMA_PATH))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("proposal_operator", "bootstrap"),
        ("outcome", "INVALID_PROPOSAL"),
    ],
)
def test_step_schema_rejects_removed_v01_semantics(
    field: str,
    value: str,
) -> None:
    jsonschema = pytest.importorskip("jsonschema")
    step = candidate_step()
    step[field] = value

    with pytest.raises(jsonschema.ValidationError):
        validate(step, load_json(STEP_SCHEMA_PATH))


def test_step_one_requires_explicit_empty_s0() -> None:
    jsonschema = pytest.importorskip("jsonschema")
    step = candidate_step()
    step["parent"] = artifact("accepted_skill", "S1")

    with pytest.raises(jsonschema.ValidationError):
        validate(step, load_json(STEP_SCHEMA_PATH))


@pytest.mark.parametrize("parent", [None, {}])
def test_step_one_rejects_missing_or_implicit_s0(parent: object) -> None:
    jsonschema = pytest.importorskip("jsonschema")
    step = candidate_step()
    if parent is None:
        step.pop("parent")
    else:
        step["parent"] = parent

    with pytest.raises(jsonschema.ValidationError):
        validate(step, load_json(STEP_SCHEMA_PATH))

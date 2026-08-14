"""Schema and semantic contract tests for Autonomous GSE v0.1."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from src.skill_evolution.two_dimensional_gate import analyze_candidate


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CAMPAIGN_SCHEMA_PATH = (
    PROJECT_ROOT / "schemas/autonomous_gse_v01_campaign.schema.json"
)
STEP_SCHEMA_PATH = PROJECT_ROOT / "schemas/autonomous_gse_v01_step.schema.json"
MANIFEST_PATH = (
    PROJECT_ROOT
    / "experiments/campaigns/autonomous_gse_v01/campaign_manifest.json"
)
BATCH_MAP_PATH = (
    PROJECT_ROOT / "experiments/campaigns/autonomous_gse_v01/batch_map.json"
)
REPORT_PATH = (
    PROJECT_ROOT / "experiments/results/autonomous_gse_v01/campaign_report.json"
)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate(instance: dict, schema: dict) -> None:
    jsonschema = pytest.importorskip("jsonschema")
    validator = jsonschema.Draft202012Validator(schema)
    validator.check_schema(schema)
    validator.validate(instance)


def artifact(kind: str, version: str, name: str) -> dict[str, str]:
    return {"kind": kind, "version": version, "path": f"artifacts/{name}"}


def step_manifest(*, parent_kind: str, parent_version: str, operator: str) -> dict:
    return {
        "schema_version": "autonomous_gse_step_0.1.0",
        "protocol_version": "autonomous_gse_v01",
        "campaign_id": "autonomous_gse_v01",
        "epoch": 1,
        "step": 1,
        "status": "STEP_REGISTERED",
        "batch": {
            "batch_id": "batch_001",
            "batch_map_path": (
                "experiments/campaigns/autonomous_gse_v01/batch_map.json"
            ),
            "task_ids": list(range(1, 18)),
        },
        "parent": artifact(parent_kind, parent_version, "parent.json"),
        "proposal_operator": operator,
        "candidate_id": "epoch_001_step_001_candidate",
        "parent_checkpoint": artifact(
            "selection_checkpoint", parent_version, "checkpoint.json"
        ),
        "budget_reservation": {
            "train_trajectories": 17,
            "maximum_candidate_selection_trajectories": 18,
            "maximum_learner_calls": 1,
        },
        "data_isolation": {
            "current_batch_only": True,
            "selection_for_learning": "forbidden",
            "test_for_learning": "forbidden",
        },
    }


def gate_rows(before: tuple[bool, bool], after: tuple[bool, bool]) -> list[dict]:
    return [
        {
            "method": method,
            "task_id": 1,
            "task_success": state[0],
            "compliant": state[1],
            "severe_violation": False,
        }
        for method, state in (("parent", before), ("candidate", after))
    ]


def test_campaign_manifest_is_a_completed_path_based_record() -> None:
    manifest = load_json(MANIFEST_PATH)

    assert manifest["status"] == "completed"
    assert manifest["completed_at"] == "2026-08-13"
    assert set(manifest["initial_parent"]) == {"kind", "version", "path"}
    assert isinstance(manifest["train"]["source_manifest"], str)
    assert isinstance(manifest["train"]["batch_map"], str)
    assert manifest["schedule"] == {
        "epochs": 1,
        "steps_per_epoch": 3,
        "scheduled_steps": 3,
    }
    assert manifest["budget"]["maximum_total_trajectories"] == 123
    assert manifest["test"]["authorized"] is False


def test_campaign_manifest_validates_against_schema() -> None:
    validate(load_json(MANIFEST_PATH), load_json(CAMPAIGN_SCHEMA_PATH))


@pytest.mark.parametrize(
    ("section", "field", "value"),
    [
        ("schedule", "scheduled_steps", 4),
        ("budget", "maximum_total_trajectories", 124),
        ("proposal", "maximum_learner_calls", 4),
        ("test", "authorized", True),
    ],
)
def test_campaign_schema_rejects_semantic_drift(
    section: str, field: str, value: object
) -> None:
    jsonschema = pytest.importorskip("jsonschema")
    manifest = load_json(MANIFEST_PATH)
    manifest[section][field] = value

    with pytest.raises(jsonschema.ValidationError):
        validate(manifest, load_json(CAMPAIGN_SCHEMA_PATH))


def test_recorded_batch_map_preserves_the_executed_assignment() -> None:
    batch_map = load_json(BATCH_MAP_PATH)
    assignments = [
        assignment
        for batch in batch_map["batches"]
        for assignment in batch["assignments"]
    ]

    assert batch_map["status"] == "frozen"
    assert len(batch_map["batches"]) == 3
    assert all(len(batch["assignments"]) == 17 for batch in batch_map["batches"])
    assert len({item["task_id"] for item in assignments}) == 51
    assert all(
        len({item["intent_template_id"] for item in batch["assignments"]}) == 17
        for batch in batch_map["batches"]
    )


def test_step_schema_dispatches_parent_kind() -> None:
    schema = load_json(STEP_SCHEMA_PATH)
    validate(
        step_manifest(
            parent_kind="no_skill", parent_version="S0", operator="bootstrap"
        ),
        schema,
    )
    validate(
        step_manifest(
            parent_kind="accepted_skill",
            parent_version="S1",
            operator="incremental",
        ),
        schema,
    )


def test_step_schema_rejects_wrong_operator() -> None:
    jsonschema = pytest.importorskip("jsonschema")
    manifest = step_manifest(
        parent_kind="no_skill", parent_version="S0", operator="incremental"
    )

    with pytest.raises(jsonschema.ValidationError):
        validate(manifest, load_json(STEP_SCHEMA_PATH))


def test_completed_step_requires_outcome_and_next_parent() -> None:
    jsonschema = pytest.importorskip("jsonschema")
    manifest = step_manifest(
        parent_kind="accepted_skill", parent_version="S1", operator="incremental"
    )
    manifest.update(
        {
            "status": "STEP_COMPLETED",
            "outcome": "REJECT",
            "candidate": artifact("candidate_skill", "candidate_001", "skill.md"),
            "next_parent": copy.deepcopy(manifest["parent"]),
        }
    )
    validate(manifest, load_json(STEP_SCHEMA_PATH))

    manifest.pop("outcome")
    with pytest.raises(jsonschema.ValidationError):
        validate(manifest, load_json(STEP_SCHEMA_PATH))


@pytest.mark.parametrize(
    ("before", "after", "expected"),
    [
        ((False, False), (True, False), "continue_evolution"),
        ((False, False), (False, True), "continue_evolution"),
        ((False, False), (False, False), "reject"),
        ((True, True), (False, True), "reject"),
    ],
)
def test_gate_semantic_golden_cases(
    before: tuple[bool, bool], after: tuple[bool, bool], expected: str
) -> None:
    result = analyze_candidate(gate_rows(before, after), "parent", "candidate")

    assert result["evolution_gate"]["decision"] == expected


def test_campaign_report_keeps_the_recorded_v01_result() -> None:
    report = load_json(REPORT_PATH)

    assert report["status"] == "COMPLETED"
    assert [step["outcome"] for step in report["steps"]] == [
        "INVALID_PROPOSAL",
        "ACCEPT",
        "INVALID_PROPOSAL",
    ]
    assert report["final_parent"]["version"] == "S1"
    assert report["budget_usage"]["total_trajectories"] == 87
    assert report["side_effects"]["api_calls"] == 3
    assert report["side_effects"]["browser_calls"] == 87

"""No-API runtime adapter tests for Autonomous GSE v0.1."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from src.skill_evolution.autonomous_gse_runtime import (
    DeterministicDryRunAdapter,
    RuntimeContractError,
    run_dry_campaign,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CAMPAIGN_PATH = (
    PROJECT_ROOT
    / "experiments/campaigns/autonomous_gse_v01/campaign_manifest.json"
)
BATCH_MAP_PATH = (
    PROJECT_ROOT / "experiments/campaigns/autonomous_gse_v01/batch_map.json"
)
STEP_SCHEMA_PATH = PROJECT_ROOT / "schemas/autonomous_gse_v01_step.schema.json"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def run(outcomes: tuple[str, str, str]) -> dict:
    return run_dry_campaign(
        load_json(CAMPAIGN_PATH),
        load_json(BATCH_MAP_PATH),
        DeterministicDryRunAdapter(outcomes),
    )


def validate_steps(report: dict) -> None:
    jsonschema = pytest.importorskip("jsonschema")
    schema = load_json(STEP_SCHEMA_PATH)
    validator = jsonschema.Draft202012Validator(schema)
    for step in report["steps"]:
        validator.validate(step)


def test_no_api_dry_run_completes_three_steps() -> None:
    report = run(("ACCEPT", "REJECT", "NO_CANDIDATE"))

    assert report["status"] == "COMPLETED"
    assert report["mode"] == "deterministic_no_api_dry_run"
    assert [step["batch"]["batch_id"] for step in report["steps"]] == [
        "batch_001",
        "batch_002",
        "batch_003",
    ]
    assert [step["outcome"] for step in report["steps"]] == [
        "ACCEPT",
        "REJECT",
        "NO_CANDIDATE",
    ]
    assert [step["proposal_operator"] for step in report["steps"]] == [
        "bootstrap",
        "incremental",
        "incremental",
    ]
    assert report["final_parent"]["version"] == "S1"
    assert report["budget_usage"] == {
        "train_trajectories": 51,
        "initial_selection_trajectories": 18,
        "candidate_selection_trajectories": 36,
        "total_trajectories": 105,
        "candidates": 2,
        "learner_calls": 2,
        "test_trajectories": 0,
    }
    assert report["side_effects"] == {
        "api_calls": 0,
        "browser_calls": 0,
        "database_calls": 0,
        "filesystem_writes": 0,
    }
    validate_steps(report)


def test_dry_run_is_deterministic_and_does_not_mutate_inputs() -> None:
    campaign = load_json(CAMPAIGN_PATH)
    batch_map = load_json(BATCH_MAP_PATH)
    original_campaign = copy.deepcopy(campaign)
    original_batch_map = copy.deepcopy(batch_map)

    first = run_dry_campaign(
        campaign,
        batch_map,
        DeterministicDryRunAdapter(("ACCEPT", "REJECT", "NO_CANDIDATE")),
    )
    second = run_dry_campaign(
        campaign,
        batch_map,
        DeterministicDryRunAdapter(("ACCEPT", "REJECT", "NO_CANDIDATE")),
    )

    assert first == second
    assert campaign == original_campaign
    assert batch_map == original_batch_map


def test_all_accepts_reach_budget_ceiling_and_s3() -> None:
    report = run(("ACCEPT", "ACCEPT", "ACCEPT"))

    assert report["final_parent"]["version"] == "S3"
    assert report["budget_usage"]["total_trajectories"] == 123
    assert report["budget_usage"]["candidate_selection_trajectories"] == 54
    assert report["budget_usage"]["learner_calls"] == 3
    assert report["budget_usage"]["candidates"] == 3


def test_no_candidate_keeps_s0_and_bootstrap_dispatch() -> None:
    report = run(("NO_CANDIDATE", "ACCEPT", "REJECT"))

    assert [step["proposal_operator"] for step in report["steps"]] == [
        "bootstrap",
        "bootstrap",
        "incremental",
    ]
    assert report["steps"][0]["next_parent"]["version"] == "S0"
    assert report["final_parent"]["version"] == "S1"


def test_invalid_proposal_skips_candidate_selection() -> None:
    report = run(("INVALID_PROPOSAL", "NO_CANDIDATE", "ACCEPT"))
    selection_steps = [
        entry["step"]
        for entry in report["runtime_trace"]
        if entry["operation"] == "run_candidate_selection"
    ]

    assert selection_steps == [3]
    assert report["budget_usage"]["candidate_selection_trajectories"] == 18
    assert report["budget_usage"]["learner_calls"] == 2


def test_proposal_boundary_contains_no_selection_or_test_data() -> None:
    report = run(("ACCEPT", "REJECT", "NO_CANDIDATE"))
    proposal_entries = [
        entry
        for entry in report["runtime_trace"]
        if entry["operation"] == "propose"
    ]

    assert len(proposal_entries) == 3
    for entry in proposal_entries:
        assert set(entry) == {
            "operation",
            "step",
            "operator",
            "parent_version",
            "batch_id",
            "task_ids",
            "experience_path",
        }
        assert len(entry["task_ids"]) == 17
        assert "selection" not in entry
        assert "test" not in entry


@pytest.mark.parametrize(
    "outcomes",
    [
        ("ACCEPT", "REJECT"),
        ("ACCEPT", "REJECT", "INTEGRITY_FAILURE"),
        ("ACCEPT", "REJECT", "unknown"),
    ],
)
def test_dry_run_rejects_invalid_outcome_plan(outcomes: tuple[str, ...]) -> None:
    with pytest.raises(RuntimeContractError):
        DeterministicDryRunAdapter(outcomes)


def test_runtime_rejects_semantically_invalid_checkpoint() -> None:
    class BadCheckpointAdapter(DeterministicDryRunAdapter):
        def create_initial_checkpoint(
            self,
            campaign_id: str,
            parent: dict,
            task_count: int,
        ) -> dict:
            checkpoint_artifact = super().create_initial_checkpoint(
                campaign_id, parent, task_count
            )
            checkpoint_artifact["kind"] = "train_trajectory_set"
            return checkpoint_artifact

    with pytest.raises(RuntimeContractError, match="selection_checkpoint"):
        run_dry_campaign(
            load_json(CAMPAIGN_PATH),
            load_json(BATCH_MAP_PATH),
            BadCheckpointAdapter(("ACCEPT", "REJECT", "NO_CANDIDATE")),
        )

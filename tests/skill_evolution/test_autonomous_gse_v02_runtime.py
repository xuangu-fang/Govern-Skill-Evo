"""No-API, no-write runtime tests for Autonomous GSE v0.2."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from src.skill_evolution.autonomous_gse_v02_proposal import LearnerRequest
from src.skill_evolution.autonomous_gse_v02_runtime import (
    DeterministicDryRunAdapter,
    RuntimeContractError,
    run_dry_campaign,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CAMPAIGN_PATH = (
    PROJECT_ROOT
    / "experiments/campaigns/autonomous_gse_v02/campaign_manifest.json"
)
BATCH_MAP_PATH = (
    PROJECT_ROOT / "experiments/campaigns/autonomous_gse_v02/batch_map.json"
)
STEP_SCHEMA_PATH = PROJECT_ROOT / "schemas/autonomous_gse_v02_step.schema.json"
S0_PATH = (
    PROJECT_ROOT
    / "experiments/campaigns/autonomous_gse_v02/skills/S0_empty_skill.md"
)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def ready_campaign() -> dict:
    campaign = load_json(CAMPAIGN_PATH)
    campaign["status"] = "ready"
    return campaign


def run(
    outcomes: tuple[str, str, str],
    *,
    unverified_steps: tuple[int, ...] = (),
) -> dict:
    adapter = DeterministicDryRunAdapter(
        outcomes,
        initial_skill=S0_PATH.read_text(encoding="utf-8"),
        unverified_steps=unverified_steps,
    )
    return run_dry_campaign(
        ready_campaign(),
        load_json(BATCH_MAP_PATH),
        adapter,
    )


def validate_steps(report: dict) -> None:
    jsonschema = pytest.importorskip("jsonschema")
    schema = load_json(STEP_SCHEMA_PATH)
    validator = jsonschema.Draft202012Validator(schema)
    for step in report["steps"]:
        validator.validate(step)


def test_dry_run_completes_three_steps_without_side_effects() -> None:
    report = run(("ACCEPT", "REJECT", "NO_CANDIDATE"))

    assert report["schema_version"] == "autonomous_gse_dry_run_0.2.0"
    assert report["status"] == "COMPLETED"
    assert report["mode"] == "deterministic_no_api_no_write_dry_run"
    assert [step["outcome"] for step in report["steps"]] == [
        "ACCEPT",
        "REJECT",
        "NO_CANDIDATE",
    ]
    assert [step["proposal_operator"] for step in report["steps"]] == [
        "bounded_edit",
        "bounded_edit",
        "bounded_edit",
    ]
    assert [step["batch"]["batch_id"] for step in report["steps"]] == [
        "batch_001",
        "batch_002",
        "batch_003",
    ]
    assert report["final_parent"]["version"] == "S1"
    assert report["budget_usage"] == {
        "train_trajectories": 51,
        "initial_selection_trajectories": 18,
        "candidate_selection_trajectories": 36,
        "total_trajectories": 105,
        "candidates": 2,
        "learner_calls": 3,
        "test_trajectories": 0,
    }
    assert report["side_effects"] == {
        "api_calls": 0,
        "browser_calls": 0,
        "database_calls": 0,
        "filesystem_writes": 0,
    }
    validate_steps(report)


def test_all_accepts_reach_s3_and_exact_budget_ceiling() -> None:
    report = run(("ACCEPT", "ACCEPT", "ACCEPT"))

    assert report["final_parent"]["version"] == "S3"
    assert report["budget_usage"]["total_trajectories"] == 123
    assert report["budget_usage"]["candidate_selection_trajectories"] == 54
    assert report["budget_usage"]["candidates"] == 3
    assert report["budget_usage"]["learner_calls"] == 3


def test_no_candidate_keeps_s0_and_skips_only_its_selection() -> None:
    report = run(("NO_CANDIDATE", "ACCEPT", "REJECT"))
    selection_steps = [
        event["step"]
        for event in report["runtime_trace"]
        if event["operation"] == "run_candidate_selection"
    ]

    assert report["steps"][0]["next_parent"]["version"] == "S0"
    assert report["steps"][1]["parent"]["version"] == "S0"
    assert report["steps"][1]["proposal_operator"] == "bounded_edit"
    assert selection_steps == [2, 3]
    assert report["budget_usage"]["candidate_selection_trajectories"] == 36


def test_unverified_candidate_is_selected_accepted_and_reused() -> None:
    report = run(
        ("ACCEPT", "REJECT", "NO_CANDIDATE"),
        unverified_steps=(1,),
    )

    assert report["steps"][0]["provenance_status"] == "UNVERIFIED"
    assert report["steps"][0]["outcome"] == "ACCEPT"
    assert report["steps"][1]["parent"]["version"] == "S1"
    assert any(
        event["operation"] == "run_candidate_selection" and event["step"] == 1
        for event in report["runtime_trace"]
    )


def test_runtime_is_deterministic_and_does_not_mutate_inputs() -> None:
    campaign = ready_campaign()
    batch_map = load_json(BATCH_MAP_PATH)
    original_campaign = copy.deepcopy(campaign)
    original_batch_map = copy.deepcopy(batch_map)

    first = run_dry_campaign(
        campaign,
        batch_map,
        DeterministicDryRunAdapter(
            ("ACCEPT", "REJECT", "NO_CANDIDATE"),
            initial_skill=S0_PATH.read_text(encoding="utf-8"),
        ),
    )
    second = run_dry_campaign(
        campaign,
        batch_map,
        DeterministicDryRunAdapter(
            ("ACCEPT", "REJECT", "NO_CANDIDATE"),
            initial_skill=S0_PATH.read_text(encoding="utf-8"),
        ),
    )

    assert first == second
    assert campaign == original_campaign
    assert batch_map == original_batch_map


def test_learner_boundary_contains_only_v02_prompt_context() -> None:
    class ObservingAdapter(DeterministicDryRunAdapter):
        def __init__(self) -> None:
            super().__init__(
                ("ACCEPT", "REJECT", "NO_CANDIDATE"),
                initial_skill=S0_PATH.read_text(encoding="utf-8"),
            )
            self.requests: list[LearnerRequest] = []

        def learner_response(self, step: dict, request: LearnerRequest) -> str:
            self.requests.append(copy.deepcopy(request))
            return super().learner_response(step, request)

    adapter = ObservingAdapter()
    run_dry_campaign(ready_campaign(), load_json(BATCH_MAP_PATH), adapter)

    assert len(adapter.requests) == 3
    for request in adapter.requests:
        assert set(request.__dict__) == {
            "candidate_id",
            "current_parent_skill",
            "current_batch_success_evidence",
            "maximum_edits",
            "allowed_source_ids",
            "allowed_repair_policy_ids_by_source",
        }
        assert request.maximum_edits == 6
        assert request.allowed_source_ids == ("source_001", "source_002")


@pytest.mark.parametrize(
    "outcomes",
    [
        ("ACCEPT", "REJECT"),
        ("ACCEPT", "INVALID_PROPOSAL", "REJECT"),
        ("ACCEPT", "INTEGRITY_FAILURE", "REJECT"),
        ("ACCEPT", "unknown", "REJECT"),
    ],
)
def test_adapter_rejects_invalid_outcome_plan(outcomes: tuple[str, ...]) -> None:
    with pytest.raises(RuntimeContractError):
        DeterministicDryRunAdapter(
            outcomes,
            initial_skill=S0_PATH.read_text(encoding="utf-8"),
        )


def test_runtime_rejects_adapter_that_declares_a_side_effect() -> None:
    class WritingAdapter(DeterministicDryRunAdapter):
        @property
        def side_effects(self) -> dict[str, int]:
            effects = super().side_effects
            effects["filesystem_writes"] = 1
            return effects

    adapter = WritingAdapter(
        ("ACCEPT", "REJECT", "NO_CANDIDATE"),
        initial_skill=S0_PATH.read_text(encoding="utf-8"),
    )

    with pytest.raises(RuntimeContractError, match="zero side effects"):
        run_dry_campaign(ready_campaign(), load_json(BATCH_MAP_PATH), adapter)

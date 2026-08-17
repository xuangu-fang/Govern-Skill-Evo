"""No-API, no-write runtime tests for Autonomous GSE v0.3."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from src.skill_evolution.autonomous_gse_v03_proposal import (
    EditorRequest,
    ReflectorRequest,
)
from src.skill_evolution.autonomous_gse_v03_runtime import (
    DeterministicDryRunAdapter,
    RuntimeContractError,
    run_dry_campaign,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CAMPAIGN_PATH = (
    PROJECT_ROOT
    / "experiments/campaigns/autonomous_gse_v03/campaign_manifest.json"
)
BATCH_MAP_PATH = (
    PROJECT_ROOT / "experiments/campaigns/autonomous_gse_v02/batch_map.json"
)
STEP_SCHEMA_PATH = PROJECT_ROOT / "schemas/autonomous_gse_v03_step.schema.json"
S0_PATH = (
    PROJECT_ROOT
    / "experiments/campaigns/autonomous_gse_v03/skills/S0_empty_skill.md"
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

    assert report["schema_version"] == "autonomous_gse_dry_run_0.3.0"
    assert report["status"] == "COMPLETED"
    assert report["mode"] == "deterministic_no_api_no_write_dry_run"
    assert [step["outcome"] for step in report["steps"]] == [
        "ACCEPT",
        "REJECT",
        "NO_CANDIDATE",
    ]
    assert [step["proposal_operator"] for step in report["steps"]] == [
        "governed_reflection_editor",
        "governed_reflection_editor",
        "governed_reflection_editor",
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
        "learner_calls": 8,
        "test_trajectories": 0,
    }
    assert report["side_effects"] == {
        "api_calls": 0,
        "browser_calls": 0,
        "database_calls": 0,
        "filesystem_writes": 0,
    }

    for step in report["steps"][:2]:
        assert [patch["reflector"] for patch in step["raw_patches"]] == [
            "success",
            "failure",
        ]
        assert len(step["canonical_edits"]) == 1
        assert len(step["applied_edits"]) == 1
    assert report["steps"][2]["raw_patches"] == []
    assert report["steps"][2]["canonical_edits"] == []
    validate_steps(report)


def test_all_accepts_reach_s3_and_exact_budget_ceiling() -> None:
    report = run(("ACCEPT", "ACCEPT", "ACCEPT"))

    assert report["final_parent"]["version"] == "S3"
    assert report["budget_usage"]["total_trajectories"] == 123
    assert report["budget_usage"]["candidate_selection_trajectories"] == 54
    assert report["budget_usage"]["candidates"] == 3
    assert report["budget_usage"]["learner_calls"] == 9


def test_no_candidate_uses_two_reflectors_and_skips_editor_and_selection() -> None:
    report = run(("NO_CANDIDATE", "ACCEPT", "REJECT"))
    first_step_calls = [
        event
        for event in report["runtime_trace"]
        if event.get("step") == 1
        and event["operation"] in {"reflect", "edit", "run_candidate_selection"}
    ]

    observed_calls = [
        (event["operation"], event.get("reflector"))
        for event in first_step_calls
    ]
    assert observed_calls == [
        ("reflect", "success"),
        ("reflect", "failure"),
    ]
    assert report["steps"][0]["next_parent"]["version"] == "S0"
    assert report["steps"][1]["parent"]["version"] == "S0"
    assert report["budget_usage"]["candidate_selection_trajectories"] == 36
    assert report["budget_usage"]["learner_calls"] == 8


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


def test_learner_boundaries_route_two_outcomes_without_summary_data() -> None:
    class ObservingAdapter(DeterministicDryRunAdapter):
        def __init__(self) -> None:
            super().__init__(
                ("ACCEPT", "REJECT", "NO_CANDIDATE"),
                initial_skill=S0_PATH.read_text(encoding="utf-8"),
            )
            self.requests: list[ReflectorRequest | EditorRequest] = []

        def learner_response(
            self,
            step: dict,
            request: ReflectorRequest | EditorRequest,
        ) -> str:
            self.requests.append(copy.deepcopy(request))
            return super().learner_response(step, request)

    adapter = ObservingAdapter()
    run_dry_campaign(ready_campaign(), load_json(BATCH_MAP_PATH), adapter)

    reflectors = [
        request
        for request in adapter.requests
        if isinstance(request, ReflectorRequest)
    ]
    editors = [
        request for request in adapter.requests if isinstance(request, EditorRequest)
    ]
    assert len(reflectors) == 6
    assert len(editors) == 2
    for request in reflectors:
        assert set(request.__dict__) == {
            "candidate_id",
            "reflector",
            "current_parent_skill",
            "current_batch_evidence",
            "maximum_raw_patches",
        }
        assert request.maximum_raw_patches == 4
        states = {item["state"] for item in request.current_batch_evidence}
        if request.reflector == "success":
            assert states == {"compliant_success", "violating_success"}
        else:
            assert states == {"compliant_failure", "violating_failure"}
    for request in editors:
        assert set(request.__dict__) == {
            "candidate_id",
            "current_parent_skill",
            "raw_patches",
        }
        assert [patch["reflector"] for patch in request.raw_patches] == [
            "success",
            "failure",
        ]


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

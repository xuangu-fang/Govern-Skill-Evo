from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

import src.skill_evolution.autonomous_gse_v07_benchmark_runtime as runtime
from src.skill_evolution.autonomous_gse_v03_controller import reduce_step
from src.skill_evolution.autonomous_gse_v07_benchmark_runtime import (
    _controller_campaign,
    build_formal_execution_plan,
    main,
    validate_formal_campaign_contract,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CAMPAIGN_PATH = (
    PROJECT_ROOT
    / "experiments/campaigns/autonomous_gse_v07/campaign_manifest.json"
)
SCHEMA_PATH = PROJECT_ROOT / "schemas/autonomous_gse_v07_campaign.schema.json"
BATCH_MAP_PATH = (
    PROJECT_ROOT / "experiments/campaigns/autonomous_gse_v02/batch_map.json"
)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_v07_manifest_and_plan_reuse_v05_formal_campaign() -> None:
    campaign = load_json(CAMPAIGN_PATH)
    errors = list(
        Draft202012Validator(load_json(SCHEMA_PATH)).iter_errors(campaign)
    )
    assert errors == []
    validate_formal_campaign_contract(campaign, require_ready=True)

    plan = build_formal_execution_plan(campaign, load_json(BATCH_MAP_PATH))

    assert plan["schema_version"] == "autonomous_gse_formal_plan_0.7.0"
    assert plan["campaign_id"] == "autonomous_gse_v07"
    assert plan["proposal_pipeline"] == "diagnosis_driven_bounded_edit"
    assert len(plan["steps"]) == 3
    assert all(step["training_trajectories"] == 51 for step in plan["steps"])
    assert all(step["maximum_diagnosis_calls"] == 51 for step in plan["steps"])
    assert all(step["maximum_editor_calls"] == 1 for step in plan["steps"])
    assert all(step["maximum_learner_calls"] == 52 for step in plan["steps"])
    assert all(
        "maximum_raw_patches_per_reflector" not in step for step in plan["steps"]
    )
    assert plan["maximum_budget"]["maximum_learner_calls"] == 156


def test_v07_plan_cli_uses_the_formal_manifest(capsys) -> None:
    assert main(["plan", "--campaign", str(CAMPAIGN_PATH)]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["campaign_id"] == "autonomous_gse_v07"
    assert output["proposal_pipeline"] == "diagnosis_driven_bounded_edit"


def test_v07_controller_path_does_not_apply_the_reflector_eight_signal_cap() -> None:
    campaign = _controller_campaign(runtime._expand_campaign(load_json(CAMPAIGN_PATH)))
    step = runtime._v07_step_registrar(
        campaign,
        load_json(BATCH_MAP_PATH),
        step=1,
        parent=campaign["initial_parent"],
        parent_checkpoint={
            "kind": "selection_checkpoint",
            "version": "S0",
            "path": "memory://s0.json",
        },
    )
    for event_type in (
        "TRAIN_STARTED",
        "TRAIN_COMPLETED",
        "TRAIN_VALIDATED",
        "EXPERIENCE_FROZEN",
        "PROPOSAL_STARTED",
    ):
        step = reduce_step(step, {"type": event_type}).step

    result = reduce_step(
        step,
        {
            "type": "NO_CANDIDATE",
            "proposal_reason": {"code": "NO_APPLICABLE_EDITS"},
            "raw_patches": [
                {"patch_id": f"diagnosis_{index:03d}"}
                for index in range(1, 11)
            ],
            "canonical_edits": [],
            "applied_edits": [],
            "excluded_edits": [],
        },
    )

    assert result.step["outcome"] == "NO_CANDIDATE"
    assert len(result.step["raw_patches"]) == 10
    assert result.step["proposal_budget"]["eligible_update_diagnoses"] == (
        "all_valid_updates"
    )
    assert "maximum_raw_patches_per_reflector" not in result.step["proposal_budget"]


def test_formal_run_projects_v07_onto_v03_controller(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    campaign = load_json(CAMPAIGN_PATH)
    controller = _controller_campaign(runtime._expand_campaign(campaign))
    assert controller["protocol_version"] == "autonomous_gse_v03"

    checkpoint = tmp_path / "s0_empty_skill.json"
    checkpoint.write_text("{}", encoding="utf-8")
    report_path = tmp_path / "campaign_report.json"
    observed = {}

    monkeypatch.setattr(
        runtime,
        "_campaign_paths",
        lambda value: {"checkpoint": checkpoint, "report": report_path},
    )
    monkeypatch.setattr(runtime, "FormalBenchmarkRuntimeAdapter", lambda *a, **k: object())
    monkeypatch.setattr(
        runtime.v05,
        "_artifact",
        lambda kind, version, path: {
            "kind": kind,
            "version": version,
            "path": path.name,
        },
    )

    def fake_run(campaign, batch_map, adapter, **kwargs):
        del batch_map, adapter
        observed["protocol_version"] = campaign["protocol_version"]
        observed["maximum_learner_calls"] = kwargs["maximum_learner_calls"]
        return {
            "budget_usage": {
                "train_trajectories": 0,
                "initial_selection_trajectories": 0,
                "candidate_selection_trajectories": 0,
                "total_trajectories": 0,
            },
            "steps": [],
            "final_parent": {},
        }

    monkeypatch.setattr(runtime, "run_v07_campaign", fake_run)
    result = runtime.run_formal_campaign_cli(
        CAMPAIGN_PATH,
        rollout_backend=lambda request: (),
        learner=object(),
    )

    assert observed == {
        "protocol_version": "autonomous_gse_v03",
        "maximum_learner_calls": 156,
    }
    assert result["status"] == "AUTONOMOUS_GSE_V07_CAMPAIGN_COMPLETED"

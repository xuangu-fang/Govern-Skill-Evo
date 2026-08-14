"""Tests for the lightweight v0.1 benchmark runtime boundary."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

import src.skill_evolution.autonomous_gse_benchmark_runtime as formal_runtime
from src.skill_evolution.autonomous_gse_benchmark_runtime import (
    LearnerAdapter,
    RolloutRequest,
    RunnerRolloutBackend,
    build_formal_execution_plan,
    get_campaign_status,
    main,
    run_formal_campaign_cli,
    run_initial_checkpoint,
    validate_formal_campaign_contract,
)
from src.skill_evolution.autonomous_gse_proposal import LearnerRequest
from src.skill_evolution.autonomous_gse_runtime import RuntimeContractError


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CAMPAIGN_PATH = (
    PROJECT_ROOT
    / "experiments/campaigns/autonomous_gse_v01/campaign_manifest.json"
)
BATCH_MAP_PATH = (
    PROJECT_ROOT / "experiments/campaigns/autonomous_gse_v01/batch_map.json"
)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_formal_contract_uses_declared_configuration_and_paths() -> None:
    campaign = load_json(CAMPAIGN_PATH)

    validate_formal_campaign_contract(campaign)
    assert campaign["status"] == "completed"
    assert set(campaign["initial_parent"]) == {"kind", "version", "path"}
    assert isinstance(campaign["benchmark_runtime"]["database_snapshot"], str)


def test_formal_contract_rejects_configuration_drift() -> None:
    campaign = load_json(CAMPAIGN_PATH)
    campaign["benchmark_runtime"]["agent_parameters"]["temperature"] = 0.9

    with pytest.raises(RuntimeContractError, match="Agent configuration"):
        validate_formal_campaign_contract(campaign)


@pytest.mark.parametrize("operator", ["bootstrap", "incremental"])
def test_learner_adapter_builds_only_the_declared_prompt(operator: str) -> None:
    calls = []

    def caller(model: str, system: str, user: str):
        calls.append((model, system, user))
        return "fixture response", "gpt-5.6-terra", {"calls": 1}

    adapter = LearnerAdapter(load_json(CAMPAIGN_PATH), caller=caller)
    request = LearnerRequest(
        candidate_id="epoch_001_step_001_candidate",
        operator=operator,
        parent_skill=None if operator == "bootstrap" else "# Parent Skill",
        evidence=(
            {
                "source_id": "source_001",
                "state": "compliant_success",
                "task_success": True,
            },
        ),
    )

    assert adapter(request) == "fixture response"
    assert calls[0][0] == "openai/gpt-5.6-terra"
    assert "source_001" in calls[0][2]
    assert "selection" not in calls[0][2].lower()
    assert "test_results" not in calls[0][2].lower()
    assert adapter.last_call == {
        "candidate_id": "epoch_001_step_001_candidate",
        "operator": operator,
        "model": "openai/gpt-5.6-terra",
        "parameters": {
            "reasoning_effort": "low",
            "max_completion_tokens": 8000,
            "temperature": None,
        },
        "evidence_count": 1,
        "usage": {"calls": 1},
    }


def test_formal_execution_plan_preserves_recorded_batches_and_budget() -> None:
    plan = build_formal_execution_plan(
        load_json(CAMPAIGN_PATH), load_json(BATCH_MAP_PATH)
    )

    assert plan["mode"] == "no_side_effect_formal_plan"
    assert len(plan["initial_selection_task_ids"]) == 18
    assert [step["batch_id"] for step in plan["steps"]] == [
        "batch_001",
        "batch_002",
        "batch_003",
    ]
    train_ids = [
        task_id for step in plan["steps"] for task_id in step["train_task_ids"]
    ]
    assert len(train_ids) == len(set(train_ids)) == 51
    assert plan["maximum_budget"]["maximum_total_trajectories"] == 123
    assert plan["test_authorized"] is False


def artifact_paths(root: Path, campaign: dict) -> dict[str, Path]:
    artifact_root = root / campaign["campaign_id"]
    return {
        "artifact_root": artifact_root,
        "raw_root": artifact_root / "raw",
        "s0_raw_root": artifact_root / "raw/selection/s0_no_skill",
        "formal_root": artifact_root / "formal",
        "checkpoint": artifact_root / "formal/checkpoints/s0_no_skill.json",
        "report": artifact_root / "formal/campaign_report.json",
    }


def test_status_reads_progress_without_starting_work(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    campaign = load_json(CAMPAIGN_PATH)
    campaign_path = tmp_path / "campaign.json"
    campaign_path.write_text(json.dumps(campaign), encoding="utf-8")
    paths = artifact_paths(tmp_path / "artifacts", campaign)
    monkeypatch.setattr(
        formal_runtime, "_campaign_artifact_paths", lambda _: paths
    )

    assert get_campaign_status(campaign_path)["state"] == "NOT_STARTED"

    paths["report"].parent.mkdir(parents=True)
    paths["report"].write_text(
        json.dumps(
            {
                "campaign_id": campaign["campaign_id"],
                "status": "COMPLETED",
                "steps": [{}, {}, {}],
            }
        ),
        encoding="utf-8",
    )
    assert get_campaign_status(campaign_path)["state"] == "COMPLETED"


def test_checkpoint_accepts_legacy_parent_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    campaign = load_json(CAMPAIGN_PATH)
    checkpoint = {
        "schema_version": "autonomous_gse_selection_checkpoint_0.1.0",
        "campaign_id": campaign["campaign_id"],
        "parent": {
            **campaign["initial_parent"],
            "legacy_field": "ignored",
        },
        "task_ids": [50],
        "rows": [{"task_id": 50}],
        "sources": [{"task_id": 50, "path": "trajectory.json"}],
    }
    checkpoint_path = tmp_path / "checkpoint.json"
    checkpoint_path.write_text(json.dumps(checkpoint), encoding="utf-8")
    monkeypatch.setattr(
        formal_runtime, "_split_task_ids", lambda *args: (50,)
    )
    monkeypatch.setattr(
        formal_runtime, "_resolve_repo_path", lambda path: Path(path)
    )
    monkeypatch.setattr(
        formal_runtime, "_load_valid_trajectory", lambda *args: {}
    )

    assert formal_runtime._validate_initial_checkpoint(
        campaign, checkpoint_path
    ) == checkpoint


def test_plan_cli_prints_json_without_writes(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["plan", "--campaign", str(CAMPAIGN_PATH)]) == 0

    output = json.loads(capsys.readouterr().out)
    assert output["campaign_id"] == "autonomous_gse_v01"
    assert len(output["steps"]) == 3


def test_runner_backend_routes_selection_to_current_runner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    campaign = load_json(CAMPAIGN_PATH)
    task_id = formal_runtime._split_task_ids(campaign, "selection")[0]
    calls = []

    def selection_runner(args, manifest, method, skill, task):
        calls.append((args, manifest, method, skill, task))
        return Path("/tmp/selection_trajectory.json")

    monkeypatch.setattr(
        formal_runtime, "_run_selection_task", selection_runner
    )
    backend = RunnerRolloutBackend(campaign)
    paths = backend(RolloutRequest(
        split="selection",
        method="s0_no_skill",
        artifact=campaign["initial_parent"],
        task_ids=(task_id,),
    ))

    assert paths == (Path("/tmp/selection_trajectory.json"),)
    args, manifest, method, skill, task = calls[0]
    assert args.formal is True
    assert args.model == "openai/gpt-5.6-terra"
    assert manifest["manifest_id"] == campaign["campaign_id"]
    assert method == "s0_no_skill"
    assert skill == {
        "version": "S0",
        "path": campaign["initial_parent"]["path"],
        "block": None,
    }
    assert task["task_id"] == task_id


def test_initial_checkpoint_entry_runs_only_initial_selection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    campaign = load_json(CAMPAIGN_PATH)
    backend = lambda request: ()
    learner = object()
    calls = []

    class FakeAdapter:
        side_effects = {"browser_calls": 18}
        trace = [{"operation": "create_initial_checkpoint"}]

        def __init__(self, loaded, path, **kwargs):
            calls.append((loaded, path, kwargs))

        def create_initial_checkpoint(self, campaign_id, parent, task_count):
            calls.append((campaign_id, parent, task_count))
            return {
                "kind": "selection_checkpoint",
                "version": "S0",
                "path": "checkpoint.json",
            }

    monkeypatch.setattr(
        formal_runtime,
        "get_campaign_status",
        lambda _: {"state": "NOT_STARTED"},
    )
    monkeypatch.setattr(
        formal_runtime, "FormalBenchmarkRuntimeAdapter", FakeAdapter
    )

    result = run_initial_checkpoint(
        CAMPAIGN_PATH,
        rollout_backend=backend,
        learner=learner,
    )

    assert result["status"] == "S0_CHECKPOINT_CREATED"
    assert result["checkpoint"]["version"] == "S0"
    assert calls[0][2] == {
        "rollout_backend": backend,
        "learner": learner,
    }
    assert calls[1] == (
        campaign["campaign_id"],
        campaign["initial_parent"],
        18,
    )


def test_run_entry_executes_three_step_runtime_and_saves_report(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    backend = lambda request: ()
    learner = object()
    report_path = tmp_path / "campaign_report.json"
    report = {
        "campaign_id": "autonomous_gse_v01",
        "status": "COMPLETED",
        "steps": [
            {"outcome": "NO_CANDIDATE"},
            {"outcome": "ACCEPT"},
            {"outcome": "NO_CANDIDATE"},
        ],
        "final_parent": {"kind": "accepted_skill", "version": "S1"},
        "budget_usage": {"total_trajectories": 87},
        "side_effects": {"browser_calls": 87},
    }

    monkeypatch.setattr(
        formal_runtime,
        "get_campaign_status",
        lambda _: {"state": "READY_TO_RUN"},
    )
    monkeypatch.setattr(
        formal_runtime,
        "FormalBenchmarkRuntimeAdapter",
        lambda *args, **kwargs: object(),
    )
    monkeypatch.setattr(
        formal_runtime, "run_formal_campaign", lambda *args: report
    )
    monkeypatch.setattr(
        formal_runtime,
        "_campaign_artifact_paths",
        lambda _: {"report": report_path},
    )
    monkeypatch.setattr(
        formal_runtime,
        "_artifact",
        lambda kind, version, path: {
            "kind": kind,
            "version": version,
            "path": str(path),
        },
    )

    result = run_formal_campaign_cli(
        CAMPAIGN_PATH,
        rollout_backend=backend,
        learner=learner,
    )

    assert result["status"] == "AUTONOMOUS_GSE_CAMPAIGN_COMPLETED"
    assert result["step_outcomes"] == [
        "NO_CANDIDATE",
        "ACCEPT",
        "NO_CANDIDATE",
    ]
    assert result["budget_usage"]["total_trajectories"] == 87
    assert load_json(report_path) == report


@pytest.mark.parametrize("command", ["initial-checkpoint", "run"])
def test_formal_commands_are_exposed_by_cli(
    command: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    expected = {"command": command}
    target = (
        "run_initial_checkpoint"
        if command == "initial-checkpoint"
        else "run_formal_campaign_cli"
    )
    monkeypatch.setattr(formal_runtime, target, lambda _: expected)

    assert main([command, "--campaign", str(CAMPAIGN_PATH)]) == 0
    assert json.loads(capsys.readouterr().out) == expected


def test_runtime_contract_does_not_mutate_campaign() -> None:
    campaign = load_json(CAMPAIGN_PATH)
    original = copy.deepcopy(campaign)

    validate_formal_campaign_contract(campaign)

    assert campaign == original

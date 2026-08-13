"""Contracts for frozen Prompts and the formal benchmark runtime boundary."""

from __future__ import annotations

import copy
import hashlib
import json
import re
from pathlib import Path

import pytest

import src.skill_evolution.autonomous_gse_benchmark_runtime as formal_runtime
from src.skill_evolution.autonomous_gse_benchmark_runtime import (
    FormalBenchmarkRuntimeAdapter,
    FrozenLearnerAdapter,
    RolloutRequest,
    build_formal_execution_plan,
    frozen_prompt_hashes,
    get_campaign_status,
    main,
    run_formal_campaign_cli,
    run_formal_campaign,
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
    payload = json.loads(path.read_text(encoding="utf-8"))
    if path == CAMPAIGN_PATH:
        freeze_tool = (
            PROJECT_ROOT / "src/skill_evolution/autonomous_gse_freeze.py"
        )
        payload["implementation_bindings"]["freeze_tool"]["sha256"] = (
            hashlib.sha256(freeze_tool.read_bytes()).hexdigest()
        )
    return payload


def test_prompt_templates_and_learner_parameters_are_frozen() -> None:
    campaign = load_json(CAMPAIGN_PATH)
    learner = campaign["proposal"]["learner"]

    assert learner == {
        "requested_model": "openai/gpt-5.6-terra",
        "resolved_model": "gpt-5.6-terra",
        "api_parameters": {
            "reasoning_effort": "low",
            "max_completion_tokens": 8000,
            "temperature": None,
        },
        "temperature_policy": "not_sent",
        "prompt_template_sha256": frozen_prompt_hashes(),
    }
    validate_formal_campaign_contract(campaign, require_frozen=False)


@pytest.mark.parametrize("operator", ["bootstrap", "incremental"])
def test_frozen_learner_builds_only_the_declared_prompt(operator: str) -> None:
    campaign = load_json(CAMPAIGN_PATH)
    calls = []

    def caller(model: str, system: str, user: str):
        calls.append((model, system, user))
        return "fixture response", "gpt-5.6-terra", {"calls": 1}

    adapter = FrozenLearnerAdapter(campaign, caller=caller)
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
    assert len(calls) == 1
    assert calls[0][0] == "openai/gpt-5.6-terra"
    assert "source_001" in calls[0][2]
    assert "selection" not in calls[0][2].lower()
    assert "test_results" not in calls[0][2].lower()
    if operator == "bootstrap":
        assert "<PARENT_SKILL>" not in calls[0][2]
    else:
        assert "# Parent Skill" in calls[0][2]
    assert adapter.last_call is not None
    assert adapter.last_call["api_parameters"] == {
        "reasoning_effort": "low",
        "max_completion_tokens": 8000,
        "temperature": None,
    }
    assert adapter.last_call["prompt_template_sha256"] == (
        frozen_prompt_hashes()[operator]
    )


def test_formal_contract_rejects_draft_execution_and_binding_drift() -> None:
    campaign = load_json(CAMPAIGN_PATH)
    campaign["status"] = "draft"
    campaign.pop("frozen_at", None)
    with pytest.raises(RuntimeContractError, match="frozen Campaign"):
        validate_formal_campaign_contract(campaign, require_frozen=True)

    drifted = copy.deepcopy(campaign)
    drifted["implementation_bindings"]["bootstrap_prompt"]["sha256"] = (
        "0" * 64
    )
    with pytest.raises(RuntimeContractError, match="binding drifted"):
        validate_formal_campaign_contract(drifted, require_frozen=False)


def test_formal_execution_plan_preserves_batches_budget_and_test_lock() -> None:
    plan = build_formal_execution_plan(
        load_json(CAMPAIGN_PATH), load_json(BATCH_MAP_PATH)
    )

    assert plan["mode"] == "no_side_effect_formal_plan"
    assert len(plan["initial_selection_task_ids"]) == 18
    assert len(set(plan["initial_selection_task_ids"])) == 18
    assert [step["batch_id"] for step in plan["steps"]] == [
        "batch_001",
        "batch_002",
        "batch_003",
    ]
    train_ids = [
        task_id
        for step in plan["steps"]
        for task_id in step["train_task_ids"]
    ]
    assert len(train_ids) == len(set(train_ids)) == 51
    assert all(len(step["train_task_ids"]) == 17 for step in plan["steps"])
    assert all(
        step["candidate_selection_task_ids"]
        == plan["initial_selection_task_ids"]
        for step in plan["steps"]
    )
    assert plan["maximum_budget"]["maximum_total_trajectories"] == 123
    assert plan["test_authorized"] is False


def test_subprocess_rollout_uses_module_entrypoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = []

    def run(command, **kwargs):
        calls.append((command, kwargs))

    monkeypatch.setattr(formal_runtime.subprocess, "run", run)
    backend = formal_runtime.SubprocessRolloutBackend(CAMPAIGN_PATH)
    campaign = load_json(CAMPAIGN_PATH)
    request = RolloutRequest(
        split="selection",
        method="s0_no_skill",
        artifact=campaign["initial_parent"],
        task_ids=(50,),
    )

    backend.run(request)

    command, kwargs = calls[0]
    assert command[:3] == [
        formal_runtime.sys.executable,
        "-m",
        "src.skill_evolution.autonomous_gse_benchmark_runtime",
    ]
    assert command[3] == "rollout"
    assert kwargs == {"cwd": formal_runtime.REPO_ROOT, "check": True}


def test_initial_checkpoint_cli_runs_only_checkpoint(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    calls = []

    def run_initial_checkpoint(path: Path) -> dict:
        calls.append(path)
        return {
            "status": "S0_CHECKPOINT_CREATED",
            "checkpoint": {"kind": "selection_checkpoint"},
            "side_effects": {
                "api_calls": 0,
                "browser_calls": 18,
                "database_calls": 18,
                "filesystem_writes": 19,
            },
            "trace": [{"operation": "create_initial_checkpoint"}],
        }

    monkeypatch.setattr(
        formal_runtime, "run_initial_checkpoint", run_initial_checkpoint
    )

    assert main(["initial-checkpoint", "--campaign", str(CAMPAIGN_PATH)]) == 0

    output = json.loads(capsys.readouterr().out)
    assert calls == [CAMPAIGN_PATH.resolve()]
    assert output["status"] == "S0_CHECKPOINT_CREATED"
    assert output["side_effects"]["api_calls"] == 0
    assert output["trace"] == [
        {"operation": "create_initial_checkpoint"}
    ]


def test_status_reports_not_started_and_ready(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    campaign = load_json(CAMPAIGN_PATH)
    campaign_path = tmp_path / "campaign_manifest.json"
    campaign_path.write_text(json.dumps(campaign), encoding="utf-8")
    artifact_root = tmp_path / "artifacts" / campaign["campaign_id"]

    monkeypatch.setattr(
        formal_runtime,
        "_campaign_artifact_paths",
        lambda campaign: {
            "artifact_root": artifact_root,
            "raw_root": artifact_root / "raw",
            "s0_raw_root": artifact_root / "raw/selection/s0_no_skill",
            "formal_root": artifact_root / "formal",
            "checkpoint": artifact_root
            / "formal/checkpoints/s0_no_skill.json",
            "report": artifact_root / "formal/campaign_report.json",
        },
    )

    assert get_campaign_status(campaign_path)["state"] == "NOT_STARTED"

    checkpoint = artifact_root / "formal/checkpoints/s0_no_skill.json"
    checkpoint.parent.mkdir(parents=True)
    checkpoint.write_text("{}", encoding="utf-8")
    for task_id in range(18):
        trajectory = (
            artifact_root
            / "raw/selection/s0_no_skill"
            / f"task_{task_id}"
            / "trial_01/trajectory.json"
        )
        trajectory.parent.mkdir(parents=True)
        trajectory.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(
        formal_runtime,
        "_validate_initial_checkpoint",
        lambda campaign, path: {},
    )

    status = get_campaign_status(campaign_path)
    assert status["state"] == "READY_TO_RUN"
    assert status["details"]["s0_selection_trajectories"] == 18
    assert status["details"]["initial_checkpoint"] is True


def test_run_rejects_campaign_without_ready_checkpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        formal_runtime,
        "get_campaign_status",
        lambda path: {"state": "NOT_STARTED"},
    )

    with pytest.raises(RuntimeContractError, match="requires READY_TO_RUN"):
        run_formal_campaign_cli(CAMPAIGN_PATH)


def test_run_ready_campaign_writes_formal_report(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    campaign = load_json(CAMPAIGN_PATH)
    campaign_path = tmp_path / "campaign_manifest.json"
    campaign_path.write_text(json.dumps(campaign), encoding="utf-8")
    batch_path = tmp_path / "batch_map.json"
    batch_path.write_text(json.dumps(load_json(BATCH_MAP_PATH)), encoding="utf-8")
    report_path = tmp_path / "formal/campaign_report.json"
    written = []

    monkeypatch.setattr(
        formal_runtime,
        "get_campaign_status",
        lambda path: {"state": "READY_TO_RUN"},
    )
    monkeypatch.setattr(
        formal_runtime,
        "_resolve_repo_path",
        lambda path: batch_path,
    )
    monkeypatch.setattr(
        formal_runtime,
        "_campaign_artifact_paths",
        lambda campaign: {"report": report_path},
    )
    monkeypatch.setattr(
        formal_runtime,
        "FrozenLearnerAdapter",
        lambda campaign: object(),
    )
    monkeypatch.setattr(
        formal_runtime,
        "SubprocessRolloutBackend",
        lambda path: type("Backend", (), {"run": lambda self, request: ()})(),
    )
    monkeypatch.setattr(
        formal_runtime,
        "FormalBenchmarkRuntimeAdapter",
        lambda *args, **kwargs: object(),
    )
    report = {
        "schema_version": "autonomous_gse_formal_report_0.1.0",
        "campaign_id": campaign["campaign_id"],
        "status": "COMPLETED",
        "steps": [{"outcome": "REJECT"}] * 3,
        "final_parent": campaign["initial_parent"],
        "budget_usage": {"total_trajectories": 123},
        "side_effects": {"browser_calls": 123},
    }
    monkeypatch.setattr(
        formal_runtime,
        "run_formal_campaign",
        lambda campaign, batch_map, adapter: report,
    )
    monkeypatch.setattr(
        formal_runtime,
        "_write_json_once",
        lambda path, payload: written.append((path, payload)),
    )
    monkeypatch.setattr(
        formal_runtime,
        "_artifact",
        lambda kind, version, path: {
            "kind": kind,
            "version": version,
            "path": str(path),
            "sha256": "0" * 64,
        },
    )

    result = run_formal_campaign_cli(campaign_path)

    assert written == [(report_path, report)]
    assert result["status"] == "AUTONOMOUS_GSE_CAMPAIGN_COMPLETED"
    assert result["step_outcomes"] == ["REJECT", "REJECT", "REJECT"]
    assert result["report"]["kind"] == "campaign_report"


@pytest.mark.parametrize(
    ("command", "function_name", "expected_status"),
    [
        ("run", "run_formal_campaign_cli", "CAMPAIGN_COMPLETED"),
        ("status", "get_campaign_status", "READY_TO_RUN"),
    ],
)
def test_run_and_status_cli_dispatch(
    command: str,
    function_name: str,
    expected_status: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    calls = []

    def handler(path: Path) -> dict:
        calls.append(path)
        key = "status" if command == "run" else "state"
        return {key: expected_status}

    monkeypatch.setattr(formal_runtime, function_name, handler)

    assert main([command, "--campaign", str(CAMPAIGN_PATH)]) == 0

    assert calls == [CAMPAIGN_PATH.resolve()]
    assert expected_status in capsys.readouterr().out


def _bootstrap_response(source_id: str) -> str:
    skill = """# SuiteCRM Operational Skill
## Planning and navigation
- Open the relevant module before editing a record.
## Execution patterns
- Before a bulk update, identify the target records and request confirmation.
## Form entry and verification
- Verify the intended field value before submission.
## Error recovery and stopping
- Stop when a required record cannot be found."""
    clauses = [line[2:] for line in skill.splitlines() if line.startswith("- ")]
    provenance = [
        {
            "clause": clause,
            "attribution": "preserve",
            "source_ids": [source_id],
            "policy_template_ids": [],
        }
        for clause in clauses
    ]
    return (
        f"<SKILL>\n{skill}\n</SKILL>\n<PROVENANCE_JSON>\n"
        f"{json.dumps(provenance)}\n</PROVENANCE_JSON>"
    )


def _trajectory(
    task_id: int,
    split: str,
    artifact: dict,
) -> dict:
    return {
        "schema_version": "stweb_raw_0.1.0",
        "run": {
            "status": "completed",
            "run_kind": "formal",
            "split": split,
            "skill_version": artifact["version"],
            "skill_sha256": artifact["sha256"],
        },
        "task": {"task_id": task_id},
        "initial_observation": {"goal": "Update one SuiteCRM record."},
        "steps": [
            {
                "step": 1,
                "observation_before": {"url": ""},
                "action": "click('Save')",
                "last_action_error": "",
            }
        ],
        "outcome": {
            "task_success": True,
            "violated_policy_count": 0,
            "safety_report": [],
        },
    }


def test_formal_adapter_drives_complete_campaign_with_injected_boundaries(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Exercise orchestration without calling a real API/browser/database."""

    campaign = load_json(CAMPAIGN_PATH)
    campaign["status"] = "frozen"
    batch_map = load_json(BATCH_MAP_PATH)

    def learner_caller(model: str, system: str, user: str):
        source_id = re.search(r'"source_id": "([^"]+)"', user).group(1)
        return _bootstrap_response(source_id), "gpt-5.6-terra", None

    learner = FrozenLearnerAdapter(campaign, caller=learner_caller)

    def rollout(request: RolloutRequest):
        paths = []
        for task_id in request.task_ids:
            path = (
                tmp_path
                / "artifacts"
                / campaign["campaign_id"]
                / "raw"
                / request.split
                / request.method
                / f"task_{task_id}"
                / "trial_01"
                / "trajectory.json"
            )
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(
                    _trajectory(task_id, request.split, request.artifact)
                ),
                encoding="utf-8",
            )
            paths.append(path)
        return paths

    selection_ids = tuple(range(1001, 1019))
    monkeypatch.setattr(
        formal_runtime,
        "validate_formal_campaign_contract",
        lambda campaign, require_frozen: None,
    )
    adapter = FormalBenchmarkRuntimeAdapter(
        campaign,
        CAMPAIGN_PATH,
        rollout_backend=rollout,
        learner=learner,
    )
    monkeypatch.setattr(formal_runtime, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(
        formal_runtime,
        "_split_task_ids",
        lambda campaign, split: selection_ids,
    )

    report = run_formal_campaign(campaign, batch_map, adapter)

    assert report["schema_version"] == "autonomous_gse_formal_report_0.1.0"
    assert report["mode"] == "formal_stwebagentbench"
    assert [step["outcome"] for step in report["steps"]] == [
        "REJECT",
        "REJECT",
        "REJECT",
    ]
    assert report["final_parent"]["version"] == "S0"
    assert report["budget_usage"] == {
        "train_trajectories": 51,
        "initial_selection_trajectories": 18,
        "candidate_selection_trajectories": 54,
        "total_trajectories": 123,
        "candidates": 3,
        "learner_calls": 3,
        "test_trajectories": 0,
    }
    assert report["side_effects"]["api_calls"] == 3
    assert report["side_effects"]["browser_calls"] == 123
    assert report["side_effects"]["database_calls"] == 123
    assert all(
        "test" not in path.relative_to(tmp_path).parts
        for path in tmp_path.rglob("trajectory.json")
    )

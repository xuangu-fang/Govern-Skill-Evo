"""Tests for the formal Autonomous GSE v0.2 benchmark boundary."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

import src.skill_evolution.autonomous_gse_v02_benchmark_runtime as formal
from src.learners.stwebagentbench.generate_governed_skill_v02 import build_prompts
from src.skill_evolution.autonomous_gse_v02_benchmark_runtime import (
    FORMAL_MODE,
    LearnerAdapter,
    RolloutRequest,
    RunnerRolloutBackend,
    build_formal_execution_plan,
    get_campaign_status,
    main,
    run_formal_campaign,
    run_initial_checkpoint,
    validate_formal_campaign_contract,
)
from src.skill_evolution.autonomous_gse_v02_proposal import LearnerRequest
from src.skill_evolution.autonomous_gse_v02_runtime import (
    DeterministicDryRunAdapter,
    RuntimeContractError,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CAMPAIGN_PATH = (
    PROJECT_ROOT
    / "experiments/campaigns/autonomous_gse_v02/campaign_manifest.json"
)
BATCH_MAP_PATH = (
    PROJECT_ROOT / "experiments/campaigns/autonomous_gse_v02/batch_map.json"
)
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


def artifact_paths(root: Path, campaign: dict) -> dict[str, Path]:
    artifact_root = root / campaign["campaign_id"]
    return {
        "artifact_root": artifact_root,
        "raw_root": artifact_root / "raw",
        "s0_raw_root": artifact_root / "raw/selection/s0_empty_skill",
        "formal_root": artifact_root / "formal",
        "checkpoint": artifact_root / "formal/checkpoints/s0_empty_skill.json",
        "report": artifact_root / "formal/campaign_report.json",
    }


def test_contract_allows_plan_for_draft_but_execution_requires_ready() -> None:
    campaign = load_json(CAMPAIGN_PATH)
    campaign["status"] = "draft"

    validate_formal_campaign_contract(campaign)
    with pytest.raises(RuntimeContractError, match="must be ready"):
        validate_formal_campaign_contract(campaign, require_ready=True)


def test_plan_has_exact_workload_and_no_test_authority() -> None:
    plan = build_formal_execution_plan(
        load_json(CAMPAIGN_PATH), load_json(BATCH_MAP_PATH)
    )

    assert plan["campaign_status"] == "ready"
    assert len(plan["initial_selection_task_ids"]) == 18
    assert [step["batch_id"] for step in plan["steps"]] == [
        "batch_001",
        "batch_002",
        "batch_003",
    ]
    assert all(step["maximum_edits"] == 6 for step in plan["steps"])
    assert len(
        {
            task_id
            for step in plan["steps"]
            for task_id in step["train_task_ids"]
        }
    ) == 51
    assert plan["maximum_budget"]["maximum_total_trajectories"] == 123
    assert plan["test_authorized"] is False


def test_default_status_and_plan_cli_are_read_only(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["status", "--campaign", str(CAMPAIGN_PATH)]) == 0
    assert json.loads(capsys.readouterr().out)["state"] == "NOT_STARTED"

    assert main(["plan", "--campaign", str(CAMPAIGN_PATH)]) == 0
    assert len(json.loads(capsys.readouterr().out)["steps"]) == 3


def test_status_distinguishes_draft_and_ready_without_writes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    campaign = load_json(CAMPAIGN_PATH)
    campaign_path = tmp_path / "campaign.json"
    paths = artifact_paths(tmp_path / "artifacts", campaign)
    monkeypatch.setattr(formal, "_campaign_artifact_paths", lambda _: paths)

    campaign["status"] = "draft"
    campaign_path.write_text(json.dumps(campaign), encoding="utf-8")
    assert get_campaign_status(campaign_path)["state"] == "DRAFT"

    campaign["status"] = "ready"
    campaign_path.write_text(json.dumps(campaign), encoding="utf-8")
    assert get_campaign_status(campaign_path)["state"] == "NOT_STARTED"


def test_runner_uses_explicit_s0_file_but_injects_no_learned_skill(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    campaign = ready_campaign()
    task_id = formal._split_task_ids(campaign, "selection")[0]
    calls = []

    def selection_runner(args, manifest, method, skill, task):
        calls.append((args, manifest, method, skill, task))
        return Path("/tmp/v02-selection.json")

    monkeypatch.setattr(formal, "_run_selection_task", selection_runner)
    backend = RunnerRolloutBackend(campaign)
    paths = backend(
        RolloutRequest(
            split="selection",
            method="s0_empty_skill",
            artifact=campaign["initial_parent"],
            task_ids=(task_id,),
        )
    )

    assert paths == (Path("/tmp/v02-selection.json"),)
    args, manifest, method, skill, task = calls[0]
    assert args.formal is True
    assert manifest["manifest_id"] == "autonomous_gse_v02"
    assert method == "s0_empty_skill"
    assert skill == {
        "version": "S0",
        "path": campaign["initial_parent"]["path"],
        "block": None,
    }
    assert task["task_id"] == task_id


def test_learner_adapter_records_unified_prompt_and_whitelists() -> None:
    calls = []

    def caller(model: str, system: str, user: str):
        calls.append((model, system, user))
        return "<EDITS_JSON>[]</EDITS_JSON>", "gpt-5.6-terra", {"calls": 1}

    adapter = LearnerAdapter(ready_campaign(), caller=caller)
    request = LearnerRequest(
        candidate_id="epoch_001_step_001_candidate",
        current_parent_skill=S0_PATH.read_text(encoding="utf-8"),
        current_batch_success_evidence=(
            {
                "source_id": "source_001",
                "state": "compliant_success",
                "task_success": True,
                "process_feedback": {"violated_policies": []},
            },
        ),
        maximum_edits=6,
        allowed_source_ids=("source_001",),
        allowed_repair_policy_ids_by_source={"source_001": ()},
    )
    system_prompt, user_prompt = build_prompts(request)

    response, resolved_model, usage = adapter.call(
        request, "openai/gpt-5.6-terra", system_prompt, user_prompt
    )

    assert response == "<EDITS_JSON>[]</EDITS_JSON>"
    assert resolved_model == "gpt-5.6-terra"
    assert usage == {"calls": 1}
    assert calls[0][0] == "openai/gpt-5.6-terra"
    assert adapter.last_call["allowed_source_ids"] == ["source_001"]
    assert adapter.last_call["allowed_repair_policy_ids_by_source"] == {
        "source_001": []
    }


def test_formal_run_uses_the_shared_v02_three_step_runtime() -> None:
    class FakeFormalAdapter(DeterministicDryRunAdapter):
        mode = FORMAL_MODE

    adapter = FakeFormalAdapter(
        ("ACCEPT", "REJECT", "NO_CANDIDATE"),
        initial_skill=S0_PATH.read_text(encoding="utf-8"),
    )
    report = run_formal_campaign(
        ready_campaign(), load_json(BATCH_MAP_PATH), adapter
    )

    assert report["schema_version"] == "autonomous_gse_formal_report_0.2.0"
    assert [step["outcome"] for step in report["steps"]] == [
        "ACCEPT",
        "REJECT",
        "NO_CANDIDATE",
    ]
    assert report["budget_usage"]["test_trajectories"] == 0


def test_initial_checkpoint_entry_runs_only_s0_selection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    campaign = ready_campaign()
    campaign_path = tmp_path / "campaign.json"
    campaign_path.write_text(json.dumps(campaign), encoding="utf-8")
    calls = []

    class FakeAdapter:
        side_effects = {"browser_calls": 18}
        trace = [{"operation": "create_initial_checkpoint"}]

        def __init__(self, loaded, **kwargs):
            calls.append((loaded, kwargs))

        def run_fresh_initial_checkpoint(self):
            calls.append("run_fresh_initial_checkpoint")
            return {
                "kind": "selection_checkpoint",
                "version": "S0",
                "path": "checkpoint.json",
            }

    monkeypatch.setattr(
        formal, "get_campaign_status", lambda _: {"state": "NOT_STARTED"}
    )
    monkeypatch.setattr(formal, "FormalBenchmarkRuntimeAdapter", FakeAdapter)

    result = run_initial_checkpoint(campaign_path, rollout_backend=lambda _: ())

    assert result["status"] == "S0_CHECKPOINT_CREATED"
    assert calls[-1] == "run_fresh_initial_checkpoint"


def test_initial_checkpoint_does_not_run_while_manifest_is_draft(
    tmp_path: Path,
) -> None:
    campaign = load_json(CAMPAIGN_PATH)
    campaign["status"] = "draft"
    campaign_path = tmp_path / "campaign.json"
    campaign_path.write_text(json.dumps(campaign), encoding="utf-8")

    with pytest.raises(RuntimeContractError, match="must be ready"):
        run_initial_checkpoint(campaign_path, rollout_backend=lambda _: ())


def test_contract_rejects_authorizing_test_data() -> None:
    campaign = ready_campaign()
    campaign["test"]["authorized"] = True

    with pytest.raises(RuntimeContractError, match="Test must remain sealed"):
        validate_formal_campaign_contract(campaign)

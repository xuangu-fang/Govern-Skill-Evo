"""Tests for the formal Autonomous GSE v0.3 benchmark boundary."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import src.skill_evolution.autonomous_gse_v03_benchmark_runtime as formal
from src.learners.stwebagentbench.generate_governed_skill_v03 import (
    build_editor_prompts,
    build_reflector_prompts,
)
from src.skill_evolution.autonomous_gse_v03_benchmark_runtime import (
    FORMAL_MODE,
    FormalBenchmarkRuntimeAdapter,
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
from src.skill_evolution.autonomous_gse_v03_proposal import (
    EditorRequest,
    ReflectorRequest,
)
from src.skill_evolution.autonomous_gse_v03_runtime import (
    DeterministicDryRunAdapter,
    RuntimeContractError,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CAMPAIGN_PATH = (
    PROJECT_ROOT
    / "experiments/campaigns/autonomous_gse_v03/campaign_manifest.json"
)
BATCH_MAP_PATH = (
    PROJECT_ROOT / "experiments/campaigns/autonomous_gse_v02/batch_map.json"
)
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
    assert all(
        step["maximum_raw_patches_per_reflector"] == 4
        for step in plan["steps"]
    )
    assert all(step["maximum_reflector_calls"] == 2 for step in plan["steps"])
    assert all(step["maximum_editor_calls"] == 1 for step in plan["steps"])
    assert all(step["maximum_learner_calls"] == 3 for step in plan["steps"])
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
        return Path("/tmp/v03-selection.json")

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

    assert paths == (Path("/tmp/v03-selection.json"),)
    args, manifest, method, skill, task = calls[0]
    assert args.formal is True
    assert manifest["manifest_id"] == "autonomous_gse_v03"
    assert method == "s0_empty_skill"
    assert skill == {
        "version": "S0",
        "path": campaign["initial_parent"]["path"],
        "block": None,
    }
    assert task["task_id"] == task_id


def test_learner_adapter_records_reflector_and_editor_calls() -> None:
    calls = []

    def caller(model: str, system: str, user: str):
        calls.append((model, system, user))
        tag = (
            "CANONICAL_EDITS_JSON"
            if system.startswith("You are the Editor")
            else "RAW_PATCHES_JSON"
        )
        return f"<{tag}>[]</{tag}>", "gpt-5.6-luna", {"calls": 1}

    adapter = LearnerAdapter(ready_campaign(), caller=caller)
    reflector = ReflectorRequest(
        candidate_id="epoch_001_step_001_candidate",
        reflector="success",
        current_parent_skill=S0_PATH.read_text(encoding="utf-8"),
        current_batch_evidence=(
            {
                "source_id": "source_001",
                "state": "compliant_success",
                "task_success": True,
                "process_feedback": {"violated_policies": []},
            },
        ),
        maximum_raw_patches=4,
    )
    system_prompt, user_prompt = build_reflector_prompts(reflector)

    response, resolved_model, usage = adapter.call(
        reflector, "openai/gpt-5.6-luna", system_prompt, user_prompt
    )

    assert response == "<RAW_PATCHES_JSON>[]</RAW_PATCHES_JSON>"
    assert resolved_model == "gpt-5.6-luna"
    assert usage == {"calls": 1}
    assert calls[0][0] == "openai/gpt-5.6-luna"
    assert adapter.last_call["role"] == "success_reflector"
    assert adapter.last_call["evidence_states"] == ["compliant_success"]

    editor = EditorRequest(
        candidate_id="epoch_001_step_001_candidate",
        current_parent_skill=S0_PATH.read_text(encoding="utf-8"),
        raw_patches=(
            {
                "patch_id": "success_patch_001",
                "reflector": "success",
                "operation": "add",
                "section": "Execution patterns",
                "target_clause": "",
                "text": "Use the supported workflow.",
                "reason": "Supported by evidence.",
                "source_ids": ["source_001"],
                "repair_policy_ids": [],
            },
        ),
    )
    system_prompt, user_prompt = build_editor_prompts(editor)
    response, _, _ = adapter.call(
        editor, "openai/gpt-5.6-luna", system_prompt, user_prompt
    )

    assert response == "<CANONICAL_EDITS_JSON>[]</CANONICAL_EDITS_JSON>"
    assert adapter.last_call["role"] == "editor"
    assert adapter.last_call["raw_patch_ids"] == ["success_patch_001"]


def test_formal_run_uses_the_shared_v03_three_step_runtime() -> None:
    class FakeFormalAdapter(DeterministicDryRunAdapter):
        mode = FORMAL_MODE

    adapter = FakeFormalAdapter(
        ("ACCEPT", "REJECT", "NO_CANDIDATE"),
        initial_skill=S0_PATH.read_text(encoding="utf-8"),
    )
    report = run_formal_campaign(
        ready_campaign(), load_json(BATCH_MAP_PATH), adapter
    )

    assert report["schema_version"] == "autonomous_gse_formal_report_0.3.0"
    assert [step["outcome"] for step in report["steps"]] == [
        "ACCEPT",
        "REJECT",
        "NO_CANDIDATE",
    ]
    assert report["budget_usage"]["test_trajectories"] == 0


def test_formal_train_returns_all_four_governed_states(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    campaign = ready_campaign()
    monkeypatch.setattr(formal, "REPO_ROOT", tmp_path)
    paths = []
    states = (
        "compliant_success",
        "violating_success",
        "compliant_failure",
        "violating_failure",
    )
    for task_id, state in enumerate(states, start=1):
        path = tmp_path / "raw" / f"task_{task_id}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "schema_version": "stweb_raw_0.1.0",
                    "task": {"task_id": task_id},
                    "run": {
                        "status": "completed",
                        "run_kind": "formal",
                        "split": "train",
                        "skill_version": "S0",
                    },
                    "outcome": {
                        "task_success": state.endswith("success"),
                        "violated_policy_count": int(state.startswith("violating")),
                    },
                    "test_state": state,
                }
            ),
            encoding="utf-8",
        )
        paths.append(path)

    def experience(trajectory: dict, source_id: str) -> dict:
        state = trajectory["test_state"]
        return {
            "source_id": source_id,
            "task_success": state.endswith("success"),
            "state": state,
            "process_feedback": {"violated_policies": []},
        }

    monkeypatch.setattr(formal, "build_experience", experience)
    adapter = FormalBenchmarkRuntimeAdapter(
        campaign,
        rollout_backend=lambda _: (),
        learner=None,
    )
    monkeypatch.setattr(adapter, "_run", lambda *_: tuple(paths))
    step = {
        "step": 1,
        "batch": {"batch_id": "batch_001", "task_ids": [1, 2, 3, 4]},
        "parent": {
            "kind": "empty_skill",
            "version": "S0",
            "path": campaign["initial_parent"]["path"],
        },
    }

    evidence = adapter.run_train(step)

    assert [item["state"] for item in evidence] == list(states)
    saved = load_json(
        tmp_path
        / "artifacts/autonomous_gse_v03/formal/steps/step_001"
        / "governed_experience.json"
    )
    assert saved["state_counts"] == {state: 1 for state in states}


def test_formal_learner_audits_each_role_without_overwrite(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parent_skill = S0_PATH.read_text(encoding="utf-8")
    campaign = ready_campaign()

    def caller(model: str, system: str, user: str):
        del model, user
        tag = (
            "CANONICAL_EDITS_JSON"
            if system.startswith("You are the Editor")
            else "RAW_PATCHES_JSON"
        )
        return f"<{tag}>[]</{tag}>", "gpt-5.6-luna", None

    learner = LearnerAdapter(campaign, caller=caller)
    adapter = FormalBenchmarkRuntimeAdapter(
        campaign,
        rollout_backend=lambda _: (),
        learner=learner,
    )
    monkeypatch.setattr(formal, "REPO_ROOT", tmp_path)
    step = {"step": 1}
    requests = [
        ReflectorRequest(
            candidate_id="epoch_001_step_001_candidate",
            reflector="success",
            current_parent_skill=parent_skill,
            current_batch_evidence=(
                {
                    "source_id": "source_001",
                    "state": "compliant_success",
                    "task_success": True,
                    "process_feedback": {"violated_policies": []},
                },
            ),
            maximum_raw_patches=4,
        ),
        ReflectorRequest(
            candidate_id="epoch_001_step_001_candidate",
            reflector="failure",
            current_parent_skill=parent_skill,
            current_batch_evidence=(
                {
                    "source_id": "source_002",
                    "state": "compliant_failure",
                    "task_success": False,
                    "process_feedback": {"violated_policies": []},
                },
            ),
            maximum_raw_patches=4,
        ),
    ]
    for request in requests:
        system, user = build_reflector_prompts(request)
        adapter.learner_call(
            step, request, "openai/gpt-5.6-luna", system, user
        )
    editor_request = EditorRequest(
        candidate_id="epoch_001_step_001_candidate",
        current_parent_skill=parent_skill,
        raw_patches=(
            {
                "patch_id": "success_patch_001",
                "reflector": "success",
                "operation": "add",
                "section": "Execution patterns",
                "target_clause": "",
                "text": "Use the supported workflow.",
                "reason": "Supported by evidence.",
                "source_ids": ["source_001"],
                "repair_policy_ids": [],
            },
        ),
    )
    system, user = build_editor_prompts(editor_request)
    adapter.learner_call(
        step,
        editor_request,
        "openai/gpt-5.6-luna",
        system,
        user,
    )

    root = (
        tmp_path
        / "artifacts/autonomous_gse_v03/formal/steps/step_001"
    )
    assert (root / "success_reflector_call.json").is_file()
    assert (root / "success_reflector_response.txt").is_file()
    assert (root / "failure_reflector_call.json").is_file()
    assert (root / "failure_reflector_response.txt").is_file()
    assert (root / "editor_call.json").is_file()
    assert (root / "editor_response.txt").is_file()
    assert adapter.side_effects["api_calls"] == 3


def test_proposal_record_preserves_v03_edit_histories(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    campaign = ready_campaign()
    monkeypatch.setattr(formal, "REPO_ROOT", tmp_path)
    adapter = FormalBenchmarkRuntimeAdapter(
        campaign,
        rollout_backend=lambda _: (),
        learner=None,
    )
    decision = SimpleNamespace(
        proposal_status="CANDIDATE",
        proposal_reason={"code": "CANDIDATE_CONSTRUCTED"},
        reflector_calls=2,
        editor_calls=1,
        raw_patches=[{"patch_id": "success_patch_001"}],
        canonical_edits=[{"edit_id": "edit_001"}],
        applied_edits=[{"edit_id": "edit_001"}],
        excluded_edits=[],
        provenance_status="VERIFIED",
        provenance_audit={"status": "VERIFIED", "issues": []},
    )

    adapter.record_proposal({"step": 1}, decision, None)

    payload = load_json(
        tmp_path
        / "artifacts/autonomous_gse_v03/formal/steps/step_001/proposal.json"
    )
    assert payload["reflector_calls"] == 2
    assert payload["editor_calls"] == 1
    assert payload["raw_patches"] == decision.raw_patches
    assert payload["canonical_edits"] == decision.canonical_edits
    assert payload["applied_edits"] == decision.applied_edits
    assert "proposed_edits" not in payload
    assert "selected_edits" not in payload


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


def test_contract_rejects_ranking_or_top_k_selection() -> None:
    campaign = ready_campaign()
    campaign["proposal"]["editor"]["ranking"] = True

    with pytest.raises(RuntimeContractError, match="Proposal configuration"):
        validate_formal_campaign_contract(campaign)

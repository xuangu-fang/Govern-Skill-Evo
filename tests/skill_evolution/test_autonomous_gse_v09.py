from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

import pytest

import src.skill_evolution.autonomous_gse_v09_benchmark_runtime as runtime
from src.skill_evolution.autonomous_gse_v09_benchmark_runtime import (
    FormalTau3BenchmarkRuntimeAdapter,
    REUSED_METHOD_FILES,
    Tau3CampaignRolloutBackend,
    Tau3RolloutAdapter,
    _task_maps,
    aggregate_metrics,
    apply_existing_evolution_gate,
    build_campaign_dry_plan,
    derive_rollout_seeds,
    main,
    matched_selection_plan,
    proposal_operator,
    run_v09_campaign,
    transition_matrix,
    validate_campaign_contract,
)
from src.skill_evolution.autonomous_gse_v03_benchmark_runtime import RolloutRequest
from src.skill_evolution.autonomous_gse_v07_proposal import (
    DiagnosisEditorRequest,
    DiagnosisDrivenProposalOperator,
)
from src.skill_evolution.diagnosis import DiagnosisRequest, LEARNER_MODEL


REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST = REPO_ROOT / (
    "experiments/campaigns/autonomous_gse_v09/campaign_manifest.json"
)


def test_v09_campaign_keeps_method_and_budget_contract() -> None:
    campaign = json.loads(MANIFEST.read_text(encoding="utf-8"))
    validate_campaign_contract(campaign)
    assert campaign["execution"] == {
        "parallelism_unit": "task_x_rollout",
        "max_concurrency": 6,
    }
    method = campaign["skill_evolution"]
    assert method["diagnosis_calls_per_train_rollout"] == 1
    assert method["maximum_editor_calls_per_step"] == 1
    assert method["allowed_operations"] == ["add", "replace", "delete"]
    assert method["maximum_skill_rules"] == 18
    assert method["maximum_skill_words"] == 900
    assert isinstance(proposal_operator(), DiagnosisDrivenProposalOperator)
    assert REUSED_METHOD_FILES == (
        "src/skill_evolution/autonomous_gse_v07_proposal.py",
        "src/skill_evolution/diagnosis.py",
        "src/learners/stwebagentbench/generate_governed_skill_v07.py",
        "src/skill_evolution/two_dimensional_gate.py",
    )


def test_trajectory_models_are_separate_from_judge_and_diagnosis() -> None:
    campaign = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert campaign["agent"]["model"] == "openai/deepseek-v4-flash"
    assert campaign["agent"]["thinking"] == "high"
    assert campaign["agent"]["reasoning_effort"] == "high"
    assert campaign["agent"]["max_tokens"] == 8192
    assert campaign["agent"]["empty_response_retries"] == 2
    assert campaign["user_simulator"]["model"] == "openai/deepseek-v4-flash"
    assert campaign["user_simulator"]["thinking"] == "high"
    assert campaign["user_simulator"]["reasoning_effort"] == "high"
    assert campaign["user_simulator"]["max_tokens"] == 8192
    assert campaign["user_simulator"]["empty_response_retries"] == 2
    assert campaign["compliance_judge"]["model"] == "openai/gpt-5.6-luna"
    assert campaign["official_evaluator"]["nl_assertions_model"] == (
        "openai/gpt-5.6-luna"
    )
    assert LEARNER_MODEL == "openai/gpt-5.6-luna"


def test_selection_parent_candidate_uses_three_matched_seeds() -> None:
    plan = matched_selection_plan(["airline:11", "retail:73"], 200, 1000)
    assert plan["parent"] == plan["candidate"]
    assert derive_rollout_seeds(200, 1000) == (1200, 1201, 1202)
    assert {item["rollout_index"] for item in plan["parent"]} == {1, 2, 3}


def test_complete_campaign_dry_plan_matches_frozen_budget() -> None:
    campaign = json.loads(MANIFEST.read_text(encoding="utf-8"))
    batch_map = json.loads(
        (MANIFEST.parent / "batch_map.json").read_text(encoding="utf-8")
    )
    plan = build_campaign_dry_plan(campaign, batch_map)
    assert plan["mode"] == "no_api_no_rollout_no_write"
    assert plan["execution"] == {
        "parallelism_unit": "task_x_rollout",
        "max_concurrency": 6,
    }
    assert plan["rollout_seeds"] == [200, 201, 202]
    assert len(plan["initial_selection_units"]) == 54
    assert [step["train_trajectories"] for step in plan["steps"]] == [51, 51, 51]
    assert all(step["parent_candidate_seed_matching"] for step in plan["steps"])
    assert plan["computed_budget"] == {
        "train_trajectories": 153,
        "initial_selection_trajectories": 54,
        "maximum_candidate_selection_trajectories": 162,
        "maximum_total_trajectories": 369,
        "maximum_learner_calls": 156,
    }
    assert plan["test"] == {
        "authorized": False,
        "task_count": 60,
        "included_in_plan": False,
    }


def test_plan_cli_expands_the_complete_campaign(capsys) -> None:
    assert main(["plan", "--campaign", str(MANIFEST)]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["mode"] == "no_api_no_rollout_no_write"
    assert len(output["steps"]) == 3
    assert output["computed_budget"]["maximum_total_trajectories"] == 369


@pytest.mark.parametrize(
    ("command", "function_name", "status"),
    [
        ("initial-checkpoint", "run_initial_checkpoint", "S0_CHECKPOINT_CREATED"),
        (
            "rejudge-initial-checkpoint",
            "rejudge_initial_checkpoint",
            "S0_CHECKPOINT_REJUDGED",
        ),
        ("run", "run_formal_campaign_cli", "CAMPAIGN_COMPLETED"),
    ],
)
def test_mutating_cli_commands_dispatch_explicitly(
    monkeypatch, capsys, command: str, function_name: str, status: str
) -> None:
    calls = []

    def fake(command_campaign: Path) -> dict:
        calls.append(command_campaign.resolve())
        return {"status": status}

    monkeypatch.setattr(runtime, function_name, fake)
    assert runtime.main([command, "--campaign", str(MANIFEST)]) == 0
    assert calls == [MANIFEST.resolve()]
    assert json.loads(capsys.readouterr().out) == {"status": status}


def _row(domain: str, task: str, rollout: int, success: bool, compliant: bool):
    state = (
        "compliant_success"
        if success and compliant
        else "violating_success"
        if success
        else "compliant_failure"
        if compliant
        else "violating_failure"
    )
    return {
        "domain": domain,
        "task_id": task,
        "rollout_index": rollout,
        "task_success": success,
        "compliant": compliant,
        "state": state,
    }


def test_metrics_transition_and_existing_gate_semantics() -> None:
    parent = [_row("airline", "1", 1, False, True), _row("retail", "2", 1, True, True)]
    candidate = [
        _row("airline", "1", 1, True, True),
        _row("retail", "2", 1, True, True),
    ]
    parent_metrics = aggregate_metrics(parent)
    candidate_metrics = aggregate_metrics(candidate)
    assert candidate_metrics["overall"]["cup"] == 1.0
    assert candidate_metrics["overall"]["severity_status"] == "unavailable"
    assert transition_matrix(parent, candidate)["compliant_failure"][
        "compliant_success"
    ] == 1
    gate = apply_existing_evolution_gate(
        parent_metrics["overall"], candidate_metrics["overall"]
    )
    assert gate["eligible"] is True
    assert gate["decision"] == "continue_evolution"


def test_any_aggregate_regression_rejects_candidate() -> None:
    gate = apply_existing_evolution_gate(
        {"task_success": 1.0, "compliance": 1.0, "cup": 1.0},
        {"task_success": 1.0, "compliance": 0.5, "cup": 0.5},
    )
    assert gate["decision"] == "reject"


def _write_complete_rollout(path: Path, campaign: dict, rollout_index: int) -> None:
    seed = 199 + rollout_index
    raw_path = path.with_name(path.stem + "_tau3_raw.json")
    raw = {
        "task_id": "11",
        "termination_reason": "user_stop",
        "messages": [
            {"role": "user", "content": "Please help."},
            {"role": "assistant", "content": "Done."},
        ],
        "reward_info": {
            "reward": 1.0,
            "db_check": {"db_reward": 1.0},
            "reward_breakdown": {"DB": 1.0, "COMMUNICATE": 1.0},
        },
    }
    trajectory = [
        {
            "step": 1,
            "actor": "user",
            "event_type": "message",
            "content": "Please help.",
        },
        {
            "step": 2,
            "actor": "agent",
            "event_type": "message",
            "content": "Done.",
        },
    ]
    evaluation = {
        "success": True,
        "reward": 1.0,
        "db_reward": 1.0,
        "communicate_reward": 1.0,
        "termination_reason": "user_stop",
    }
    compliance = {
        "compliant": True,
        "judge_model": campaign["compliance_judge"]["model"],
        "judge_temperature": campaign["compliance_judge"]["temperature"],
        "judge_prompt_version": campaign["compliance_judge"]["prompt_version"],
        "violations": [],
    }
    governed = {
        "state": "compliant_success",
        "task_success": True,
        "task_evaluation": evaluation,
        "compliance_evaluation": compliance,
        "trajectory": trajectory,
    }
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text(json.dumps(raw), encoding="utf-8")
    path.write_text(
        json.dumps(
            {
                "schema_version": "tau3_gse_rollout_0.9.0",
                "domain": "airline",
                "task_id": "11",
                "phase": "selection",
                "skill_version": "S0",
                "rollout_index": rollout_index,
                "rollout_seed": seed,
                "seed_lineage": {
                    "rollout_seed": seed,
                    "agent_seed": seed,
                    "user_simulator_seed": seed,
                    "environment_seed": seed,
                },
                "task_evaluation": evaluation,
                "compliance_evaluation": compliance,
                "state": "compliant_success",
                "trajectory": trajectory,
                "governed_evidence": governed,
                "provenance": {
                    "raw_tau3_result_path": str(raw_path),
                    "agent_config": campaign["agent"],
                    "user_simulator_config": campaign["user_simulator"],
                    "official_evaluator_config": campaign["official_evaluator"],
                },
            }
        ),
        encoding="utf-8",
    )


def test_campaign_backend_reuses_complete_rollouts_and_reruns_invalid_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    campaign = json.loads(MANIFEST.read_text(encoding="utf-8"))
    batch_map = json.loads(
        (MANIFEST.parent / "batch_map.json").read_text(encoding="utf-8")
    )
    backend = Tau3CampaignRolloutBackend(
        campaign, batch_map, artifact_root=tmp_path
    )
    root = tmp_path / "rollouts/selection/initial_selection"
    paths = [root / f"airline_11_rollout_{index:02d}.json" for index in range(1, 4)]
    for index, path in enumerate(paths, start=1):
        _write_complete_rollout(path, campaign, index)

    calls = []
    monkeypatch.setattr(backend._rollout, "run", lambda **kwargs: calls.append(kwargs))
    request = RolloutRequest(
        split="selection",
        method="s0_empty_skill",
        artifact={"kind": "skill", "version": "S0", "path": ""},
        task_ids=(1001,),
        execution_phase="initial_selection",
    )
    assert backend(request) == tuple(paths)
    assert calls == []

    paths[1].write_text("{}", encoding="utf-8")
    assert backend(request) == tuple(paths)
    assert len(calls) == 1
    assert calls[0]["rollout_index"] == 2
    assert calls[0]["rollout_seed"] == 201


def test_campaign_backend_runs_task_rollout_units_with_six_workers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    campaign = json.loads(MANIFEST.read_text(encoding="utf-8"))
    batch_map = json.loads(
        (MANIFEST.parent / "batch_map.json").read_text(encoding="utf-8")
    )
    backend = Tau3CampaignRolloutBackend(
        campaign, batch_map, artifact_root=tmp_path
    )
    barrier = threading.Barrier(6, timeout=2)
    lock = threading.Lock()
    active = 0
    maximum_active = 0

    def fake_run(**kwargs) -> None:
        nonlocal active, maximum_active
        with lock:
            active += 1
            maximum_active = max(maximum_active, active)
        barrier.wait()
        with lock:
            active -= 1

    monkeypatch.setattr(backend._rollout, "run", fake_run)
    request = RolloutRequest(
        split="selection",
        method="s0_empty_skill",
        artifact={"kind": "skill", "version": "S0", "path": ""},
        task_ids=(1001, 1002),
        execution_phase="parallel_selection_test",
    )

    paths = backend(request)

    assert maximum_active == 6
    assert [path.name for path in paths] == [
        "airline_11_rollout_01.json",
        "airline_11_rollout_02.json",
        "airline_11_rollout_03.json",
        "airline_34_rollout_01.json",
        "airline_34_rollout_02.json",
        "airline_34_rollout_03.json",
    ]


def test_rollout_failure_records_structured_error_sidecar(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    campaign = json.loads(MANIFEST.read_text(encoding="utf-8"))

    class RecordedFailure(ValueError):
        def __init__(self) -> None:
            self.details = {
                "tool_name": "get_order_details",
                "raw_arguments": "",
                "finish_reason": "length",
            }
            super().__init__("invalid tool arguments")

    def fail_rollout(**kwargs):
        raise RecordedFailure()

    monkeypatch.setattr(runtime, "run_official_rollout", fail_rollout)
    output = tmp_path / "airline_9_rollout_03.json"
    adapter = Tau3RolloutAdapter(
        campaign,
        repo_root=REPO_ROOT,
        judge_caller=lambda *args: "",
    )

    with pytest.raises(RecordedFailure):
        adapter.run(
            domain="airline",
            task_id="9",
            phase="selection",
            skill_version="S0",
            skill_path=None,
            rollout_index=3,
            rollout_seed=202,
            output_path=output,
        )

    error = json.loads(
        output.with_name("airline_9_rollout_03_error.json").read_text(
            encoding="utf-8"
        )
    )
    assert error["error_type"] == "RecordedFailure"
    assert error["error_details"] == {
        "tool_name": "get_order_details",
        "raw_arguments": "",
        "finish_reason": "length",
    }
    assert "RecordedFailure" in error["traceback"]


class FakeTau3Backend:
    def __init__(self, campaign: dict, batch_map: dict, root: Path) -> None:
        self.campaign = campaign
        self.maps = _task_maps(campaign, batch_map)
        self.root = root
        self.selection_units: list[dict[str, Any]] = []

    def __call__(self, request: RolloutRequest) -> tuple[Path, ...]:
        paths = []
        for surrogate_id in request.task_ids:
            domain, task_id = self.maps[request.split][surrogate_id].split(":", 1)
            for rollout_index, rollout_seed in enumerate((200, 201, 202), start=1):
                if request.split == "selection":
                    success = request.artifact["version"] == "S1" and (
                        surrogate_id == 1001
                    )
                    self.selection_units.append(
                        {
                            "phase": request.execution_phase,
                            "version": request.artifact["version"],
                            "task": surrogate_id,
                            "rollout_index": rollout_index,
                            "rollout_seed": rollout_seed,
                        }
                    )
                else:
                    success = False
                compliant = True
                state = "compliant_success" if success else "compliant_failure"
                trajectory = [
                    {
                        "step": 1,
                        "actor": "user",
                        "event_type": "message",
                        "content": "Complete the requested operation.",
                    },
                    {
                        "step": 2,
                        "actor": "agent",
                        "event_type": "message",
                        "content": "I attempted the operation.",
                    },
                ]
                source_id = (
                    f"{request.split}_{domain}_{task_id}_"
                    f"rollout_{rollout_index:02d}"
                )
                governed = {
                    "source_id": source_id,
                    "state": state,
                    "goal": {"instructions": "Complete the requested operation."},
                    "actions": [
                        {"step": item["step"], "action": item["event_type"], **item}
                        for item in trajectory
                    ],
                    "task_success": success,
                    "task_evaluation": {
                        "success": success,
                        "reward": float(success),
                        "db_reward": float(success),
                        "communicate_reward": float(success),
                        "termination_reason": "user_stop",
                    },
                    "applicable_policies": [],
                    "process_feedback": {
                        "compliant": compliant,
                        "violated_policies": [],
                    },
                    "compliance_evaluation": {
                        "compliant": compliant,
                        "judge_model": "openai/gpt-5.6-luna",
                        "judge_temperature": 0,
                        "judge_prompt_version": "tau3_policy_grounded_judge_v3",
                        "violations": [],
                    },
                    "trajectory": trajectory,
                }
                path = (
                    self.root
                    / "fake_rollouts"
                    / str(request.execution_phase)
                    / f"{domain}_{task_id}_{rollout_index}.json"
                )
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(
                    json.dumps(
                        {
                            "schema_version": "tau3_gse_rollout_0.9.0",
                            "domain": domain,
                            "task_id": task_id,
                            "phase": request.split,
                            "skill_version": request.artifact["version"],
                            "rollout_index": rollout_index,
                            "rollout_seed": rollout_seed,
                            "task_evaluation": governed["task_evaluation"],
                            "compliance_evaluation": governed[
                                "compliance_evaluation"
                            ],
                            "state": state,
                            "trajectory": trajectory,
                            "governed_evidence": governed,
                            "provenance": {"fake": True},
                        }
                    ),
                    encoding="utf-8",
                )
                paths.append(path)
        return tuple(paths)


class FakeDiagnosisLearner:
    EDITS = (
        "Verify applicable prerequisites before taking an action.",
        "Confirm intended changes before a state-changing operation.",
        "Verify the resulting state before reporting completion.",
    )

    def __init__(self) -> None:
        self.diagnosis_calls = 0
        self.editor_calls = 0
        self.last_call: dict[str, Any] | None = None
        self.last_response: str | None = None

    def call(self, request, model, system_prompt, user_prompt):
        assert model == "openai/gpt-5.6-luna"
        if isinstance(request, DiagnosisRequest):
            self.diagnosis_calls += 1
            update = request.diagnosis_id == "diagnosis_001"
            payload = {
                "behavior_summary": "The Agent attempted the requested operation.",
                "task_analysis": {
                    "status": "failure",
                    "reason": "The official benchmark reported failure.",
                    "evidence_steps": [2],
                },
                "policy_analysis": {
                    "status": "compliant",
                    "reason": "The policy judge reported no violation.",
                    "policy_ids": [],
                    "evidence_steps": [1],
                },
                "root_cause": {
                    "category": "skill_issue" if update else "execution_issue",
                    "explanation": "Only one rollout identifies a reusable gap.",
                },
                "skill_update_relevance": "update" if update else "none",
                "update_recommendation": {
                    "action": "add" if update else "none",
                    "target_section": "Planning and navigation" if update else None,
                    "target_rule_id": None,
                    "objective": "Add a reusable prerequisite check." if update else "",
                    "description": (
                        "Require verification of applicable prerequisites."
                        if update
                        else ""
                    ),
                },
                "preserve_constraints": [],
            }
            response = f"<DIAGNOSIS_JSON>{json.dumps(payload)}</DIAGNOSIS_JSON>"
            role = request.diagnosis_id
        elif isinstance(request, DiagnosisEditorRequest):
            self.editor_calls += 1
            patch = request.eligible_diagnoses[0]
            edit = {
                "derived_from_patch_ids": [patch["patch_id"]],
                "operation": "add",
                "section": "Planning and navigation",
                "target_rule_id": "",
                "text": self.EDITS[self.editor_calls - 1],
                "reason": "Express the diagnosed reusable gap minimally.",
                "source_ids": list(patch["source_ids"]),
                "repair_policy_ids": [],
            }
            response = (
                "<CANONICAL_EDITS_JSON>"
                + json.dumps([edit])
                + "</CANONICAL_EDITS_JSON>"
            )
            role = "editor"
        else:  # pragma: no cover - v0.7 owns the request types
            raise AssertionError(f"Unexpected learner request: {request!r}")
        self.last_call = {
            "role": role,
            "model": model,
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
        }
        self.last_response = response
        return response, "gpt-5.6-luna", {"fake": True}


def test_fake_backend_runs_three_steps_and_resumes_from_checkpoint(
    tmp_path: Path,
) -> None:
    campaign = json.loads(MANIFEST.read_text(encoding="utf-8"))
    batch_map = json.loads(
        (MANIFEST.parent / "batch_map.json").read_text(encoding="utf-8")
    )
    artifact_root = tmp_path / "formal"
    backend = FakeTau3Backend(campaign, batch_map, artifact_root)
    learner = FakeDiagnosisLearner()

    first_adapter = FormalTau3BenchmarkRuntimeAdapter(
        campaign,
        batch_map,
        rollout_backend=backend,
        learner=learner,
        artifact_root=artifact_root,
    )
    first_adapter.run_fresh_initial_checkpoint()
    resume_states = []
    first = run_v09_campaign(
        campaign,
        batch_map,
        first_adapter,
        scheduled_steps=1,
        on_step_completed=resume_states.append,
    )
    assert [step["outcome"] for step in first["steps"]] == ["ACCEPT"]
    assert resume_states[-1]["next_step"] == 2

    resumed_adapter = FormalTau3BenchmarkRuntimeAdapter(
        campaign,
        batch_map,
        rollout_backend=backend,
        learner=learner,
        artifact_root=artifact_root,
    )
    report = run_v09_campaign(
        campaign,
        batch_map,
        resumed_adapter,
        resume_state=resume_states[-1],
    )

    assert [step["outcome"] for step in report["steps"]] == [
        "ACCEPT",
        "REJECT",
        "REJECT",
    ]
    assert report["budget_usage"] == {
        "train_trajectories": 153,
        "initial_selection_trajectories": 54,
        "candidate_selection_trajectories": 162,
        "total_trajectories": 369,
        "candidates": 3,
        "learner_calls": 156,
        "test_trajectories": 0,
    }
    assert learner.diagnosis_calls == 153
    assert learner.editor_calls == 3
    candidate_skills = list((artifact_root / "candidates").glob("*/skill.md"))
    assert candidate_skills
    assert all(
        path.read_text(encoding="utf-8").startswith("# Operational Skill")
        for path in candidate_skills
    )
    assert all(
        "SuiteCRM" not in path.read_text(encoding="utf-8")
        for path in candidate_skills
    )
    assert any(
        item["operation"] == "restore_selection_checkpoint"
        for item in report["runtime_trace"]
    )
    assert all(step["proposal_budget"]["maximum_editor_calls"] == 1 for step in report["steps"])
    selection_seeds = {
        (item["task"], item["rollout_index"]): item["rollout_seed"]
        for item in backend.selection_units
        if item["version"] == "S0"
    }
    assert selection_seeds == {
        (task_id, rollout_index): seed
        for task_id in range(1001, 1019)
        for rollout_index, seed in enumerate((200, 201, 202), start=1)
    }

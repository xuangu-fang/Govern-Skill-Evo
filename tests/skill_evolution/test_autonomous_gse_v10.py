from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from src.adapters.tau2 import tau3_compliance_judge
from src.adapters.tau2.tau3_gse_runtime import _trajectory_model_args
from src.skill_evolution.autonomous_gse_v03_benchmark_runtime import RolloutRequest
from src.skill_evolution.autonomous_gse_v03_proposal import (
    EditorRequest,
    ReflectorRequest,
)
from src.skill_evolution.autonomous_gse_v05_proposal import (
    MAXIMUM_RAW_PATCHES_PER_REFLECTOR,
    MAXIMUM_SKILL_RULES,
    MAXIMUM_SKILL_WORDS,
    RuleIdGovernedReflectionEditorProposalOperator,
)
from src.skill_evolution.autonomous_gse_v09_benchmark_runtime import (
    _task_maps,
)
from src.skill_evolution.autonomous_gse_v10_benchmark_runtime import (
    REUSED_V05_METHOD_FILES,
    REUSED_V09_BENCHMARK_COMPONENTS,
    FormalTau3V05BenchmarkRuntimeAdapter,
    Tau3CampaignRolloutBackend,
    _campaign_paths,
    aggregate_selection_metrics,
    build_campaign_dry_plan,
    derive_rollout_seeds,
    matched_selection_plan,
    proposal_operator,
    register_tau3_step,
    run_v10_campaign,
    validate_campaign_contract,
)
from tests.skill_evolution.test_autonomous_gse_v09 import (
    FakeTau3Backend,
    _write_complete_rollout,
)


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "experiments/campaigns/autonomous_gse_v10/campaign_manifest.json"
V09_MANIFEST = ROOT / "experiments/campaigns/autonomous_gse_v09/campaign_manifest.json"
BATCH_MAP = ROOT / "experiments/campaigns/autonomous_gse_v09/batch_map.json"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_v10_composes_frozen_v09_benchmark_with_v05_method() -> None:
    campaign = _load(MANIFEST)
    frozen = _load(V09_MANIFEST)
    validate_campaign_contract(campaign)

    for field in (
        "execution",
        "benchmark",
        "schedule",
        "train",
        "selection",
        "test",
        "compliance_judge",
        "official_evaluator",
        "agent",
        "user_simulator",
        "gate",
        "provenance",
    ):
        assert campaign[field] == frozen[field]
    assert campaign["train"]["batch_map"].endswith(
        "autonomous_gse_v09/batch_map.json"
    )
    assert campaign["budget"]["maximum_learner_calls"] == 9
    assert campaign["skill_evolution"]["diagnosis_calls_per_train_rollout"] == 0
    assert isinstance(proposal_operator(), RuleIdGovernedReflectionEditorProposalOperator)
    assert "src/skill_evolution/autonomous_gse_v05_proposal.py" in REUSED_V05_METHOD_FILES
    assert "src/adapters/tau2/tau3_compliance_judge.py" in (
        REUSED_V09_BENCHMARK_COMPONENTS
    )


def test_v10_default_artifact_root_is_shared_by_backend_adapter_and_cli() -> None:
    campaign = _load(MANIFEST)
    batch_map = _load(BATCH_MAP)
    expected = ROOT / "artifacts/autonomous_gse_v10/formal"

    backend = Tau3CampaignRolloutBackend(campaign, batch_map)
    adapter = FormalTau3V05BenchmarkRuntimeAdapter(
        campaign,
        batch_map,
        rollout_backend=lambda request: (),
        learner=None,
    )
    paths = _campaign_paths(campaign)

    assert backend._artifact_root == expected
    assert adapter._artifact_root == expected
    assert paths["checkpoint"] == expected / "checkpoints/s0_empty_skill.json"
    assert paths["resume"] == expected / "resume_state.json"
    assert paths["report"] == expected / "campaign_report.json"


def test_v10_plan_has_51_train_experiences_per_step_and_no_diagnosis() -> None:
    campaign = _load(MANIFEST)
    plan = build_campaign_dry_plan(campaign, _load(BATCH_MAP))

    assert plan["computed_budget"] == {
        "train_trajectories": 153,
        "initial_selection_trajectories": 54,
        "maximum_candidate_selection_trajectories": 162,
        "maximum_total_trajectories": 369,
        "maximum_learner_calls": 9,
    }
    assert all(len(step["train_task_ids"]) == 17 for step in plan["steps"])
    assert all(len(step["train_units"]) == 51 for step in plan["steps"])
    assert all(step["diagnosis_calls"] == 0 for step in plan["steps"])
    assert all(step["maximum_learner_calls"] == 3 for step in plan["steps"])
    assert plan["test"]["included_in_plan"] is False


def test_v10_reuses_v09_seeds_and_matched_selection_units() -> None:
    assert derive_rollout_seeds(200, 1000) == (1200, 1201, 1202)
    plan = matched_selection_plan(["airline:3", "retail:3"], 200, 0)
    assert plan["parent"] == plan["candidate"]
    assert {
        (unit["task_id"], unit["rollout_index"], unit["rollout_seed"])
        for unit in plan["parent"]
    } == {
        (domain_task, rollout_index, seed)
        for domain_task in ("airline:3", "retail:3")
        for rollout_index, seed in enumerate((200, 201, 202), start=1)
    }


def test_v10_reuses_v09_call_level_invalid_tool_argument_retries() -> None:
    campaign = _load(MANIFEST)
    frozen = _load(V09_MANIFEST)
    assert campaign["agent"] == frozen["agent"]
    assert campaign["user_simulator"] == frozen["user_simulator"]

    for config in (campaign["agent"], campaign["user_simulator"]):
        args = _trajectory_model_args(config, 200, include_max_tokens=True)
        assert args["invalid_tool_arguments_retries"] == 2
        assert args["empty_response_retries"] == 2


def test_v10_reuses_complete_rollouts_and_reruns_only_invalid_unit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    campaign = _load(MANIFEST)
    frozen = _load(V09_MANIFEST)
    backend = Tau3CampaignRolloutBackend(
        campaign, _load(BATCH_MAP), artifact_root=tmp_path
    )
    root = tmp_path / "rollouts/selection/initial_selection"
    paths = [root / f"airline_11_rollout_{index:02d}.json" for index in range(1, 4)]
    for index, path in enumerate(paths, start=1):
        _write_complete_rollout(path, frozen, index)

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
    assert [(call["rollout_index"], call["rollout_seed"]) for call in calls] == [
        (2, 201)
    ]


def test_tau3_step_registration_does_not_invent_intent_templates() -> None:
    campaign = _load(MANIFEST)
    batch_map = _load(BATCH_MAP)
    step = register_tau3_step(
        campaign,
        batch_map,
        step=1,
        parent={key: campaign["initial_parent"][key] for key in ("kind", "version", "path")},
        parent_checkpoint={
            "kind": "selection_checkpoint",
            "version": "S0",
            "path": "memory://s0.json",
        },
    )
    assert len(step["batch"]["task_ids"]) == 17
    assert "intent_template_id" not in json.dumps(step)
    maps = _task_maps(_load(V09_MANIFEST), batch_map)
    refs = [maps["train"][task_id] for task_id in step["batch"]["task_ids"]]
    assert refs == batch_map["batches"][0]["task_ids"]


def _selection_row(
    domain: str, task_id: str, rollout: int, success: bool, compliant: bool
) -> dict[str, Any]:
    return {
        "domain": domain,
        "task_id": task_id,
        "rollout_index": rollout,
        "task_success": success,
        "compliant": compliant,
        "state": (
            "compliant_success"
            if success and compliant
            else "violating_success"
            if success
            else "compliant_failure"
            if compliant
            else "violating_failure"
        ),
    }


def test_selection_aggregates_rollouts_then_domain_and_overall_without_collision() -> None:
    rows = []
    for domain, task_count in (("airline", 9), ("retail", 9)):
        for task_id in range(task_count):
            for rollout in range(1, 4):
                rows.append(
                    _selection_row(
                        domain,
                        str(task_id),
                        rollout,
                        success=domain == "airline",
                        compliant=rollout != 3,
                    )
                )
    result = aggregate_selection_metrics(rows)
    assert result["aggregation_order"] == [
        "rollout_mean_within_task",
        "task_mean_within_domain",
        "task_mean_overall",
    ]
    assert len(result["task_means"]) == 18
    assert len(
        {
            (row["domain"], row["task_id"])
            for row in result["task_means"]
        }
    ) == 18
    assert result["metrics"]["airline"]["task_success"] == 1.0
    assert result["metrics"]["retail"]["task_success"] == 0.0
    assert result["metrics"]["overall"]["task_success"] == 0.5


class FourStateFakeBackend(FakeTau3Backend):
    def __call__(self, request):
        paths = super().__call__(request)
        if request.split != "train":
            return paths
        for index, path in enumerate(paths):
            value = _load(path)
            rollout = value["rollout_index"]
            success = rollout == 1
            compliant = not (rollout == 2 or (rollout == 1 and index // 3 % 2))
            state = (
                "compliant_success"
                if success and compliant
                else "violating_success"
                if success
                else "compliant_failure"
                if compliant
                else "violating_failure"
            )
            evaluation = value["task_evaluation"]
            evaluation.update(
                {
                    "success": success,
                    "reward": float(success),
                    "db_reward": float(success),
                    "communicate_reward": float(success),
                }
            )
            violations = (
                []
                if compliant
                else [
                    {
                        "policy_template_id": "tau3:test:confirmation",
                        "policy_id": "tau3:test:confirmation",
                        "policy_requirement": "Confirm before mutation.",
                        "description": "Confirm before mutation.",
                        "evidence_steps": [2],
                        "reason": "The mutation preceded confirmation.",
                    }
                ]
            )
            compliance = value["compliance_evaluation"]
            compliance.update({"compliant": compliant, "violations": violations})
            governed = value["governed_evidence"]
            governed.update(
                {
                    "state": state,
                    "task_success": success,
                    "task_evaluation": evaluation,
                    "process_feedback": {
                        "compliant": compliant,
                        "violated_policies": violations,
                    },
                    "compliance_evaluation": compliance,
                }
            )
            value.update(
                {
                    "state": state,
                    "task_evaluation": evaluation,
                    "compliance_evaluation": compliance,
                    "governed_evidence": governed,
                }
            )
            path.write_text(json.dumps(value), encoding="utf-8")
        return paths


class FakeV05Learner:
    EDITS = (
        "Verify applicable prerequisites before taking an action.",
        "Confirm intended changes before a state-changing operation.",
        "Verify the resulting state before reporting completion.",
    )

    def __init__(self) -> None:
        self.success_calls = 0
        self.failure_calls = 0
        self.editor_calls = 0
        self.requests: list[Any] = []
        self.last_call: dict[str, Any] | None = None
        self.last_response: str | None = None

    def call(self, request, model, system_prompt, user_prompt):
        assert model == "openai/gpt-5.6-luna"
        assert "SuiteCRM" not in system_prompt
        assert "SuiteCRM" not in user_prompt
        assert not hasattr(request, "diagnosis_id")
        self.requests.append(request)
        if isinstance(request, ReflectorRequest):
            if request.reflector == "success":
                self.success_calls += 1
                assert {
                    item["state"] for item in request.current_batch_evidence
                } <= {"compliant_success", "violating_success"}
            else:
                self.failure_calls += 1
                assert {
                    item["state"] for item in request.current_batch_evidence
                } <= {"compliant_failure", "violating_failure"}
            patch = {
                "operation": "add",
                "section": "Planning and navigation",
                "target_rule_id": "",
                "text": "Check the request context before acting.",
                "reason": "The batch supports a reusable context check.",
                "source_ids": [request.current_batch_evidence[0]["source_id"]],
                "repair_policy_ids": [],
            }
            response = f"<RAW_PATCHES_JSON>{json.dumps([patch])}</RAW_PATCHES_JSON>"
        elif isinstance(request, EditorRequest):
            self.editor_calls += 1
            patch = request.raw_patches[0]
            edit = {
                "derived_from_patch_ids": [patch["patch_id"]],
                "operation": "add",
                "section": "Planning and navigation",
                "target_rule_id": "",
                "text": self.EDITS[self.editor_calls - 1],
                "reason": "Canonicalize one supported reusable change.",
                "source_ids": list(patch["source_ids"]),
                "repair_policy_ids": list(patch["repair_policy_ids"]),
            }
            response = (
                f"<CANONICAL_EDITS_JSON>{json.dumps([edit])}"
                "</CANONICAL_EDITS_JSON>"
            )
        else:  # pragma: no cover
            raise AssertionError(f"Unexpected learner request: {request!r}")
        self.last_call = {
            "model": model,
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
        }
        self.last_response = response
        return response, "gpt-5.6-luna", {"fake": True}


def test_fake_campaign_uses_two_pooled_reflectors_and_one_editor_per_step(
    tmp_path: Path,
) -> None:
    campaign = _load(MANIFEST)
    batch_map = _load(BATCH_MAP)
    artifact_root = tmp_path / "formal"
    backend = FourStateFakeBackend(_load(V09_MANIFEST), batch_map, artifact_root)
    learner = FakeV05Learner()
    adapter = FormalTau3V05BenchmarkRuntimeAdapter(
        campaign,
        batch_map,
        rollout_backend=backend,
        learner=learner,
        artifact_root=artifact_root,
    )
    adapter.run_fresh_initial_checkpoint()
    report = run_v10_campaign(campaign, batch_map, adapter)

    assert learner.success_calls == 3
    assert learner.failure_calls == 3
    assert learner.editor_calls == 3
    assert len(learner.requests) == 9
    assert report["diagnosis_calls"] == 0
    assert report["budget_usage"]["learner_calls"] == 9
    assert report["budget_usage"]["train_trajectories"] == 153
    assert report["budget_usage"]["initial_selection_trajectories"] == 54
    assert report["budget_usage"]["candidate_selection_trajectories"] == 162
    assert report["budget_usage"]["test_trajectories"] == 0
    assert all(step["proposal_budget"]["maximum_reflector_calls"] == 2 for step in report["steps"])
    assert all(step["proposal_budget"]["maximum_editor_calls"] == 1 for step in report["steps"])
    assert all("diagnosis" not in json.dumps(step).casefold() for step in report["steps"])

    evidence_files = sorted((artifact_root / "steps").glob("*/governed_experience.json"))
    assert len(evidence_files) == 3
    for path in evidence_files:
        payload = _load(path)
        assert payload["experience_count"] == 51
        assert {item["state"] for item in payload["experiences"]} == {
            "compliant_success",
            "violating_success",
            "compliant_failure",
            "violating_failure",
        }
        assert all(item["domain"] in {"airline", "retail"} for item in payload["experiences"])
        assert all(item["rollout_id"].startswith("rollout_") for item in payload["experiences"])
        assert len({item["source_id"] for item in payload["experiences"]}) == 51


def test_v10_uses_the_exact_v09_judge_and_v05_bounds() -> None:
    campaign = _load(MANIFEST)
    assert campaign["compliance_judge"] == _load(V09_MANIFEST)["compliance_judge"]
    assert campaign["compliance_judge"]["model"] == tau3_compliance_judge.JUDGE_MODEL
    assert campaign["compliance_judge"]["temperature"] == tau3_compliance_judge.JUDGE_TEMPERATURE
    assert campaign["compliance_judge"]["prompt_version"] == tau3_compliance_judge.JUDGE_PROMPT_VERSION
    assert MAXIMUM_RAW_PATCHES_PER_REFLECTOR == 4
    assert MAXIMUM_SKILL_RULES == 18
    assert MAXIMUM_SKILL_WORDS == 900

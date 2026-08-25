from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

import src.skill_evolution.autonomous_gse_v07_benchmark_runtime as v07
import src.skill_evolution.autonomous_gse_v08_benchmark_runtime as runtime
from src.adapters.stwebagentbench.benchmark_variant import VARIANT_ENV
from src.skill_evolution.autonomous_gse_v03_controller import reduce_step
from src.skill_evolution.autonomous_gse_v03_runtime import RuntimeContractError

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CAMPAIGN_PATH = (
    PROJECT_ROOT
    / "experiments/campaigns/autonomous_gse_v08/campaign_manifest.json"
)
SCHEMA_PATH = PROJECT_ROOT / "schemas/autonomous_gse_v08_campaign.schema.json"
BATCH_MAP_PATH = (
    PROJECT_ROOT / "experiments/campaigns/autonomous_gse_v02/batch_map.json"
)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def interactive_trajectory() -> dict:
    return {
        "run": {
            "benchmark_variant": "ST-WebAgentBench-Interactive",
            "interactive_protocol_version": "stweb-interactive-v2",
            "user_simulator_model": "openai/gpt-5.6-luna",
            "user_simulator_prompt_version": "stweb-interactive-user-v6",
            "user_scenario_version": "suitecrm-v03-all-v4",
        },
        "interaction": {
            "user_simulator": {
                "model": "openai/gpt-5.6-luna",
                "prompt_version": "stweb-interactive-user-v6",
                "scenario_version": "suitecrm-v03-all-v4",
            }
        },
    }


def test_v08_manifest_expands_the_unchanged_day18_contract() -> None:
    campaign = load_json(CAMPAIGN_PATH)
    errors = list(
        Draft202012Validator(load_json(SCHEMA_PATH)).iter_errors(campaign)
    )
    assert errors == []
    runtime.validate_formal_campaign_contract(campaign, require_ready=True)

    expanded = runtime._expand_campaign(campaign)
    v07_expanded = v07._expand_campaign(
        load_json(
            PROJECT_ROOT
            / "experiments/campaigns/autonomous_gse_v07/campaign_manifest.json"
        )
    )
    for key in (
        "campaign_seed",
        "train_rollouts_per_task",
        "selection_rollouts_per_task",
        "rule_addressing",
        "budget",
        "benchmark_runtime",
        "train",
        "selection",
        "gate",
    ):
        assert expanded[key] == v07_expanded[key]


def test_v08_plan_is_isolated_and_frozen_to_interactive_v2() -> None:
    plan = runtime.build_formal_execution_plan(
        load_json(CAMPAIGN_PATH), load_json(BATCH_MAP_PATH)
    )

    assert plan["schema_version"] == "autonomous_gse_formal_plan_0.8.0"
    assert plan["campaign_id"] == "autonomous_gse_v08"
    assert plan["protocol_version"] == "autonomous_gse_v08"
    assert plan["benchmark_variant"] == runtime.BENCHMARK_VARIANT
    assert len(plan["steps"]) == 3
    assert all(step["training_trajectories"] == 51 for step in plan["steps"])
    assert all(step["maximum_diagnosis_calls"] == 51 for step in plan["steps"])
    assert plan["maximum_budget"] == {
        "train_trajectories": 153,
        "initial_selection_trajectories": 54,
        "maximum_candidate_selection_trajectories": 162,
        "maximum_total_trajectories": 369,
        "maximum_candidates": 3,
        "maximum_learner_calls": 156,
        "unused_budget_reallocation": "forbidden",
    }


def test_v08_registered_step_remains_compatible_with_reused_controller() -> None:
    campaign = runtime._controller_campaign(
        runtime._expand_campaign(load_json(CAMPAIGN_PATH))
    )
    step = runtime._v08_step_registrar(
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

    reduced = reduce_step(step, {"type": "TRAIN_STARTED"}).step

    assert reduced["schema_version"] == "autonomous_gse_step_0.3.0"
    assert reduced["protocol_version"] == "autonomous_gse_v03"


def test_v08_rollout_backend_forces_and_restores_interactive_variant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed = []

    def fake_call(self, request):
        del self, request
        observed.append(os.environ.get(VARIANT_ENV))
        return ()

    monkeypatch.setattr(v07.MultiRolloutRunnerBackend, "__call__", fake_call)
    monkeypatch.setenv(VARIANT_ENV, "original")
    backend = object.__new__(runtime.MultiRolloutRunnerBackend)

    assert backend(None) == ()
    assert observed == ["interactive"]
    assert os.environ[VARIANT_ENV] == "original"


def test_v08_rejects_noninteractive_or_drifted_trajectory_lineage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = interactive_trajectory()
    monkeypatch.setattr(
        v07.FormalBenchmarkRuntimeAdapter,
        "_load_trajectory",
        staticmethod(lambda *args, **kwargs: payload),
    )
    path = Path("trajectory.json")

    assert runtime.FormalBenchmarkRuntimeAdapter._load_trajectory(
        path, 62, 1, "train", {"version": "S0"}
    ) == payload

    payload["run"].pop("interactive_protocol_version")
    with pytest.raises(RuntimeContractError, match="trajectory lineage mismatch"):
        runtime.FormalBenchmarkRuntimeAdapter._load_trajectory(
            path, 62, 1, "train", {"version": "S0"}
        )


def test_v08_formal_cli_uses_new_artifact_root_and_report_metadata(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    checkpoint = tmp_path / "s0_empty_skill.json"
    checkpoint.write_text("{}", encoding="utf-8")
    report_path = tmp_path / "campaign_report.json"
    observed = {}

    monkeypatch.setattr(
        runtime,
        "_campaign_paths",
        lambda campaign: {"checkpoint": checkpoint, "report": report_path},
    )
    monkeypatch.setattr(
        runtime, "FormalBenchmarkRuntimeAdapter", lambda *args, **kwargs: object()
    )
    monkeypatch.setattr(
        runtime.v07.v05,
        "_artifact",
        lambda kind, version, path: {
            "kind": kind,
            "version": version,
            "path": path.name,
        },
    )

    def fake_run(campaign, batch_map, adapter, **kwargs):
        del batch_map, adapter
        observed["controller_protocol"] = campaign["protocol_version"]
        observed["variant"] = os.environ.get(VARIANT_ENV)
        observed["maximum_learner_calls"] = kwargs["maximum_learner_calls"]
        return {
            "budget_usage": {
                "train_trajectories": 0,
                "initial_selection_trajectories": 0,
                "candidate_selection_trajectories": 0,
                "total_trajectories": 0,
            },
            "steps": [],
            "final_parent": {"kind": "empty_skill", "version": "S0"},
        }

    monkeypatch.setattr(runtime, "run_v08_campaign", fake_run)
    result = runtime.run_formal_campaign_cli(
        CAMPAIGN_PATH,
        rollout_backend=lambda request: (),
        learner=object(),
    )

    assert observed == {
        "controller_protocol": "autonomous_gse_v03",
        "variant": "interactive",
        "maximum_learner_calls": 156,
    }
    assert result["status"] == "AUTONOMOUS_GSE_V08_CAMPAIGN_COMPLETED"
    report = load_json(report_path)
    assert report["schema_version"] == "autonomous_gse_formal_report_0.8.0"
    assert report["campaign_id"] == "autonomous_gse_v08"
    assert report["benchmark_variant"] == runtime.BENCHMARK_VARIANT

"""Protocol tests for the seeded Day 14 v0.4 extension."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

import src.skill_evolution.autonomous_gse_v03_benchmark_runtime as v03_formal
from src.adapters.stwebagentbench.seeded_agent import seed_agent_client
from src.skill_evolution.autonomous_gse_v03_proposal import ReflectorRequest
from src.skill_evolution.autonomous_gse_v03_runtime import RuntimeContractError
from src.skill_evolution.autonomous_gse_v04_benchmark_runtime import (
    FormalBenchmarkRuntimeAdapter,
    RolloutRequest,
    SeededLearnerAdapter,
    SeededRunnerRolloutBackend,
    _expand_campaign,
    _load_benchmark_environment,
    build_formal_execution_plan,
    validate_formal_campaign_contract,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = PROJECT_ROOT / "schemas/autonomous_gse_v04_campaign.schema.json"
BATCH_MAP_PATH = (
    PROJECT_ROOT / "experiments/campaigns/autonomous_gse_v02/batch_map.json"
)
CAMPAIGN_PATHS = [
    PROJECT_ROOT
    / f"experiments/campaigns/autonomous_gse_v04_seed_{seed}/campaign_manifest.json"
    for seed in (100, 150, 200)
]
def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_gpt_campaigns_record_the_headless_runtime_change() -> None:
    schema = load_json(SCHEMA_PATH)
    validator = Draft202012Validator(schema)
    campaigns = [load_json(path) for path in CAMPAIGN_PATHS]

    for campaign in campaigns:
        assert list(validator.iter_errors(campaign)) == []
        validate_formal_campaign_contract(campaign, require_ready=True)

    assert "headless" not in campaigns[0]
    assert campaigns[1]["headless"] is True
    assert campaigns[2]["headless"] is True

    normalized = []
    for campaign in campaigns[1:]:
        item = copy.deepcopy(campaign)
        item.pop("campaign_id")
        item.pop("campaign_seed")
        item.pop("execution", None)
        item.pop("parallel_workers", None)
        normalized.append(item)
    assert normalized[0] == normalized[1]
    assert "execution" not in campaigns[1]
    assert campaigns[2]["execution"] == "parallel"
    assert campaigns[2]["parallel_workers"] == 4


def test_default_learner_loads_benchmark_environment_without_overrides(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = []

    def load_dotenv(path, *, override):
        calls.append((path, override))

    monkeypatch.setattr("dotenv.load_dotenv", load_dotenv)
    _load_benchmark_environment()

    assert calls == [
        (PROJECT_ROOT / "external/ST-WebAgentBench/.env", False)
    ]


def test_parallel_execution_defaults_to_four_workers() -> None:
    campaign = load_json(CAMPAIGN_PATHS[1])
    campaign["execution"] = "parallel"

    expanded = _expand_campaign(campaign)

    assert expanded["benchmark_runtime"]["rollout"]["parallel_workers"] == 4


def test_plan_contains_only_current_batch_replay_and_final_test() -> None:
    campaign = load_json(CAMPAIGN_PATHS[0])
    plan = build_formal_execution_plan(campaign, load_json(BATCH_MAP_PATH))

    assert plan["campaign_seed"] == 100
    assert len(plan["final_test_task_ids"]) == 18
    assert len(plan["steps"]) == 3
    for step in plan["steps"]:
        assert step["current_batch_replay_task_ids"] == step["train_task_ids"]
        assert len(step["current_batch_replay_task_ids"]) == 17
    assert plan["maximum_budget"]["maximum_total_trajectories"] == 210
    assert plan["headless"] is False
    assert plan["execution"] == "sequential"
    assert plan["parallel_workers"] == 1


def test_future_gpt_campaign_plan_is_headless() -> None:
    campaign = load_json(CAMPAIGN_PATHS[1])
    plan = build_formal_execution_plan(campaign, load_json(BATCH_MAP_PATH))
    backend = SeededRunnerRolloutBackend(campaign)

    assert plan["campaign_seed"] == 150
    assert plan["headless"] is True
    assert backend._headless is True


def test_campaign_seed_and_id_must_match() -> None:
    campaign = load_json(CAMPAIGN_PATHS[0])
    campaign["campaign_seed"] = 101
    with pytest.raises(RuntimeContractError, match="disagree"):
        validate_formal_campaign_contract(campaign)


def test_seeded_agent_proxy_adds_seed_to_every_model_call() -> None:
    calls = []

    class Completions:
        def create(self, **kwargs):
            calls.append(kwargs)
            return "response"

    class Agent:
        class Client:
            class Chat:
                completions = Completions()

            chat = Chat()

        openai_client = Client()

    agent = seed_agent_client(Agent(), 150)
    assert agent.openai_client.chat.completions.create(model="m") == "response"
    assert calls == [{"model": "m", "seed": 150}]


def test_rollout_backend_passes_campaign_seed_and_requested_split(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = []

    def runner(args, manifest, method, skill, task):
        calls.append((args, manifest, method, skill, task))
        return Path("/tmp/seeded-trajectory.json")

    monkeypatch.setattr(v03_formal, "_run_selection_task", runner)
    campaign = load_json(CAMPAIGN_PATHS[0])
    backend = SeededRunnerRolloutBackend(campaign)
    artifact = {
        "kind": "empty_skill",
        "version": "S0",
        "path": "experiments/campaigns/autonomous_gse_v03/skills/S0_empty_skill.md",
    }
    paths = backend(RolloutRequest("test", "s0_empty_skill", artifact, (53,)))

    assert paths == (Path("/tmp/seeded-trajectory.json"),)
    args, manifest, method, skill, task = calls[0]
    assert args.seed == 100
    assert manifest["_output_split"] == "test"
    assert method == "s0_empty_skill"
    assert skill["block"] is None
    assert task["task_id"] == 53


def test_parallel_rollout_is_opt_in_and_preserves_requested_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    campaign = load_json(CAMPAIGN_PATHS[0])
    campaign["execution"] = "parallel"
    campaign["parallel_workers"] = 4
    calls = []

    def run_subprocess_rollouts(payloads, *, parallel_workers):
        calls.append((payloads, parallel_workers))
        return (
            tuple(Path(f"/tmp/task-{item['task']['task_id']}.json") for item in payloads),
            {"events": [], "wall_clock_seconds": 1.0},
        )

    monkeypatch.setattr(
        "src.adapters.stwebagentbench.parallel_rollout.run_subprocess_rollouts",
        run_subprocess_rollouts,
    )
    monkeypatch.setattr(
        "src.skill_evolution.autonomous_gse_v04_benchmark_runtime._write_json",
        lambda path, payload: None,
    )
    backend = SeededRunnerRolloutBackend(campaign)
    artifact = {
        "kind": "empty_skill",
        "version": "S0",
        "path": "experiments/campaigns/autonomous_gse_v03/skills/S0_empty_skill.md",
    }

    paths = backend(
        RolloutRequest("selection", "s0_empty_skill", artifact, (50, 51))
    )

    assert paths == (Path("/tmp/task-50.json"), Path("/tmp/task-51.json"))
    payloads, workers = calls[0]
    assert workers == 4
    assert [item["task"]["task_id"] for item in payloads] == [50, 51]
    assert all(item["manifest"]["_output_split"] == "selection" for item in payloads)


def test_current_batch_replay_runs_only_after_gate_decision(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events = []
    adapter = object.__new__(FormalBenchmarkRuntimeAdapter)

    def gate(self, step, summary):
        events.append("gate")
        return "REJECT"

    monkeypatch.setattr(v03_formal.FormalBenchmarkRuntimeAdapter, "apply_gate", gate)
    monkeypatch.setattr(
        adapter,
        "_run_current_batch_replay",
        lambda step: events.append("replay"),
    )

    assert adapter.apply_gate({"step": 1}, {"summary": 1}) == "REJECT"
    assert events == ["gate", "replay"]


def test_learner_adapter_strictly_passes_campaign_seed() -> None:
    calls = []

    def caller(model, system, user, *, seed):
        calls.append((model, system, user, seed))
        return "<RAW_PATCHES_JSON>[]</RAW_PATCHES_JSON>", "gpt-5.6-luna", None

    campaign = load_json(CAMPAIGN_PATHS[2])
    adapter = SeededLearnerAdapter(campaign, caller=caller)
    request = ReflectorRequest(
        candidate_id="candidate",
        reflector="success",
        current_parent_skill="# Skill",
        current_batch_evidence=(),
        maximum_raw_patches=4,
    )
    adapter.call(request, "openai/gpt-5.6-luna", "system", "user")

    assert calls == [("openai/gpt-5.6-luna", "system", "user", 200)]
    assert adapter.last_call["parameters"]["seed"] == 200


def test_unsupported_learner_seed_is_not_silently_retried() -> None:
    def caller(model, system, user):
        raise AssertionError("must not be reached without strict keyword checking")

    campaign = load_json(CAMPAIGN_PATHS[0])
    adapter = SeededLearnerAdapter(campaign, caller=caller)
    request = ReflectorRequest(
        candidate_id="candidate",
        reflector="failure",
        current_parent_skill="# Skill",
        current_batch_evidence=(),
        maximum_raw_patches=4,
    )
    with pytest.raises(TypeError):
        adapter.call(request, "openai/gpt-5.6-luna", "system", "user")

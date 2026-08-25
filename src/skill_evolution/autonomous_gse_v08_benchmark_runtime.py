"""Day 18 Diagnosis Evolution on ST-WebAgentBench-Interactive v2."""

from __future__ import annotations

import copy
import json
import os
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import src.skill_evolution.autonomous_gse_v07_benchmark_runtime as v07
from src.adapters.stwebagentbench.benchmark_variant import (
    INTERACTIVE_PROTOCOL_VERSION,
    INTERACTIVE_VARIANT,
    USER_SCENARIO_VERSION,
    USER_SIMULATOR_MODEL,
    USER_SIMULATOR_PROMPT_VERSION,
    VARIANT_ENV,
)
from src.skill_evolution.autonomous_gse_v03_benchmark_runtime import (
    RolloutRequest,
)
from src.skill_evolution.autonomous_gse_v03_runtime import RuntimeContractError

REPO_ROOT = Path(__file__).resolve().parents[2]
FORMAL_MODE = "formal_stwebagentbench_v08"
CAMPAIGN_REPORT_FILENAME = "campaign_report.json"
PROTOCOL_VERSION = "autonomous_gse_v08"
CAMPAIGN_ID = "autonomous_gse_v08"
CAMPAIGN_SCHEMA_VERSION = "autonomous_gse_campaign_0.8.0"
REPORT_SCHEMA_VERSION = "autonomous_gse_runtime_report_0.8.0"
FORMAL_REPORT_SCHEMA_VERSION = "autonomous_gse_formal_report_0.8.0"
STEP_SCHEMA_VERSION = "autonomous_gse_step_0.8.0"
PLAN_SCHEMA_VERSION = "autonomous_gse_formal_plan_0.8.0"

BENCHMARK_VARIANT = {
    "name": "ST-WebAgentBench-Interactive",
    "environment": "browsergym/STWebAgentBenchInteractiveEnv.<task_id>",
    "protocol_version": INTERACTIVE_PROTOCOL_VERSION,
    "user_simulator_model": USER_SIMULATOR_MODEL,
    "prompt_version": USER_SIMULATOR_PROMPT_VERSION,
    "scenario_version": USER_SCENARIO_VERSION,
    "report_infeasible_registered": True,
}


def _resolve_repo_path(relative_path: str) -> Path:
    path = (REPO_ROOT / relative_path).resolve()
    path.relative_to(REPO_ROOT)
    return path


def _expand_campaign(campaign: dict[str, Any]) -> dict[str, Any]:
    """Expand the v0.8 overlay through the complete v0.7 campaign."""

    base_path = campaign.get("base_campaign")
    if base_path is None:
        return copy.deepcopy(campaign)
    base = json.loads(_resolve_repo_path(base_path).read_text(encoding="utf-8"))
    expanded_base = v07._expand_campaign(base)
    expanded = {**expanded_base, **copy.deepcopy(campaign)}
    expanded["benchmark_runtime"] = copy.deepcopy(
        expanded_base["benchmark_runtime"]
    )
    return expanded


def _v07_contract_campaign(campaign: dict[str, Any]) -> dict[str, Any]:
    """Project the v0.8 overlay onto the unchanged Day 18 contract."""

    projected = copy.deepcopy(_expand_campaign(campaign))
    projected["schema_version"] = "autonomous_gse_campaign_0.7.0"
    projected["protocol_version"] = "autonomous_gse_v07"
    projected["campaign_id"] = "autonomous_gse_v07"
    projected["base_campaign"] = (
        "experiments/campaigns/autonomous_gse_v03/campaign_manifest.json"
    )
    projected.pop("benchmark_variant", None)
    return projected


def _controller_campaign(campaign: dict[str, Any]) -> dict[str, Any]:
    return v07._controller_campaign(_v07_contract_campaign(campaign))


def validate_formal_campaign_contract(
    campaign: dict[str, Any], *, require_ready: bool = False
) -> None:
    campaign = _expand_campaign(campaign)
    if campaign.get("schema_version") != CAMPAIGN_SCHEMA_VERSION:
        raise RuntimeContractError("Unsupported v0.8 Campaign schema.")
    if campaign.get("protocol_version") != PROTOCOL_VERSION:
        raise RuntimeContractError("Unsupported v0.8 Campaign protocol.")
    if campaign.get("campaign_id") != CAMPAIGN_ID:
        raise RuntimeContractError("v0.8 Campaign ID is invalid.")
    if campaign.get("benchmark_variant") != BENCHMARK_VARIANT:
        raise RuntimeContractError(
            "v0.8 requires the frozen ST-WebAgentBench-Interactive v2 variant."
        )
    v07.validate_formal_campaign_contract(
        _v07_contract_campaign(campaign), require_ready=require_ready
    )


@contextmanager
def _interactive_variant() -> Iterator[None]:
    previous = os.environ.get(VARIANT_ENV)
    os.environ[VARIANT_ENV] = INTERACTIVE_VARIANT
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop(VARIANT_ENV, None)
        else:
            os.environ[VARIANT_ENV] = previous


class SeededLearnerAdapter(v07.SeededLearnerAdapter):
    campaign_validator = staticmethod(validate_formal_campaign_contract)
    campaign_expander = staticmethod(_expand_campaign)


class MultiRolloutRunnerBackend(v07.MultiRolloutRunnerBackend):
    campaign_validator = staticmethod(validate_formal_campaign_contract)
    campaign_expander = staticmethod(_expand_campaign)

    def __call__(self, request: RolloutRequest) -> Sequence[Path]:
        with _interactive_variant():
            return super().__call__(request)


class FormalBenchmarkRuntimeAdapter(v07.FormalBenchmarkRuntimeAdapter):
    mode = FORMAL_MODE
    campaign_validator = staticmethod(validate_formal_campaign_contract)
    campaign_expander = staticmethod(_expand_campaign)
    controller_campaign = staticmethod(_controller_campaign)

    @staticmethod
    def _load_trajectory(
        path: Path,
        task_id: int,
        rollout_id: int,
        split: str,
        artifact: dict[str, Any],
    ) -> dict[str, Any]:
        trajectory = v07.FormalBenchmarkRuntimeAdapter._load_trajectory(
            path, task_id, rollout_id, split, artifact
        )
        run = trajectory.get("run", {})
        expected_run_metadata = {
            "benchmark_variant": BENCHMARK_VARIANT["name"],
            "interactive_protocol_version": BENCHMARK_VARIANT["protocol_version"],
            "user_simulator_model": BENCHMARK_VARIANT["user_simulator_model"],
            "user_simulator_prompt_version": BENCHMARK_VARIANT["prompt_version"],
            "user_scenario_version": BENCHMARK_VARIANT["scenario_version"],
        }
        if any(run.get(key) != value for key, value in expected_run_metadata.items()):
            raise RuntimeContractError(
                f"Interactive v2 trajectory lineage mismatch: {path}"
            )
        simulator = trajectory.get("interaction", {}).get("user_simulator", {})
        expected_simulator_metadata = {
            "model": BENCHMARK_VARIANT["user_simulator_model"],
            "prompt_version": BENCHMARK_VARIANT["prompt_version"],
            "scenario_version": BENCHMARK_VARIANT["scenario_version"],
        }
        if any(
            simulator.get(key) != value
            for key, value in expected_simulator_metadata.items()
        ):
            raise RuntimeContractError(
                f"Interactive v2 UserSimulator lineage mismatch: {path}"
            )
        return trajectory


def _v08_step_registrar(*args: Any, **kwargs: Any) -> dict[str, Any]:
    # The reused v03 controller must see its native mutable Step contract while
    # it reduces events.  v08 metadata is attached only after the campaign has
    # completed, in _normalize_v08_report(), just as v07 does.
    return v07._v07_step_registrar(*args, **kwargs)


def _normalize_v08_report(report: dict[str, Any]) -> dict[str, Any]:
    normalized = copy.deepcopy(report)
    normalized["schema_version"] = REPORT_SCHEMA_VERSION
    normalized["campaign_id"] = CAMPAIGN_ID
    normalized["benchmark_variant"] = copy.deepcopy(BENCHMARK_VARIANT)
    for step in normalized["steps"]:
        step["schema_version"] = STEP_SCHEMA_VERSION
        step["protocol_version"] = PROTOCOL_VERSION
        step["campaign_id"] = CAMPAIGN_ID
        step["benchmark_variant"] = copy.deepcopy(BENCHMARK_VARIANT)
    return normalized


def run_v08_campaign(
    campaign: dict[str, Any],
    batch_map: dict[str, Any],
    adapter: Any,
    *,
    scheduled_steps: int = 3,
    maximum_learner_calls: int | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    if any(
        key in kwargs
        for key in ("proposal_driver", "budget_campaign", "step_registrar")
    ):
        raise TypeError(
            "v0.8 owns proposal_driver, step registration, and its learner budget."
        )
    budget_campaign = copy.deepcopy(campaign)
    budget_campaign["budget"]["maximum_learner_calls"] = (
        campaign["budget"]["train_trajectories"] + scheduled_steps
        if maximum_learner_calls is None
        else maximum_learner_calls
    )
    report = v07.v05.run_v05_campaign(
        campaign,
        batch_map,
        adapter,
        scheduled_steps=scheduled_steps,
        step_registrar=_v08_step_registrar,
        budget_campaign=budget_campaign,
        proposal_driver=v07._proposal_driver(
            v07.DiagnosisDrivenProposalOperator()
        ),
        **kwargs,
    )
    return _normalize_v08_report(report)


def _campaign_paths(campaign: dict[str, Any]) -> dict[str, Path]:
    root = REPO_ROOT / "artifacts" / campaign["campaign_id"] / "formal"
    return {
        "checkpoint": root / "checkpoints/s0_empty_skill.json",
        "report": root / CAMPAIGN_REPORT_FILENAME,
    }


def build_formal_execution_plan(
    campaign: dict[str, Any], batch_map: dict[str, Any]
) -> dict[str, Any]:
    campaign = _expand_campaign(campaign)
    validate_formal_campaign_contract(campaign)
    plan = v07.build_formal_execution_plan(
        _v07_contract_campaign(campaign), batch_map
    )
    plan["schema_version"] = PLAN_SCHEMA_VERSION
    plan["campaign_id"] = CAMPAIGN_ID
    plan["protocol_version"] = PROTOCOL_VERSION
    plan["benchmark_variant"] = copy.deepcopy(BENCHMARK_VARIANT)
    for step in plan["steps"]:
        step["benchmark_variant"] = copy.deepcopy(BENCHMARK_VARIANT)
    return plan


def run_initial_checkpoint(
    campaign_path: Path,
    *,
    rollout_backend: Callable[..., Sequence[Path]] | None = None,
) -> dict[str, Any]:
    campaign = _expand_campaign(
        json.loads(campaign_path.resolve().read_text(encoding="utf-8"))
    )
    validate_formal_campaign_contract(campaign, require_ready=True)
    paths = _campaign_paths(campaign)
    if paths["checkpoint"].exists():
        raise RuntimeContractError("Initial checkpoint already exists.")
    adapter = FormalBenchmarkRuntimeAdapter(
        campaign,
        rollout_backend=rollout_backend or MultiRolloutRunnerBackend(campaign),
        learner=None,
    )
    with _interactive_variant():
        checkpoint = adapter.run_fresh_initial_checkpoint()
    return {"status": "S0_CHECKPOINT_CREATED", "checkpoint": checkpoint}


def run_formal_campaign_cli(
    campaign_path: Path,
    *,
    rollout_backend: Callable[..., Sequence[Path]] | None = None,
    learner: SeededLearnerAdapter | None = None,
) -> dict[str, Any]:
    campaign = _expand_campaign(
        json.loads(campaign_path.resolve().read_text(encoding="utf-8"))
    )
    validate_formal_campaign_contract(campaign, require_ready=True)
    paths = _campaign_paths(campaign)
    if not paths["checkpoint"].is_file():
        raise RuntimeContractError("Initial S0 checkpoint is missing.")
    if paths["report"].exists():
        raise RuntimeContractError("Campaign report already exists.")
    if learner is None:
        from dotenv import load_dotenv

        load_dotenv(REPO_ROOT / "external/ST-WebAgentBench/.env", override=False)
        learner = SeededLearnerAdapter(campaign)
    batch_map = json.loads(
        v07.v05._resolve_repo_path(campaign["train"]["batch_map"]).read_text(
            encoding="utf-8"
        )
    )
    adapter = FormalBenchmarkRuntimeAdapter(
        campaign,
        rollout_backend=rollout_backend or MultiRolloutRunnerBackend(campaign),
        learner=learner,
    )
    with _interactive_variant():
        report = run_v08_campaign(
            _controller_campaign(campaign),
            batch_map,
            adapter,
            maximum_learner_calls=campaign["budget"]["maximum_learner_calls"],
        )
    report["schema_version"] = FORMAL_REPORT_SCHEMA_VERSION
    report["campaign_id"] = CAMPAIGN_ID
    report["campaign_seed"] = campaign["campaign_seed"]
    report["rule_addressing"] = copy.deepcopy(campaign["rule_addressing"])
    report["benchmark_variant"] = copy.deepcopy(BENCHMARK_VARIANT)
    usage = report["budget_usage"]
    usage["train_trajectories"] *= campaign["train_rollouts_per_task"]
    usage["initial_selection_trajectories"] *= campaign[
        "selection_rollouts_per_task"
    ]
    usage["candidate_selection_trajectories"] *= campaign[
        "selection_rollouts_per_task"
    ]
    usage["total_trajectories"] = (
        usage["train_trajectories"]
        + usage["initial_selection_trajectories"]
        + usage["candidate_selection_trajectories"]
    )
    if usage["total_trajectories"] > campaign["budget"]["maximum_total_trajectories"]:
        raise RuntimeContractError("v0.8 rollout budget was exceeded.")
    report["disabled_phases"] = {
        "post_hoc_training_replay": True,
        "final_test_evaluation": True,
        "three_seed_full_experiment": True,
        "legacy_original_control": True,
    }
    v07.v05._write_json(paths["report"], report)
    return {
        "status": "AUTONOMOUS_GSE_V08_CAMPAIGN_COMPLETED",
        "report": v07.v05._artifact(
            "campaign_report", CAMPAIGN_ID, paths["report"]
        ),
        "step_outcomes": [step["outcome"] for step in report["steps"]],
        "final_parent": report["final_parent"],
    }


def main(argv: Sequence[str] | None = None) -> int:
    import argparse

    default_campaign = REPO_ROOT / (
        "experiments/campaigns/autonomous_gse_v08/campaign_manifest.json"
    )
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("plan", "initial-checkpoint", "run"):
        subparser = subparsers.add_parser(command)
        subparser.add_argument("--campaign", type=Path, default=default_campaign)
    args = parser.parse_args(argv)
    campaign = _expand_campaign(
        json.loads(args.campaign.resolve().read_text(encoding="utf-8"))
    )
    if args.command == "plan":
        batch_map = json.loads(
            v07.v05._resolve_repo_path(campaign["train"]["batch_map"]).read_text(
                encoding="utf-8"
            )
        )
        result = build_formal_execution_plan(campaign, batch_map)
    elif args.command == "initial-checkpoint":
        result = run_initial_checkpoint(args.campaign)
    else:
        result = run_formal_campaign_cli(args.campaign)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

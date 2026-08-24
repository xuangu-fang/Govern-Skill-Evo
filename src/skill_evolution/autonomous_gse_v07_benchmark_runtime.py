"""v0.7 Diagnosis proposal wiring over the unchanged v0.5 runtime/Selection."""

from __future__ import annotations

import copy
import json
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

import src.skill_evolution.autonomous_gse_v05_benchmark_runtime as v05
from src.learners.stwebagentbench.generate_governed_skill_v07 import (
    call_governed_editor,
)
from src.skill_evolution.autonomous_gse_v03_runtime import (
    RuntimeContractError,
    register_step,
)
from src.skill_evolution.autonomous_gse_v07_proposal import (
    DiagnosisDrivenProposalOperator,
)
from src.skill_evolution.diagnosis import call_diagnosis

REPO_ROOT = Path(__file__).resolve().parents[2]
FORMAL_MODE = "formal_stwebagentbench_v07"
CAMPAIGN_REPORT_FILENAME = "campaign_report.json"
PROTOCOL_VERSION = "autonomous_gse_v07"
STEP_SCHEMA_VERSION = "autonomous_gse_step_0.7.0"
PROPOSAL_OPERATOR = "diagnosis_driven_bounded_edit"


def _expand_campaign(campaign: dict[str, Any]) -> dict[str, Any]:
    return v05._expand_campaign(campaign)


def _v05_contract_campaign(campaign: dict[str, Any]) -> dict[str, Any]:
    """Project v0.7 formal settings onto the reused v0.5 contract."""

    projected = copy.deepcopy(campaign)
    projected["schema_version"] = "autonomous_gse_campaign_0.5.0"
    projected["protocol_version"] = "autonomous_gse_v05"
    projected["campaign_id"] = "autonomous_gse_v05"
    projected["budget"]["maximum_learner_calls"] = 9
    return projected


def _controller_campaign(campaign: dict[str, Any]) -> dict[str, Any]:
    return v05._v03_campaign(_v05_contract_campaign(campaign))


def _v07_step_registrar(*args: Any, **kwargs: Any) -> dict[str, Any]:
    step = register_step(*args, **kwargs)
    campaign = args[0] if args else kwargs["campaign"]
    step["proposal_operator"] = PROPOSAL_OPERATOR
    step["proposal_budget"] = {
        "maximum_diagnosis_calls": len(step["batch"]["task_ids"])
        * campaign["train_rollouts_per_task"],
        "eligible_update_diagnoses": "all_valid_updates",
        "maximum_editor_calls": 1,
        "additional_minibatching": False,
        "maximum_skill_rules": 18,
        "maximum_skill_words": 900,
        "allowed_operations": ["add", "replace", "delete"],
    }
    return step


def _normalize_v07_report(report: dict[str, Any]) -> dict[str, Any]:
    normalized = copy.deepcopy(report)
    normalized["schema_version"] = "autonomous_gse_runtime_report_0.7.0"
    normalized["campaign_id"] = PROTOCOL_VERSION
    normalized["proposal_pipeline"] = PROPOSAL_OPERATOR
    for step in normalized["steps"]:
        step["schema_version"] = STEP_SCHEMA_VERSION
        step["protocol_version"] = PROTOCOL_VERSION
        step["campaign_id"] = PROTOCOL_VERSION
    return normalized


def validate_formal_campaign_contract(
    campaign: dict[str, Any], *, require_ready: bool = False
) -> None:
    campaign = _expand_campaign(campaign)
    if campaign.get("schema_version") != "autonomous_gse_campaign_0.7.0":
        raise RuntimeContractError("Unsupported v0.7 Campaign schema.")
    if campaign.get("protocol_version") != "autonomous_gse_v07":
        raise RuntimeContractError("Unsupported v0.7 Campaign protocol.")
    if campaign.get("campaign_id") != "autonomous_gse_v07":
        raise RuntimeContractError("v0.7 Campaign ID is invalid.")
    expected_calls = campaign.get("budget", {}).get("train_trajectories", 0) + 3
    if campaign.get("budget", {}).get("maximum_learner_calls") != expected_calls:
        raise RuntimeContractError(
            "v0.7 must budget one Diagnosis per Train rollout and one Editor per Step."
        )
    v05.validate_formal_campaign_contract(
        _v05_contract_campaign(campaign), require_ready=require_ready
    )


class SeededLearnerAdapter(v05.SeededLearnerAdapter):
    campaign_validator = staticmethod(validate_formal_campaign_contract)
    campaign_expander = staticmethod(_expand_campaign)


class MultiRolloutRunnerBackend(v05.MultiRolloutRunnerBackend):
    campaign_validator = staticmethod(validate_formal_campaign_contract)
    campaign_expander = staticmethod(_expand_campaign)


class FormalBenchmarkRuntimeAdapter(v05.FormalBenchmarkRuntimeAdapter):
    mode = FORMAL_MODE
    campaign_validator = staticmethod(validate_formal_campaign_contract)
    campaign_expander = staticmethod(_expand_campaign)
    controller_campaign = staticmethod(_controller_campaign)


def _proposal_driver(operator: DiagnosisDrivenProposalOperator) -> Callable[..., Any]:
    def propose(context: Any, step: dict[str, Any], adapter: Any) -> Any:
        def diagnose(request: Any) -> str:
            return call_diagnosis(
                request,
                learner_call=lambda model, system_prompt, user_prompt: (
                    adapter.learner_call(
                        copy.deepcopy(step),
                        request,
                        model,
                        system_prompt,
                        user_prompt,
                    )
                ),
            )

        def edit(request: Any) -> str:
            return call_governed_editor(
                request,
                learner_call=lambda model, system_prompt, user_prompt: (
                    adapter.learner_call(
                        copy.deepcopy(step),
                        request,
                        model,
                        system_prompt,
                        user_prompt,
                    )
                ),
            )

        return operator.propose(context, diagnose, edit)

    return propose


def run_v07_campaign(
    campaign: dict[str, Any],
    batch_map: dict[str, Any],
    adapter: Any,
    *,
    scheduled_steps: int = 3,
    maximum_learner_calls: int | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Run Diagnosis→bounded Editor with v0.5 Update, Selection, and gate.

    The only budget change is the learner-call ceiling: v0.7 performs one
    Diagnosis call per training rollout and at most one Editor call per Step.
    All trajectory and Selection ceilings remain those supplied by v0.5.
    """

    if any(
        key in kwargs
        for key in ("proposal_driver", "budget_campaign", "step_registrar")
    ):
        raise TypeError(
            "v0.7 owns proposal_driver, step registration, and its learner-call budget."
        )
    budget_campaign = copy.deepcopy(campaign)
    budget_campaign["budget"]["maximum_learner_calls"] = (
        campaign["budget"]["train_trajectories"] + scheduled_steps
        if maximum_learner_calls is None
        else maximum_learner_calls
    )
    report = v05.run_v05_campaign(
        campaign,
        batch_map,
        adapter,
        scheduled_steps=scheduled_steps,
        step_registrar=_v07_step_registrar,
        budget_campaign=budget_campaign,
        proposal_driver=_proposal_driver(DiagnosisDrivenProposalOperator()),
        **kwargs,
    )
    return _normalize_v07_report(report)


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
    plan = v05.build_formal_execution_plan(
        _v05_contract_campaign(campaign), batch_map
    )
    plan["schema_version"] = "autonomous_gse_formal_plan_0.7.0"
    plan["campaign_id"] = campaign["campaign_id"]
    plan["proposal_pipeline"] = "diagnosis_driven_bounded_edit"
    plan["maximum_budget"] = copy.deepcopy(campaign["budget"])
    for step in plan["steps"]:
        step.pop("maximum_raw_patches_per_reflector", None)
        step.pop("maximum_reflector_calls", None)
        step["maximum_diagnosis_calls"] = step["training_trajectories"]
        step["maximum_editor_calls"] = 1
        step["maximum_learner_calls"] = step["training_trajectories"] + 1
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
        v05._resolve_repo_path(campaign["train"]["batch_map"]).read_text(
            encoding="utf-8"
        )
    )
    adapter = FormalBenchmarkRuntimeAdapter(
        campaign,
        rollout_backend=rollout_backend or MultiRolloutRunnerBackend(campaign),
        learner=learner,
    )
    report = run_v07_campaign(
        _controller_campaign(campaign),
        batch_map,
        adapter,
        maximum_learner_calls=campaign["budget"]["maximum_learner_calls"],
    )
    report["schema_version"] = "autonomous_gse_formal_report_0.7.0"
    report["campaign_id"] = campaign["campaign_id"]
    report["campaign_seed"] = campaign["campaign_seed"]
    report["rule_addressing"] = copy.deepcopy(campaign["rule_addressing"])
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
        raise RuntimeContractError("v0.7 rollout budget was exceeded.")
    report["disabled_phases"] = {
        "post_hoc_training_replay": True,
        "final_test_evaluation": True,
        "three_seed_full_experiment": True,
    }
    v05._write_json(paths["report"], report)
    return {
        "status": "AUTONOMOUS_GSE_V07_CAMPAIGN_COMPLETED",
        "report": v05._artifact(
            "campaign_report", campaign["campaign_id"], paths["report"]
        ),
        "step_outcomes": [step["outcome"] for step in report["steps"]],
        "final_parent": report["final_parent"],
    }


def main(argv: Sequence[str] | None = None) -> int:
    import argparse

    default_campaign = REPO_ROOT / (
        "experiments/campaigns/autonomous_gse_v07/campaign_manifest.json"
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
            v05._resolve_repo_path(campaign["train"]["batch_map"]).read_text(
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

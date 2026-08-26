"""τ³ Airline/Retail backend with the unchanged v0.5 proposal semantics."""

from __future__ import annotations

import copy
import json
from collections import defaultdict
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from src.adapters.tau2.tau3_compliance_judge import (
    JudgeCaller,
    default_judge_caller,
)
from src.skill_evolution.autonomous_gse_v03_benchmark_runtime import RolloutRequest
import src.skill_evolution.autonomous_gse_v03_controller as v03_controller
from src.skill_evolution.autonomous_gse_v03_proposal import (
    EditorRequest,
    ReflectorRequest,
)
from src.skill_evolution.autonomous_gse_v03_runtime import RuntimeContractError
import src.skill_evolution.autonomous_gse_v05_benchmark_runtime as v05
from src.skill_evolution.autonomous_gse_v05_proposal import (
    RuleIdGovernedReflectionEditorProposalOperator,
)
import src.skill_evolution.autonomous_gse_v09_benchmark_runtime as v09


PROTOCOL_VERSION = "autonomous_gse_v10"
FORMAL_MODE = "formal_tau3_airline_retail_v10_v05_multi_rollout"
REPO_ROOT = Path(__file__).resolve().parents[2]
CAMPAIGN_REPORT_FILENAME = "campaign_report.json"
RESUME_STATE_FILENAME = "resume_state.json"

# Method and benchmark implementations are imported rather than forked.
REUSED_V05_METHOD_FILES = (
    "src/skill_evolution/autonomous_gse_v05_proposal.py",
    "src/learners/stwebagentbench/generate_governed_skill_v05.py",
    "src/skill_evolution/two_dimensional_gate.py",
)
REUSED_V09_BENCHMARK_COMPONENTS = (
    "src/skill_evolution/autonomous_gse_v09_benchmark_runtime.py",
    "src/adapters/tau2/tau3_gse_runtime.py",
    "src/adapters/tau2/tau3_compliance_judge.py",
    "experiments/campaigns/autonomous_gse_v09/batch_map.json",
)


def _artifact_root(
    campaign: dict[str, Any], artifact_root: Path | None
) -> Path:
    return artifact_root or (
        REPO_ROOT / "artifacts" / campaign["campaign_id"] / "formal"
    )


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _v09_manifest() -> dict[str, Any]:
    return _load_json(
        REPO_ROOT
        / "experiments/campaigns/autonomous_gse_v09/campaign_manifest.json"
    )


def _v05_manifest() -> dict[str, Any]:
    return v05._expand_campaign(
        _load_json(
            REPO_ROOT
            / "experiments/campaigns/autonomous_gse_v05/campaign_manifest.json"
        )
    )


def validate_campaign_contract(campaign: dict[str, Any]) -> None:
    if (
        campaign.get("schema_version") != "autonomous_gse_campaign_0.10.0"
        or campaign.get("protocol_version") != PROTOCOL_VERSION
        or campaign.get("campaign_id") != PROTOCOL_VERSION
        or campaign.get("campaign_seed") != 200
        or campaign.get("status") != "ready"
    ):
        raise RuntimeContractError("τ³ v0.10 Campaign identity is invalid.")
    if campaign.get("benchmark_adapter_reference") != "v09_tau3" or campaign.get(
        "proposal_semantics"
    ) != "v05_multi_rollout_reflection":
        raise RuntimeContractError("τ³ v0.10 composition identity drifted.")

    frozen = _v09_manifest()
    shared_fields = (
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
    )
    if any(campaign.get(field) != frozen.get(field) for field in shared_fields):
        raise RuntimeContractError("Frozen v0.9 τ³ benchmark semantics drifted.")
    method = campaign.get("skill_evolution", {})
    if method != {
        "proposal_operator": "rule_id_governed_reflection_editor",
        "proposal_semantics": "v05_multi_rollout_reflection",
        "maximum_success_reflector_calls_per_step": 1,
        "maximum_failure_reflector_calls_per_step": 1,
        "maximum_raw_patches_per_reflector": 4,
        "maximum_editor_calls_per_step": 1,
        "diagnosis_calls_per_train_rollout": 0,
        "allowed_operations": ["add", "replace", "delete"],
        "stable_parent_rule_id": True,
        "maximum_skill_rules": 18,
        "maximum_skill_words": 900,
        "task_specific_recipe": "forbidden",
        "selection_feedback_to_learner": "forbidden",
        "test_feedback_to_learner": "forbidden",
    }:
        raise RuntimeContractError("v0.5 Skill Evolution semantics drifted.")
    if campaign.get("budget") != {
        "train_trajectories": 153,
        "initial_selection_trajectories": 54,
        "maximum_candidate_selection_trajectories": 162,
        "maximum_total_trajectories": 369,
        "maximum_candidates": 3,
        "maximum_learner_calls": 9,
        "unused_budget_reallocation": "forbidden",
    }:
        raise RuntimeContractError("τ³ v0.10 budget drifted.")


def _v09_benchmark_campaign(campaign: dict[str, Any]) -> dict[str, Any]:
    """Project v10 onto the frozen v09 backend validator."""

    validate_campaign_contract(campaign)
    projected = _v09_manifest()
    projected["status"] = campaign["status"]
    projected["initial_parent"] = copy.deepcopy(campaign["initial_parent"])
    return projected


def _v05_controller_campaign(campaign: dict[str, Any]) -> dict[str, Any]:
    """Project v10 onto the unchanged v05/v03 three-Step controller."""

    validate_campaign_contract(campaign)
    projected = _v05_manifest()
    projected["campaign_seed"] = campaign["campaign_seed"]
    projected["status"] = campaign["status"]
    projected["initial_parent"] = copy.deepcopy(campaign["initial_parent"])
    return v05._v03_campaign(projected)


def register_tau3_step(
    campaign: dict[str, Any],
    batch_map: dict[str, Any],
    *,
    step: int,
    parent: dict[str, Any],
    parent_checkpoint: dict[str, Any],
    epoch: int = 1,
    batch_step: int | None = None,
    scheduled_steps: int = 3,
) -> dict[str, Any]:
    """Register a v05 Step directly from τ³ batches without fake templates."""

    validate_campaign_contract(campaign)
    v09.build_campaign_dry_plan(_v09_benchmark_campaign(campaign), batch_map)
    resolved_batch_step = step if batch_step is None else batch_step
    if (
        not isinstance(step, int)
        or isinstance(step, bool)
        or not 1 <= step <= scheduled_steps
        or epoch != 1
        or not isinstance(resolved_batch_step, int)
        or isinstance(resolved_batch_step, bool)
        or not 1 <= resolved_batch_step <= 3
    ):
        raise RuntimeContractError("τ³ v0.10 Step schedule is invalid.")
    current_parent = v03_controller._require_parent(parent)
    initial_parent = v03_controller._require_parent(
        _v05_controller_campaign(campaign)["initial_parent"]
    )
    if step == 1 and current_parent != initial_parent:
        raise RuntimeContractError("Step 1 must start from the frozen S0 Parent.")
    checkpoint = v03_controller._require_checkpoint(
        parent_checkpoint, current_parent
    )
    task_maps = v09._task_maps(_v09_benchmark_campaign(campaign), batch_map)
    train_lookup = {ref: task_id for task_id, ref in task_maps["train"].items()}
    frozen_batch = batch_map["batches"][resolved_batch_step - 1]
    registered = {
        "schema_version": v03_controller.STEP_SCHEMA_VERSION,
        "protocol_version": v03_controller.PROTOCOL_VERSION,
        "campaign_id": v03_controller.PROTOCOL_VERSION,
        "epoch": epoch,
        "step": step,
        "status": "STEP_REGISTERED",
        "batch": {
            "batch_id": f"batch_{resolved_batch_step:03d}",
            "batch_map": campaign["train"]["batch_map"],
            "task_ids": [train_lookup[ref] for ref in frozen_batch["task_ids"]],
        },
        "parent": current_parent,
        "proposal_operator": "governed_reflection_editor",
        "candidate_id": f"epoch_{epoch:03d}_step_{step:03d}_candidate",
        "parent_checkpoint": checkpoint,
        "proposal_budget": copy.deepcopy(v03_controller.PROPOSAL_BUDGET),
        "data_isolation": copy.deepcopy(v03_controller.DATA_ISOLATION),
    }
    if batch_step is not None:
        registered["batch_step"] = resolved_batch_step
        registered["scheduled_steps"] = scheduled_steps
    return registered


def proposal_operator() -> RuleIdGovernedReflectionEditorProposalOperator:
    return RuleIdGovernedReflectionEditorProposalOperator()


def derive_rollout_seeds(
    campaign_seed: int, execution_seed_offset: int, rollouts_per_task: int = 3
) -> tuple[int, ...]:
    return v09.derive_rollout_seeds(
        campaign_seed, execution_seed_offset, rollouts_per_task
    )


def matched_selection_plan(
    task_ids: list[str], campaign_seed: int, execution_seed_offset: int
) -> dict[str, list[dict[str, Any]]]:
    return v09.matched_selection_plan(
        task_ids, campaign_seed, execution_seed_offset
    )


def build_campaign_dry_plan(
    campaign: dict[str, Any], batch_map: dict[str, Any]
) -> dict[str, Any]:
    validate_campaign_contract(campaign)
    plan = v09.build_campaign_dry_plan(
        _v09_benchmark_campaign(campaign), batch_map
    )
    plan["schema_version"] = "autonomous_gse_dry_plan_0.10.0"
    plan["campaign_id"] = campaign["campaign_id"]
    for step in plan["steps"]:
        step.pop("maximum_diagnosis_calls")
        step.update(
            {
                "maximum_success_reflector_calls": 1,
                "maximum_failure_reflector_calls": 1,
                "maximum_editor_calls": 1,
                "maximum_learner_calls": 3,
                "diagnosis_calls": 0,
            }
        )
    plan["computed_budget"]["maximum_learner_calls"] = 9
    if plan["computed_budget"] != {
        key: campaign["budget"][key]
        for key in (
            "train_trajectories",
            "initial_selection_trajectories",
            "maximum_candidate_selection_trajectories",
            "maximum_total_trajectories",
            "maximum_learner_calls",
        )
    }:
        raise RuntimeContractError("τ³ v0.10 dry-plan budget mismatch.")
    return plan


def _mean(rows: Sequence[dict[str, Any]], metric: str) -> float:
    return sum(float(row[metric]) for row in rows) / len(rows)


def aggregate_selection_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """rollout mean within task, then Domain and Overall task means."""

    by_task: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        domain = row.get("domain")
        task_id = str(row.get("task_id"))
        rollout_index = row.get("rollout_index")
        if domain not in {"airline", "retail"} or not isinstance(
            rollout_index, int
        ):
            raise RuntimeContractError("Selection rollout lineage is invalid.")
        by_task[(domain, task_id)].append(row)
    task_means = []
    for (domain, task_id), task_rows in sorted(by_task.items()):
        task_rows.sort(key=lambda row: row["rollout_index"])
        if [row["rollout_index"] for row in task_rows] != [1, 2, 3]:
            raise RuntimeContractError("Selection task needs exactly 3 rollouts.")
        task_means.append(
            {
                "domain": domain,
                "task_id": task_id,
                "rollout_count": 3,
                "task_success": _mean(task_rows, "task_success"),
                "compliance": _mean(task_rows, "compliant"),
                "cup": sum(
                    float(row["task_success"] and row["compliant"])
                    for row in task_rows
                )
                / 3,
            }
        )
    if len(task_means) != 18:
        raise RuntimeContractError("Selection requires exactly 18 tasks.")

    rollout_metrics = v09.aggregate_metrics(rows)
    for group, group_rows in (
        ("airline", [row for row in task_means if row["domain"] == "airline"]),
        ("retail", [row for row in task_means if row["domain"] == "retail"]),
        ("overall", task_means),
    ):
        if not group_rows:
            raise RuntimeContractError("Selection Domain is empty.")
        rollout_metrics[group].update(
            {
                "task_count": len(group_rows),
                "task_success": _mean(group_rows, "task_success"),
                "compliance": _mean(group_rows, "compliance"),
                "cup": _mean(group_rows, "cup"),
            }
        )
    return {
        "aggregation_order": [
            "rollout_mean_within_task",
            "task_mean_within_domain",
            "task_mean_overall",
        ],
        "task_means": task_means,
        "metrics": rollout_metrics,
    }


class Tau3CampaignRolloutBackend(v09.Tau3CampaignRolloutBackend):
    """The v09 backend configured through a validated v10 projection."""

    def __init__(
        self,
        campaign: dict[str, Any],
        batch_map: dict[str, Any],
        *,
        judge_caller: JudgeCaller = default_judge_caller,
        artifact_root: Path | None = None,
    ) -> None:
        validate_campaign_contract(campaign)
        resolved_artifact_root = _artifact_root(campaign, artifact_root)
        super().__init__(
            _v09_benchmark_campaign(campaign),
            batch_map,
            judge_caller=judge_caller,
            artifact_root=resolved_artifact_root,
        )


class FormalTau3V05BenchmarkRuntimeAdapter(v09.FormalTau3BenchmarkRuntimeAdapter):
    """Keep v09 benchmark behavior and replace only its proposal method layer."""

    mode = FORMAL_MODE

    def __init__(
        self,
        campaign: dict[str, Any],
        batch_map: dict[str, Any],
        *,
        rollout_backend: Callable[[RolloutRequest], Sequence[Path]],
        learner: Any | None,
        artifact_root: Path | None = None,
    ) -> None:
        validate_campaign_contract(campaign)
        resolved_artifact_root = _artifact_root(campaign, artifact_root)
        super().__init__(
            _v09_benchmark_campaign(campaign),
            batch_map,
            rollout_backend=rollout_backend,
            learner=learner,
            artifact_root=resolved_artifact_root,
        )
        self._campaign = copy.deepcopy(campaign)

    def run_train(self, step: dict[str, Any]) -> tuple[dict[str, Any], ...]:
        experiences = list(super().run_train(step))
        for experience in experiences:
            source = self._current_sources[experience["source_id"]]
            experience.update(
                {
                    "domain": source["domain"],
                    "task_id": source["task_id"],
                    "rollout_id": f"rollout_{source['rollout_index']:02d}",
                    "task_feedback": copy.deepcopy(experience["task_evaluation"]),
                    "reflector": (
                        "success"
                        if experience["state"]
                        in {"compliant_success", "violating_success"}
                        else "failure"
                    ),
                }
            )
            source["rollout_id"] = f"rollout_{source['rollout_index']:02d}"
            source["reflector"] = experience["reflector"]
        root = self._artifact_root / "steps" / f"step_{step['step']:03d}"
        v09._write_json(
            root / "governed_experience.json",
            {
                "schema_version": "governed_experience_0.10.0",
                "experience_count": len(experiences),
                "training_tasks": len(step["batch"]["task_ids"]),
                "training_trajectories": len(experiences),
                "experiences": experiences,
                "sources": list(self._current_sources.values()),
            },
        )
        self._side_effects["filesystem_writes"] += 1
        return tuple(experiences)

    def _checkpoint(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        checkpoint = super()._checkpoint(*args, **kwargs)
        payload = self._checkpoints[checkpoint["path"]]
        aggregation = aggregate_selection_metrics(payload["rows"])
        payload["aggregation"] = aggregation
        payload["metrics"] = aggregation["metrics"]
        v09._write_json(v09._resolved_path(checkpoint["path"]), payload)
        self._side_effects["filesystem_writes"] += 1
        return checkpoint

    def learner_call(
        self,
        step: dict[str, Any],
        request: ReflectorRequest | EditorRequest,
        model: str,
        system_prompt: str,
        user_prompt: str,
    ) -> tuple[str, str, dict[str, Any] | None]:
        if self._learner is None:
            raise RuntimeContractError("Learner is unavailable for a formal run.")
        # v05's parser retains its historical internal title. Do not expose the
        # SuiteCRM-only label to the τ³ learner prompt.
        system_prompt = system_prompt.replace(
            v09.V07_METHOD_SKILL_TITLE, v09.CANONICAL_SKILL_TITLE
        )
        user_prompt = user_prompt.replace(
            v09.V07_METHOD_SKILL_TITLE, v09.CANONICAL_SKILL_TITLE
        )
        response = self._learner.call(request, model, system_prompt, user_prompt)
        role = (
            f"{request.reflector}_reflector"
            if isinstance(request, ReflectorRequest)
            else "editor"
        )
        root = self._artifact_root / "steps" / f"step_{step['step']:03d}"
        if self._learner.last_call is not None:
            v09._write_json(root / f"{role}_call.json", self._learner.last_call)
        if self._learner.last_response is not None:
            (root / f"{role}_response.txt").write_text(
                self._learner.last_response + "\n", encoding="utf-8"
            )
        self._side_effects["api_calls"] += 1
        self._side_effects["filesystem_writes"] += 2
        return response

    def record_proposal(
        self,
        step: dict[str, Any],
        decision: Any,
        candidate: dict[str, Any] | None,
    ) -> None:
        patch_provenance = {
            patch["patch_id"]: [
                copy.deepcopy(self._current_sources[source_id])
                for source_id in patch.get("source_ids", [])
                if source_id in self._current_sources
            ]
            for patch in decision.raw_patches
        }
        payload = {
            "schema_version": "autonomous_gse_proposal_record_0.10.0",
            "step": step["step"],
            "candidate": copy.deepcopy(candidate),
            "proposal_status": decision.proposal_status,
            "proposal_reason": copy.deepcopy(decision.proposal_reason),
            "reflector_calls": decision.reflector_calls,
            "editor_calls": decision.editor_calls,
            "diagnosis_calls": 0,
            "raw_patches": copy.deepcopy(decision.raw_patches),
            "canonical_edits": copy.deepcopy(decision.canonical_edits),
            "applied_edits": copy.deepcopy(decision.applied_edits),
            "excluded_edits": copy.deepcopy(decision.excluded_edits),
            "source_provenance": copy.deepcopy(self._current_sources),
            "patch_provenance": patch_provenance,
            "provenance_status": decision.provenance_status,
            "provenance_audit": copy.deepcopy(decision.provenance_audit),
        }
        path = (
            self._artifact_root
            / "steps"
            / f"step_{step['step']:03d}"
            / "proposal.json"
        )
        v09._write_json(path, payload)
        self._side_effects["filesystem_writes"] += 1


def run_v10_campaign(
    campaign: dict[str, Any],
    batch_map: dict[str, Any],
    adapter: FormalTau3V05BenchmarkRuntimeAdapter,
    *,
    scheduled_steps: int = 3,
    resume_state: dict[str, Any] | None = None,
    on_step_completed: Callable[[dict[str, Any]], None] | None = None,
    proposal_driver: Callable[[Any, dict[str, Any], Any], Any] | None = None,
) -> dict[str, Any]:
    validate_campaign_contract(campaign)

    def register_composed_step(
        _controller_campaign: dict[str, Any],
        _controller_batch_map: dict[str, Any],
        **kwargs: Any,
    ) -> dict[str, Any]:
        del _controller_campaign, _controller_batch_map
        return register_tau3_step(campaign, batch_map, **kwargs)

    report = v05.run_v05_campaign(
        _v05_controller_campaign(campaign),
        batch_map,
        adapter,
        scheduled_steps=scheduled_steps,
        step_registrar=register_composed_step,
        resume_state=resume_state,
        on_step_completed=on_step_completed,
        proposal_driver=proposal_driver,
    )
    report["schema_version"] = "autonomous_gse_formal_report_0.10.0"
    report["protocol_version"] = PROTOCOL_VERSION
    report["campaign_id"] = campaign["campaign_id"]
    report["mode"] = FORMAL_MODE
    for step in report["steps"]:
        step["schema_version"] = "autonomous_gse_step_0.10.0"
        step["protocol_version"] = PROTOCOL_VERSION
        step["campaign_id"] = campaign["campaign_id"]
    usage = report["budget_usage"]
    for field in (
        "train_trajectories",
        "initial_selection_trajectories",
        "candidate_selection_trajectories",
    ):
        usage[field] *= 3
    usage["total_trajectories"] = sum(
        usage[field]
        for field in (
            "train_trajectories",
            "initial_selection_trajectories",
            "candidate_selection_trajectories",
        )
    )
    if usage["total_trajectories"] > campaign["budget"]["maximum_total_trajectories"]:
        raise RuntimeContractError("v0.10 rollout budget was exceeded.")
    report["disabled_phases"] = {"official_test": True}
    report["diagnosis_calls"] = 0
    return report


def _campaign_paths(
    campaign: dict[str, Any], artifact_root: Path | None = None
) -> dict[str, Path]:
    root = _artifact_root(campaign, artifact_root)
    return {
        "checkpoint": root / "checkpoints/s0_empty_skill.json",
        "resume": root / RESUME_STATE_FILENAME,
        "report": root / CAMPAIGN_REPORT_FILENAME,
    }


def run_initial_checkpoint(
    campaign_path: Path,
    *,
    rollout_backend: Callable[[RolloutRequest], Sequence[Path]] | None = None,
    judge_caller: JudgeCaller = default_judge_caller,
    artifact_root: Path | None = None,
) -> dict[str, Any]:
    campaign = _load_json(campaign_path.resolve())
    validate_campaign_contract(campaign)
    batch_map = _load_json(v09._resolved_path(campaign["train"]["batch_map"]))
    paths = _campaign_paths(campaign, artifact_root)
    if paths["checkpoint"].exists():
        raise RuntimeContractError("Initial S0 checkpoint already exists.")
    backend = rollout_backend or Tau3CampaignRolloutBackend(
        campaign,
        batch_map,
        judge_caller=judge_caller,
        artifact_root=artifact_root,
    )
    adapter = FormalTau3V05BenchmarkRuntimeAdapter(
        campaign,
        batch_map,
        rollout_backend=backend,
        learner=None,
        artifact_root=artifact_root,
    )
    checkpoint = adapter.run_fresh_initial_checkpoint()
    return {"status": "S0_CHECKPOINT_CREATED", "checkpoint": checkpoint}


def run_formal_campaign_cli(
    campaign_path: Path,
    *,
    rollout_backend: Callable[[RolloutRequest], Sequence[Path]] | None = None,
    learner: Any | None = None,
    judge_caller: JudgeCaller = default_judge_caller,
    artifact_root: Path | None = None,
) -> dict[str, Any]:
    campaign = _load_json(campaign_path.resolve())
    validate_campaign_contract(campaign)
    batch_map = _load_json(v09._resolved_path(campaign["train"]["batch_map"]))
    paths = _campaign_paths(campaign, artifact_root)
    if not paths["checkpoint"].is_file():
        raise RuntimeContractError("Initial S0 checkpoint is missing.")
    if paths["report"].exists():
        raise RuntimeContractError("Campaign report already exists.")
    if learner is None:
        from dotenv import load_dotenv

        load_dotenv(REPO_ROOT / ".env", override=False)
        learner = v05.SeededLearnerAdapter(_v05_manifest())
    backend = rollout_backend or Tau3CampaignRolloutBackend(
        campaign,
        batch_map,
        judge_caller=judge_caller,
        artifact_root=artifact_root,
    )
    adapter = FormalTau3V05BenchmarkRuntimeAdapter(
        campaign,
        batch_map,
        rollout_backend=backend,
        learner=learner,
        artifact_root=artifact_root,
    )
    resume_state = (
        _load_json(paths["resume"]) if paths["resume"].is_file() else None
    )
    report = run_v10_campaign(
        campaign,
        batch_map,
        adapter,
        resume_state=resume_state,
        on_step_completed=lambda state: v09._write_json(paths["resume"], state),
    )
    v09._write_json(paths["report"], report)
    return {
        "status": "AUTONOMOUS_GSE_V10_CAMPAIGN_COMPLETED",
        "report": v09._artifact(
            "campaign_report", campaign["campaign_id"], paths["report"]
        ),
        "step_outcomes": [step["outcome"] for step in report["steps"]],
        "final_parent": report["final_parent"],
    }


def main(argv: Sequence[str] | None = None) -> int:
    import argparse

    default_campaign = REPO_ROOT / (
        "experiments/campaigns/autonomous_gse_v10/campaign_manifest.json"
    )
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("plan", "initial-checkpoint", "run"):
        subparser = subparsers.add_parser(command)
        subparser.add_argument("--campaign", type=Path, default=default_campaign)
    args = parser.parse_args(argv)
    campaign = _load_json(args.campaign.resolve())
    if args.command == "plan":
        batch_map = _load_json(v09._resolved_path(campaign["train"]["batch_map"]))
        result = build_campaign_dry_plan(campaign, batch_map)
    elif args.command == "initial-checkpoint":
        result = run_initial_checkpoint(args.campaign)
    else:
        result = run_formal_campaign_cli(args.campaign)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

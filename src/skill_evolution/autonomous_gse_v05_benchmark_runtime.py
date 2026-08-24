"""Day 16 v0.5 multi-rollout extension of Autonomous GSE v0.4 semantics."""

from __future__ import annotations

import copy
import json
from collections import defaultdict
from collections.abc import Callable, Sequence
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import src.skill_evolution.autonomous_gse_v03_benchmark_runtime as v03_formal
import src.skill_evolution.autonomous_gse_v03_runtime as v03_runtime
from src.learners.stwebagentbench.generate_skill import call_learner
from src.learners.stwebagentbench.generate_governed_skill_v05 import (
    call_governed_editor as call_v05_editor,
)
from src.learners.stwebagentbench.generate_governed_skill_v05 import (
    call_governed_reflector as call_v05_reflector,
)
from src.skill_evolution.autonomous_gse_v03_benchmark_runtime import RolloutRequest
from src.skill_evolution.autonomous_gse_v03_proposal import (
    EditorRequest,
    ReflectorRequest,
)
from src.skill_evolution.autonomous_gse_v03_runtime import RuntimeContractError
from src.skill_evolution.governed_experience import build_experience
from src.skill_evolution.two_dimensional_gate import classify_state
from src.skill_evolution.autonomous_gse_v05_proposal import (
    RuleIdGovernedReflectionEditorProposalOperator,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
FORMAL_MODE = "formal_stwebagentbench_v05"
CAMPAIGN_REPORT_FILENAME = "campaign_report.json"
METRICS = ("task_success", "compliance", "cup")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _resolve_repo_path(relative_path: str) -> Path:
    path = (REPO_ROOT / relative_path).resolve()
    path.relative_to(REPO_ROOT)
    return path


def _artifact(kind: str, version: str, path: Path) -> dict[str, str]:
    return {
        "kind": kind,
        "version": version,
        "path": path.resolve().relative_to(REPO_ROOT).as_posix(),
    }


def _expand_campaign(campaign: dict[str, Any]) -> dict[str, Any]:
    base_path = campaign.get("base_campaign")
    if base_path is None:
        return copy.deepcopy(campaign)
    base = json.loads(_resolve_repo_path(base_path).read_text(encoding="utf-8"))
    expanded = {**base, **copy.deepcopy(campaign)}
    expanded["benchmark_runtime"] = copy.deepcopy(base["benchmark_runtime"])
    rollout = expanded["benchmark_runtime"]["rollout"]
    rollout["headless"] = expanded.get("headless", rollout["headless"])
    rollout["execution"] = expanded.get("execution", rollout["execution"])
    rollout["parallel_workers"] = expanded.get(
        "parallel_workers", 4 if rollout["execution"] == "parallel" else 1
    )
    return expanded


def _v03_campaign(campaign: dict[str, Any]) -> dict[str, Any]:
    """Project v0.5 onto the unchanged v0.3 controller state machine."""

    projected = copy.deepcopy(campaign)
    projected["schema_version"] = "autonomous_gse_campaign_0.3.0"
    projected["protocol_version"] = "autonomous_gse_v03"
    projected["campaign_id"] = "autonomous_gse_v03"
    projected["benchmark_runtime"]["rollout"] = {
        "headless": False,
        "trials_per_task": 1,
        "execution": "sequential",
        "database_reset_before_every_trial": True,
    }
    projected["budget"] = {
        "train_trajectories": 51,
        "initial_selection_trajectories": 18,
        "maximum_candidate_selection_trajectories": 54,
        "maximum_total_trajectories": 123,
        "maximum_candidates": 3,
        "maximum_learner_calls": 9,
        "unused_budget_reallocation": "forbidden",
    }
    projected["test"] = {
        "authorized": False,
        "data_for_learning": "forbidden",
    }
    return projected


def validate_formal_campaign_contract(
    campaign: dict[str, Any], *, require_ready: bool = False
) -> None:
    campaign = _expand_campaign(campaign)
    if campaign.get("schema_version") != "autonomous_gse_campaign_0.5.0":
        raise RuntimeContractError("Unsupported v0.5 Campaign schema.")
    if campaign.get("protocol_version") != "autonomous_gse_v05":
        raise RuntimeContractError("Unsupported v0.5 Campaign protocol.")
    if campaign.get("campaign_id") != "autonomous_gse_v05":
        raise RuntimeContractError("v0.5 uses one full Campaign, not seed replicas.")
    seed = campaign.get("campaign_seed")
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise RuntimeContractError("campaign_seed must be an integer.")
    if campaign.get("status") not in {"draft", "ready"}:
        raise RuntimeContractError("Campaign status must be draft or ready.")
    if require_ready and campaign["status"] != "ready":
        raise RuntimeContractError("Campaign must be ready before execution.")

    rollout = campaign.get("benchmark_runtime", {}).get("rollout", {})
    if campaign.get("headless") is not True or rollout.get("headless") is not True:
        raise RuntimeContractError("Every v0.5 rollout must be headless.")
    if (
        campaign.get("execution") != "parallel"
        or campaign.get("parallel_workers") != 4
        or rollout.get("execution") != "parallel"
        or rollout.get("parallel_workers") != 4
    ):
        raise RuntimeContractError("v0.5 requires the existing 4-worker path.")
    train_rollouts = campaign.get("train_rollouts_per_task")
    selection_rollouts = campaign.get("selection_rollouts_per_task")
    if not isinstance(train_rollouts, int) or train_rollouts < 1:
        raise RuntimeContractError("train_rollouts_per_task must be positive.")
    if not isinstance(selection_rollouts, int) or selection_rollouts < 1:
        raise RuntimeContractError("selection_rollouts_per_task must be positive.")
    if rollout.get("database_reset_before_every_trial") is not True:
        raise RuntimeContractError("Every rollout must start with a database reset.")
    if campaign.get("post_hoc_training_replay") != {"enabled": False}:
        raise RuntimeContractError("Post-hoc training replay must be disabled.")
    if campaign.get("test") != {
        "authorized": False,
        "data_for_learning": "forbidden",
    }:
        raise RuntimeContractError("Final Test execution must be disabled.")
    if campaign.get("full_experiment_seeds") != 1:
        raise RuntimeContractError("v0.5 must not run three full seed replicas.")
    if campaign.get("rule_addressing") != {
        "mode": "stable_parent_rule_id",
        "legacy_target_clause_fallback": "normalize_markdown_bullet_and_whitespace",
        "ambiguous_legacy_match": "reject_edit",
    }:
        raise RuntimeContractError("v0.5 rule-addressing contract drifted.")

    budget = campaign.get("budget", {})
    expected_budget = {
        "train_trajectories": 51 * train_rollouts,
        "initial_selection_trajectories": 18 * selection_rollouts,
        "maximum_candidate_selection_trajectories": 54 * selection_rollouts,
        "maximum_total_trajectories": (
            51 * train_rollouts + 72 * selection_rollouts
        ),
        "maximum_candidates": 3,
        "maximum_learner_calls": 9,
        "unused_budget_reallocation": "forbidden",
    }
    if budget != expected_budget:
        raise RuntimeContractError("v0.5 rollout budget drifted.")
    v03_formal.validate_formal_campaign_contract(
        _v03_campaign(campaign), require_ready=require_ready
    )


LearnerCaller = Callable[..., tuple[str, str, dict[str, Any] | None]]


def _learner_role(request: Any) -> str:
    """Name v0.5 roles while allowing additive proposal stages to log safely."""

    diagnosis_id = getattr(request, "diagnosis_id", None)
    if isinstance(diagnosis_id, str) and diagnosis_id:
        return f"{diagnosis_id}_diagnosis"
    if isinstance(request, ReflectorRequest):
        return f"{request.reflector}_reflector"
    return "editor"


class SeededLearnerAdapter:
    """Reuse the v0.4 learner prompts and deterministic campaign seed."""

    campaign_validator = staticmethod(validate_formal_campaign_contract)
    campaign_expander = staticmethod(_expand_campaign)

    def __init__(
        self,
        campaign: dict[str, Any],
        *,
        caller: LearnerCaller = call_learner,
    ) -> None:
        campaign = self.campaign_expander(campaign)
        self.campaign_validator(campaign)
        self._model = campaign["proposal"]["learner"]["model"]
        self._parameters = copy.deepcopy(
            campaign["proposal"]["learner"]["parameters"]
        )
        self._seed = campaign["campaign_seed"]
        self._caller = caller
        self.last_call: dict[str, Any] | None = None
        self.last_response: str | None = None

    def call(
        self,
        request: ReflectorRequest | EditorRequest,
        model: str,
        system_prompt: str,
        user_prompt: str,
    ) -> tuple[str, str, dict[str, Any] | None]:
        if model != self._model:
            raise RuntimeContractError("Learner model drifted from the Manifest.")
        sampling_parameters = self._sampling_parameters(request)
        response, resolved_model, usage = self._caller(
            model, system_prompt, user_prompt, **sampling_parameters
        )
        if resolved_model != "gpt-5.6-luna":
            raise RuntimeContractError("Learner resolved model is unexpected.")
        if not isinstance(response, str) or not response.strip():
            raise RuntimeContractError("Learner returned an empty response.")
        role = _learner_role(request)
        self.last_response = response.strip()
        self.last_call = {
            "candidate_id": request.candidate_id,
            "role": role,
            "model": model,
            "parameters": {**self._parameters, **sampling_parameters},
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "usage": usage,
        }
        return self.last_response, resolved_model, usage

    def _sampling_parameters(
        self, request: ReflectorRequest | EditorRequest
    ) -> dict[str, Any]:
        del request
        return {"seed": self._seed}


class MultiRolloutRunnerBackend:
    """Execute configured task × rollout units through the v0.4 workers."""

    campaign_validator = staticmethod(validate_formal_campaign_contract)
    campaign_expander = staticmethod(_expand_campaign)
    record_benchmark_agent_model = False
    sampling_temperature: float | None = None
    sampling_max_tokens: int | None = None
    sampling_retry_max_tokens: int | None = None
    sampling_thinking: bool | None = None
    sampling_retry_on_token_exhaustion: bool | None = None

    def __init__(self, campaign: dict[str, Any]) -> None:
        campaign = self.campaign_expander(campaign)
        self.campaign_validator(campaign, require_ready=True)
        source = json.loads(
            _resolve_repo_path(campaign["train"]["source_manifest"]).read_text(
                encoding="utf-8"
            )
        )
        self._tasks = {
            split: {
                task_id: {
                    "task_id": task_id,
                    "intent_template_id": template["intent_template_id"],
                    "subset": template["subset"],
                }
                for template in source["splits"][split]["templates"]
                for task_id in template["task_ids"]
            }
            for split in ("train", "selection")
        }
        self._campaign_id = campaign["campaign_id"]
        self._benchmark_commit = source["benchmark"]["commit"]
        self._model = campaign["benchmark_runtime"]["agent_model"]
        self._headless = True
        self._parallel_workers = 4
        self._campaign_seed = campaign["campaign_seed"]
        self._rollouts = {
            "train": campaign["train_rollouts_per_task"],
            "selection": campaign["selection_rollouts_per_task"],
        }
        self.last_parallel_summary: dict[str, Any] | None = None

    def __call__(self, request: RolloutRequest) -> Sequence[Path]:
        tasks = self._tasks.get(request.split)
        if tasks is None:
            raise RuntimeContractError("v0.5 runs only Train and Selection.")
        missing = [task_id for task_id in request.task_ids if task_id not in tasks]
        if missing:
            raise RuntimeContractError(f"Unknown {request.split} Task IDs: {missing}")
        skill = v03_formal.RunnerRolloutBackend._load_skill(request.artifact)
        manifest = {
            "manifest_id": self._campaign_id,
            "benchmark": {"commit": self._benchmark_commit},
            "_output_split": request.split,
        }
        if request.execution_phase is not None:
            manifest["_output_phase"] = request.execution_phase
        runner = (
            v03_formal._run_train_task
            if request.split == "train"
            else v03_formal._run_selection_task
        )
        payloads = []
        for task_id in request.task_ids:
            for rollout_id in range(1, self._rollouts[request.split] + 1):
                args = {
                    "formal": True,
                    "headless": self._headless,
                    "model": self._model,
                    "method": request.method,
                    "campaign_seed": self._campaign_seed,
                    "seed": self._execution_seed(request, task_id, rollout_id),
                    "rollout_id": rollout_id,
                }
                if self.record_benchmark_agent_model:
                    args["benchmark_agent_model"] = self._model
                if self.sampling_temperature is not None:
                    args["temperature"] = self.sampling_temperature
                if self.sampling_max_tokens is not None:
                    args["max_tokens"] = self.sampling_max_tokens
                if self.sampling_retry_max_tokens is not None:
                    args["retry_max_tokens"] = self.sampling_retry_max_tokens
                if self.sampling_thinking is not None:
                    args["thinking"] = self.sampling_thinking
                if self.sampling_retry_on_token_exhaustion is not None:
                    args["retry_on_token_exhaustion"] = (
                        self.sampling_retry_on_token_exhaustion
                    )
                payloads.append(
                    {
                        "source_split": request.split,
                        "args": args,
                        "manifest": manifest,
                        "method": request.method,
                        "skill": skill,
                        "task": tasks[task_id],
                    }
                )

        from src.adapters.stwebagentbench.parallel_rollout import (
            run_subprocess_rollouts,
        )

        paths, summary = run_subprocess_rollouts(
            payloads, parallel_workers=self._parallel_workers
        )
        self.last_parallel_summary = summary
        log_root = (
            REPO_ROOT
            / "artifacts"
            / self._campaign_id
            / "formal/parallel_runtime"
            / request.split
        )
        if request.execution_phase is not None:
            log_root /= request.execution_phase
        log_path = log_root / (
            f"{request.method}_{request.task_ids[0]}_{request.task_ids[-1]}.json"
        )
        _write_json(log_path, summary)
        return paths

    def _execution_seed(
        self, request: RolloutRequest, task_id: int, rollout_id: int
    ) -> int:
        del task_id
        return (
            self._campaign_seed
            + request.execution_seed_offset
            + rollout_id
            - 1
        )


def _rollout_units(
    task_ids: Sequence[int], rollouts_per_task: int
) -> list[tuple[int, int]]:
    return [
        (task_id, rollout_id)
        for task_id in task_ids
        for rollout_id in range(1, rollouts_per_task + 1)
    ]


def _mean(rows: Sequence[dict[str, Any]], metric: str) -> float:
    return sum(float(row[metric]) for row in rows) / len(rows)


def aggregate_selection_metrics(
    rows: Sequence[dict[str, Any]],
    task_templates: dict[int, int],
    *,
    rollouts_per_task: int,
) -> dict[str, Any]:
    """rollout → task mean → intent-template mean → equal macro mean."""

    by_task: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        task_id = row.get("task_id")
        rollout_id = row.get("rollout_id")
        if task_id not in task_templates or not isinstance(rollout_id, int):
            raise RuntimeContractError("Selection rollout lineage is invalid.")
        by_task[task_id].append(row)
    if set(by_task) != set(task_templates):
        raise RuntimeContractError("Selection task set is incomplete.")

    task_means = []
    for task_id in sorted(by_task):
        task_rows = sorted(by_task[task_id], key=lambda row: row["rollout_id"])
        if [row["rollout_id"] for row in task_rows] != list(
            range(1, rollouts_per_task + 1)
        ):
            raise RuntimeContractError("Selection rollout set is incomplete.")
        task_means.append(
            {
                "task_id": task_id,
                "intent_template_id": task_templates[task_id],
                **{metric: _mean(task_rows, metric) for metric in METRICS},
            }
        )

    by_template: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in task_means:
        by_template[row["intent_template_id"]].append(row)
    template_means = [
        {
            "intent_template_id": template_id,
            "task_count": len(template_rows),
            **{metric: _mean(template_rows, metric) for metric in METRICS},
        }
        for template_id, template_rows in sorted(by_template.items())
    ]
    final = {metric: _mean(template_means, metric) for metric in METRICS}
    return {
        "rollout_results": copy.deepcopy(list(rows)),
        "task_means": task_means,
        "intent_template_means": template_means,
        "final_macro_average": final,
    }


def analyze_hierarchical_selection(
    parent: dict[str, Any], candidate: dict[str, Any]
) -> dict[str, Any]:
    reference = parent["aggregation"]["final_macro_average"]
    proposed = candidate["aggregation"]["final_macro_average"]
    deltas = {metric: proposed[metric] - reference[metric] for metric in METRICS}
    regressions = [metric for metric in METRICS if deltas[metric] < 0]
    improvements = [metric for metric in METRICS if deltas[metric] > 0]
    if regressions:
        gate = {
            "eligible": False,
            "decision": "reject",
            "reasons": [f"aggregate_{metric}_regression" for metric in regressions],
        }
    elif improvements:
        gate = {
            "eligible": True,
            "decision": "continue_evolution",
            "reasons": ["aggregate_pareto_progress"],
            "improved_metrics": improvements,
        }
    else:
        gate = {
            "eligible": False,
            "decision": "reject",
            "reasons": ["no_aggregate_progress"],
        }
    return {
        "aggregation_order": [
            "rollout_mean_within_task",
            "task_mean_within_intent_template",
            "equal_weight_intent_template_macro_average",
        ],
        "aggregate": {
            "reference": reference,
            "candidate": proposed,
            "deltas": deltas,
        },
        "evolution_gate": gate,
    }


class FormalBenchmarkRuntimeAdapter(v03_formal.FormalBenchmarkRuntimeAdapter):
    """Keep v0.4 Reflect/Aggregate/Gate semantics with v0.5 evidence counts."""

    mode = FORMAL_MODE
    campaign_validator = staticmethod(validate_formal_campaign_contract)
    campaign_expander = staticmethod(_expand_campaign)
    controller_campaign = staticmethod(_v03_campaign)

    def __init__(
        self,
        campaign: dict[str, Any],
        *,
        rollout_backend: Callable[[RolloutRequest], Sequence[Path]],
        learner: SeededLearnerAdapter | None,
    ) -> None:
        campaign = self.campaign_expander(campaign)
        self.campaign_validator(campaign, require_ready=True)
        super().__init__(
            self.controller_campaign(campaign),
            rollout_backend=rollout_backend,
            learner=None,
        )
        self._campaign = copy.deepcopy(campaign)
        self._learner = learner
        self._current_sources: dict[str, dict[str, Any]] = {}
        source = json.loads(
            _resolve_repo_path(campaign["train"]["source_manifest"]).read_text(
                encoding="utf-8"
            )
        )
        self._selection_templates = {
            task_id: template["intent_template_id"]
            for template in source["splits"]["selection"]["templates"]
            for task_id in template["task_ids"]
        }
        if len(set(self._selection_templates.values())) != 6:
            raise RuntimeContractError("Frozen Selection must contain 6 templates.")

    def _rollout_count(self, split: str) -> int:
        if split == "train":
            return self._campaign["train_rollouts_per_task"]
        if split == "selection":
            return self._campaign["selection_rollouts_per_task"]
        raise RuntimeContractError("v0.5 runs only Train and Selection.")

    def _run(
        self, split: str, artifact: dict[str, Any], task_ids: Sequence[int]
    ) -> tuple[Path, ...]:
        paths = tuple(
            self._rollout(
                self._prepare_rollout_request(
                    RolloutRequest(
                        split=split,
                        method=self._method(artifact),
                        artifact=copy.deepcopy(artifact),
                        task_ids=tuple(task_ids),
                    )
                )
            )
        )
        expected = len(task_ids) * self._rollout_count(split)
        if len(paths) != expected:
            raise RuntimeContractError("Rollout backend returned wrong count.")
        self._side_effects["browser_calls"] += expected
        self._side_effects["database_calls"] += expected
        self._side_effects["filesystem_writes"] += expected
        return paths

    def _prepare_rollout_request(self, request: RolloutRequest) -> RolloutRequest:
        return request

    @staticmethod
    def _load_trajectory(
        path: Path,
        task_id: int,
        rollout_id: int,
        split: str,
        artifact: dict[str, Any],
    ) -> dict[str, Any]:
        if not path.is_file():
            raise RuntimeContractError(f"Missing formal trajectory: {path}")
        trajectory = json.loads(path.read_text(encoding="utf-8"))
        run = trajectory.get("run", {})
        if (
            trajectory.get("schema_version") != "stweb_raw_0.1.0"
            or trajectory.get("task", {}).get("task_id") != task_id
            or run.get("status") != "completed"
            or run.get("run_kind") != "formal"
            or run.get("split") != split
            or run.get("skill_version") != artifact["version"]
            or run.get("rollout_id", run.get("trial")) != rollout_id
            or not isinstance(run.get("trajectory_id", run.get("run_id")), str)
        ):
            raise RuntimeContractError(f"Formal trajectory lineage mismatch: {path}")
        outcome = trajectory.get("outcome", {})
        if not isinstance(outcome.get("task_success"), bool) or not isinstance(
            outcome.get("violated_policy_count"), int
        ):
            raise RuntimeContractError(f"Formal trajectory verdict is invalid: {path}")
        return trajectory

    def _checkpoint(
        self, artifact: dict[str, Any], task_ids: Sequence[int]
    ) -> dict[str, Any]:
        paths = self._run("selection", artifact, task_ids)
        rows = []
        sources = []
        units = _rollout_units(
            task_ids, self._campaign["selection_rollouts_per_task"]
        )
        for (task_id, rollout_id), path in zip(units, paths, strict=True):
            trajectory = self._load_trajectory(
                path, task_id, rollout_id, "selection", artifact
            )
            outcome = trajectory["outcome"]
            compliant = outcome["violated_policy_count"] == 0
            trajectory_id = trajectory["run"].get(
                "trajectory_id", trajectory["run"]["run_id"]
            )
            rows.append(
                {
                    "task_id": task_id,
                    "rollout_id": rollout_id,
                    "trajectory_id": trajectory_id,
                    "intent_template_id": self._selection_templates[task_id],
                    "task_success": float(outcome["task_success"]),
                    "compliance": float(compliant),
                    "cup": float(outcome["task_success"] and compliant),
                    "state": classify_state(
                        outcome["task_success"], compliant
                    ).value,
                }
            )
            sources.append(
                {
                    "task_id": task_id,
                    "rollout_id": rollout_id,
                    "trajectory_id": trajectory_id,
                    "path": path.relative_to(REPO_ROOT).as_posix(),
                    "execution_seed": trajectory["run"].get("execution_seed"),
                    "worker_id": trajectory["run"].get("worker_id"),
                }
            )
        aggregation = aggregate_selection_metrics(
            rows,
            self._selection_templates,
            rollouts_per_task=self._campaign["selection_rollouts_per_task"],
        )
        payload = {
            "schema_version": "autonomous_gse_selection_checkpoint_0.5.0",
            "campaign_id": self._campaign["campaign_id"],
            "parent": copy.deepcopy(artifact),
            "task_count": len(task_ids),
            "trajectory_count": len(rows),
            "task_ids": list(task_ids),
            "rows": rows,
            "sources": sources,
            "aggregation": aggregation,
        }
        path = (
            REPO_ROOT
            / "artifacts"
            / self._campaign["campaign_id"]
            / "formal/checkpoints"
            / f"{self._method(artifact)}.json"
        )
        _write_json(path, payload)
        self._side_effects["filesystem_writes"] += 1
        checkpoint = _artifact("selection_checkpoint", artifact["version"], path)
        self._checkpoints[checkpoint["path"]] = payload
        return checkpoint

    def restore_checkpoint(
        self, checkpoint: dict[str, Any], parent: dict[str, Any]
    ) -> None:
        """Reload a frozen Selection checkpoint into memory for a resumed run.

        This is read-only fault recovery: the checkpoint was already produced by
        a completed Step, so Selection is never re-run. The stored Parent inside
        the checkpoint may be a ``candidate_skill`` (its version before promotion)
        while the resumed controller Parent is the promoted ``accepted_skill``;
        lineage is therefore matched on version and path, not on ``kind``.
        """

        if checkpoint.get("kind") != "selection_checkpoint":
            raise RuntimeContractError(
                "Resume checkpoint must be a selection_checkpoint."
            )
        if checkpoint.get("version") != parent.get("version"):
            raise RuntimeContractError(
                "Resume checkpoint version must match the Parent."
            )
        path = _resolve_repo_path(checkpoint["path"])
        if not path.is_file():
            raise RuntimeContractError(f"Resume checkpoint is missing: {path}")
        payload = json.loads(path.read_text(encoding="utf-8"))
        rollouts = self._campaign["selection_rollouts_per_task"]
        stored_parent = payload.get("parent", {})
        if (
            payload.get("schema_version")
            != "autonomous_gse_selection_checkpoint_0.5.0"
            or payload.get("campaign_id") != self._campaign["campaign_id"]
            or payload.get("task_count") != 18
            or payload.get("trajectory_count") != 18 * rollouts
            or not isinstance(payload.get("sources"), list)
            or not isinstance(payload.get("rows"), list)
            or len(payload["sources"]) != 18 * rollouts
            or len(payload["rows"]) != 18 * rollouts
        ):
            raise RuntimeContractError("Resume checkpoint contract is invalid.")
        if (
            stored_parent.get("version") != parent.get("version")
            or stored_parent.get("path") != parent.get("path")
        ):
            raise RuntimeContractError(
                "Resume checkpoint lineage does not match the Parent."
            )
        self._checkpoints[checkpoint["path"]] = payload
        self._trace.append(
            {
                "operation": "restore_selection_checkpoint",
                "version": checkpoint["version"],
                "path": checkpoint["path"],
            }
        )

    def create_initial_checkpoint(
        self, parent: dict[str, Any], task_count: int
    ) -> dict[str, Any]:
        if parent != self._campaign["initial_parent"] or task_count != 18:
            raise RuntimeContractError("Initial checkpoint contract is invalid.")
        path = (
            REPO_ROOT
            / "artifacts"
            / self._campaign["campaign_id"]
            / "formal/checkpoints/s0_empty_skill.json"
        )
        if not path.is_file():
            raise RuntimeContractError("Initial S0 checkpoint is missing.")
        payload = json.loads(path.read_text(encoding="utf-8"))
        if (
            payload.get("schema_version")
            != "autonomous_gse_selection_checkpoint_0.5.0"
            or payload.get("task_count") != 18
            or payload.get("trajectory_count")
            != 18 * self._campaign["selection_rollouts_per_task"]
        ):
            raise RuntimeContractError("Initial S0 checkpoint contract is invalid.")
        checkpoint = _artifact("selection_checkpoint", "S0", path)
        self._checkpoints[checkpoint["path"]] = payload
        self._trace.append({"operation": "load_initial_checkpoint"})
        return checkpoint

    def run_train(self, step: dict[str, Any]) -> tuple[dict[str, Any], ...]:
        task_ids = step["batch"]["task_ids"]
        paths = self._run("train", step["parent"], task_ids)
        units = _rollout_units(task_ids, self._campaign["train_rollouts_per_task"])
        experiences = []
        sources = []
        state_counts = {state: 0 for state in v03_formal.OUTCOME_STATES}
        for (task_id, rollout_id), path in zip(units, paths, strict=True):
            trajectory = self._load_trajectory(
                path, task_id, rollout_id, "train", step["parent"]
            )
            trajectory_id = trajectory["run"].get(
                "trajectory_id", trajectory["run"]["run_id"]
            )
            source_id = (
                f"step_{step['step']:03d}_task_{task_id:03d}_"
                f"rollout_{rollout_id:02d}"
            )
            experience = build_experience(trajectory, source_id)
            reflector = (
                "success"
                if experience["state"] in {"compliant_success", "violating_success"}
                else "failure"
            )
            experience.update(
                {
                    "task_id": task_id,
                    "rollout_id": rollout_id,
                    "trajectory_id": trajectory_id,
                    "reflector": reflector,
                }
            )
            source = {
                "source_id": source_id,
                "task_id": task_id,
                "rollout_id": rollout_id,
                "trajectory_id": trajectory_id,
                "state": experience["state"],
                "reflector": reflector,
                "path": path.relative_to(REPO_ROOT).as_posix(),
            }
            experiences.append(experience)
            sources.append(source)
            state_counts[experience["state"]] += 1
        self._current_sources = {source["source_id"]: source for source in sources}
        train_payload = {
            "step": step["step"],
            "batch_id": step["batch"]["batch_id"],
            "parent": copy.deepcopy(step["parent"]),
            "training_tasks": len(task_ids),
            "training_trajectories": len(experiences),
            "task_ids": list(task_ids),
            "sources": copy.deepcopy(sources),
        }
        experience_payload = {
            "schema_version": "governed_experience_0.5.0",
            "experience_count": len(experiences),
            "training_tasks": len(task_ids),
            "training_trajectories": len(experiences),
            "state_counts": state_counts,
            "sources": sources,
            "experiences": experiences,
            "lineage": {
                "batch_id": step["batch"]["batch_id"],
                "parent_version": step["parent"]["version"],
                "task_ids": list(task_ids),
                "rollouts_per_task": self._campaign["train_rollouts_per_task"],
            },
        }
        root = (
            REPO_ROOT
            / "artifacts"
            / self._campaign["campaign_id"]
            / "formal/steps"
            / f"step_{step['step']:03d}"
        )
        _write_json(root / "train_set.json", train_payload)
        _write_json(root / "governed_experience.json", experience_payload)
        self._side_effects["filesystem_writes"] += 2
        self._trace.append({"operation": "run_train", "step": step["step"]})
        return tuple(experiences)

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
        response = self._learner.call(request, model, system_prompt, user_prompt)
        role = _learner_role(request)
        root = (
            REPO_ROOT
            / "artifacts"
            / self._campaign["campaign_id"]
            / "formal/steps"
            / f"step_{step['step']:03d}"
        )
        assert self._learner.last_call is not None
        assert self._learner.last_response is not None
        _write_json(root / f"{role}_call.json", self._learner.last_call)
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
            "schema_version": "autonomous_gse_proposal_record_0.5.0",
            "step": step["step"],
            "candidate": copy.deepcopy(candidate),
            "proposal_status": decision.proposal_status,
            "proposal_reason": copy.deepcopy(decision.proposal_reason),
            "reflector_calls": decision.reflector_calls,
            "editor_calls": decision.editor_calls,
            "raw_patches": copy.deepcopy(decision.raw_patches),
            "canonical_edits": copy.deepcopy(decision.canonical_edits),
            "applied_edits": copy.deepcopy(decision.applied_edits),
            "excluded_edits": copy.deepcopy(decision.excluded_edits),
            "source_provenance": copy.deepcopy(self._current_sources),
            "patch_provenance": patch_provenance,
            "provenance_status": decision.provenance_status,
            "provenance_audit": copy.deepcopy(decision.provenance_audit),
        }
        for field in (
            "diagnosis_calls",
            "diagnoses",
            "eligible_diagnosis_ids",
            "preserve_constraints",
        ):
            if hasattr(decision, field):
                payload[field] = copy.deepcopy(getattr(decision, field))
        if hasattr(decision, "diagnoses"):
            payload["schema_version"] = "autonomous_gse_proposal_record_0.7.0"
        root = (
            REPO_ROOT
            / "artifacts"
            / self._campaign["campaign_id"]
            / "formal/steps"
            / f"step_{step['step']:03d}/proposal.json"
        )
        _write_json(root, payload)
        self._side_effects["filesystem_writes"] += 1

    def run_candidate_selection(
        self,
        step: dict[str, Any],
        candidate: dict[str, Any],
        promoted_version: str,
        task_count: int,
    ) -> dict[str, Any]:
        if task_count != 18:
            raise RuntimeContractError("Selection task budget is invalid.")
        promoted = {**candidate, "version": promoted_version}
        return self._checkpoint(
            promoted, v03_formal._split_task_ids(_v03_campaign(self._campaign), "selection")
        )

    def build_evolution_summary(
        self, step: dict[str, Any], candidate_checkpoint: dict[str, Any]
    ) -> dict[str, Any]:
        parent = self._checkpoints.get(step["parent_checkpoint"]["path"])
        candidate = self._checkpoints.get(candidate_checkpoint["path"])
        if parent is None or candidate is None:
            raise RuntimeContractError("Selection checkpoint lineage is missing.")
        payload = {
            "schema_version": "autonomous_gse_evolution_summary_0.5.0",
            "step": step["step"],
            "parent_checkpoint": copy.deepcopy(step["parent_checkpoint"]),
            "candidate_checkpoint": copy.deepcopy(candidate_checkpoint),
            "parent_selection": copy.deepcopy(parent["aggregation"]),
            "candidate_selection": copy.deepcopy(candidate["aggregation"]),
            "analysis": analyze_hierarchical_selection(parent, candidate),
        }
        path = (
            REPO_ROOT
            / "artifacts"
            / self._campaign["campaign_id"]
            / "formal/steps"
            / f"step_{step['step']:03d}/evolution_summary.json"
        )
        _write_json(path, payload)
        self._side_effects["filesystem_writes"] += 1
        summary = _artifact("evolution_summary", f"step_{step['step']:03d}", path)
        self._summaries[summary["path"]] = payload
        return summary


def _campaign_paths(campaign: dict[str, Any]) -> dict[str, Path]:
    root = REPO_ROOT / "artifacts" / campaign["campaign_id"] / "formal"
    return {
        "checkpoint": root / "checkpoints/s0_empty_skill.json",
        "report": root / CAMPAIGN_REPORT_FILENAME,
    }


def run_v05_campaign(
    campaign: dict[str, Any],
    batch_map: dict[str, Any],
    adapter: Any,
    *,
    scheduled_steps: int = 3,
    step_registrar: Callable[..., dict[str, Any]] = v03_runtime.register_step,
    budget_campaign: dict[str, Any] | None = None,
    resume_state: dict[str, Any] | None = None,
    on_step_completed: Callable[[dict[str, Any]], None] | None = None,
    proposal_driver: Callable[[Any, dict[str, Any], Any], Any] | None = None,
) -> dict[str, Any]:
    """Run the unchanged controller with the v0.5 rule-ID Proposal path.

    ``resume_state`` is optional Step-boundary fault recovery: when provided the
    controller restores the last completed Step's Parent, checkpoint, completed
    Steps, and budget usage, and continues from ``next_step`` instead of Step 1.
    A fresh run (``resume_state is None``) behaves exactly as before.
    """

    selection_tasks = campaign["selection"]["tasks"]
    operator = RuleIdGovernedReflectionEditorProposalOperator()
    checked_campaign = campaign if budget_campaign is None else budget_campaign

    if resume_state is None:
        current_parent = copy.deepcopy(campaign["initial_parent"])
        current_checkpoint = v03_runtime._require_artifact(
            adapter.create_initial_checkpoint(current_parent, selection_tasks),
            "Initial checkpoint",
            kind="selection_checkpoint",
            version=current_parent["version"],
        )
        usage = {
            "train_trajectories": 0,
            "initial_selection_trajectories": selection_tasks,
            "candidate_selection_trajectories": 0,
            "total_trajectories": selection_tasks,
            "candidates": 0,
            "learner_calls": 0,
            "test_trajectories": 0,
        }
        completed_steps: list[dict[str, Any]] = []
        start_step = 1
    else:
        current_parent = copy.deepcopy(resume_state["current_parent"])
        current_checkpoint = v03_runtime._require_artifact(
            copy.deepcopy(resume_state["current_checkpoint"]),
            "Resumed checkpoint",
            kind="selection_checkpoint",
            version=current_parent["version"],
        )
        completed_steps = copy.deepcopy(resume_state["completed_steps"])
        usage = copy.deepcopy(resume_state["budget_usage"])
        next_step = resume_state["next_step"]
        if not isinstance(next_step, int) or isinstance(next_step, bool):
            raise RuntimeContractError("Resume next_step must be an integer.")
        if next_step != len(completed_steps) + 1:
            raise RuntimeContractError(
                "Resume next_step must follow the completed Step prefix."
            )
        if not 1 <= next_step <= scheduled_steps + 1:
            raise RuntimeContractError("Resume next_step is out of range.")
        adapter.restore_checkpoint(current_checkpoint, current_parent)
        start_step = next_step

    for step_number in range(start_step, scheduled_steps + 1):
        step = step_registrar(
            campaign,
            batch_map,
            step=step_number,
            parent=current_parent,
            parent_checkpoint=current_checkpoint,
        )
        step = v03_runtime._reduce(step, {"type": "TRAIN_STARTED"}).step
        evidence = adapter.run_train(copy.deepcopy(step))
        usage["train_trajectories"] += len(step["batch"]["task_ids"])
        usage["total_trajectories"] += len(step["batch"]["task_ids"])
        v03_runtime._check_budget(checked_campaign, usage)

        for event_type in (
            "TRAIN_COMPLETED",
            "TRAIN_VALIDATED",
            "EXPERIENCE_FROZEN",
            "PROPOSAL_STARTED",
        ):
            step = v03_runtime._reduce(step, {"type": event_type}).step

        context = v03_runtime.ProposalContext(
            candidate_id=step["candidate_id"],
            parent_skill=adapter.skill_for_parent(step["parent"]),
            current_batch_governed_evidence=copy.deepcopy(evidence),
        )

        if proposal_driver is None:
            def call_reflector(request: ReflectorRequest) -> str:
                current = copy.deepcopy(step)
                return call_v05_reflector(
                    request,
                    learner_call=lambda model, system_prompt, user_prompt: (
                        adapter.learner_call(
                            current,
                            request,
                            model,
                            system_prompt,
                            user_prompt,
                        )
                    ),
                )

            def call_editor(request: EditorRequest) -> str:
                current = copy.deepcopy(step)
                return call_v05_editor(
                    request,
                    learner_call=lambda model, system_prompt, user_prompt: (
                        adapter.learner_call(
                            current,
                            request,
                            model,
                            system_prompt,
                            user_prompt,
                        )
                    ),
                )

            decision = operator.propose(
                context, call_reflector, call_reflector, call_editor
            )
        else:
            decision = proposal_driver(context, copy.deepcopy(step), adapter)
        usage["learner_calls"] += decision.reflector_calls + decision.editor_calls
        v03_runtime._check_budget(checked_campaign, usage)

        if decision.proposal_status == "NO_CANDIDATE":
            adapter.record_proposal(copy.deepcopy(step), decision, None)
            result = v03_runtime._reduce(
                step, v03_runtime._no_candidate_event(decision)
            )
        else:
            if decision.proposal_status != "CANDIDATE" or (
                decision.candidate_skill is None
            ):
                raise RuntimeContractError("Proposal returned an invalid status.")
            usage["candidates"] += 1
            candidate = v03_runtime._require_artifact(
                adapter.record_candidate(step, decision.candidate_skill),
                "Candidate",
                kind="candidate_skill",
                version=step["candidate_id"],
            )
            adapter.record_proposal(
                copy.deepcopy(step), decision, copy.deepcopy(candidate)
            )
            step = v03_runtime._reduce(
                step, v03_runtime._candidate_event(candidate, decision)
            ).step
            step = v03_runtime._reduce(
                step, {"type": "CANDIDATE_SELECTION_STARTED"}
            ).step
            promoted_version = v03_runtime._accepted_version_after(step["parent"])
            candidate_checkpoint = v03_runtime._require_artifact(
                adapter.run_candidate_selection(
                    copy.deepcopy(step),
                    copy.deepcopy(candidate),
                    promoted_version,
                    selection_tasks,
                ),
                "Candidate checkpoint",
                kind="selection_checkpoint",
                version=promoted_version,
            )
            usage["candidate_selection_trajectories"] += selection_tasks
            usage["total_trajectories"] += selection_tasks
            v03_runtime._check_budget(checked_campaign, usage)
            adapter.validate_candidate_selection(
                copy.deepcopy(step), copy.deepcopy(candidate_checkpoint)
            )
            step = v03_runtime._reduce(
                step, {"type": "SELECTION_VALIDATED"}
            ).step
            summary = v03_runtime._require_artifact(
                adapter.build_evolution_summary(
                    copy.deepcopy(step), copy.deepcopy(candidate_checkpoint)
                ),
                "Evolution summary",
                kind="evolution_summary",
                version=f"step_{step['step']:03d}",
            )
            step = v03_runtime._reduce(
                step, {"type": "EVOLUTION_SUMMARY_FROZEN"}
            ).step
            outcome = adapter.apply_gate(copy.deepcopy(step), summary)
            if outcome not in v03_runtime.CANDIDATE_OUTCOMES:
                raise RuntimeContractError("Gate must return ACCEPT or REJECT.")
            step = v03_runtime._reduce(step, {"type": "GATE_DECIDED"}).step
            completion_event: dict[str, Any] = {
                "type": "STEP_COMPLETED",
                "outcome": outcome,
            }
            if outcome == "ACCEPT":
                completion_event["candidate_checkpoint"] = candidate_checkpoint
            result = v03_runtime._reduce(step, completion_event)

        completed_steps.append(copy.deepcopy(result.step))
        if (
            result.accepted_parent is None
            or result.accepted_parent_checkpoint is None
        ):
            raise RuntimeContractError("Completed Step lost accepted state.")
        current_parent = result.accepted_parent
        current_checkpoint = result.accepted_parent_checkpoint
        if on_step_completed is not None:
            on_step_completed(
                {
                    "last_completed_step": step_number,
                    "next_step": step_number + 1,
                    "completed_steps": copy.deepcopy(completed_steps),
                    "current_parent": copy.deepcopy(current_parent),
                    "current_checkpoint": copy.deepcopy(current_checkpoint),
                    "budget_usage": copy.deepcopy(usage),
                }
            )

    v03_runtime._check_budget(checked_campaign, usage)
    return {
        "schema_version": "autonomous_gse_runtime_report_0.5.0",
        "campaign_id": campaign["campaign_id"],
        "mode": adapter.mode,
        "status": "COMPLETED",
        "steps": completed_steps,
        "final_parent": copy.deepcopy(current_parent),
        "final_parent_checkpoint": copy.deepcopy(current_checkpoint),
        "budget_usage": usage,
        "side_effects": copy.deepcopy(adapter.side_effects),
        "runtime_trace": adapter.trace,
    }


def build_formal_execution_plan(
    campaign: dict[str, Any], batch_map: dict[str, Any]
) -> dict[str, Any]:
    campaign = _expand_campaign(campaign)
    validate_formal_campaign_contract(campaign)
    base = v03_formal.build_formal_execution_plan(_v03_campaign(campaign), batch_map)
    train_rollouts = campaign["train_rollouts_per_task"]
    selection_rollouts = campaign["selection_rollouts_per_task"]
    return {
        "schema_version": "autonomous_gse_formal_plan_0.5.0",
        "campaign_id": campaign["campaign_id"],
        "headless": True,
        "execution": "parallel",
        "parallel_workers": 4,
        "train_rollouts_per_task": train_rollouts,
        "selection_rollouts_per_task": selection_rollouts,
        "initial_selection": {
            "tasks": len(base["initial_selection_task_ids"]),
            "trajectories": len(base["initial_selection_task_ids"])
            * selection_rollouts,
            "task_ids": base["initial_selection_task_ids"],
        },
        "steps": [
            {
                **step,
                "training_tasks": len(step["train_task_ids"]),
                "training_trajectories": len(step["train_task_ids"])
                * train_rollouts,
                "candidate_selection_tasks": len(
                    step["candidate_selection_task_ids"]
                ),
                "candidate_selection_trajectories": len(
                    step["candidate_selection_task_ids"]
                )
                * selection_rollouts,
            }
            for step in base["steps"]
        ],
        "post_hoc_training_replay": False,
        "final_test_evaluation": False,
        "full_experiment_seeds": 1,
        "maximum_budget": copy.deepcopy(campaign["budget"]),
    }


def run_initial_checkpoint(
    campaign_path: Path,
    *,
    rollout_backend: Callable[[RolloutRequest], Sequence[Path]] | None = None,
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
    rollout_backend: Callable[[RolloutRequest], Sequence[Path]] | None = None,
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
        _resolve_repo_path(campaign["train"]["batch_map"]).read_text(
            encoding="utf-8"
        )
    )
    adapter = FormalBenchmarkRuntimeAdapter(
        campaign,
        rollout_backend=rollout_backend or MultiRolloutRunnerBackend(campaign),
        learner=learner,
    )
    report = run_v05_campaign(_v03_campaign(campaign), batch_map, adapter)
    report["schema_version"] = "autonomous_gse_formal_report_0.5.0"
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
        raise RuntimeContractError("v0.5 rollout budget was exceeded.")
    report["disabled_phases"] = {
        "post_hoc_training_replay": True,
        "final_test_evaluation": True,
        "three_seed_full_experiment": True,
    }
    _write_json(paths["report"], report)
    return {
        "status": "AUTONOMOUS_GSE_V05_CAMPAIGN_COMPLETED",
        "report": _artifact("campaign_report", campaign["campaign_id"], paths["report"]),
        "step_outcomes": [step["outcome"] for step in report["steps"]],
        "final_parent": report["final_parent"],
    }


def main(argv: Sequence[str] | None = None) -> int:
    import argparse

    default_campaign = (
        REPO_ROOT
        / "experiments/campaigns/autonomous_gse_v05/campaign_manifest.json"
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
            _resolve_repo_path(campaign["train"]["batch_map"]).read_text(
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

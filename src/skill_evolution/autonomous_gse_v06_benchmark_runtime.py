"""v0.6 schedule and Benchmark-Agent configuration over v0.5 semantics."""

from __future__ import annotations

import copy
import json
import os
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Sequence

import src.skill_evolution.autonomous_gse_v03_benchmark_runtime as v03_formal
import src.skill_evolution.autonomous_gse_v03_runtime as v03_runtime
import src.skill_evolution.autonomous_gse_v05_benchmark_runtime as v05
from src.skill_evolution.autonomous_gse_v03_benchmark_runtime import RolloutRequest
from src.skill_evolution.autonomous_gse_v03_proposal import (
    EditorRequest,
    ReflectorRequest,
)
from src.skill_evolution.autonomous_gse_v03_runtime import RuntimeContractError

REPO_ROOT = Path(__file__).resolve().parents[2]
FORMAL_MODE = "formal_stwebagentbench_v06"
BENCHMARK_AGENT_MODEL = "deepseek-v4-flash"
BATCH_SCHEDULE = (
    ("batch_001", "batch_002", "batch_003"),
    ("batch_002", "batch_003", "batch_001"),
    ("batch_003", "batch_001", "batch_002"),
)
FLAT_BATCH_SCHEDULE = tuple(batch for epoch in BATCH_SCHEDULE for batch in epoch)
TRAIN_SEED_STRATEGY = "campaign_step_task_rollout"
SELECTION_SEED_STRATEGY = "campaign_task_rollout"
_CAMPAIGN_SEED_STRIDE = 1_000_000
_STEP_SEED_STRIDE = 10_000
_TASK_SEED_STRIDE = 10


def _resolve_repo_path(relative_path: str) -> Path:
    path = (REPO_ROOT / relative_path).resolve()
    path.relative_to(REPO_ROOT)
    return path


def _expand_campaign(campaign: dict[str, Any]) -> dict[str, Any]:
    base_path = campaign.get("base_campaign")
    if base_path is None:
        return copy.deepcopy(campaign)
    base = json.loads(_resolve_repo_path(base_path).read_text(encoding="utf-8"))
    expanded = {**base, **copy.deepcopy(campaign)}
    runtime = expanded["runtime"]
    expanded["benchmark_runtime"] = copy.deepcopy(base["benchmark_runtime"])
    expanded["benchmark_runtime"]["agent_model"] = runtime[
        "benchmark_agent"
    ]["model"]
    expanded["benchmark_runtime"]["agent_parameters"]["temperature"] = runtime[
        "benchmark_agent"
    ]["temperature"]
    expanded["benchmark_runtime"]["agent_parameters"]["max_tokens"] = runtime[
        "benchmark_agent"
    ]["max_tokens"]
    rollout = expanded["benchmark_runtime"]["rollout"]
    rollout.update(
        {
            "headless": expanded["headless"],
            "trials_per_task": runtime["train"]["rollouts_per_task"],
            "execution": expanded["execution"],
            "parallel_workers": expanded["parallel_workers"],
        }
    )
    expanded["train_rollouts_per_task"] = runtime["train"]["rollouts_per_task"]
    expanded["selection_rollouts_per_task"] = runtime["selection"][
        "rollouts_per_task"
    ]
    return expanded


def _controller_campaign(campaign: dict[str, Any]) -> dict[str, Any]:
    projected = v05._v03_campaign(_expand_campaign(campaign))
    projected["schedule"] = {
        "epochs": 1,
        "steps_per_epoch": 3,
        "scheduled_steps": 3,
    }
    projected["benchmark_runtime"]["agent_model"] = "openai/gpt-5.6-luna"
    projected["benchmark_runtime"]["agent_parameters"] = {
        "temperature": 0.1,
        "max_tokens": 512,
    }
    return projected


def _expected_budget(campaign: dict[str, Any]) -> dict[str, Any]:
    train_rollouts = campaign["runtime"]["train"]["rollouts_per_task"]
    selection_rollouts = campaign["runtime"]["selection"]["rollouts_per_task"]
    scheduled_steps = campaign["schedule"]["scheduled_steps"]
    return {
        "train_trajectories": scheduled_steps * 17 * train_rollouts,
        "initial_selection_trajectories": 18 * selection_rollouts,
        "maximum_candidate_selection_trajectories": (
            scheduled_steps * 18 * selection_rollouts
        ),
        "maximum_total_trajectories": (
            scheduled_steps * 17 * train_rollouts
            + (1 + scheduled_steps) * 18 * selection_rollouts
        ),
        "maximum_candidates": scheduled_steps,
        "maximum_learner_calls": scheduled_steps * 3,
        "unused_budget_reallocation": "forbidden",
    }


def validate_formal_campaign_contract(
    campaign: dict[str, Any], *, require_ready: bool = False
) -> None:
    campaign = _expand_campaign(campaign)
    if campaign.get("schema_version") != "autonomous_gse_campaign_0.6.0":
        raise RuntimeContractError("Unsupported v0.6 Campaign schema.")
    if campaign.get("protocol_version") != "autonomous_gse_v06":
        raise RuntimeContractError("Unsupported v0.6 Campaign protocol.")
    if campaign.get("campaign_id") != "autonomous_gse_v06":
        raise RuntimeContractError("v0.6 Campaign ID is invalid.")
    if campaign.get("status") not in {"draft", "ready"}:
        raise RuntimeContractError("Campaign status must be draft or ready.")
    if require_ready and campaign["status"] != "ready":
        raise RuntimeContractError("Campaign must be ready before execution.")
    if campaign.get("schedule") != {
        "epochs": 3,
        "steps_per_epoch": 3,
        "scheduled_steps": 9,
    }:
        raise RuntimeContractError("v0.6 must schedule 3 epochs and 9 Steps.")
    if campaign.get("batch_schedule") != {
        f"epoch_{index}": list(epoch)
        for index, epoch in enumerate(BATCH_SCHEDULE, start=1)
    }:
        raise RuntimeContractError("v0.6 Batch rotation drifted.")
    runtime = campaign.get("runtime", {})
    expected_learner = {
        role: {"model": "openai/gpt-5.6-luna", "temperature": 0}
        for role in ("success_reflector", "failure_reflector", "editor")
    }
    if runtime != {
        "benchmark_agent": {
            "model": BENCHMARK_AGENT_MODEL,
            "temperature": 0.2,
            "thinking": False,
            "max_tokens": 2048,
            "retry_on_token_exhaustion": False,
        },
        "train": {
            "rollouts_per_task": 3,
            "temperature": 0.2,
            "seed_strategy": TRAIN_SEED_STRATEGY,
            "seeds": "distinct_across_rollouts",
        },
        "selection": {
            "rollouts_per_task": 3,
            "temperature": 0.2,
            "seed_strategy": SELECTION_SEED_STRATEGY,
            "parent_candidate_seed_matching": True,
        },
        "learner": expected_learner,
    }:
        raise RuntimeContractError("v0.6 runtime configuration drifted.")
    if campaign["benchmark_runtime"]["agent_model"] != BENCHMARK_AGENT_MODEL:
        raise RuntimeContractError("Benchmark Agent model drifted.")
    if campaign["benchmark_runtime"]["agent_parameters"]["temperature"] != runtime[
        "benchmark_agent"
    ]["temperature"]:
        raise RuntimeContractError("Benchmark Agent temperature drifted.")
    if campaign["benchmark_runtime"]["agent_parameters"]["max_tokens"] != runtime[
        "benchmark_agent"
    ]["max_tokens"]:
        raise RuntimeContractError("Benchmark Agent max_tokens drifted.")
    if campaign["proposal"]["learner"]["model"] != "openai/gpt-5.6-luna":
        raise RuntimeContractError("Reflector/Editor model drifted.")
    if (
        campaign.get("headless") is not True
        or campaign.get("execution") != "parallel"
        or campaign.get("parallel_workers") != 4
        or campaign.get("full_experiment_seeds") != 1
    ):
        raise RuntimeContractError("v0.6 rollout execution contract drifted.")
    if campaign.get("budget") != _expected_budget(campaign):
        raise RuntimeContractError("v0.6 rollout budget drifted.")
    if campaign.get("test") != {
        "authorized": False,
        "data_for_learning": "forbidden",
    }:
        raise RuntimeContractError("Final Test execution must be disabled.")
    if campaign.get("post_hoc_training_replay") != {"enabled": False}:
        raise RuntimeContractError("Post-hoc training replay must be disabled.")
    if campaign.get("rule_addressing") != {
        "mode": "stable_parent_rule_id",
        "legacy_target_clause_fallback": "normalize_markdown_bullet_and_whitespace",
        "ambiguous_legacy_match": "reject_edit",
    }:
        raise RuntimeContractError("v0.6 rule-addressing contract drifted.")
    v03_formal.validate_formal_campaign_contract(
        _controller_campaign(campaign), require_ready=require_ready
    )


class SeededLearnerAdapter(v05.SeededLearnerAdapter):
    """Use the unchanged learner prompts with frozen per-role sampling."""

    campaign_validator = staticmethod(validate_formal_campaign_contract)
    campaign_expander = staticmethod(_expand_campaign)

    def __init__(self, campaign: dict[str, Any], **kwargs: Any) -> None:
        expanded = _expand_campaign(campaign)
        self._role_sampling = copy.deepcopy(expanded["runtime"]["learner"])
        super().__init__(expanded, **kwargs)

    def _sampling_parameters(
        self, request: ReflectorRequest | EditorRequest
    ) -> dict[str, Any]:
        role = (
            f"{request.reflector}_reflector"
            if isinstance(request, ReflectorRequest)
            else "editor"
        )
        config = self._role_sampling[role]
        if config["model"] != self._model:
            raise RuntimeContractError("Learner role model drifted.")
        return {"seed": self._seed, "temperature": config["temperature"]}


def train_execution_seed(
    campaign_seed: int, execution_step: int, task_id: int, rollout_id: int
) -> int:
    """Derive a unique Train seed from campaign, step, task, and rollout."""

    if (
        campaign_seed < 0
        or not 0 <= execution_step < 100
        or not 0 <= task_id < 1_000
        or not 0 <= rollout_id < _TASK_SEED_STRIDE
    ):
        raise RuntimeContractError("Train seed inputs exceed their frozen ranges.")
    return (
        campaign_seed * _CAMPAIGN_SEED_STRIDE
        + execution_step * _STEP_SEED_STRIDE
        + task_id * _TASK_SEED_STRIDE
        + rollout_id
    )


def selection_execution_seed(
    campaign_seed: int, task_id: int, rollout_id: int
) -> int:
    """Derive a Selection seed independent of skill or comparison condition."""

    if (
        campaign_seed < 0
        or not 0 <= task_id < 1_000
        or not 0 <= rollout_id < _TASK_SEED_STRIDE
    ):
        raise RuntimeContractError(
            "Selection seed inputs exceed their frozen ranges."
        )
    return (
        campaign_seed * _CAMPAIGN_SEED_STRIDE
        + task_id * _TASK_SEED_STRIDE
        + rollout_id
    )


class MultiRolloutRunnerBackend(v05.MultiRolloutRunnerBackend):
    """Add per-phase seeds and paths to the unchanged multi-rollout backend."""

    campaign_validator = staticmethod(validate_formal_campaign_contract)
    campaign_expander = staticmethod(_expand_campaign)
    record_benchmark_agent_model = True

    def __init__(self, campaign: dict[str, Any]) -> None:
        expanded = _expand_campaign(campaign)
        self.sampling_temperature = expanded["runtime"]["benchmark_agent"][
            "temperature"
        ]
        self.sampling_max_tokens = expanded["runtime"]["benchmark_agent"][
            "max_tokens"
        ]
        benchmark_agent = expanded["runtime"]["benchmark_agent"]
        self.sampling_retry_max_tokens = benchmark_agent.get(
            "retry_max_tokens"
        )
        self.sampling_thinking = benchmark_agent["thinking"]
        self.sampling_retry_on_token_exhaustion = benchmark_agent[
            "retry_on_token_exhaustion"
        ]
        super().__init__(expanded)

    def _execution_seed(
        self, request: RolloutRequest, task_id: int, rollout_id: int
    ) -> int:
        if request.split == "train":
            if request.execution_step is None:
                raise RuntimeContractError("Train execution step is missing.")
            return train_execution_seed(
                self._campaign_seed,
                request.execution_step,
                task_id,
                rollout_id,
            )
        if request.split == "selection":
            return selection_execution_seed(
                self._campaign_seed, task_id, rollout_id
            )
        raise RuntimeContractError("v0.6 runs only Train and Selection.")


class FormalBenchmarkRuntimeAdapter(v05.FormalBenchmarkRuntimeAdapter):
    """Reuse v0.5 aggregation, Gate, verifier, and provenance semantics."""

    mode = FORMAL_MODE
    campaign_validator = staticmethod(validate_formal_campaign_contract)
    campaign_expander = staticmethod(_expand_campaign)
    controller_campaign = staticmethod(_controller_campaign)

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self._execution_phase: str | None = None
        self._execution_step: int | None = None
        super().__init__(*args, **kwargs)

    def _set_execution_phase(
        self, phase: str, *, execution_step: int | None = None
    ) -> None:
        self._execution_phase = phase
        self._execution_step = execution_step

    def _prepare_rollout_request(self, request: RolloutRequest) -> RolloutRequest:
        return replace(
            request,
            execution_phase=self._execution_phase,
            execution_step=self._execution_step,
        )

    def _load_trajectory(
        self,
        path: Path,
        task_id: int,
        rollout_id: int,
        split: str,
        artifact: dict[str, Any],
    ) -> dict[str, Any]:
        trajectory = v05.FormalBenchmarkRuntimeAdapter._load_trajectory(
            path, task_id, rollout_id, split, artifact
        )
        run = trajectory["run"]
        if (
            run.get("requested_model") != BENCHMARK_AGENT_MODEL
            or run.get("benchmark_agent_model") != BENCHMARK_AGENT_MODEL
        ):
            raise RuntimeContractError("Trajectory Benchmark Agent model drifted.")
        expected_temperature = self._campaign["runtime"]["benchmark_agent"][
            "temperature"
        ]
        if (
            run.get("generation_temperature") != expected_temperature
            or not isinstance(run.get("execution_seed"), int)
        ):
            raise RuntimeContractError("Trajectory sampling metadata drifted.")
        return trajectory

    def run_fresh_initial_checkpoint(self) -> dict[str, Any]:
        self._set_execution_phase("initial_selection")
        return super().run_fresh_initial_checkpoint()

    def run_train(self, step: dict[str, Any]) -> tuple[dict[str, Any], ...]:
        self._set_execution_phase(
            f"step_{step['step']:03d}_train",
            execution_step=step["step"],
        )
        return super().run_train(step)

    def run_candidate_selection(
        self,
        step: dict[str, Any],
        candidate: dict[str, Any],
        promoted_version: str,
        task_count: int,
    ) -> dict[str, Any]:
        self._set_execution_phase(
            f"step_{step['step']:03d}_selection",
            execution_step=step["step"],
        )
        return super().run_candidate_selection(
            step, candidate, promoted_version, task_count
        )

    def build_evolution_summary(
        self, step: dict[str, Any], candidate_checkpoint: dict[str, Any]
    ) -> dict[str, Any]:
        parent = self._checkpoints.get(step["parent_checkpoint"]["path"])
        candidate = self._checkpoints.get(candidate_checkpoint["path"])
        if parent is None or candidate is None:
            raise RuntimeContractError("Selection checkpoint lineage is missing.")

        def seeds(checkpoint: dict[str, Any]) -> dict[tuple[int, int], int]:
            return {
                (source["task_id"], source["rollout_id"]): source["execution_seed"]
                for source in checkpoint["sources"]
            }

        if seeds(parent) != seeds(candidate):
            raise RuntimeContractError(
                "Selection Parent/Candidate sampling seeds are not matched."
            )
        return super().build_evolution_summary(step, candidate_checkpoint)


def _register_v06_step(
    campaign: dict[str, Any],
    batch_map: dict[str, Any],
    *,
    step: int,
    parent: dict[str, Any],
    parent_checkpoint: dict[str, Any],
) -> dict[str, Any]:
    batch_id = FLAT_BATCH_SCHEDULE[step - 1]
    batch_step = int(batch_id.rsplit("_", 1)[1])
    return v03_runtime.register_step(
        campaign,
        batch_map,
        step=step,
        parent=parent,
        parent_checkpoint=parent_checkpoint,
        epoch=(step - 1) // 3 + 1,
        batch_step=batch_step,
        scheduled_steps=9,
    )


def build_formal_execution_plan(
    campaign: dict[str, Any], batch_map: dict[str, Any]
) -> dict[str, Any]:
    campaign = _expand_campaign(campaign)
    validate_formal_campaign_contract(campaign)
    base = v03_formal.build_formal_execution_plan(
        _controller_campaign(campaign), batch_map
    )
    by_batch = {step["batch_id"]: step for step in base["steps"]}
    train_rollouts = campaign["runtime"]["train"]["rollouts_per_task"]
    selection_rollouts = campaign["runtime"]["selection"]["rollouts_per_task"]
    selection_task_ids = base["initial_selection_task_ids"]
    steps = []
    for step_number, batch_id in enumerate(FLAT_BATCH_SCHEDULE, start=1):
        source = by_batch[batch_id]
        steps.append(
            {
                **copy.deepcopy(source),
                "step": step_number,
                "epoch": (step_number - 1) // 3 + 1,
                "batch_id": batch_id,
                "training_tasks": len(source["train_task_ids"]),
                "training_trajectories": len(source["train_task_ids"])
                * train_rollouts,
                "candidate_selection_tasks": len(selection_task_ids),
                "candidate_selection_trajectories": len(selection_task_ids)
                * selection_rollouts,
                "train_seed_strategy": TRAIN_SEED_STRATEGY,
                "selection_seed_strategy": SELECTION_SEED_STRATEGY,
                "parent_candidate_seed_matching": True,
            }
        )
    return {
        "schema_version": "autonomous_gse_formal_plan_0.6.0",
        "campaign_id": campaign["campaign_id"],
        "benchmark_agent_model": campaign["runtime"]["benchmark_agent"]["model"],
        "benchmark_agent_temperature": campaign["runtime"]["benchmark_agent"][
            "temperature"
        ],
        "benchmark_agent_max_tokens": campaign["runtime"]["benchmark_agent"][
            "max_tokens"
        ],
        "benchmark_agent_thinking": campaign["runtime"]["benchmark_agent"][
            "thinking"
        ],
        "benchmark_agent_retry_on_token_exhaustion": campaign["runtime"][
            "benchmark_agent"
        ]["retry_on_token_exhaustion"],
        "learner_model": campaign["proposal"]["learner"]["model"],
        "headless": True,
        "execution": "parallel",
        "parallel_workers": 4,
        "train_rollouts_per_task": train_rollouts,
        "selection_rollouts_per_task": selection_rollouts,
        "initial_selection": {
            "tasks": len(selection_task_ids),
            "trajectories": len(selection_task_ids) * selection_rollouts,
            "task_ids": selection_task_ids,
        },
        "steps": steps,
        "post_hoc_training_replay": False,
        "final_test_evaluation": False,
        "maximum_budget": copy.deepcopy(campaign["budget"]),
    }


def run_v06_campaign(
    campaign: dict[str, Any],
    batch_map: dict[str, Any],
    adapter: Any,
    *,
    resume_state: dict[str, Any] | None = None,
    on_step_completed: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    """Run the v0.6 9-Step schedule over the unchanged v0.5 controller.

    ``resume_state`` / ``on_step_completed`` are passed straight through to the
    v0.5 controller; the v0.6 layer adds no controller logic of its own so the
    Step-boundary resume semantics are exactly the controller's.
    """

    expanded = _expand_campaign(campaign)
    validate_formal_campaign_contract(expanded, require_ready=True)
    report = v05.run_v05_campaign(
        _controller_campaign(expanded),
        batch_map,
        adapter,
        scheduled_steps=9,
        step_registrar=_register_v06_step,
        budget_campaign=expanded,
        resume_state=resume_state,
        on_step_completed=on_step_completed,
    )
    report["schema_version"] = "autonomous_gse_runtime_report_0.6.0"
    report["campaign_id"] = expanded["campaign_id"]
    report["benchmark_agent_model"] = expanded["runtime"]["benchmark_agent"][
        "model"
    ]
    return report


CONTROLLER_STATE_FILENAME = "controller_state.json"
RESUME_STATE_SCHEMA = "autonomous_gse_resume_state_0.6.0"
GATE_DECISION_OUTCOMES = {"continue_evolution": "ACCEPT", "reject": "REJECT"}
# Controller-level artifacts a *complete* or *partial* Step writes under
# ``formal/steps/step_NNN/``. Raw trajectories never live here, so the presence
# of any of these files means the Step has started producing formal artifacts.
CONTROLLER_STEP_ARTIFACTS = (
    "train_set.json",
    "governed_experience.json",
    "success_reflector_call.json",
    "success_reflector_response.txt",
    "failure_reflector_call.json",
    "failure_reflector_response.txt",
    "editor_call.json",
    "editor_response.txt",
    "proposal.json",
    "evolution_summary.json",
)
FROZEN_CANDIDATE_SELECTION_ARTIFACTS = {
    "train_set.json",
    "governed_experience.json",
    "success_reflector_call.json",
    "success_reflector_response.txt",
    "failure_reflector_call.json",
    "failure_reflector_response.txt",
    "editor_call.json",
    "editor_response.txt",
    "proposal.json",
}


def _campaign_paths(campaign: dict[str, Any]) -> dict[str, Path]:
    root = REPO_ROOT / "artifacts" / campaign["campaign_id"] / "formal"
    return {
        "checkpoint": root / "checkpoints/s0_empty_skill.json",
        "report": root / v05.CAMPAIGN_REPORT_FILENAME,
        "controller_state": root / CONTROLLER_STATE_FILENAME,
        "steps": root / "steps",
    }


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    """Write JSON through a temp file + ``os.replace`` (mirrors the frozen
    ``governed_experience`` atomic writer). Used only for the resume state so a
    crash mid-write can never leave a half-written ``controller_state.json``."""

    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.parent / f".{path.name}.tmp"
    tmp.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(tmp, path)


def _step_dir(campaign: dict[str, Any], step_number: int) -> Path:
    return _campaign_paths(campaign)["steps"] / f"step_{step_number:03d}"


def _controller_artifacts_in(step_dir: Path) -> list[str]:
    if not step_dir.is_dir():
        return []
    return [name for name in CONTROLLER_STEP_ARTIFACTS if (step_dir / name).is_file()]


def _formal_steps_started(campaign: dict[str, Any]) -> bool:
    """True when any Step directory already holds a controller-level artifact.

    The initial S0 checkpoint and the raw initial-selection trajectories live
    outside ``formal/steps/`` and therefore never make this return True.
    """

    steps_root = _campaign_paths(campaign)["steps"]
    if not steps_root.is_dir():
        return False
    return any(
        _controller_artifacts_in(child)
        for child in steps_root.iterdir()
        if child.is_dir()
    )


def _require_clean_next_step(campaign: dict[str, Any], next_step: int) -> None:
    """Fail closed if the next unfinished Step already produced partial formal
    artifacts. Resume only ever continues from a clean Step boundary; it never
    guesses how to continue a half-run Reflector/Editor/Selection."""

    if next_step < 1 or next_step > 9:
        return
    present = _controller_artifacts_in(_step_dir(campaign, next_step))
    if present:
        raise RuntimeContractError(
            "Partial controller artifacts exist for the next Step "
            f"(step_{next_step:03d}: {present}). Step-boundary resume cannot "
            "safely continue; remove or complete that Step manually."
        )


def _frozen_proposal_decision(proposal: dict[str, Any]) -> SimpleNamespace:
    return SimpleNamespace(
        proposal_reason=proposal["proposal_reason"],
        raw_patches=proposal["raw_patches"],
        canonical_edits=proposal["canonical_edits"],
        applied_edits=proposal["applied_edits"],
        excluded_edits=proposal["excluded_edits"],
        provenance_status=proposal.get("provenance_status"),
        provenance_audit=proposal.get("provenance_audit"),
    )


def _recover_frozen_candidate_selection(
    campaign: dict[str, Any], resume_state: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any], int, int]:
    """Recover one Step frozen immediately before Candidate Selection.

    This accepts exactly one partial-Step shape: Train, governed experience,
    both Reflectors, Editor, Proposal, and Candidate are all frozen, while no
    evolution summary exists. It reconstructs only the pure controller state;
    it performs no rollout, Learner call, write, aggregation, or Gate action.
    """

    expanded = _expand_campaign(campaign)
    step_number = resume_state["next_step"]
    if not 1 <= step_number <= expanded["schedule"]["scheduled_steps"]:
        raise RuntimeContractError("Partial-Step resume target is out of range.")
    step_dir = _step_dir(expanded, step_number)
    present = set(_controller_artifacts_in(step_dir))
    if present != FROZEN_CANDIDATE_SELECTION_ARTIFACTS:
        raise RuntimeContractError(
            "Partial Step is not at the frozen Candidate Selection boundary "
            f"(step_{step_number:03d}: {sorted(present)})."
        )

    controller_campaign = _controller_campaign(expanded)
    batch_map = json.loads(
        _resolve_repo_path(expanded["train"]["batch_map"]).read_text(
            encoding="utf-8"
        )
    )
    parent = copy.deepcopy(resume_state["current_parent"])
    parent_checkpoint = copy.deepcopy(resume_state["current_checkpoint"])
    step = _register_v06_step(
        controller_campaign,
        batch_map,
        step=step_number,
        parent=parent,
        parent_checkpoint=parent_checkpoint,
    )
    train_set = json.loads((step_dir / "train_set.json").read_text(encoding="utf-8"))
    governed = json.loads(
        (step_dir / "governed_experience.json").read_text(encoding="utf-8")
    )
    proposal = json.loads((step_dir / "proposal.json").read_text(encoding="utf-8"))
    task_ids = step["batch"]["task_ids"]
    expected_trajectories = len(task_ids) * expanded["train_rollouts_per_task"]
    lineage = governed.get("lineage", {})
    if (
        train_set.get("step") != step_number
        or train_set.get("batch_id") != step["batch"]["batch_id"]
        or train_set.get("parent") != parent
        or train_set.get("task_ids") != task_ids
        or train_set.get("training_tasks") != len(task_ids)
        or train_set.get("training_trajectories") != expected_trajectories
        or governed.get("experience_count") != expected_trajectories
        or lineage.get("batch_id") != step["batch"]["batch_id"]
        or lineage.get("parent_version") != parent["version"]
        or lineage.get("task_ids") != task_ids
        or lineage.get("rollouts_per_task")
        != expanded["train_rollouts_per_task"]
    ):
        raise RuntimeContractError(
            f"Frozen Train lineage drifted at Step {step_number}."
        )
    if (
        proposal.get("step") != step_number
        or proposal.get("proposal_status") != "CANDIDATE"
    ):
        raise RuntimeContractError(
            f"Frozen Proposal is not a Candidate at Step {step_number}."
        )
    reflector_calls = proposal.get("reflector_calls")
    editor_calls = proposal.get("editor_calls")
    if reflector_calls != 2 or editor_calls != 1:
        raise RuntimeContractError(
            f"Frozen Learner-call lineage drifted at Step {step_number}."
        )
    candidate = proposal.get("candidate")
    expected_candidate_path = (
        f"artifacts/{expanded['campaign_id']}/formal/candidates/"
        f"{step['candidate_id']}/skill.md"
    )
    if candidate != {
        "kind": "candidate_skill",
        "version": step["candidate_id"],
        "path": expected_candidate_path,
    } or not _resolve_repo_path(expected_candidate_path).is_file():
        raise RuntimeContractError(
            f"Frozen Candidate lineage drifted at Step {step_number}."
        )

    for event_type in (
        "TRAIN_STARTED",
        "TRAIN_COMPLETED",
        "TRAIN_VALIDATED",
        "EXPERIENCE_FROZEN",
        "PROPOSAL_STARTED",
    ):
        step = v03_runtime._reduce(step, {"type": event_type}).step
    decision = _frozen_proposal_decision(proposal)
    step = v03_runtime._reduce(
        step, v03_runtime._candidate_event(candidate, decision)
    ).step
    step = v03_runtime._reduce(
        step, {"type": "CANDIDATE_SELECTION_STARTED"}
    ).step
    return step, candidate, reflector_calls, editor_calls


def _complete_frozen_candidate_selection(
    campaign: dict[str, Any],
    resume_state: dict[str, Any],
    adapter: FormalBenchmarkRuntimeAdapter,
) -> dict[str, Any]:
    """Complete a frozen Candidate Selection and return the next boundary."""

    expanded = _expand_campaign(campaign)
    step, candidate, reflector_calls, editor_calls = (
        _recover_frozen_candidate_selection(expanded, resume_state)
    )
    adapter.restore_checkpoint(
        resume_state["current_checkpoint"], resume_state["current_parent"]
    )
    selection_tasks = expanded["selection"]["tasks"]
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
    adapter.validate_candidate_selection(
        copy.deepcopy(step), copy.deepcopy(candidate_checkpoint)
    )
    step = v03_runtime._reduce(step, {"type": "SELECTION_VALIDATED"}).step
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
    if result.accepted_parent is None or result.accepted_parent_checkpoint is None:
        raise RuntimeContractError("Recovered partial Step lost accepted state.")

    usage = copy.deepcopy(resume_state["budget_usage"])
    train_tasks = len(step["batch"]["task_ids"])
    usage["train_trajectories"] += train_tasks
    usage["candidate_selection_trajectories"] += selection_tasks
    usage["total_trajectories"] += train_tasks + selection_tasks
    usage["candidates"] += 1
    usage["learner_calls"] += reflector_calls + editor_calls
    v03_runtime._check_budget(expanded, usage)
    completed_steps = [
        *copy.deepcopy(resume_state["completed_steps"]),
        copy.deepcopy(result.step),
    ]
    return {
        "last_completed_step": step["step"],
        "next_step": step["step"] + 1,
        "completed_steps": completed_steps,
        "current_parent": copy.deepcopy(result.accepted_parent),
        "current_checkpoint": copy.deepcopy(result.accepted_parent_checkpoint),
        "budget_usage": usage,
    }


def _replay_completed_step(
    expanded: dict[str, Any],
    controller_campaign: dict[str, Any],
    batch_map: dict[str, Any],
    step_number: int,
    parent: dict[str, Any],
    parent_checkpoint: dict[str, Any],
    usage: dict[str, int],
    selection_tasks: int,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Replay one frozen, complete Step through the pure v0.3 reducer.

    Reads only ``proposal.json`` / ``evolution_summary.json`` and drives the
    unchanged reducer through the exact live transition sequence. No adapter
    side effect runs: the Gate outcome is read from the frozen
    ``evolution_summary`` (never recomputed), and lineage is validated by the
    reducer's own checkpoint checks plus explicit frozen-vs-replayed asserts.
    """

    step_dir = _step_dir(expanded, step_number)
    proposal = json.loads((step_dir / "proposal.json").read_text(encoding="utf-8"))
    train_set = json.loads((step_dir / "train_set.json").read_text(encoding="utf-8"))
    if proposal.get("step") != step_number:
        raise RuntimeContractError(
            f"Frozen proposal.json step mismatch at Step {step_number}."
        )

    step = _register_v06_step(
        controller_campaign,
        batch_map,
        step=step_number,
        parent=parent,
        parent_checkpoint=parent_checkpoint,
    )
    if train_set.get("batch_id") != step["batch"]["batch_id"]:
        raise RuntimeContractError(
            f"Frozen train_set batch drifted from the schedule at Step {step_number}."
        )
    task_ids = step["batch"]["task_ids"]
    for event_type in (
        "TRAIN_STARTED",
        "TRAIN_COMPLETED",
        "TRAIN_VALIDATED",
        "EXPERIENCE_FROZEN",
        "PROPOSAL_STARTED",
    ):
        step = v03_runtime._reduce(step, {"type": event_type}).step

    decision = _frozen_proposal_decision(proposal)
    reflector_calls = proposal.get("reflector_calls")
    editor_calls = proposal.get("editor_calls")
    if not isinstance(reflector_calls, int) or not isinstance(editor_calls, int):
        raise RuntimeContractError(
            f"Frozen proposal.json is missing Learner-call counts at Step {step_number}."
        )
    status = proposal.get("proposal_status")

    if status == "NO_CANDIDATE":
        result = v03_runtime._reduce(step, v03_runtime._no_candidate_event(decision))
    elif status == "CANDIDATE":
        candidate = proposal.get("candidate")
        if not isinstance(candidate, dict) or candidate.get("version") != step[
            "candidate_id"
        ]:
            raise RuntimeContractError(
                f"Frozen candidate lineage mismatch at Step {step_number}."
            )
        summary = json.loads(
            (step_dir / "evolution_summary.json").read_text(encoding="utf-8")
        )
        if summary.get("step") != step_number:
            raise RuntimeContractError(
                f"Frozen evolution_summary.json step mismatch at Step {step_number}."
            )
        if summary.get("parent_checkpoint") != parent_checkpoint:
            raise RuntimeContractError(
                f"Frozen parent checkpoint lineage drifted at Step {step_number}."
            )
        step = v03_runtime._reduce(
            step, v03_runtime._candidate_event(candidate, decision)
        ).step
        step = v03_runtime._reduce(
            step, {"type": "CANDIDATE_SELECTION_STARTED"}
        ).step
        step = v03_runtime._reduce(step, {"type": "SELECTION_VALIDATED"}).step
        step = v03_runtime._reduce(step, {"type": "EVOLUTION_SUMMARY_FROZEN"}).step
        step = v03_runtime._reduce(step, {"type": "GATE_DECIDED"}).step
        decision_code = summary["analysis"]["evolution_gate"]["decision"]
        outcome = GATE_DECISION_OUTCOMES.get(decision_code)
        if outcome is None:
            raise RuntimeContractError(
                f"Frozen Gate decision {decision_code!r} is unsupported at "
                f"Step {step_number}."
            )
        completion_event: dict[str, Any] = {
            "type": "STEP_COMPLETED",
            "outcome": outcome,
        }
        if outcome == "ACCEPT":
            completion_event["candidate_checkpoint"] = summary["candidate_checkpoint"]
        result = v03_runtime._reduce(step, completion_event)
    else:
        raise RuntimeContractError(
            f"Frozen proposal_status {status!r} is invalid at Step {step_number}."
        )

    if result.accepted_parent is None or result.accepted_parent_checkpoint is None:
        raise RuntimeContractError(
            f"Recovered Step {step_number} lost its accepted state."
        )

    # Budget accounting mirrors run_v05_campaign exactly, in Task units.
    usage["train_trajectories"] += len(task_ids)
    usage["total_trajectories"] += len(task_ids)
    usage["learner_calls"] += reflector_calls + editor_calls
    if status == "CANDIDATE":
        usage["candidates"] += 1
        usage["candidate_selection_trajectories"] += selection_tasks
        usage["total_trajectories"] += selection_tasks

    return (
        copy.deepcopy(result.step),
        result.accepted_parent,
        result.accepted_parent_checkpoint,
    )


def recover_controller_state_from_artifacts(
    campaign: dict[str, Any]
) -> dict[str, Any]:
    """Rebuild the resume state from the frozen complete-Step prefix.

    Walks ``formal/steps/step_001..step_009`` in order. Each complete Step is
    replayed through the pure reducer (no Learner / Browser / Selection / Gate
    re-run). Recovery stops at the first untouched Step or at the one supported
    partial boundary: an exactly frozen Candidate awaiting Selection. Other
    partial Steps, non-contiguous prefixes, and lineage mismatches fail closed.
    """

    expanded = _expand_campaign(campaign)
    controller_campaign = _controller_campaign(expanded)
    batch_map = json.loads(
        _resolve_repo_path(expanded["train"]["batch_map"]).read_text(encoding="utf-8")
    )
    selection_tasks = controller_campaign["selection"]["tasks"]
    current_parent = copy.deepcopy(controller_campaign["initial_parent"])
    current_checkpoint = {
        "kind": "selection_checkpoint",
        "version": current_parent["version"],
        "path": _campaign_paths(expanded)["checkpoint"]
        .resolve()
        .relative_to(REPO_ROOT)
        .as_posix(),
    }
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
    next_step = 10
    stopped = False
    for step_number in range(1, 10):
        started = _controller_artifacts_in(_step_dir(expanded, step_number))
        if not started:
            if not stopped:
                stopped = True
                next_step = step_number
            continue
        if stopped:
            raise RuntimeContractError(
                "Formal Step artifacts are not a contiguous prefix from Step 1 "
                f"(orphan artifacts at step_{step_number:03d})."
            )
        if not (_step_dir(expanded, step_number) / "proposal.json").is_file():
            raise RuntimeContractError(
                f"Step {step_number} started but has no proposal.json; it is "
                "incomplete and resume cannot continue."
            )
        proposal = json.loads(
            (_step_dir(expanded, step_number) / "proposal.json").read_text(
                encoding="utf-8"
            )
        )
        if proposal.get("proposal_status") == "CANDIDATE" and not (
            _step_dir(expanded, step_number) / "evolution_summary.json"
        ).is_file():
            if set(started) == FROZEN_CANDIDATE_SELECTION_ARTIFACTS:
                stopped = True
                next_step = step_number
                continue
            raise RuntimeContractError(
                f"Step {step_number} produced a Candidate but no "
                "evolution_summary.json and is not at the supported frozen "
                "Candidate Selection boundary."
            )
        step_record, current_parent, current_checkpoint = _replay_completed_step(
            expanded,
            controller_campaign,
            batch_map,
            step_number,
            current_parent,
            current_checkpoint,
            usage,
            selection_tasks,
        )
        completed_steps.append(step_record)

    if next_step != len(completed_steps) + 1:
        raise RuntimeContractError(
            "Recovered Step prefix is inconsistent with the next Step."
        )
    return {
        "current_parent": current_parent,
        "current_checkpoint": current_checkpoint,
        "completed_steps": completed_steps,
        "budget_usage": usage,
        "next_step": next_step,
        "last_completed_step": len(completed_steps),
    }


def _write_controller_state(campaign: dict[str, Any], state: dict[str, Any]) -> None:
    """Persist the resume state after a *complete* Step (the on_step_completed
    callback). Never called mid-Step, so the file always describes a clean
    Step boundary."""

    payload = {
        "schema_version": RESUME_STATE_SCHEMA,
        "campaign_id": campaign["campaign_id"],
        "campaign_seed": campaign["campaign_seed"],
        "last_completed_step": state["last_completed_step"],
        "next_step": state["next_step"],
        "completed_steps": state["completed_steps"],
        "current_parent": state["current_parent"],
        "current_checkpoint": state["current_checkpoint"],
        "budget_usage": state["budget_usage"],
    }
    _write_json_atomic(_campaign_paths(campaign)["controller_state"], payload)


def _reconcile_controller_state_with_artifacts(
    persisted: dict[str, Any], recovered: dict[str, Any]
) -> tuple[dict[str, Any], bool]:
    """Prefer a safely advanced frozen-artifact prefix over stale state.

    ``controller_state.json`` is written only after a complete Step. A crash
    between freezing ``evolution_summary.json`` and that atomic write can leave
    it exactly one or more complete Steps behind. Pure artifact replay may
    advance it, but may never move it backwards or disagree with its completed
    prefix. The boolean reports whether the caller should persist the advance.
    """

    persisted_next = persisted["next_step"]
    recovered_next = recovered["next_step"]
    if recovered_next < persisted_next:
        raise RuntimeContractError(
            "Frozen artifacts are behind the persisted controller state."
        )
    persisted_steps = persisted["completed_steps"]
    if recovered["completed_steps"][: len(persisted_steps)] != persisted_steps:
        raise RuntimeContractError(
            "Frozen artifacts disagree with the persisted completed-Step prefix."
        )
    if recovered_next == persisted_next:
        for field in (
            "completed_steps",
            "current_parent",
            "current_checkpoint",
            "budget_usage",
        ):
            if recovered[field] != persisted[field]:
                raise RuntimeContractError(
                    f"Frozen artifacts disagree with persisted {field}."
                )
        return persisted, False
    return recovered, True


def _load_controller_state(campaign: dict[str, Any], path: Path) -> dict[str, Any]:
    """Validate and load a persisted ``controller_state.json`` into a resume
    state. Fails closed on schema / campaign / seed / prefix drift."""

    payload = json.loads(path.read_text(encoding="utf-8"))
    completed_steps = payload.get("completed_steps")
    next_step = payload.get("next_step")
    current_parent = payload.get("current_parent")
    current_checkpoint = payload.get("current_checkpoint")
    if (
        payload.get("schema_version") != RESUME_STATE_SCHEMA
        or payload.get("campaign_id") != campaign["campaign_id"]
        or payload.get("campaign_seed") != campaign["campaign_seed"]
    ):
        raise RuntimeContractError("Persisted controller_state contract drifted.")
    if not isinstance(completed_steps, list) or not isinstance(current_parent, dict) or (
        not isinstance(current_checkpoint, dict)
    ):
        raise RuntimeContractError("Persisted controller_state payload is invalid.")
    for index, record in enumerate(completed_steps, start=1):
        if not isinstance(record, dict) or record.get("step") != index:
            raise RuntimeContractError(
                "Persisted completed_steps is not a contiguous prefix from Step 1."
            )
    if not isinstance(next_step, int) or isinstance(next_step, bool) or (
        next_step != len(completed_steps) + 1
    ):
        raise RuntimeContractError(
            "Persisted next_step must follow the completed Step prefix."
        )
    if current_checkpoint.get("version") != current_parent.get("version"):
        raise RuntimeContractError(
            "Persisted checkpoint version must match the current Parent."
        )
    return {
        "current_parent": copy.deepcopy(current_parent),
        "current_checkpoint": copy.deepcopy(current_checkpoint),
        "completed_steps": copy.deepcopy(completed_steps),
        "budget_usage": copy.deepcopy(payload["budget_usage"]),
        "next_step": next_step,
    }


def run_initial_checkpoint(campaign_path: Path) -> dict[str, Any]:
    campaign = _expand_campaign(
        json.loads(campaign_path.resolve().read_text(encoding="utf-8"))
    )
    validate_formal_campaign_contract(campaign, require_ready=True)
    paths = _campaign_paths(campaign)
    if paths["checkpoint"].exists():
        raise RuntimeContractError("Initial checkpoint already exists.")
    adapter = FormalBenchmarkRuntimeAdapter(
        campaign,
        rollout_backend=MultiRolloutRunnerBackend(campaign),
        learner=None,
    )
    checkpoint = adapter.run_fresh_initial_checkpoint()
    return {"status": "S0_CHECKPOINT_CREATED", "checkpoint": checkpoint}


def _execute_and_write_report(
    campaign: dict[str, Any],
    paths: dict[str, Path],
    *,
    resume_state: dict[str, Any] | None = None,
    on_step_completed: Callable[[dict[str, Any]], None] | None = None,
    resumed: bool = False,
    adapter: FormalBenchmarkRuntimeAdapter | None = None,
) -> dict[str, Any]:
    """Run the (fresh or resumed) campaign and write the formal report.

    The rollout multiplication, budget check, and disabled-phase markers are
    identical for a fresh and a resumed run, so a resumed report is byte-for-byte
    the report an uninterrupted run would have produced (plus a ``resumed`` flag).
    """

    batch_map = json.loads(
        _resolve_repo_path(campaign["train"]["batch_map"]).read_text(
            encoding="utf-8"
        )
    )
    if adapter is None:
        adapter = FormalBenchmarkRuntimeAdapter(
            campaign,
            rollout_backend=MultiRolloutRunnerBackend(campaign),
            learner=SeededLearnerAdapter(campaign),
        )
    report = run_v06_campaign(
        campaign,
        batch_map,
        adapter,
        resume_state=resume_state,
        on_step_completed=on_step_completed,
    )
    report["schema_version"] = "autonomous_gse_formal_report_0.6.0"
    report["campaign_seed"] = campaign["campaign_seed"]
    report["schedule"] = copy.deepcopy(campaign["schedule"])
    report["batch_schedule"] = copy.deepcopy(campaign["batch_schedule"])
    report["runtime"] = copy.deepcopy(campaign["runtime"])
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
        raise RuntimeContractError("v0.6 rollout budget was exceeded.")
    report["disabled_phases"] = {
        "post_hoc_training_replay": True,
        "final_test_evaluation": True,
        "full_seed_replicas": True,
    }
    if resumed:
        report["resumed"] = True
    v05._write_json(paths["report"], report)
    return {
        "status": "AUTONOMOUS_GSE_V06_CAMPAIGN_COMPLETED",
        "report": v05._artifact(
            "campaign_report", campaign["campaign_id"], paths["report"]
        ),
        "step_outcomes": [step["outcome"] for step in report["steps"]],
        "final_parent": report["final_parent"],
    }


def run_formal_campaign_cli(campaign_path: Path) -> dict[str, Any]:
    from dotenv import load_dotenv

    load_dotenv(REPO_ROOT / "external/ST-WebAgentBench/.env", override=False)
    campaign = _expand_campaign(
        json.loads(campaign_path.resolve().read_text(encoding="utf-8"))
    )
    validate_formal_campaign_contract(campaign, require_ready=True)
    paths = _campaign_paths(campaign)
    if not paths["checkpoint"].is_file():
        raise RuntimeContractError("Initial S0 checkpoint is missing.")
    if paths["report"].exists():
        raise RuntimeContractError("Campaign report already exists.")
    if _formal_steps_started(campaign):
        raise RuntimeContractError(
            "Formal Step artifacts already exist. A fresh run would redo "
            "completed Steps; use the resume command instead of run."
        )
    return _execute_and_write_report(
        campaign,
        paths,
        on_step_completed=lambda state: _write_controller_state(campaign, state),
    )


def run_resume_cli(campaign_path: Path) -> dict[str, Any]:
    """Conservative frozen-boundary fault recovery for an interrupted campaign.

    In addition to a clean Step boundary, resume accepts a Candidate whose
    Train/Learner/Proposal artifacts are fully frozen and continues only its
    Selection. A stale controller state may also advance through complete frozen
    summaries by pure reducer replay. Every other partial shape fails closed.
    Rollout backends still receive the full workload; their unchanged validated-
    trajectory skip executes only missing units.
    """

    from dotenv import load_dotenv

    load_dotenv(REPO_ROOT / "external/ST-WebAgentBench/.env", override=False)
    campaign = _expand_campaign(
        json.loads(campaign_path.resolve().read_text(encoding="utf-8"))
    )
    validate_formal_campaign_contract(campaign, require_ready=True)
    paths = _campaign_paths(campaign)
    if not paths["checkpoint"].is_file():
        raise RuntimeContractError("Initial S0 checkpoint is missing.")
    if paths["report"].exists():
        raise RuntimeContractError(
            "Campaign report already exists; the campaign is complete."
        )
    if not _formal_steps_started(campaign):
        raise RuntimeContractError(
            "No formal Step artifacts exist; use run, not resume."
        )
    if paths["controller_state"].is_file():
        persisted_state = _load_controller_state(
            campaign, paths["controller_state"]
        )
        recovered_state = recover_controller_state_from_artifacts(campaign)
        resume_state, advanced = _reconcile_controller_state_with_artifacts(
            persisted_state, recovered_state
        )
        if advanced:
            _write_controller_state(campaign, resume_state)
    else:
        resume_state = recover_controller_state_from_artifacts(campaign)
        _write_controller_state(
            campaign,
            {
                "last_completed_step": resume_state["next_step"] - 1,
                "next_step": resume_state["next_step"],
                "completed_steps": resume_state["completed_steps"],
                "current_parent": resume_state["current_parent"],
                "current_checkpoint": resume_state["current_checkpoint"],
                "budget_usage": resume_state["budget_usage"],
            },
        )
    adapter = FormalBenchmarkRuntimeAdapter(
        campaign,
        rollout_backend=MultiRolloutRunnerBackend(campaign),
        learner=SeededLearnerAdapter(campaign),
    )
    present = set(
        _controller_artifacts_in(_step_dir(campaign, resume_state["next_step"]))
    )
    if present:
        if present != FROZEN_CANDIDATE_SELECTION_ARTIFACTS:
            _require_clean_next_step(campaign, resume_state["next_step"])
        resume_state = _complete_frozen_candidate_selection(
            campaign, resume_state, adapter
        )
        _write_controller_state(campaign, resume_state)
    else:
        _require_clean_next_step(campaign, resume_state["next_step"])
    return _execute_and_write_report(
        campaign,
        paths,
        resume_state=resume_state,
        on_step_completed=lambda state: _write_controller_state(campaign, state),
        resumed=True,
        adapter=adapter,
    )


def main(argv: Sequence[str] | None = None) -> int:
    import argparse

    default_campaign = REPO_ROOT / (
        "experiments/campaigns/autonomous_gse_v06/campaign_manifest.json"
    )
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command", choices=("plan", "initial-checkpoint", "run", "resume")
    )
    parser.add_argument("--campaign", type=Path, default=default_campaign)
    args = parser.parse_args(argv)
    if args.command == "initial-checkpoint":
        result = run_initial_checkpoint(args.campaign)
        print(json.dumps(result, indent=2))
        return 0
    if args.command == "run":
        result = run_formal_campaign_cli(args.campaign)
        print(json.dumps(result, indent=2))
        return 0
    if args.command == "resume":
        result = run_resume_cli(args.campaign)
        print(json.dumps(result, indent=2))
        return 0
    campaign = _expand_campaign(
        json.loads(args.campaign.resolve().read_text(encoding="utf-8"))
    )
    batch_map = json.loads(
        _resolve_repo_path(campaign["train"]["batch_map"]).read_text(
            encoding="utf-8"
        )
    )
    print(json.dumps(build_formal_execution_plan(campaign, batch_map), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

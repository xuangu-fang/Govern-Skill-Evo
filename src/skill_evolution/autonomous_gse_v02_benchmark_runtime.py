"""Formal ST-WebAgentBench runtime and CLI for Autonomous GSE v0.2.

Importing this module is side-effect free. ``plan`` and ``status`` only read
local files; ``initial-checkpoint`` and ``run`` are the explicit execution
boundaries for benchmark, database, Learner, and artifact writes.
"""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Sequence

from src.skill_evolution.autonomous_gse_v02_controller import register_step
from src.skill_evolution.autonomous_gse_v02_proposal import LearnerRequest
from src.skill_evolution.autonomous_gse_v02_runtime import (
    RuntimeContractError,
    run_campaign,
)
from src.skill_evolution.governed_experience import build_experience
from src.skill_evolution.two_dimensional_gate import analyze_candidate


REPO_ROOT = Path(__file__).resolve().parents[2]
FORMAL_MODE = "formal_stwebagentbench_v02"
CAMPAIGN_REPORT_FILENAME = "campaign_report.json"
ELIGIBLE_EVIDENCE_STATES = {"compliant_success", "violating_success"}
OUTCOME_STATES = (
    "violating_failure",
    "violating_success",
    "compliant_failure",
    "compliant_success",
)


def _json_bytes(payload: dict[str, Any]) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode()


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


def _write_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    _write_bytes(path, _json_bytes(payload))


def validate_formal_campaign_contract(
    campaign: dict[str, Any], *, require_ready: bool = False
) -> None:
    """Validate the v0.2 settings needed by the formal runtime."""

    if campaign.get("protocol_version") != "autonomous_gse_v02":
        raise RuntimeContractError("Unsupported formal Campaign protocol.")
    if campaign.get("status") not in {"draft", "ready"}:
        raise RuntimeContractError("Campaign status must be draft or ready.")
    if require_ready and campaign.get("status") != "ready":
        raise RuntimeContractError("Campaign status must be ready before execution.")
    if campaign.get("test") != {
        "authorized": False,
        "data_for_learning": "forbidden",
    }:
        raise RuntimeContractError("Test must remain sealed.")

    proposal = campaign.get("proposal", {})
    learner = proposal.get("learner", {})
    if (
        proposal.get("operator") != "bounded_edit"
        or proposal.get("maximum_edits_per_step") != 6
        or proposal.get("candidates_per_step") != 1
        or learner.get("model") != "openai/gpt-5.6-terra"
        or learner.get("parameters")
        != {
            "reasoning_effort": "low",
            "max_completion_tokens": 8000,
            "temperature": None,
        }
        or learner.get("prompt")
        != "src/learners/stwebagentbench/generate_bounded_skill_v02.py"
    ):
        raise RuntimeContractError("Bounded Learner configuration is invalid.")

    runtime = campaign.get("benchmark_runtime", {})
    if runtime.get("agent_model") != "openai/gpt-5.6-terra" or runtime.get(
        "agent_parameters"
    ) != {"temperature": 0.1, "max_tokens": 512}:
        raise RuntimeContractError("Benchmark Agent configuration is invalid.")
    if runtime.get("rollout") != {
        "headless": False,
        "trials_per_task": 1,
        "execution": "sequential",
        "database_reset_before_every_trial": True,
    }:
        raise RuntimeContractError("Benchmark rollout configuration is invalid.")


LearnerCaller = Callable[[str, str, str], tuple[str, str, dict | None]]


class LearnerAdapter:
    """Call the single v0.2 bounded-edit prompt through an injected caller."""

    def __init__(
        self,
        campaign: dict[str, Any],
        *,
        caller: LearnerCaller | None = None,
    ) -> None:
        validate_formal_campaign_contract(campaign)
        if caller is None:
            from src.learners.stwebagentbench.generate_skill import call_learner

            caller = call_learner
        self._contract = copy.deepcopy(campaign["proposal"]["learner"])
        self._caller = caller
        self.last_call: dict[str, Any] | None = None
        self.last_response: str | None = None

    def call(
        self,
        request: LearnerRequest,
        model: str,
        system_prompt: str,
        user_prompt: str,
    ) -> tuple[str, str, dict | None]:
        if model != self._contract["model"]:
            raise RuntimeContractError("Learner model drifted from the Manifest.")
        response, resolved_model, usage = self._caller(
            model, system_prompt, user_prompt
        )
        if resolved_model != "gpt-5.6-terra":
            raise RuntimeContractError("Learner resolved model is unexpected.")
        if not isinstance(response, str) or not response.strip():
            raise RuntimeContractError("Learner returned an empty response.")
        self.last_response = response.strip()
        self.last_call = {
            "candidate_id": request.candidate_id,
            "model": model,
            "parameters": copy.deepcopy(self._contract["parameters"]),
            "evidence_count": len(request.current_batch_success_evidence),
            "allowed_source_ids": list(request.allowed_source_ids),
            "allowed_repair_policy_ids_by_source": {
                source_id: list(policy_ids)
                for source_id, policy_ids in (
                    request.allowed_repair_policy_ids_by_source.items()
                )
            },
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "usage": usage,
        }
        return self.last_response, resolved_model, usage


@dataclass(frozen=True)
class RolloutRequest:
    split: str
    method: str
    artifact: dict[str, Any]
    task_ids: tuple[int, ...]


RolloutBackend = Callable[[RolloutRequest], Sequence[Path]]


def _run_train_task(
    args: SimpleNamespace,
    manifest: dict[str, Any],
    method: str,
    skill: dict[str, Any],
    task: dict[str, Any],
) -> Path:
    from src.adapters.stwebagentbench.run_evolution_train import (
        get_output_dir,
        run_task,
    )

    run_task(args, manifest, method, skill, task)
    return get_output_dir(manifest, method, task["task_id"], True) / "trajectory.json"


def _run_selection_task(
    args: SimpleNamespace,
    manifest: dict[str, Any],
    method: str,
    skill: dict[str, Any],
    task: dict[str, Any],
) -> Path:
    from src.adapters.stwebagentbench.run_evolution_selection import (
        get_output_dir,
        run_task,
    )

    run_task(args, manifest, task, skill)
    return get_output_dir(manifest, method, task["task_id"], True) / "trajectory.json"


class RunnerRolloutBackend:
    """Route formal requests to the existing ST-WebAgentBench runners."""

    def __init__(self, campaign: dict[str, Any]) -> None:
        validate_formal_campaign_contract(campaign, require_ready=True)
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
        self._manifest = {
            "manifest_id": campaign["campaign_id"],
            "benchmark": {"commit": source["benchmark"]["commit"]},
        }
        runtime = campaign["benchmark_runtime"]
        self._model = runtime["agent_model"]
        self._headless = runtime["rollout"]["headless"]

    @staticmethod
    def _load_skill(artifact: dict[str, Any]) -> dict[str, Any]:
        path = _resolve_repo_path(artifact["path"])
        if not path.is_file():
            raise RuntimeContractError(f"Skill artifact is missing: {path}")
        text = path.read_text(encoding="utf-8").strip()
        if not text:
            raise RuntimeContractError("Skill artifact is empty.")
        if artifact["kind"] == "empty_skill" and artifact["version"] == "S0":
            block = None
        elif artifact["kind"] in {"accepted_skill", "candidate_skill"}:
            block = f"# Operational Skill\n{text}"
        else:
            raise RuntimeContractError("Unknown rollout artifact kind.")
        return {
            "version": artifact["version"],
            "path": artifact["path"],
            "block": block,
        }

    def __call__(self, request: RolloutRequest) -> Sequence[Path]:
        tasks = self._tasks.get(request.split)
        if tasks is None:
            raise RuntimeContractError("Only Train and Selection are runnable.")
        missing = [task_id for task_id in request.task_ids if task_id not in tasks]
        if missing:
            raise RuntimeContractError(
                f"Unknown {request.split} Task IDs: {missing}"
            )
        skill = self._load_skill(request.artifact)
        args = SimpleNamespace(
            formal=True,
            headless=self._headless,
            model=self._model,
            method=request.method,
        )
        runner = _run_train_task if request.split == "train" else _run_selection_task
        return tuple(
            runner(args, self._manifest, request.method, skill, tasks[task_id])
            for task_id in request.task_ids
        )


def _step_path(campaign: dict[str, Any], step: int, name: str) -> Path:
    return (
        REPO_ROOT
        / "artifacts"
        / campaign["campaign_id"]
        / "formal"
        / "steps"
        / f"step_{step:03d}"
        / name
    )


def _split_task_ids(campaign: dict[str, Any], split: str) -> tuple[int, ...]:
    source = json.loads(
        _resolve_repo_path(campaign["train"]["source_manifest"]).read_text(
            encoding="utf-8"
        )
    )
    return tuple(
        task_id
        for template in source["splits"][split]["templates"]
        for task_id in template["task_ids"]
    )


def _load_valid_trajectory(
    path: Path,
    task_id: int,
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
    ):
        raise RuntimeContractError(f"Formal trajectory lineage mismatch: {path}")
    outcome = trajectory.get("outcome", {})
    if not isinstance(outcome.get("task_success"), bool) or not isinstance(
        outcome.get("violated_policy_count"), int
    ):
        raise RuntimeContractError(f"Formal trajectory verdict is invalid: {path}")
    return trajectory


class FormalBenchmarkRuntimeAdapter:
    """Implement the shared v0.2 runtime ports with benchmark side effects."""

    mode = FORMAL_MODE

    def __init__(
        self,
        campaign: dict[str, Any],
        *,
        rollout_backend: RolloutBackend,
        learner: LearnerAdapter | None,
    ) -> None:
        validate_formal_campaign_contract(campaign, require_ready=True)
        self._campaign = copy.deepcopy(campaign)
        self._rollout = rollout_backend
        self._learner = learner
        self._trace: list[dict[str, Any]] = []
        self._side_effects = {
            "api_calls": 0,
            "browser_calls": 0,
            "database_calls": 0,
            "filesystem_writes": 0,
        }
        self._checkpoints: dict[str, dict[str, Any]] = {}
        self._summaries: dict[str, dict[str, Any]] = {}

    @property
    def trace(self) -> list[dict[str, Any]]:
        return copy.deepcopy(self._trace)

    @property
    def side_effects(self) -> dict[str, int]:
        return copy.deepcopy(self._side_effects)

    @staticmethod
    def _method(artifact: dict[str, Any]) -> str:
        if artifact["kind"] == "empty_skill":
            return "s0_empty_skill"
        path = Path(artifact["path"])
        return path.parent.name or artifact["version"].lower()

    def _run(
        self, split: str, artifact: dict[str, Any], task_ids: Sequence[int]
    ) -> tuple[Path, ...]:
        paths = tuple(
            self._rollout(
                RolloutRequest(
                    split=split,
                    method=self._method(artifact),
                    artifact=copy.deepcopy(artifact),
                    task_ids=tuple(task_ids),
                )
            )
        )
        if len(paths) != len(task_ids):
            raise RuntimeContractError("Rollout backend returned wrong count.")
        self._side_effects["browser_calls"] += len(task_ids)
        self._side_effects["database_calls"] += len(task_ids)
        self._side_effects["filesystem_writes"] += len(task_ids)
        return paths

    def _checkpoint(
        self, artifact: dict[str, Any], task_ids: Sequence[int]
    ) -> dict[str, Any]:
        paths = self._run("selection", artifact, task_ids)
        rows = []
        sources = []
        for task_id, path in zip(task_ids, paths, strict=True):
            trajectory = _load_valid_trajectory(path, task_id, "selection", artifact)
            outcome = trajectory["outcome"]
            rows.append(
                {
                    "task_id": task_id,
                    "task_success": outcome["task_success"],
                    "compliant": outcome["violated_policy_count"] == 0,
                }
            )
            sources.append(
                {"task_id": task_id, "path": path.relative_to(REPO_ROOT).as_posix()}
            )
        payload = {
            "schema_version": "autonomous_gse_selection_checkpoint_0.2.0",
            "campaign_id": self._campaign["campaign_id"],
            "parent": copy.deepcopy(artifact),
            "task_ids": list(task_ids),
            "rows": rows,
            "sources": sources,
        }
        path = (
            REPO_ROOT
            / "artifacts"
            / self._campaign["campaign_id"]
            / "formal"
            / "checkpoints"
            / f"{self._method(artifact)}.json"
        )
        _write_json(path, payload)
        self._side_effects["filesystem_writes"] += 1
        checkpoint = _artifact("selection_checkpoint", artifact["version"], path)
        self._checkpoints[checkpoint["path"]] = payload
        return checkpoint

    def run_fresh_initial_checkpoint(self) -> dict[str, Any]:
        checkpoint = self._checkpoint(
            self._campaign["initial_parent"],
            _split_task_ids(self._campaign, "selection"),
        )
        self._trace.append({"operation": "create_initial_checkpoint"})
        return checkpoint

    def create_initial_checkpoint(
        self, parent: dict[str, Any], task_count: int
    ) -> dict[str, Any]:
        if parent != self._campaign["initial_parent"] or task_count != 18:
            raise RuntimeContractError("Initial checkpoint contract is invalid.")
        path = _campaign_artifact_paths(self._campaign)["checkpoint"]
        payload = _validate_initial_checkpoint(self._campaign, path)
        checkpoint = _artifact("selection_checkpoint", "S0", path)
        self._checkpoints[checkpoint["path"]] = payload
        self._trace.append({"operation": "load_initial_checkpoint"})
        return checkpoint

    def run_train(self, step: dict[str, Any]) -> tuple[dict[str, Any], ...]:
        paths = self._run("train", step["parent"], step["batch"]["task_ids"])
        experiences = []
        sources = []
        state_counts = {state: 0 for state in OUTCOME_STATES}
        for index, (task_id, path) in enumerate(
            zip(step["batch"]["task_ids"], paths, strict=True), start=1
        ):
            trajectory = _load_valid_trajectory(path, task_id, "train", step["parent"])
            source_id = f"step_{step['step']:03d}_source_{index:03d}"
            experience = build_experience(trajectory, source_id)
            experiences.append(experience)
            state_counts[experience["state"]] += 1
            sources.append(
                {
                    "source_id": source_id,
                    "task_id": task_id,
                    "path": path.relative_to(REPO_ROOT).as_posix(),
                }
            )
        train_payload = {
            "step": step["step"],
            "batch_id": step["batch"]["batch_id"],
            "parent": copy.deepcopy(step["parent"]),
            "task_ids": list(step["batch"]["task_ids"]),
            "sources": copy.deepcopy(sources),
        }
        experience_payload = {
            "schema_version": "governed_experience_0.2.0",
            "experience_count": len(experiences),
            "state_counts": state_counts,
            "sources": sources,
            "experiences": experiences,
            "lineage": {
                "batch_id": step["batch"]["batch_id"],
                "parent_version": step["parent"]["version"],
                "task_ids": list(step["batch"]["task_ids"]),
            },
        }
        _write_json(_step_path(self._campaign, step["step"], "train_set.json"), train_payload)
        _write_json(
            _step_path(self._campaign, step["step"], "governed_experience.json"),
            experience_payload,
        )
        self._side_effects["filesystem_writes"] += 2
        self._trace.append({"operation": "run_train", "step": step["step"]})
        return tuple(
            experience
            for experience in experiences
            if experience["state"] in ELIGIBLE_EVIDENCE_STATES
        )

    def skill_for_parent(self, parent: dict[str, Any]) -> str:
        path = _resolve_repo_path(parent["path"])
        text = path.read_text(encoding="utf-8")
        if not text.strip():
            raise RuntimeContractError("Parent Skill is empty.")
        return text

    def learner_call(
        self,
        step: dict[str, Any],
        request: LearnerRequest,
        model: str,
        system_prompt: str,
        user_prompt: str,
    ) -> tuple[str, str, dict | None]:
        if self._learner is None:
            raise RuntimeContractError("Learner is unavailable for a formal run.")
        response = self._learner.call(
            request, model, system_prompt, user_prompt
        )
        if self._learner.last_call is None or self._learner.last_response is None:
            raise RuntimeContractError("Learner call audit is incomplete.")
        _write_json(
            _step_path(self._campaign, step["step"], "learner_call.json"),
            self._learner.last_call,
        )
        _write_bytes(
            _step_path(self._campaign, step["step"], "learner_response.txt"),
            (self._learner.last_response + "\n").encode(),
        )
        self._side_effects["api_calls"] += 1
        self._side_effects["filesystem_writes"] += 2
        return response

    def record_candidate(
        self, step: dict[str, Any], candidate_skill: str
    ) -> dict[str, Any]:
        path = (
            REPO_ROOT
            / "artifacts"
            / self._campaign["campaign_id"]
            / "formal"
            / "candidates"
            / step["candidate_id"]
            / "skill.md"
        )
        _write_bytes(path, candidate_skill.encode())
        self._side_effects["filesystem_writes"] += 1
        return _artifact("candidate_skill", step["candidate_id"], path)

    def record_proposal(
        self,
        step: dict[str, Any],
        decision: Any,
        candidate: dict[str, Any] | None,
    ) -> None:
        payload = {
            "schema_version": "autonomous_gse_proposal_record_0.2.0",
            "step": step["step"],
            "candidate": copy.deepcopy(candidate),
            "proposal_status": decision.proposal_status,
            "proposal_reason": copy.deepcopy(decision.proposal_reason),
            "proposed_edits": copy.deepcopy(decision.proposed_edits),
            "selected_edits": copy.deepcopy(decision.selected_edits),
            "excluded_edits": copy.deepcopy(decision.excluded_edits),
            "provenance_status": decision.provenance_status,
            "provenance_audit": copy.deepcopy(decision.provenance_audit),
        }
        _write_json(_step_path(self._campaign, step["step"], "proposal.json"), payload)
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
        return self._checkpoint(promoted, _split_task_ids(self._campaign, "selection"))

    def validate_candidate_selection(
        self, step: dict[str, Any], checkpoint: dict[str, Any]
    ) -> None:
        del step
        if checkpoint["path"] not in self._checkpoints:
            raise RuntimeContractError("Candidate checkpoint is unavailable.")

    def build_evolution_summary(
        self, step: dict[str, Any], candidate_checkpoint: dict[str, Any]
    ) -> dict[str, Any]:
        parent = self._checkpoints.get(step["parent_checkpoint"]["path"])
        candidate = self._checkpoints.get(candidate_checkpoint["path"])
        if parent is None or candidate is None:
            raise RuntimeContractError("Selection checkpoint lineage is missing.")
        rows = [{**row, "method": "parent"} for row in parent["rows"]]
        rows += [{**row, "method": "candidate"} for row in candidate["rows"]]
        payload = {
            "schema_version": "autonomous_gse_evolution_summary_0.2.0",
            "step": step["step"],
            "parent_checkpoint": copy.deepcopy(step["parent_checkpoint"]),
            "candidate_checkpoint": copy.deepcopy(candidate_checkpoint),
            "analysis": analyze_candidate(rows, "parent", "candidate"),
        }
        path = _step_path(self._campaign, step["step"], "evolution_summary.json")
        _write_json(path, payload)
        self._side_effects["filesystem_writes"] += 1
        summary = _artifact("evolution_summary", f"step_{step['step']:03d}", path)
        self._summaries[summary["path"]] = payload
        return summary

    def apply_gate(self, step: dict[str, Any], summary: dict[str, Any]) -> str:
        del step
        payload = self._summaries.get(summary["path"])
        if payload is None:
            raise RuntimeContractError("Evolution summary is unavailable.")
        decision = payload["analysis"]["evolution_gate"]["decision"]
        mapping = {"continue_evolution": "ACCEPT", "reject": "REJECT"}
        if decision not in mapping:
            raise RuntimeContractError("Evolution Gate decision is unsupported.")
        return mapping[decision]


def build_formal_execution_plan(
    campaign: dict[str, Any], batch_map: dict[str, Any]
) -> dict[str, Any]:
    """Build the exact workload preview without running any Task."""

    validate_formal_campaign_contract(campaign)
    check_campaign = copy.deepcopy(campaign)
    check_campaign["status"] = "ready"
    checkpoint = {
        "kind": "selection_checkpoint",
        "version": "S0",
        "path": "plan://s0-selection",
    }
    steps = []
    for number in range(1, 4):
        registered = register_step(
            check_campaign,
            batch_map,
            step=number,
            parent=check_campaign["initial_parent"],
            parent_checkpoint=checkpoint,
        )
        steps.append(
            {
                "step": number,
                "batch_id": registered["batch"]["batch_id"],
                "train_task_ids": registered["batch"]["task_ids"],
                "candidate_selection_task_ids": list(
                    _split_task_ids(campaign, "selection")
                ),
                "maximum_edits": registered["edit_budget"][
                    "maximum_edits_per_step"
                ],
                "maximum_learner_calls": 1,
            }
        )
    return {
        "schema_version": "autonomous_gse_formal_plan_0.2.0",
        "campaign_id": campaign["campaign_id"],
        "campaign_status": campaign["status"],
        "mode": "no_side_effect_formal_plan",
        "initial_selection_task_ids": list(_split_task_ids(campaign, "selection")),
        "steps": steps,
        "maximum_budget": copy.deepcopy(campaign["budget"]),
        "test_authorized": False,
    }


def run_formal_campaign(
    campaign: dict[str, Any],
    batch_map: dict[str, Any],
    adapter: FormalBenchmarkRuntimeAdapter,
) -> dict[str, Any]:
    validate_formal_campaign_contract(campaign, require_ready=True)
    report = run_campaign(campaign, batch_map, adapter)
    if report["mode"] != FORMAL_MODE:
        raise RuntimeContractError("Formal runtime adapter mode is invalid.")
    if report["budget_usage"]["total_trajectories"] > 123:
        raise RuntimeContractError("Formal runtime exceeded rollout budget.")
    report["schema_version"] = "autonomous_gse_formal_report_0.2.0"
    return report


def _campaign_artifact_paths(campaign: dict[str, Any]) -> dict[str, Path]:
    root = REPO_ROOT / "artifacts" / campaign["campaign_id"]
    return {
        "artifact_root": root,
        "raw_root": root / "raw",
        "s0_raw_root": root / "raw/selection/s0_empty_skill",
        "formal_root": root / "formal",
        "checkpoint": root / "formal/checkpoints/s0_empty_skill.json",
        "report": root / "formal" / CAMPAIGN_REPORT_FILENAME,
    }


def _validate_initial_checkpoint(
    campaign: dict[str, Any], checkpoint_path: Path
) -> dict[str, Any]:
    if not checkpoint_path.is_file():
        raise RuntimeContractError("Initial S0 checkpoint is missing.")
    checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    task_ids = list(_split_task_ids(campaign, "selection"))
    parent = checkpoint.get("parent", {})
    expected_parent = campaign["initial_parent"]
    if (
        checkpoint.get("schema_version")
        != "autonomous_gse_selection_checkpoint_0.2.0"
        or checkpoint.get("campaign_id") != campaign["campaign_id"]
        or any(parent.get(key) != expected_parent[key] for key in ("kind", "version", "path"))
        or checkpoint.get("task_ids") != task_ids
        or len(checkpoint.get("rows", [])) != len(task_ids)
        or len(checkpoint.get("sources", [])) != len(task_ids)
    ):
        raise RuntimeContractError("Initial S0 checkpoint contract is invalid.")
    for source in checkpoint["sources"]:
        _load_valid_trajectory(
            _resolve_repo_path(source["path"]),
            source["task_id"],
            "selection",
            expected_parent,
        )
    return checkpoint


def get_campaign_status(campaign_path: Path) -> dict[str, Any]:
    """Inspect artifact progress without starting or resuming work."""

    campaign = json.loads(campaign_path.resolve().read_text(encoding="utf-8"))
    validate_formal_campaign_contract(campaign)
    paths = _campaign_artifact_paths(campaign)
    s0_trajectories = sorted(paths["s0_raw_root"].rglob("trajectory.json"))
    all_trajectories = sorted(paths["raw_root"].rglob("trajectory.json"))
    failures = sorted(paths["artifact_root"].rglob("failure_*.json"))
    checkpoint_exists = paths["checkpoint"].is_file()
    report_exists = paths["report"].is_file()
    formal_files = {
        path.resolve()
        for path in paths["formal_root"].rglob("*")
        if path.is_file()
    }
    initial_files = {paths["checkpoint"].resolve()} if checkpoint_exists else set()
    report_files = {paths["report"].resolve()} if report_exists else set()
    step_files = formal_files - initial_files - report_files
    details = {
        "s0_selection_trajectories": len(s0_trajectories),
        "other_trajectories": len(all_trajectories) - len(s0_trajectories),
        "failure_records": len(failures),
        "initial_checkpoint": checkpoint_exists,
        "step_artifacts": len(step_files),
        "campaign_report": report_exists,
    }
    state = "NOT_STARTED"
    error = None
    try:
        if checkpoint_exists:
            _validate_initial_checkpoint(campaign, paths["checkpoint"])
        if report_exists:
            report = json.loads(paths["report"].read_text(encoding="utf-8"))
            if (
                report.get("schema_version") != "autonomous_gse_formal_report_0.2.0"
                or report.get("campaign_id") != campaign["campaign_id"]
                or report.get("status") != "COMPLETED"
                or len(report.get("steps", [])) != 3
            ):
                raise RuntimeContractError("Campaign report is invalid.")
    except (KeyError, OSError, ValueError, RuntimeContractError) as exc:
        state = "INVALID"
        error = str(exc)
    else:
        if campaign["status"] == "draft" and not all_trajectories and not formal_files:
            state = "DRAFT"
        elif failures:
            state = "RUNNING_OR_INTERRUPTED"
        elif report_exists:
            state = "COMPLETED"
        elif details["other_trajectories"] or step_files:
            state = "RUNNING_OR_INTERRUPTED"
        elif not checkpoint_exists and not s0_trajectories:
            state = "NOT_STARTED"
        elif not checkpoint_exists or len(s0_trajectories) != 18:
            state = "INITIAL_CHECKPOINT_INCOMPLETE"
        else:
            state = "READY_TO_RUN"
    result = {
        "schema_version": "autonomous_gse_status_0.2.0",
        "campaign_id": campaign["campaign_id"],
        "campaign_status": campaign["status"],
        "state": state,
        "details": details,
    }
    if error is not None:
        result["error"] = error
    return result


def run_initial_checkpoint(
    campaign_path: Path, *, rollout_backend: RolloutBackend | None = None
) -> dict[str, Any]:
    """Run only the fresh 18-Task explicit-empty-S0 Selection."""

    campaign_path = campaign_path.resolve()
    campaign = json.loads(campaign_path.read_text(encoding="utf-8"))
    validate_formal_campaign_contract(campaign, require_ready=True)
    status = get_campaign_status(campaign_path)
    if status["state"] != "NOT_STARTED":
        raise RuntimeContractError(
            "Initial checkpoint requires NOT_STARTED; "
            f"current state is {status['state']}."
        )
    adapter = FormalBenchmarkRuntimeAdapter(
        campaign,
        rollout_backend=rollout_backend or RunnerRolloutBackend(campaign),
        learner=None,
    )
    checkpoint = adapter.run_fresh_initial_checkpoint()
    return {
        "status": "S0_CHECKPOINT_CREATED",
        "checkpoint": checkpoint,
        "side_effects": adapter.side_effects,
        "trace": adapter.trace,
    }


def run_formal_campaign_cli(
    campaign_path: Path,
    *,
    rollout_backend: RolloutBackend | None = None,
    learner: LearnerAdapter | None = None,
) -> dict[str, Any]:
    """Execute all three Steps from an existing S0 checkpoint."""

    campaign_path = campaign_path.resolve()
    campaign = json.loads(campaign_path.read_text(encoding="utf-8"))
    validate_formal_campaign_contract(campaign, require_ready=True)
    status = get_campaign_status(campaign_path)
    if status["state"] != "READY_TO_RUN":
        raise RuntimeContractError(
            "Formal Campaign run requires READY_TO_RUN; "
            f"current state is {status['state']}."
        )
    if learner is None:
        from dotenv import load_dotenv

        load_dotenv(REPO_ROOT / "external/ST-WebAgentBench/.env", override=False)
        learner = LearnerAdapter(campaign)
    batch_map = json.loads(
        _resolve_repo_path(campaign["train"]["batch_map"]).read_text(
            encoding="utf-8"
        )
    )
    adapter = FormalBenchmarkRuntimeAdapter(
        campaign,
        rollout_backend=rollout_backend or RunnerRolloutBackend(campaign),
        learner=learner,
    )
    report = run_formal_campaign(campaign, batch_map, adapter)
    report_path = _campaign_artifact_paths(campaign)["report"]
    _write_json(report_path, report)
    return {
        "status": "AUTONOMOUS_GSE_V02_CAMPAIGN_COMPLETED",
        "report": _artifact("campaign_report", campaign["campaign_id"], report_path),
        "step_outcomes": [step["outcome"] for step in report["steps"]],
        "final_parent": copy.deepcopy(report["final_parent"]),
        "budget_usage": copy.deepcopy(report["budget_usage"]),
        "side_effects": copy.deepcopy(report["side_effects"]),
    }


def main(argv: Sequence[str] | None = None) -> int:
    import argparse

    default_campaign = (
        REPO_ROOT
        / "experiments/campaigns/autonomous_gse_v02/campaign_manifest.json"
    )
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("plan", "initial-checkpoint", "run", "status"):
        subparser = subparsers.add_parser(command)
        subparser.add_argument("--campaign", type=Path, default=default_campaign)
    args = parser.parse_args(argv)

    campaign_path = args.campaign.resolve()
    campaign = json.loads(campaign_path.read_text(encoding="utf-8"))
    if args.command == "status":
        result = get_campaign_status(campaign_path)
    elif args.command == "plan":
        batch_map = json.loads(
            _resolve_repo_path(campaign["train"]["batch_map"]).read_text(
                encoding="utf-8"
            )
        )
        result = build_formal_execution_plan(campaign, batch_map)
    elif args.command == "initial-checkpoint":
        result = run_initial_checkpoint(campaign_path)
    else:
        result = run_formal_campaign_cli(campaign_path)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""ST-WebAgentBench runtime boundary for Autonomous GSE v0.1.

The completed v0.1 experiment is represented by paths, versions, recorded
trajectories, and its campaign report. This module keeps the useful runtime
ports and semantic validation around that recorded experiment.

Importing the module has no side effects.  Formal work requires an explicitly
injected rollout backend and Learner caller.
"""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Sequence

from src.learners.stwebagentbench.generate_governed_s2 import (
    SYSTEM_PROMPT as INCREMENTAL_SYSTEM_PROMPT,
    USER_PROMPT as INCREMENTAL_USER_PROMPT,
)
from src.learners.stwebagentbench.generate_governed_skill import (
    SYSTEM_PROMPT as BOOTSTRAP_SYSTEM_PROMPT,
    USER_PROMPT_TEMPLATE as BOOTSTRAP_USER_PROMPT,
)
from src.learners.stwebagentbench.generate_skill import call_learner
from src.skill_evolution.autonomous_gse_proposal import (
    BootstrapProposalOperator,
    IncrementalProposalOperator,
    LearnerRequest,
    ProposalContext,
)
from src.skill_evolution.autonomous_gse_runtime import (
    ProposalRequest,
    ProposalResult,
    RuntimeContractError,
    run_campaign,
)
from src.skill_evolution.governed_experience import build_experience
from src.skill_evolution.two_dimensional_gate import analyze_candidate


REPO_ROOT = Path(__file__).resolve().parents[2]
FORMAL_MODE = "formal_stwebagentbench"
CAMPAIGN_REPORT_FILENAME = "campaign_report.json"
OUTCOME_STATES = (
    "violating_failure",
    "violating_success",
    "compliant_failure",
    "compliant_success",
)


def _canonical_json_bytes(payload: dict[str, Any]) -> bytes:
    return (
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")


def _resolve_repo_path(relative_path: str) -> Path:
    path = (REPO_ROOT / relative_path).resolve()
    path.relative_to(REPO_ROOT)
    return path


def _artifact(kind: str, version: str, path: Path) -> dict[str, str]:
    return {
        "kind": kind,
        "version": version,
        "path": path.relative_to(REPO_ROOT).as_posix(),
    }


def _write_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    _write_bytes(path, _canonical_json_bytes(payload))


def validate_formal_campaign_contract(campaign: dict[str, Any]) -> None:
    """Validate the small semantic contract needed by the runtime."""

    if campaign.get("protocol_version") != "autonomous_gse_v01":
        raise RuntimeContractError("Unsupported formal Campaign protocol.")
    if campaign.get("status") != "completed":
        raise RuntimeContractError("v0.1 must be a completed Campaign.")
    if campaign.get("test") != {
        "authorized": False,
        "data_for_learning": "forbidden",
    }:
        raise RuntimeContractError("Test must remain sealed.")

    learner = campaign.get("proposal", {}).get("learner", {})
    if learner.get("model") != "openai/gpt-5.6-terra" or learner.get(
        "parameters"
    ) != {
        "reasoning_effort": "low",
        "max_completion_tokens": 8000,
        "temperature": None,
    }:
        raise RuntimeContractError("Learner configuration is invalid.")
    if not all(
        isinstance(learner.get(key), str) and learner[key]
        for key in ("bootstrap_prompt", "incremental_prompt")
    ):
        raise RuntimeContractError("Proposal prompt sources are missing.")

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
    """Build one declared Proposal prompt and call an injected Learner."""

    def __init__(
        self,
        campaign: dict[str, Any],
        *,
        caller: LearnerCaller = call_learner,
    ) -> None:
        validate_formal_campaign_contract(campaign)
        self._contract = copy.deepcopy(campaign["proposal"]["learner"])
        self._caller = caller
        self.last_call: dict[str, Any] | None = None
        self.last_response: str | None = None

    def __call__(self, request: LearnerRequest) -> str:
        evidence = json.dumps(
            list(request.evidence), ensure_ascii=False, indent=2
        )
        if request.operator == "bootstrap":
            if request.parent_skill is not None:
                raise RuntimeContractError(
                    "Bootstrap Learner cannot receive a Parent Skill."
                )
            system_prompt = BOOTSTRAP_SYSTEM_PROMPT
            user_prompt = BOOTSTRAP_USER_PROMPT.format(evidence=evidence)
        elif request.operator == "incremental":
            if not isinstance(request.parent_skill, str):
                raise RuntimeContractError(
                    "Incremental Learner requires a Parent Skill."
                )
            system_prompt = INCREMENTAL_SYSTEM_PROMPT
            user_prompt = INCREMENTAL_USER_PROMPT.format(
                parent_skill=request.parent_skill,
                evidence=evidence,
            )
        else:
            raise RuntimeContractError("Unknown Proposal operator.")

        response, resolved_model, usage = self._caller(
            self._contract["model"], system_prompt, user_prompt
        )
        if resolved_model != "gpt-5.6-terra":
            raise RuntimeContractError("Learner resolved model is unexpected.")
        self.last_response = response
        self.last_call = {
            "candidate_id": request.candidate_id,
            "operator": request.operator,
            "model": self._contract["model"],
            "parameters": copy.deepcopy(self._contract["parameters"]),
            "evidence_count": len(request.evidence),
            "usage": usage,
        }
        return response


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
    return get_output_dir(
        manifest, method, task["task_id"], True
    ) / "trajectory.json"


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
    return get_output_dir(
        manifest, method, task["task_id"], True
    ) / "trajectory.json"


class RunnerRolloutBackend:
    """Connect formal Campaign requests to the current benchmark Runners."""

    def __init__(self, campaign: dict[str, Any]) -> None:
        validate_formal_campaign_contract(campaign)
        source = json.loads(
            _resolve_repo_path(campaign["train"]["source_manifest"])
            .read_text(encoding="utf-8")
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
        if artifact["kind"] == "no_skill":
            payload = json.loads(path.read_text(encoding="utf-8"))
            if (
                payload.get("kind") != "no_skill"
                or payload.get("skill_version") != artifact["version"]
            ):
                raise RuntimeContractError("S0 artifact semantics are invalid.")
            block = None
        elif artifact["kind"] in {"accepted_skill", "candidate_skill"}:
            text = path.read_text(encoding="utf-8").strip()
            if not text:
                raise RuntimeContractError("Skill artifact is empty.")
            block = f"# Operational Skill\n{text}"
        else:
            raise RuntimeContractError("Unknown rollout artifact kind.")
        return {
            "version": artifact["version"],
            "path": artifact["path"],
            "block": block,
        }

    def __call__(self, request: RolloutRequest) -> Sequence[Path]:
        if request.split not in self._tasks:
            raise RuntimeContractError("Only Train and Selection are runnable.")
        missing = [
            task_id
            for task_id in request.task_ids
            if task_id not in self._tasks[request.split]
        ]
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
        runner = (
            _run_train_task
            if request.split == "train"
            else _run_selection_task
        )
        return tuple(
            runner(
                args,
                self._manifest,
                request.method,
                skill,
                self._tasks[request.split][task_id],
            )
            for task_id in request.task_ids
        )


class FormalBenchmarkRuntimeAdapter:
    """Runtime adapter backed by injected ST-WebAgentBench rollouts."""

    mode = FORMAL_MODE

    def __init__(
        self,
        campaign: dict[str, Any],
        campaign_path: Path,
        *,
        rollout_backend: RolloutBackend,
        learner: LearnerAdapter,
    ) -> None:
        validate_formal_campaign_contract(campaign)
        self._campaign = copy.deepcopy(campaign)
        self._campaign_path = campaign_path.resolve()
        self._rollout = rollout_backend
        self._learner = learner
        self._trace: list[dict[str, Any]] = []
        self._side_effects = {
            "api_calls": 0,
            "browser_calls": 0,
            "database_calls": 0,
            "filesystem_writes": 0,
        }
        self._datasets: dict[str, dict[str, Any]] = {}
        self._train_paths: dict[int, tuple[Path, ...]] = {}
        self._checkpoints: dict[str, dict[str, Any]] = {}

    @property
    def trace(self) -> list[dict[str, Any]]:
        return copy.deepcopy(self._trace)

    @property
    def side_effects(self) -> dict[str, int]:
        return copy.deepcopy(self._side_effects)

    @staticmethod
    def _method(artifact: dict[str, Any]) -> str:
        if artifact["kind"] == "no_skill":
            return "s0_no_skill"
        path = Path(artifact["path"])
        if path.name == "skill.md" and path.parent.name:
            return path.parent.name
        return artifact["version"].lower().replace("-", "_")

    def _run(
        self,
        split: str,
        artifact: dict[str, Any],
        task_ids: Sequence[int],
    ) -> tuple[Path, ...]:
        request = RolloutRequest(
            split=split,
            method=self._method(artifact),
            artifact=copy.deepcopy(artifact),
            task_ids=tuple(task_ids),
        )
        paths = tuple(self._rollout(request))
        if len(paths) != len(task_ids):
            raise RuntimeContractError("Rollout backend returned wrong count.")
        self._side_effects["browser_calls"] += len(task_ids)
        self._side_effects["database_calls"] += len(task_ids)
        self._side_effects["filesystem_writes"] += len(task_ids)
        return paths

    def _checkpoint(
        self,
        artifact: dict[str, Any],
        task_ids: Sequence[int],
    ) -> dict[str, Any]:
        paths = self._run("selection", artifact, task_ids)
        rows = []
        sources = []
        for task_id, path in zip(task_ids, paths, strict=True):
            trajectory = _load_valid_trajectory(
                path, task_id, "selection", artifact
            )
            outcome = trajectory["outcome"]
            rows.append(
                {
                    "task_id": task_id,
                    "task_success": outcome["task_success"],
                    "compliant": outcome["violated_policy_count"] == 0,
                }
            )
            sources.append(
                {
                    "task_id": task_id,
                    "path": path.relative_to(REPO_ROOT).as_posix(),
                }
            )
        payload = {
            "schema_version": "autonomous_gse_selection_checkpoint_0.1.0",
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

    def create_initial_checkpoint(
        self,
        campaign_id: str,
        parent: dict[str, Any],
        task_count: int,
    ) -> dict[str, Any]:
        if campaign_id != self._campaign["campaign_id"] or task_count != 18:
            raise RuntimeContractError("Initial checkpoint contract is invalid.")
        checkpoint = self._checkpoint(
            parent, _split_task_ids(self._campaign, "selection")
        )
        self._trace.append({"operation": "create_initial_checkpoint"})
        return checkpoint

    def run_train(self, step: dict[str, Any]) -> dict[str, Any]:
        paths = self._run("train", step["parent"], step["batch"]["task_ids"])
        self._train_paths[step["step"]] = paths
        payload = {
            "step": step["step"],
            "batch_id": step["batch"]["batch_id"],
            "parent": copy.deepcopy(step["parent"]),
            "task_ids": list(step["batch"]["task_ids"]),
            "sources": [
                {"path": path.relative_to(REPO_ROOT).as_posix()}
                for path in paths
            ],
        }
        path = _step_path(self._campaign, step["step"], "train_set.json")
        _write_json(path, payload)
        self._side_effects["filesystem_writes"] += 1
        return _artifact(
            "train_trajectory_set", f"step_{step['step']:03d}", path
        )

    def validate_train(
        self,
        step: dict[str, Any],
        train_artifact: dict[str, Any],
    ) -> None:
        paths = self._train_paths.get(step["step"])
        if paths is None or not _resolve_repo_path(train_artifact["path"]).is_file():
            raise RuntimeContractError("Train trajectory set is unavailable.")
        for task_id, path in zip(step["batch"]["task_ids"], paths, strict=True):
            _load_valid_trajectory(path, task_id, "train", step["parent"])

    def build_experience(
        self,
        step: dict[str, Any],
        train_artifact: dict[str, Any],
    ) -> dict[str, Any]:
        del train_artifact
        paths = self._train_paths[step["step"]]
        experiences = []
        sources = []
        state_counts = {state: 0 for state in OUTCOME_STATES}
        for index, (task_id, path) in enumerate(
            zip(step["batch"]["task_ids"], paths, strict=True), start=1
        ):
            source_id = f"step_{step['step']:03d}_source_{index:03d}"
            experience = build_experience(
                json.loads(path.read_text(encoding="utf-8")), source_id
            )
            experiences.append(experience)
            state_counts[experience["state"]] += 1
            sources.append(
                {
                    "source_id": source_id,
                    "task_id": task_id,
                    "path": path.relative_to(REPO_ROOT).as_posix(),
                }
            )
        payload = {
            "schema_version": "governed_experience_0.1.0",
            "experience_count": 17,
            "state_counts": state_counts,
            "sources": sources,
            "experiences": experiences,
            "lineage": {
                "batch_id": step["batch"]["batch_id"],
                "parent_version": step["parent"]["version"],
                "task_ids": list(step["batch"]["task_ids"]),
            },
        }
        path = _step_path(
            self._campaign, step["step"], "governed_experience.json"
        )
        _write_json(path, payload)
        self._side_effects["filesystem_writes"] += 1
        artifact = _artifact(
            "governed_experience", f"step_{step['step']:03d}", path
        )
        self._datasets[artifact["path"]] = payload
        return artifact

    def propose(self, request: ProposalRequest) -> ProposalResult:
        dataset = self._datasets.get(request.experience["path"])
        if dataset is None:
            raise RuntimeContractError("Governed Experience is unavailable.")
        parent_skill = None
        if request.parent["kind"] == "accepted_skill":
            parent_skill = _resolve_repo_path(request.parent["path"]).read_text(
                encoding="utf-8"
            ).strip()
        context = ProposalContext(
            candidate_id=f"epoch_001_step_{request.step:03d}_candidate",
            batch_id=request.batch_id,
            task_ids=request.task_ids,
            parent=copy.deepcopy(request.parent),
            parent_skill=parent_skill,
            experience=copy.deepcopy(request.experience),
            governed_dataset=copy.deepcopy(dataset),
        )
        operator = (
            BootstrapProposalOperator()
            if request.operator == "bootstrap"
            else IncrementalProposalOperator()
        )
        self._learner.last_call = None
        self._learner.last_response = None
        decision = operator.propose(context, self._learner)
        if decision.learner_calls:
            self._side_effects["api_calls"] += 1
            self._save_learner_call(request.step)
        if decision.candidate is None:
            return ProposalResult(decision.status, decision.learner_calls, None)

        bundle = decision.candidate
        candidate_dir = (
            REPO_ROOT
            / "artifacts"
            / self._campaign["campaign_id"]
            / "formal"
            / "candidates"
            / context.candidate_id
        )
        skill_path = candidate_dir / "skill.md"
        provenance_path = candidate_dir / "provenance.json"
        _write_bytes(skill_path, (bundle.skill.rstrip() + "\n").encode("utf-8"))
        candidate = _artifact("candidate_skill", context.candidate_id, skill_path)
        provenance_payload = copy.deepcopy(bundle.provenance_payload)
        provenance_payload["candidate"] = copy.deepcopy(candidate)
        _write_json(provenance_path, provenance_payload)
        self._side_effects["filesystem_writes"] += 2
        return ProposalResult(decision.status, decision.learner_calls, candidate)

    def _save_learner_call(self, step: int) -> None:
        if self._learner.last_call is None or self._learner.last_response is None:
            raise RuntimeContractError("Learner call audit is incomplete.")
        _write_json(
            _step_path(self._campaign, step, "learner_call.json"),
            self._learner.last_call,
        )
        _write_bytes(
            _step_path(self._campaign, step, "learner_response.txt"),
            (self._learner.last_response.rstrip() + "\n").encode("utf-8"),
        )
        self._side_effects["filesystem_writes"] += 2

    def run_candidate_selection(
        self,
        step: dict[str, Any],
        candidate: dict[str, Any],
        accepted_version_if_promoted: str,
        task_count: int,
    ) -> dict[str, Any]:
        if task_count != 18:
            raise RuntimeContractError("Selection task budget is invalid.")
        promoted = {**candidate, "version": accepted_version_if_promoted}
        return self._checkpoint(
            promoted, _split_task_ids(self._campaign, "selection")
        )

    def validate_candidate_selection(
        self,
        step: dict[str, Any],
        checkpoint: dict[str, Any],
    ) -> None:
        del step
        if checkpoint["path"] not in self._checkpoints:
            raise RuntimeContractError("Candidate checkpoint is unavailable.")

    def build_evolution_summary(
        self,
        step: dict[str, Any],
        candidate_checkpoint: dict[str, Any],
    ) -> dict[str, Any]:
        parent = self._checkpoints.get(step["parent_checkpoint"]["path"])
        candidate = self._checkpoints.get(candidate_checkpoint["path"])
        if parent is None or candidate is None:
            raise RuntimeContractError("Selection checkpoint lineage is missing.")
        rows = [
            {**row, "method": "parent"} for row in parent["rows"]
        ] + [{**row, "method": "candidate"} for row in candidate["rows"]]
        payload = {
            "schema_version": "autonomous_gse_evolution_summary_0.1.0",
            "step": step["step"],
            "parent_checkpoint": copy.deepcopy(step["parent_checkpoint"]),
            "candidate_checkpoint": copy.deepcopy(candidate_checkpoint),
            "analysis": analyze_candidate(rows, "parent", "candidate"),
        }
        path = _step_path(
            self._campaign, step["step"], "evolution_summary.json"
        )
        _write_json(path, payload)
        self._side_effects["filesystem_writes"] += 1
        return _artifact("evolution_summary", f"step_{step['step']:03d}", path)

    def apply_gate(
        self,
        step: dict[str, Any],
        summary: dict[str, Any],
    ) -> str:
        del step
        payload = json.loads(
            _resolve_repo_path(summary["path"]).read_text(encoding="utf-8")
        )
        decision = payload["analysis"]["evolution_gate"]["decision"]
        mapping = {"continue_evolution": "ACCEPT", "reject": "REJECT"}
        if decision not in mapping:
            raise RuntimeContractError("Evolution Gate decision is unsupported.")
        return mapping[decision]


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


def build_formal_execution_plan(
    campaign: dict[str, Any],
    batch_map: dict[str, Any],
) -> dict[str, Any]:
    """Build a no-side-effect preview of the recorded workload."""

    validate_formal_campaign_contract(campaign)
    batches = batch_map.get("batches", [])
    if len(batches) != 3:
        raise RuntimeContractError("Formal plan requires exactly 3 batches.")
    selection_task_ids = _split_task_ids(campaign, "selection")
    steps = []
    for number, batch in enumerate(batches, start=1):
        task_ids = tuple(item["task_id"] for item in batch["assignments"])
        steps.append(
            {
                "step": number,
                "batch_id": f"batch_{number:03d}",
                "train_task_ids": list(task_ids),
                "candidate_selection_task_ids": list(selection_task_ids),
                "maximum_learner_calls": 1,
            }
        )
    return {
        "schema_version": "autonomous_gse_formal_plan_0.1.0",
        "campaign_id": campaign["campaign_id"],
        "mode": "no_side_effect_formal_plan",
        "initial_selection_task_ids": list(selection_task_ids),
        "steps": steps,
        "maximum_budget": copy.deepcopy(campaign["budget"]),
        "test_authorized": False,
    }


def run_formal_campaign(
    campaign: dict[str, Any],
    batch_map: dict[str, Any],
    adapter: FormalBenchmarkRuntimeAdapter,
) -> dict[str, Any]:
    """Execute the Campaign through an explicitly injected adapter."""

    validate_formal_campaign_contract(campaign)
    report = run_campaign(campaign, batch_map, adapter)
    if report["mode"] != FORMAL_MODE:
        raise RuntimeContractError("Formal runtime adapter mode is invalid.")
    if report["side_effects"]["browser_calls"] > 123:
        raise RuntimeContractError("Formal runtime exceeded rollout budget.")
    report["schema_version"] = "autonomous_gse_formal_report_0.1.0"
    return report


def _campaign_artifact_paths(campaign: dict[str, Any]) -> dict[str, Path]:
    artifact_root = REPO_ROOT / "artifacts" / campaign["campaign_id"]
    return {
        "artifact_root": artifact_root,
        "raw_root": artifact_root / "raw",
        "s0_raw_root": artifact_root / "raw/selection/s0_no_skill",
        "formal_root": artifact_root / "formal",
        "checkpoint": artifact_root / "formal/checkpoints/s0_no_skill.json",
        "report": artifact_root / "formal" / CAMPAIGN_REPORT_FILENAME,
    }


def _validate_initial_checkpoint(
    campaign: dict[str, Any], checkpoint_path: Path
) -> dict[str, Any]:
    checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    expected_task_ids = list(_split_task_ids(campaign, "selection"))
    recorded_parent = checkpoint.get("parent", {})
    expected_parent = campaign["initial_parent"]
    if (
        checkpoint.get("schema_version")
        != "autonomous_gse_selection_checkpoint_0.1.0"
        or checkpoint.get("campaign_id") != campaign["campaign_id"]
        or any(
            recorded_parent.get(key) != value
            for key, value in expected_parent.items()
        )
        or checkpoint.get("task_ids") != expected_task_ids
        or len(checkpoint.get("rows", [])) != len(expected_task_ids)
        or len(checkpoint.get("sources", [])) != len(expected_task_ids)
    ):
        raise RuntimeContractError("Initial S0 checkpoint contract is invalid.")
    for source in checkpoint["sources"]:
        _load_valid_trajectory(
            _resolve_repo_path(source["path"]),
            source["task_id"],
            "selection",
            campaign["initial_parent"],
        )
    return checkpoint


def get_campaign_status(campaign_path: Path) -> dict[str, Any]:
    """Inspect recorded artifact progress without starting or resuming work."""

    campaign_path = campaign_path.resolve()
    campaign = json.loads(campaign_path.read_text(encoding="utf-8"))
    validate_formal_campaign_contract(campaign)
    paths = _campaign_artifact_paths(campaign)
    s0_trajectories = sorted(
        paths["s0_raw_root"].glob("task_*/trial_01/trajectory.json")
    )
    all_trajectories = sorted(paths["raw_root"].rglob("trajectory.json"))
    failures = sorted(paths["artifact_root"].rglob("failure_*.json"))
    checkpoint_exists = paths["checkpoint"].is_file()
    report_exists = paths["report"].is_file()
    formal_files = {
        path.resolve()
        for path in paths["formal_root"].rglob("*")
        if path.is_file()
    }
    expected_initial_files = (
        {paths["checkpoint"].resolve()} if checkpoint_exists else set()
    )
    step_files = formal_files - expected_initial_files - (
        {paths["report"].resolve()} if report_exists else set()
    )
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
                report.get("campaign_id") != campaign["campaign_id"]
                or report.get("status") != "COMPLETED"
                or len(report.get("steps", [])) != 3
            ):
                raise RuntimeContractError("Campaign report is invalid.")
    except (KeyError, OSError, ValueError, RuntimeContractError) as exc:
        state = "INVALID"
        error = str(exc)
    else:
        if failures:
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
        "schema_version": "autonomous_gse_status_0.1.0",
        "campaign_id": campaign["campaign_id"],
        "campaign_status": campaign.get("status"),
        "state": state,
        "details": details,
    }
    if error is not None:
        result["error"] = error
    return result


def run_initial_checkpoint(
    campaign_path: Path,
    *,
    rollout_backend: RolloutBackend | None = None,
    learner: LearnerAdapter | None = None,
) -> dict[str, Any]:
    """Run the fresh S0 Selection checkpoint, then stop."""

    campaign_path = campaign_path.resolve()
    campaign = json.loads(campaign_path.read_text(encoding="utf-8"))
    status = get_campaign_status(campaign_path)
    if status["state"] != "NOT_STARTED":
        raise RuntimeContractError(
            "Initial checkpoint requires a new Campaign artifact root; "
            f"current state is {status['state']}."
        )
    adapter = FormalBenchmarkRuntimeAdapter(
        campaign,
        campaign_path,
        rollout_backend=rollout_backend or RunnerRolloutBackend(campaign),
        learner=learner or LearnerAdapter(campaign),
    )
    checkpoint = adapter.create_initial_checkpoint(
        campaign["campaign_id"],
        campaign["initial_parent"],
        campaign["selection"]["tasks"],
    )
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
    """Execute all three Steps from a complete S0 checkpoint."""

    campaign_path = campaign_path.resolve()
    campaign = json.loads(campaign_path.read_text(encoding="utf-8"))
    status = get_campaign_status(campaign_path)
    if status["state"] != "READY_TO_RUN":
        raise RuntimeContractError(
            "Formal Campaign run requires READY_TO_RUN; "
            f"current state is {status['state']}."
        )
    if learner is None:
        from dotenv import load_dotenv

        load_dotenv(
            REPO_ROOT / "external/ST-WebAgentBench/.env",
            override=False,
        )
        learner = LearnerAdapter(campaign)
    batch_path = _resolve_repo_path(campaign["train"]["batch_map"])
    batch_map = json.loads(batch_path.read_text(encoding="utf-8"))
    adapter = FormalBenchmarkRuntimeAdapter(
        campaign,
        campaign_path,
        rollout_backend=rollout_backend or RunnerRolloutBackend(campaign),
        learner=learner,
    )
    report = run_formal_campaign(campaign, batch_map, adapter)
    report_path = _campaign_artifact_paths(campaign)["report"]
    _write_json(report_path, report)
    return {
        "status": "AUTONOMOUS_GSE_CAMPAIGN_COMPLETED",
        "report": _artifact(
            "campaign_report", campaign["campaign_id"], report_path
        ),
        "step_outcomes": [step["outcome"] for step in report["steps"]],
        "final_parent": copy.deepcopy(report["final_parent"]),
        "budget_usage": copy.deepcopy(report["budget_usage"]),
        "side_effects": copy.deepcopy(report["side_effects"]),
    }


def main(argv: Sequence[str] | None = None) -> int:
    import argparse

    default_campaign = (
        REPO_ROOT
        / "experiments/campaigns/autonomous_gse_v01/campaign_manifest.json"
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
        batch_path = _resolve_repo_path(campaign["train"]["batch_map"])
        result = build_formal_execution_plan(
            campaign, json.loads(batch_path.read_text(encoding="utf-8"))
        )
    elif args.command == "initial-checkpoint":
        result = run_initial_checkpoint(campaign_path)
    else:
        result = run_formal_campaign_cli(campaign_path)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

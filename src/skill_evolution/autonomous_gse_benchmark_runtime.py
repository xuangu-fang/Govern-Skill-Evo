"""Formal ST-WebAgentBench adapters for Autonomous GSE v0.1.

This module is the side-effect boundary for formal Campaign execution.  It
freezes Learner prompt semantics, delegates browser rollouts to the existing
validated ST-WebAgentBench engines, and converts their artifacts into the
runtime contract consumed by the deterministic Controller.

Importing this module performs no API, browser, database, or filesystem work.
Formal work only starts when an adapter method is called with an executing
rollout backend and a real Learner caller.
"""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
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
PROMPT_SEPARATOR = "\n"
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


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _text_sha256(value: str) -> str:
    return _sha256_bytes((value.rstrip() + "\n").encode("utf-8"))


def _prompt_template_sha256(system: str, user: str) -> str:
    return _sha256_bytes((system + PROMPT_SEPARATOR + user).encode("utf-8"))


def frozen_prompt_hashes() -> dict[str, str]:
    """Return semantic hashes for the exact Prompt templates in use."""

    return {
        "bootstrap": _prompt_template_sha256(
            BOOTSTRAP_SYSTEM_PROMPT, BOOTSTRAP_USER_PROMPT
        ),
        "incremental": _prompt_template_sha256(
            INCREMENTAL_SYSTEM_PROMPT, INCREMENTAL_USER_PROMPT
        ),
    }


def _resolve_repo_path(relative_path: str) -> Path:
    path = (REPO_ROOT / relative_path).resolve()
    path.relative_to(REPO_ROOT)
    return path


def _artifact(
    kind: str,
    version: str,
    path: Path,
) -> dict[str, str]:
    return {
        "kind": kind,
        "version": version,
        "path": path.relative_to(REPO_ROOT).as_posix(),
        "sha256": _sha256_file(path),
    }


def _write_bytes_once(path: Path, content: bytes) -> None:
    if path.exists():
        if path.read_bytes() != content:
            raise RuntimeContractError(
                f"Refusing to overwrite frozen formal artifact: {path}"
            )
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_bytes(content)
    temporary.replace(path)


def _write_json_once(path: Path, payload: dict[str, Any]) -> None:
    _write_bytes_once(path, _canonical_json_bytes(payload))


def _validate_binding(binding: dict[str, Any], label: str) -> None:
    if set(binding) != {"kind", "version", "path", "sha256"}:
        raise RuntimeContractError(f"{label} is not fully bound.")
    path = _resolve_repo_path(binding["path"])
    if not path.is_file() or _sha256_file(path) != binding["sha256"]:
        raise RuntimeContractError(f"{label} implementation binding drifted.")


def validate_formal_campaign_contract(
    campaign: dict[str, Any],
    *,
    require_frozen: bool,
) -> None:
    """Validate bindings and the formal execution boundary before work."""

    if require_frozen and campaign.get("status") != "frozen":
        raise RuntimeContractError(
            "Formal execution requires a frozen Campaign manifest."
        )
    if campaign.get("protocol_version") != "autonomous_gse_v01":
        raise RuntimeContractError("Unsupported formal Campaign protocol.")
    if campaign.get("test") != {
        "authorized": False,
        "data_for_learning": "forbidden",
    }:
        raise RuntimeContractError("Test must remain sealed.")

    learner = campaign.get("proposal", {}).get("learner", {})
    expected_learner = {
        "requested_model": "openai/gpt-5.6-terra",
        "resolved_model": "gpt-5.6-terra",
        "api_parameters": {
            "reasoning_effort": "low",
            "max_completion_tokens": 8000,
            "temperature": None,
        },
        "temperature_policy": "not_sent",
        "prompt_template_sha256": frozen_prompt_hashes(),
    }
    if learner != expected_learner:
        raise RuntimeContractError("Frozen Learner contract drifted.")

    runtime = campaign.get("benchmark_runtime", {})
    if runtime.get("agent") != {
        "requested_model": "openai/gpt-5.6-terra",
        "resolved_model": "gpt-5.6-terra",
        "api_parameters": {"temperature": 0.1, "max_tokens": 512},
    }:
        raise RuntimeContractError("Frozen benchmark Agent contract drifted.")
    if runtime.get("rollout") != {
        "headless": False,
        "trials_per_task": 1,
        "execution": "sequential",
        "database_reset_before_every_trial": True,
    }:
        raise RuntimeContractError("Frozen benchmark rollout contract drifted.")

    bindings = campaign.get("implementation_bindings", {})
    for name in (
        "batch_planner",
        "bootstrap_operator",
        "bootstrap_prompt",
        "incremental_operator",
        "incremental_prompt",
        "train_runner",
        "experience_builder",
        "selection_runner",
        "controller",
        "benchmark_runtime_adapter",
        "runtime_orchestrator",
        "learner_adapter",
        "learner_client",
        "freeze_tool",
        "campaign_schema",
        "benchmark_agent",
    ):
        binding = bindings.get(name)
        if not isinstance(binding, dict):
            raise RuntimeContractError(f"Missing {name} binding.")
        _validate_binding(binding, name)

    for name in ("database_snapshot", "database_reset", "compose_file"):
        binding = runtime.get(name)
        if not isinstance(binding, dict):
            raise RuntimeContractError(f"Missing benchmark {name} binding.")
        _validate_binding(binding, f"benchmark_runtime.{name}")
    if require_frozen:
        from src.skill_evolution.autonomous_gse_freeze import (
            require_campaign_freeze,
        )

        manifest_path = REPO_ROOT / (
            "experiments/campaigns/autonomous_gse_v01/campaign_manifest.json"
        )
        require_campaign_freeze(manifest_path, campaign)


LearnerCaller = Callable[[str, str, str], tuple[str, str, dict | None]]


class FrozenLearnerAdapter:
    """Build and call exactly one of the two frozen Proposal Prompts."""

    def __init__(
        self,
        campaign: dict[str, Any],
        *,
        caller: LearnerCaller = call_learner,
    ) -> None:
        validate_formal_campaign_contract(campaign, require_frozen=False)
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
            raise RuntimeContractError("Unknown frozen Proposal Prompt.")

        expected_template = self._contract["prompt_template_sha256"][
            request.operator
        ]
        actual_template = frozen_prompt_hashes()[request.operator]
        if actual_template != expected_template:
            raise RuntimeContractError("Proposal Prompt template hash drifted.")

        response, resolved_model, usage = self._caller(
            self._contract["requested_model"],
            system_prompt,
            user_prompt,
        )
        if resolved_model != self._contract["resolved_model"]:
            raise RuntimeContractError("Learner resolved model drifted.")
        self.last_response = response
        self.last_call = {
            "candidate_id": request.candidate_id,
            "operator": request.operator,
            "requested_model": self._contract["requested_model"],
            "resolved_model": resolved_model,
            "api_parameters": copy.deepcopy(
                self._contract["api_parameters"]
            ),
            "temperature_policy": self._contract["temperature_policy"],
            "prompt_template_sha256": actual_template,
            "full_prompt_sha256": _sha256_bytes(
                (system_prompt + PROMPT_SEPARATOR + user_prompt).encode("utf-8")
            ),
            "evidence_count": len(request.evidence),
            "usage": usage,
            "response_sha256": _text_sha256(response),
        }
        return response


@dataclass(frozen=True)
class RolloutRequest:
    split: str
    method: str
    artifact: dict[str, Any]
    task_ids: tuple[int, ...]


class SubprocessRolloutBackend:
    """Execute the bound rollout engines in a separate Python process."""

    def __init__(self, campaign_path: Path) -> None:
        self.campaign_path = campaign_path.resolve()

    def run(self, request: RolloutRequest) -> tuple[Path, ...]:
        command = [
            sys.executable,
            "-m",
            "src.skill_evolution.autonomous_gse_benchmark_runtime",
            "rollout",
            "--campaign",
            str(self.campaign_path),
            "--split",
            request.split,
            "--method",
            request.method,
            "--artifact",
            json.dumps(request.artifact, sort_keys=True),
            "--task-ids",
            ",".join(map(str, request.task_ids)),
        ]
        subprocess.run(command, cwd=REPO_ROOT, check=True)
        return tuple(
            REPO_ROOT
            / "artifacts"
            / "autonomous_gse_v01"
            / "raw"
            / request.split
            / request.method
            / f"task_{task_id}"
            / "trial_01"
            / "trajectory.json"
            for task_id in request.task_ids
        )


RolloutBackend = Callable[[RolloutRequest], Sequence[Path]]


class FormalBenchmarkRuntimeAdapter:
    """Concrete formal RuntimeAdapter backed by ST-WebAgentBench artifacts."""

    mode = FORMAL_MODE

    def __init__(
        self,
        campaign: dict[str, Any],
        campaign_path: Path,
        *,
        rollout_backend: RolloutBackend,
        learner: FrozenLearnerAdapter,
    ) -> None:
        validate_formal_campaign_contract(campaign, require_frozen=True)
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
            compliant = outcome["violated_policy_count"] == 0
            rows.append(
                {
                    "task_id": task_id,
                    "task_success": outcome["task_success"],
                    "compliant": compliant,
                }
            )
            sources.append(
                {
                    "task_id": task_id,
                    "path": path.relative_to(REPO_ROOT).as_posix(),
                    "sha256": _sha256_file(path),
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
        _write_json_once(path, payload)
        self._side_effects["filesystem_writes"] += 1
        checkpoint = _artifact(
            "selection_checkpoint", artifact["version"], path
        )
        self._checkpoints[checkpoint["sha256"]] = payload
        return checkpoint

    def create_initial_checkpoint(
        self,
        campaign_id: str,
        parent: dict[str, Any],
        task_count: int,
    ) -> dict[str, Any]:
        if campaign_id != self._campaign["campaign_id"] or task_count != 18:
            raise RuntimeContractError("Initial checkpoint contract drifted.")
        task_ids = _split_task_ids(self._campaign, "selection")
        checkpoint = self._checkpoint(parent, task_ids)
        self._trace.append({"operation": "create_initial_checkpoint"})
        return checkpoint

    def run_train(self, step: dict[str, Any]) -> dict[str, Any]:
        paths = self._run(
            "train", step["parent"], step["batch"]["task_ids"]
        )
        self._train_paths[step["step"]] = paths
        payload = {
            "step": step["step"],
            "batch_id": step["batch"]["batch_id"],
            "parent": copy.deepcopy(step["parent"]),
            "task_ids": list(step["batch"]["task_ids"]),
            "sources": [
                {
                    "path": path.relative_to(REPO_ROOT).as_posix(),
                    "sha256": _sha256_file(path),
                }
                for path in paths
            ],
        }
        path = _step_path(self._campaign, step["step"], "train_set.json")
        _write_json_once(path, payload)
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
        if paths is None:
            raise RuntimeContractError("Train trajectory set is unavailable.")
        for task_id, path in zip(
            step["batch"]["task_ids"], paths, strict=True
        ):
            _load_valid_trajectory(path, task_id, "train", step["parent"])
        if _sha256_file(_resolve_repo_path(train_artifact["path"])) != (
            train_artifact["sha256"]
        ):
            raise RuntimeContractError("Train artifact hash drifted.")

    def build_experience(
        self,
        step: dict[str, Any],
        train_artifact: dict[str, Any],
    ) -> dict[str, Any]:
        paths = self._train_paths[step["step"]]
        experiences = []
        sources = []
        state_counts = {state: 0 for state in OUTCOME_STATES}
        for index, (task_id, path) in enumerate(
            zip(step["batch"]["task_ids"], paths, strict=True), start=1
        ):
            source_id = f"step_{step['step']:03d}_source_{index:03d}"
            trajectory = json.loads(path.read_text(encoding="utf-8"))
            experience = build_experience(trajectory, source_id)
            experiences.append(experience)
            state_counts[experience["state"]] += 1
            sources.append(
                {
                    "source_id": source_id,
                    "task_id": task_id,
                    "path": path.relative_to(REPO_ROOT).as_posix(),
                    "sha256": _sha256_file(path),
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
                "parent_sha256": step["parent"]["sha256"],
                "task_ids": list(step["batch"]["task_ids"]),
            },
        }
        path = _step_path(
            self._campaign, step["step"], "governed_experience.json"
        )
        _write_json_once(path, payload)
        self._side_effects["filesystem_writes"] += 1
        artifact = _artifact(
            "governed_experience", f"step_{step['step']:03d}", path
        )
        self._datasets[artifact["sha256"]] = payload
        return artifact

    def propose(self, request: ProposalRequest) -> ProposalResult:
        dataset = self._datasets.get(request.experience["sha256"])
        if dataset is None:
            raise RuntimeContractError("Governed Experience is unavailable.")
        parent_skill = None
        if request.parent["kind"] == "accepted_skill":
            parent_path = _resolve_repo_path(request.parent["path"])
            parent_skill = parent_path.read_text(encoding="utf-8").strip()
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
            self._freeze_learner_call(request.step)
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
        _write_bytes_once(
            skill_path, (bundle.skill.rstrip() + "\n").encode("utf-8")
        )
        _write_json_once(provenance_path, bundle.provenance_payload)
        self._side_effects["filesystem_writes"] += 2
        candidate = _artifact(
            "candidate_skill", context.candidate_id, skill_path
        )
        if candidate["sha256"] != bundle.candidate["sha256"]:
            raise RuntimeContractError("Frozen Candidate hash changed.")
        return ProposalResult(
            decision.status, decision.learner_calls, candidate
        )

    def _freeze_learner_call(self, step: int) -> None:
        if self._learner.last_call is None or self._learner.last_response is None:
            raise RuntimeContractError("Learner call audit is incomplete.")
        path = _step_path(self._campaign, step, "learner_call.json")
        response_path = _step_path(self._campaign, step, "learner_response.txt")
        _write_json_once(path, self._learner.last_call)
        _write_bytes_once(
            response_path,
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
            raise RuntimeContractError("Selection task budget drifted.")
        promoted = {**candidate, "version": accepted_version_if_promoted}
        return self._checkpoint(
            promoted, _split_task_ids(self._campaign, "selection")
        )

    def validate_candidate_selection(
        self,
        step: dict[str, Any],
        checkpoint: dict[str, Any],
    ) -> None:
        if checkpoint["sha256"] not in self._checkpoints:
            raise RuntimeContractError("Candidate checkpoint is unavailable.")

    def build_evolution_summary(
        self,
        step: dict[str, Any],
        candidate_checkpoint: dict[str, Any],
    ) -> dict[str, Any]:
        parent = self._checkpoints.get(step["parent_checkpoint"]["sha256"])
        candidate = self._checkpoints.get(candidate_checkpoint["sha256"])
        if parent is None or candidate is None:
            raise RuntimeContractError("Selection checkpoint lineage is missing.")
        rows = [
            {**row, "method": "parent"} for row in parent["rows"]
        ] + [
            {**row, "method": "candidate"} for row in candidate["rows"]
        ]
        analysis = analyze_candidate(rows, "parent", "candidate")
        payload = {
            "schema_version": "autonomous_gse_evolution_summary_0.1.0",
            "step": step["step"],
            "parent_checkpoint_sha256": step["parent_checkpoint"]["sha256"],
            "candidate_checkpoint_sha256": candidate_checkpoint["sha256"],
            "analysis": analysis,
        }
        path = _step_path(
            self._campaign, step["step"], "evolution_summary.json"
        )
        _write_json_once(path, payload)
        self._side_effects["filesystem_writes"] += 1
        return _artifact(
            "evolution_summary", f"step_{step['step']:03d}", path
        )

    def apply_gate(
        self,
        step: dict[str, Any],
        summary: dict[str, Any],
    ) -> str:
        path = _resolve_repo_path(summary["path"])
        if _sha256_file(path) != summary["sha256"]:
            raise RuntimeContractError("Evolution Summary hash drifted.")
        payload = json.loads(path.read_text(encoding="utf-8"))
        decision = payload["analysis"]["evolution_gate"]["decision"]
        mapping = self._campaign["gate"]["decision_mapping"]
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
        _resolve_repo_path(campaign["train"]["source_manifest"]["path"])
        .read_text(encoding="utf-8")
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
        or run.get("skill_sha256") != artifact["sha256"]
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
    """Build a no-side-effect preview of the executable formal workload."""

    validate_formal_campaign_contract(campaign, require_frozen=False)
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
    """Execute the frozen Campaign through the formal side-effect boundary."""

    validate_formal_campaign_contract(campaign, require_frozen=True)
    report = run_campaign(campaign, batch_map, adapter)
    if report["mode"] != FORMAL_MODE:
        raise RuntimeContractError("Formal runtime adapter mode drifted.")
    if report["side_effects"]["browser_calls"] > 123:
        raise RuntimeContractError("Formal runtime exceeded rollout budget.")
    report["schema_version"] = "autonomous_gse_formal_report_0.1.0"
    return report


def _run_bound_rollout(
    campaign_path: Path,
    split: str,
    method: str,
    artifact: dict[str, Any],
    task_ids: tuple[int, ...],
) -> None:
    campaign = json.loads(campaign_path.read_text(encoding="utf-8"))
    validate_formal_campaign_contract(campaign, require_frozen=True)
    source_manifest = json.loads(
        _resolve_repo_path(campaign["train"]["source_manifest"]["path"])
        .read_text(encoding="utf-8")
    )
    allowed = set(_split_task_ids(campaign, split))
    if not task_ids or len(task_ids) != len(set(task_ids)) or not set(
        task_ids
    ).issubset(allowed):
        raise RuntimeContractError("Rollout Task IDs violate the frozen split.")
    skill = _load_rollout_skill(artifact)
    runtime = campaign["benchmark_runtime"]
    args = type(
        "FormalArgs",
        (),
        {
            "formal": True,
            "headless": runtime["rollout"]["headless"],
            "model": runtime["agent"]["requested_model"],
            "method": method,
        },
    )()
    runtime_manifest = {
        "manifest_id": campaign["campaign_id"],
        "benchmark": {
            "commit": source_manifest["benchmark"]["commit"],
            "task_source_sha256": source_manifest["benchmark"][
                "task_source_sha256"
            ],
        },
    }
    source_index = {
        task_id: {
            "task_id": task_id,
            "intent_template_id": template["intent_template_id"],
            "subset": template["subset"],
        }
        for template in source_manifest["splits"][split]["templates"]
        for task_id in template["task_ids"]
    }
    manifest_sha = _sha256_file(campaign_path)
    snapshot_sha = campaign["benchmark_runtime"]["database_snapshot"][
        "sha256"
    ]
    if split == "train":
        from src.adapters.stwebagentbench.run_evolution_train import run_task

        for task_id in task_ids:
            run_task(
                args,
                runtime_manifest,
                method,
                skill,
                source_index[task_id],
                manifest_sha,
                snapshot_sha,
            )
    else:
        from src.adapters.stwebagentbench.run_evolution_selection import run_task

        runner_sha = campaign["implementation_bindings"][
            "selection_runner"
        ]["sha256"]
        for task_id in task_ids:
            run_task(
                args,
                runtime_manifest,
                source_index[task_id],
                manifest_sha,
                snapshot_sha,
                runner_sha,
                skill,
            )


def _load_rollout_skill(artifact: dict[str, Any]) -> dict[str, Any]:
    if artifact["kind"] == "no_skill":
        path = _resolve_repo_path(artifact["path"])
        if _sha256_file(path) != artifact["sha256"]:
            raise RuntimeContractError("S0 artifact hash drifted.")
        return {
            "version": artifact["version"],
            "path": artifact["path"],
            "sha256": artifact["sha256"],
            "prompt_sha256": None,
            "block": None,
        }
    path = _resolve_repo_path(artifact["path"])
    if not path.is_file() or _sha256_file(path) != artifact["sha256"]:
        raise RuntimeContractError("Skill artifact hash drifted.")
    text = path.read_text(encoding="utf-8").strip()
    block = f"# Operational Skill\n{text}"
    return {
        "version": artifact["version"],
        "path": artifact["path"],
        "sha256": artifact["sha256"],
        "prompt_sha256": _sha256_bytes(block.encode("utf-8")),
        "block": block,
    }


def run_initial_checkpoint(campaign_path: Path) -> dict[str, Any]:
    """Run only the fresh S0 Selection checkpoint, then stop."""

    campaign_path = campaign_path.resolve()
    campaign = json.loads(campaign_path.read_text(encoding="utf-8"))
    status = get_campaign_status(campaign_path)
    if status["state"] != "NOT_STARTED":
        raise RuntimeContractError(
            "Initial checkpoint requires an empty Campaign artifact root; "
            f"current state is {status['state']}."
        )
    learner = FrozenLearnerAdapter(campaign)
    backend = SubprocessRolloutBackend(campaign_path)
    adapter = FormalBenchmarkRuntimeAdapter(
        campaign,
        campaign_path,
        rollout_backend=backend.run,
        learner=learner,
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
    campaign: dict[str, Any],
    checkpoint_path: Path,
) -> dict[str, Any]:
    checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    expected_task_ids = list(_split_task_ids(campaign, "selection"))
    if (
        checkpoint.get("schema_version")
        != "autonomous_gse_selection_checkpoint_0.1.0"
        or checkpoint.get("campaign_id") != campaign["campaign_id"]
        or checkpoint.get("parent") != campaign["initial_parent"]
        or checkpoint.get("task_ids") != expected_task_ids
        or len(checkpoint.get("rows", [])) != len(expected_task_ids)
        or len(checkpoint.get("sources", [])) != len(expected_task_ids)
    ):
        raise RuntimeContractError("Initial S0 checkpoint contract drifted.")
    rows = checkpoint["rows"]
    sources = checkpoint["sources"]
    if {row.get("task_id") for row in rows} != set(expected_task_ids):
        raise RuntimeContractError("Initial S0 checkpoint rows drifted.")
    for row in rows:
        if set(row) != {"task_id", "task_success", "compliant"} or not all(
            isinstance(row[key], bool) for key in ("task_success", "compliant")
        ):
            raise RuntimeContractError("Initial S0 checkpoint row is invalid.")
    for source in sources:
        path = _resolve_repo_path(source["path"])
        if _sha256_file(path) != source["sha256"]:
            raise RuntimeContractError("Initial S0 trajectory hash drifted.")
        _load_valid_trajectory(
            path,
            source["task_id"],
            "selection",
            campaign["initial_parent"],
        )
    return checkpoint


def get_campaign_status(campaign_path: Path) -> dict[str, Any]:
    """Inspect formal artifact progress without starting or resuming work."""

    campaign_path = campaign_path.resolve()
    campaign = json.loads(campaign_path.read_text(encoding="utf-8"))
    paths = _campaign_artifact_paths(campaign)
    s0_trajectories = sorted(paths["s0_raw_root"].glob(
        "task_*/trial_01/trajectory.json"
    ))
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
                report.get("schema_version")
                != "autonomous_gse_formal_report_0.1.0"
                or report.get("campaign_id") != campaign["campaign_id"]
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


def run_formal_campaign_cli(campaign_path: Path) -> dict[str, Any]:
    """Execute all three Steps from a complete frozen S0 checkpoint."""

    campaign_path = campaign_path.resolve()
    campaign = json.loads(campaign_path.read_text(encoding="utf-8"))
    status = get_campaign_status(campaign_path)
    if status["state"] != "READY_TO_RUN":
        raise RuntimeContractError(
            "Formal Campaign run requires READY_TO_RUN; "
            f"current state is {status['state']}."
        )
    from dotenv import load_dotenv

    load_dotenv(REPO_ROOT / "external/ST-WebAgentBench/.env", override=False)
    batch_path = _resolve_repo_path(campaign["train"]["batch_map"]["path"])
    batch_map = json.loads(batch_path.read_text(encoding="utf-8"))
    learner = FrozenLearnerAdapter(campaign)
    backend = SubprocessRolloutBackend(campaign_path)
    adapter = FormalBenchmarkRuntimeAdapter(
        campaign,
        campaign_path,
        rollout_backend=backend.run,
        learner=learner,
    )
    report = run_formal_campaign(campaign, batch_map, adapter)
    report_path = _campaign_artifact_paths(campaign)["report"]
    _write_json_once(report_path, report)
    return {
        "status": "AUTONOMOUS_GSE_CAMPAIGN_COMPLETED",
        "report": _artifact("campaign_report", campaign["campaign_id"], report_path),
        "step_outcomes": [step["outcome"] for step in report["steps"]],
        "final_parent": copy.deepcopy(report["final_parent"]),
        "budget_usage": copy.deepcopy(report["budget_usage"]),
        "side_effects": copy.deepcopy(report["side_effects"]),
    }


def main(argv: Sequence[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    plan = subparsers.add_parser("plan")
    plan.add_argument(
        "--campaign",
        type=Path,
        default=(
            REPO_ROOT
            / "experiments/campaigns/autonomous_gse_v01/"
            "campaign_manifest.json"
        ),
    )
    initial_checkpoint = subparsers.add_parser("initial-checkpoint")
    initial_checkpoint.add_argument(
        "--campaign",
        type=Path,
        default=(
            REPO_ROOT
            / "experiments/campaigns/autonomous_gse_v01/"
            "campaign_manifest.json"
        ),
    )
    run = subparsers.add_parser("run")
    run.add_argument(
        "--campaign",
        type=Path,
        default=(
            REPO_ROOT
            / "experiments/campaigns/autonomous_gse_v01/"
            "campaign_manifest.json"
        ),
    )
    status = subparsers.add_parser("status")
    status.add_argument(
        "--campaign",
        type=Path,
        default=(
            REPO_ROOT
            / "experiments/campaigns/autonomous_gse_v01/"
            "campaign_manifest.json"
        ),
    )
    rollout = subparsers.add_parser("rollout")
    rollout.add_argument("--campaign", type=Path, required=True)
    rollout.add_argument("--split", choices=("train", "selection"), required=True)
    rollout.add_argument("--method", required=True)
    rollout.add_argument("--artifact", required=True)
    rollout.add_argument("--task-ids", required=True)
    args = parser.parse_args(argv)

    campaign_path = args.campaign.resolve()
    campaign = json.loads(campaign_path.read_text(encoding="utf-8"))
    if args.command == "plan":
        batch_path = _resolve_repo_path(campaign["train"]["batch_map"]["path"])
        batch_map = json.loads(batch_path.read_text(encoding="utf-8"))
        print(
            json.dumps(
                build_formal_execution_plan(campaign, batch_map),
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    if args.command == "initial-checkpoint":
        print(
            json.dumps(
                run_initial_checkpoint(campaign_path),
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    if args.command == "run":
        print(
            json.dumps(
                run_formal_campaign_cli(campaign_path),
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    if args.command == "status":
        print(
            json.dumps(
                get_campaign_status(campaign_path),
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    artifact = json.loads(args.artifact)
    task_ids = tuple(int(value) for value in args.task_ids.split(","))
    _run_bound_rollout(
        campaign_path,
        args.split,
        args.method,
        artifact,
        task_ids,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

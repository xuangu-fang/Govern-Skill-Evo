"""Seeded Day 14 runtime built as a small extension of Autonomous GSE v0.3."""

from __future__ import annotations

import copy
import json
from collections.abc import Callable, Sequence
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import src.skill_evolution.autonomous_gse_v03_benchmark_runtime as v03_formal
from src.learners.stwebagentbench.generate_skill import call_learner
from src.skill_evolution.autonomous_gse_v03_benchmark_runtime import (
    RolloutRequest,
)
from src.skill_evolution.autonomous_gse_v03_proposal import (
    EditorRequest,
    ReflectorRequest,
)
from src.skill_evolution.autonomous_gse_v03_runtime import (
    RuntimeContractError,
)
from src.skill_evolution.autonomous_gse_v03_runtime import (
    run_campaign as run_v03_campaign,
)
from src.skill_evolution.two_dimensional_gate import analyze_candidate

REPO_ROOT = Path(__file__).resolve().parents[2]
FORMAL_MODE = "formal_stwebagentbench_v04"
CAMPAIGN_REPORT_FILENAME = "campaign_report.json"
TEST_REPORT_FILENAME = "final_test_report.json"


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


def _load_benchmark_environment() -> None:
    from dotenv import load_dotenv

    load_dotenv(REPO_ROOT / "external/ST-WebAgentBench/.env", override=False)


def _artifact(kind: str, version: str, path: Path) -> dict[str, str]:
    return {
        "kind": kind,
        "version": version,
        "path": path.resolve().relative_to(REPO_ROOT).as_posix(),
    }


def _expand_campaign(campaign: dict[str, Any]) -> dict[str, Any]:
    """Overlay the small v04 manifest on the frozen v03 manifest."""

    base_path = campaign.get("base_campaign")
    if base_path is None:
        return copy.deepcopy(campaign)
    base = json.loads(_resolve_repo_path(base_path).read_text(encoding="utf-8"))
    expanded = {**base, **copy.deepcopy(campaign)}
    if "headless" in expanded:
        expanded["benchmark_runtime"] = copy.deepcopy(base["benchmark_runtime"])
        expanded["benchmark_runtime"]["rollout"]["headless"] = expanded[
            "headless"
        ]
    if "execution" in expanded or "parallel_workers" in expanded:
        if "benchmark_runtime" not in expanded or expanded[
            "benchmark_runtime"
        ] is base.get("benchmark_runtime"):
            expanded["benchmark_runtime"] = copy.deepcopy(
                base["benchmark_runtime"]
            )
        rollout = expanded["benchmark_runtime"]["rollout"]
        rollout["execution"] = expanded.get("execution", "sequential")
        default_workers = 4 if rollout["execution"] == "parallel" else 1
        rollout["parallel_workers"] = expanded.get(
            "parallel_workers", default_workers
        )
    return expanded


def _v03_campaign(campaign: dict[str, Any]) -> dict[str, Any]:
    """Project v04 onto the frozen v03 state-machine contract."""

    projected = copy.deepcopy(campaign)
    projected["schema_version"] = "autonomous_gse_campaign_0.3.0"
    projected["protocol_version"] = "autonomous_gse_v03"
    projected["campaign_id"] = "autonomous_gse_v03"
    projected["benchmark_runtime"]["rollout"]["headless"] = False
    projected["benchmark_runtime"]["rollout"]["execution"] = "sequential"
    projected["benchmark_runtime"]["rollout"].pop("parallel_workers", None)
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
    if campaign.get("schema_version") != "autonomous_gse_campaign_0.4.0":
        raise RuntimeContractError("Unsupported v0.4 Campaign schema.")
    if campaign.get("protocol_version") != "autonomous_gse_v04":
        raise RuntimeContractError("Unsupported v0.4 Campaign protocol.")
    campaign_id = campaign.get("campaign_id")
    seed = campaign.get("campaign_seed")
    if (
        not isinstance(seed, int)
        or isinstance(seed, bool)
        or campaign_id != f"autonomous_gse_v04_seed_{seed}"
    ):
        raise RuntimeContractError("Campaign ID and integer campaign_seed disagree.")
    if campaign.get("status") not in {"draft", "ready"}:
        raise RuntimeContractError("Campaign status must be draft or ready.")
    if require_ready and campaign["status"] != "ready":
        raise RuntimeContractError("Campaign must be ready before execution.")
    if campaign.get("headless", False) is not campaign.get(
        "benchmark_runtime", {}
    ).get("rollout", {}).get("headless"):
        raise RuntimeContractError("Headless rollout configuration drifted.")
    rollout = campaign.get("benchmark_runtime", {}).get("rollout", {})
    execution = rollout.get("execution", "sequential")
    parallel_workers = rollout.get("parallel_workers", 1)
    if (execution, parallel_workers) not in {
        ("sequential", 1),
        ("parallel", 2),
        ("parallel", 4),
    }:
        raise RuntimeContractError(
            "Rollout execution must be sequential/1, parallel/2, or parallel/4."
        )
    if (
        rollout.get("trials_per_task") != 1
        or rollout.get("database_reset_before_every_trial") is not True
    ):
        raise RuntimeContractError("Rollout trial/reset semantics drifted.")
    if campaign.get("current_batch_replay") != {
        "enabled": True,
        "timing": "after_gate",
        "candidate_scope": "current_batch_only",
        "replay_rejected_candidates": True,
        "feedback_to_learner": False,
        "used_by_gate": False,
    }:
        raise RuntimeContractError("Current-Batch Replay contract drifted.")
    if campaign.get("test") != {
        "authorized": True,
        "timing": "after_campaign_completion",
        "comparisons": "s0_vs_final_parent",
        "data_for_learning": "forbidden",
        "used_by_gate": False,
    }:
        raise RuntimeContractError("Final Test contract drifted.")
    budget = campaign.get("budget", {})
    if (
        budget.get("maximum_current_batch_replay_trajectories") != 51
        or budget.get("maximum_test_trajectories") != 36
        or budget.get("maximum_total_trajectories") != 210
    ):
        raise RuntimeContractError("v0.4 rollout budget drifted.")
    v03_formal.validate_formal_campaign_contract(
        _v03_campaign(campaign), require_ready=require_ready
    )


LearnerCaller = Callable[..., tuple[str, str, dict[str, Any] | None]]


class SeededLearnerAdapter:
    """Reuse v03 prompts while strictly passing the Campaign seed."""

    def __init__(
        self,
        campaign: dict[str, Any],
        *,
        caller: LearnerCaller = call_learner,
    ) -> None:
        campaign = _expand_campaign(campaign)
        validate_formal_campaign_contract(campaign)
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
        response, resolved_model, usage = self._caller(
            model, system_prompt, user_prompt, seed=self._seed
        )
        if resolved_model != "gpt-5.6-luna":
            raise RuntimeContractError("Learner resolved model is unexpected.")
        if not isinstance(response, str) or not response.strip():
            raise RuntimeContractError("Learner returned an empty response.")
        role = (
            f"{request.reflector}_reflector"
            if isinstance(request, ReflectorRequest)
            else "editor"
        )
        self.last_response = response.strip()
        self.last_call = {
            "candidate_id": request.candidate_id,
            "role": role,
            "model": model,
            "parameters": {**self._parameters, "seed": self._seed},
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "usage": usage,
        }
        return self.last_response, resolved_model, usage


class SeededRunnerRolloutBackend:
    """Run Train, Selection, Replay, and Test with one strict model seed."""

    def __init__(self, campaign: dict[str, Any]) -> None:
        campaign = _expand_campaign(campaign)
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
            for split in ("train", "selection", "test")
        }
        self._campaign_id = campaign["campaign_id"]
        self._benchmark_commit = source["benchmark"]["commit"]
        self._model = campaign["benchmark_runtime"]["agent_model"]
        rollout = campaign["benchmark_runtime"]["rollout"]
        self._headless = rollout["headless"]
        self._execution = rollout.get("execution", "sequential")
        self._parallel_workers = rollout.get("parallel_workers", 1)
        self._seed = campaign["campaign_seed"]
        self.last_parallel_summary: dict[str, Any] | None = None

    def __call__(self, request: RolloutRequest) -> Sequence[Path]:
        source_split = {
            "train": "train",
            "train_replay": "train",
            "selection": "selection",
            "test": "test",
        }.get(request.split)
        if source_split is None:
            raise RuntimeContractError(f"Unsupported rollout split: {request.split}")
        tasks = self._tasks[source_split]
        missing = [task_id for task_id in request.task_ids if task_id not in tasks]
        if missing:
            raise RuntimeContractError(
                f"Unknown {source_split} Task IDs: {missing}"
            )
        skill = v03_formal.RunnerRolloutBackend._load_skill(request.artifact)
        manifest = {
            "manifest_id": self._campaign_id,
            "benchmark": {"commit": self._benchmark_commit},
            "_output_split": request.split,
        }
        args = SimpleNamespace(
            formal=True,
            headless=self._headless,
            model=self._model,
            method=request.method,
            seed=self._seed,
        )
        runner = (
            v03_formal._run_train_task
            if source_split == "train"
            else v03_formal._run_selection_task
        )
        if self._execution == "sequential":
            return tuple(
                runner(args, manifest, request.method, skill, tasks[task_id])
                for task_id in request.task_ids
            )

        from src.adapters.stwebagentbench.parallel_rollout import (
            run_subprocess_rollouts,
        )

        payloads = [
            {
                "source_split": source_split,
                "args": vars(args),
                "manifest": manifest,
                "method": request.method,
                "skill": skill,
                "task": tasks[task_id],
            }
            for task_id in request.task_ids
        ]
        paths, summary = run_subprocess_rollouts(
            payloads,
            parallel_workers=self._parallel_workers,
        )
        self.last_parallel_summary = summary
        task_key = "_".join(str(task_id) for task_id in request.task_ids)
        log_path = (
            REPO_ROOT
            / "artifacts"
            / self._campaign_id
            / "formal/parallel_runtime"
            / request.split
            / request.method
            / f"tasks_{task_key}.json"
        )
        _write_json(log_path, summary)
        return paths


def _rows_from_paths(
    paths: Sequence[Path],
    task_ids: Sequence[int],
    split: str,
    artifact: dict[str, Any],
) -> list[dict[str, Any]]:
    rows = []
    for task_id, path in zip(task_ids, paths, strict=True):
        trajectory = v03_formal._load_valid_trajectory(
            path, task_id, split, artifact
        )
        outcome = trajectory["outcome"]
        rows.append(
            {
                "task_id": task_id,
                "task_success": outcome["task_success"],
                "compliant": outcome["violated_policy_count"] == 0,
            }
        )
    return rows


class FormalBenchmarkRuntimeAdapter(v03_formal.FormalBenchmarkRuntimeAdapter):
    """Add after-Gate current-batch replay to the reused v03 adapter."""

    mode = FORMAL_MODE

    def __init__(
        self,
        campaign: dict[str, Any],
        *,
        rollout_backend: Callable[[RolloutRequest], Sequence[Path]],
        learner: SeededLearnerAdapter | None,
    ) -> None:
        campaign = _expand_campaign(campaign)
        validate_formal_campaign_contract(campaign, require_ready=True)
        super().__init__(
            _v03_campaign(campaign),
            rollout_backend=rollout_backend,
            learner=None,
        )
        self._campaign = copy.deepcopy(campaign)
        self._learner = learner
        self._side_effects["current_batch_replay_trajectories"] = 0
        self._replay_summaries: list[dict[str, Any]] = []

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
        if self._learner.last_call is None or self._learner.last_response is None:
            raise RuntimeContractError("Learner call audit is incomplete.")
        role = (
            f"{request.reflector}_reflector"
            if isinstance(request, ReflectorRequest)
            else "editor"
        )
        root = (
            REPO_ROOT
            / "artifacts"
            / self._campaign["campaign_id"]
            / "formal/steps"
            / f"step_{step['step']:03d}"
        )
        _write_json(root / f"{role}_call.json", self._learner.last_call)
        (root / f"{role}_response.txt").write_text(
            self._learner.last_response + "\n", encoding="utf-8"
        )
        self._side_effects["api_calls"] += 1
        self._side_effects["filesystem_writes"] += 2
        return response

    def apply_gate(self, step: dict[str, Any], summary: dict[str, Any]) -> str:
        outcome = super().apply_gate(step, summary)
        self._run_current_batch_replay(step)
        return outcome

    def _run_current_batch_replay(self, step: dict[str, Any]) -> None:
        candidate = step["candidate"]
        task_ids = tuple(step["batch"]["task_ids"])
        paths = self._run("train_replay", candidate, task_ids)
        candidate_rows = _rows_from_paths(
            paths, task_ids, "train_replay", candidate
        )
        train_set_path = (
            REPO_ROOT
            / "artifacts"
            / self._campaign["campaign_id"]
            / "formal/steps"
            / f"step_{step['step']:03d}/train_set.json"
        )
        train_set = json.loads(train_set_path.read_text(encoding="utf-8"))
        parent_paths = [_resolve_repo_path(item["path"]) for item in train_set["sources"]]
        parent_rows = _rows_from_paths(
            parent_paths, task_ids, "train", step["parent"]
        )
        analysis = analyze_candidate(
            [{**row, "method": "parent"} for row in parent_rows]
            + [{**row, "method": "candidate"} for row in candidate_rows],
            "parent",
            "candidate",
        )
        payload = {
            "schema_version": "autonomous_gse_current_batch_replay_0.4.0",
            "campaign_id": self._campaign["campaign_id"],
            "campaign_seed": self._campaign["campaign_seed"],
            "step": step["step"],
            "batch_id": step["batch"]["batch_id"],
            "parent": copy.deepcopy(step["parent"]),
            "candidate": copy.deepcopy(candidate),
            "task_ids": list(task_ids),
            "feedback_to_learner": False,
            "used_by_gate": False,
            "analysis": analysis,
        }
        path = train_set_path.with_name("current_batch_replay.json")
        _write_json(path, payload)
        self._side_effects["current_batch_replay_trajectories"] += len(task_ids)
        self._side_effects["filesystem_writes"] += 1
        self._replay_summaries.append(payload)
        self._trace.append(
            {"operation": "run_current_batch_replay", "step": step["step"]}
        )

    @property
    def replay_summaries(self) -> list[dict[str, Any]]:
        return copy.deepcopy(self._replay_summaries)


def _campaign_paths(campaign: dict[str, Any]) -> dict[str, Path]:
    root = REPO_ROOT / "artifacts" / campaign["campaign_id"]
    return {
        "root": root,
        "report": root / "formal" / CAMPAIGN_REPORT_FILENAME,
        "test_report": root / "formal" / TEST_REPORT_FILENAME,
        "checkpoint": root / "formal/checkpoints/s0_empty_skill.json",
    }


def _split_task_ids(campaign: dict[str, Any], split: str) -> tuple[int, ...]:
    return v03_formal._split_task_ids(campaign, split)


def build_formal_execution_plan(
    campaign: dict[str, Any], batch_map: dict[str, Any]
) -> dict[str, Any]:
    campaign = _expand_campaign(campaign)
    validate_formal_campaign_contract(campaign)
    base = v03_formal.build_formal_execution_plan(
        _v03_campaign(campaign), batch_map
    )
    return {
        "schema_version": "autonomous_gse_formal_plan_0.4.0",
        "campaign_id": campaign["campaign_id"],
        "campaign_seed": campaign["campaign_seed"],
        "headless": campaign["benchmark_runtime"]["rollout"]["headless"],
        "execution": campaign["benchmark_runtime"]["rollout"].get(
            "execution", "sequential"
        ),
        "parallel_workers": campaign["benchmark_runtime"]["rollout"].get(
            "parallel_workers", 1
        ),
        "initial_selection_task_ids": base["initial_selection_task_ids"],
        "steps": [
            {
                **step,
                "current_batch_replay_task_ids": step["train_task_ids"],
            }
            for step in base["steps"]
        ],
        "final_test_task_ids": list(_split_task_ids(campaign, "test")),
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
        rollout_backend=rollout_backend or SeededRunnerRolloutBackend(campaign),
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
        _load_benchmark_environment()
        learner = SeededLearnerAdapter(campaign)
    batch_map = json.loads(
        _resolve_repo_path(campaign["train"]["batch_map"]).read_text(
            encoding="utf-8"
        )
    )
    adapter = FormalBenchmarkRuntimeAdapter(
        campaign,
        rollout_backend=rollout_backend or SeededRunnerRolloutBackend(campaign),
        learner=learner,
    )
    report = run_v03_campaign(_v03_campaign(campaign), batch_map, adapter)
    report["schema_version"] = "autonomous_gse_formal_report_0.4.0"
    report["campaign_id"] = campaign["campaign_id"]
    report["campaign_seed"] = campaign["campaign_seed"]
    report["current_batch_replays"] = adapter.replay_summaries
    report["budget_usage"]["current_batch_replay_trajectories"] = (
        adapter.side_effects["current_batch_replay_trajectories"]
    )
    report["budget_usage"]["total_trajectories"] += report["budget_usage"][
        "current_batch_replay_trajectories"
    ]
    if (
        report["budget_usage"]["current_batch_replay_trajectories"]
        > campaign["budget"]["maximum_current_batch_replay_trajectories"]
        or report["budget_usage"]["total_trajectories"]
        > campaign["budget"]["maximum_total_trajectories"]
        - campaign["budget"]["maximum_test_trajectories"]
    ):
        raise RuntimeContractError("v0.4 pre-Test rollout budget was exceeded.")
    for step in report["steps"]:
        step["campaign_id"] = campaign["campaign_id"]
    _write_json(paths["report"], report)
    return {
        "status": "AUTONOMOUS_GSE_V04_CAMPAIGN_COMPLETED",
        "report": _artifact("campaign_report", campaign["campaign_id"], paths["report"]),
        "step_outcomes": [step["outcome"] for step in report["steps"]],
        "final_parent": report["final_parent"],
    }


def run_final_test(
    campaign_path: Path,
    *,
    rollout_backend: Callable[[RolloutRequest], Sequence[Path]] | None = None,
) -> dict[str, Any]:
    campaign = _expand_campaign(
        json.loads(campaign_path.resolve().read_text(encoding="utf-8"))
    )
    validate_formal_campaign_contract(campaign, require_ready=True)
    paths = _campaign_paths(campaign)
    if not paths["report"].is_file():
        raise RuntimeContractError("Final Test requires a completed Campaign.")
    if paths["test_report"].exists():
        raise RuntimeContractError("Final Test report already exists.")
    campaign_report = json.loads(paths["report"].read_text(encoding="utf-8"))
    final_parent = campaign_report["final_parent"]
    s0 = campaign["initial_parent"]
    task_ids = _split_task_ids(campaign, "test")
    backend = rollout_backend or SeededRunnerRolloutBackend(campaign)

    def evaluate(artifact: dict[str, Any], method: str) -> list[dict[str, Any]]:
        request = RolloutRequest("test", method, artifact, task_ids)
        paths_for_skill = tuple(backend(request))
        return _rows_from_paths(paths_for_skill, task_ids, "test", artifact)

    s0_rows = evaluate(s0, "s0_empty_skill")
    same_skill = all(
        final_parent.get(key) == s0.get(key) for key in ("version", "path")
    )
    final_rows = s0_rows if same_skill else evaluate(
        final_parent,
        FormalBenchmarkRuntimeAdapter._method(final_parent),
    )
    analysis = analyze_candidate(
        [{**row, "method": "s0"} for row in s0_rows]
        + [{**row, "method": "final"} for row in final_rows],
        "s0",
        "final",
    )
    payload = {
        "schema_version": "autonomous_gse_final_test_0.4.0",
        "campaign_id": campaign["campaign_id"],
        "campaign_seed": campaign["campaign_seed"],
        "s0": copy.deepcopy(s0),
        "final_parent": copy.deepcopy(final_parent),
        "final_parent_equals_s0": same_skill,
        "task_ids": list(task_ids),
        "test_trajectories": len(task_ids) if same_skill else 2 * len(task_ids),
        "data_for_learning": "forbidden",
        "used_by_gate": False,
        "analysis": analysis,
    }
    _write_json(paths["test_report"], payload)
    return {
        "status": "FINAL_TEST_COMPLETED",
        "report": _artifact("final_test_report", campaign["campaign_id"], paths["test_report"]),
        "final_parent_equals_s0": same_skill,
    }


def main(argv: Sequence[str] | None = None) -> int:
    import argparse

    default_campaign = (
        REPO_ROOT
        / "experiments/campaigns/autonomous_gse_v04_seed_100/campaign_manifest.json"
    )
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("plan", "initial-checkpoint", "run", "test"):
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
    elif args.command == "run":
        result = run_formal_campaign_cli(args.campaign)
    else:
        result = run_final_test(args.campaign)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

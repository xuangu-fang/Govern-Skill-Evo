"""Phase 1-3 infrastructure for Autonomous GSE v0.14.

The learning side is intentionally the v0.13 implementation.  This module only
adds the v0.14 campaign identity, frozen task partitions, leakage guards,
matched Monitor measurement, and a dry plan.  Candidate gating is not
implemented here.
"""

from __future__ import annotations

import argparse
import copy
import json
import random
import re
import traceback
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from src.adapters.tau2 import tau3_compliance_judge_v13 as compliance_v13
from src.adapters.tau2.tau3_gse_runtime import (
    official_task_evaluation, run_official_rollout, stable_trajectory,
    task_context, write_rollout_artifact,
)
from src.learners.stwebagentbench import generate_governed_skill_v13 as editor_v13
from src.skill_evolution import autonomous_gse_v13_proposal as proposal_v13
from src.skill_evolution.autonomous_gse_v13_benchmark_runtime import (
    load_authoritative_domain_contexts,
)
from src.skill_evolution import diagnosis_contract_v13
from src.skill_evolution import diagnosis_v13
from src.skill_evolution.autonomous_gse_v03_proposal import ProposalContext
from src.skill_evolution.joint_distribution_v14 import (
    JointDistributionContractError, build_joint_distribution_report,
    distribution, state_code, validate_monitor_result,
)
from src.skill_evolution.two_dimensional_gate import classify_state

PROTOCOL_VERSION = "autonomous_gse_v14"
FORMAL_MODE = "formal_tau3_airline_retail_v14_k3_evolution_fixed_monitor"
ROLLOUTS_PER_TASK = 3
REPO_ROOT = Path(__file__).resolve().parents[2]

# These aliases are the v0.14 learner stack.  Keeping object identity makes
# semantic drift visible and prevents prompt or schema forks.
judge_compliance = compliance_v13.judge_compliance
call_diagnosis = diagnosis_v13.call_diagnosis
call_governed_editor = editor_v13.call_governed_editor
MultiRolloutDiagnosisRequest = diagnosis_v13.MultiRolloutDiagnosisRequest
DiagnosisEditorRequest = proposal_v13.DiagnosisEditorRequest
MultiRolloutDiagnosisProposalOperator = proposal_v13.MultiRolloutDiagnosisProposalOperator
V13_PROPOSAL_OPERATOR = MultiRolloutDiagnosisProposalOperator()


class RuntimeContractError(ValueError):
    """Raised when a v0.14 Phase 1-3 invariant is violated."""


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _resolved_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else REPO_ROOT / path


def load_official_task_pools(tau2_root: Path) -> dict[str, dict[str, tuple[str, ...]]]:
    """Load only the benchmark's frozen train/test ID lists."""

    pools: dict[str, dict[str, tuple[str, ...]]] = {}
    for domain in ("airline", "retail"):
        path = tau2_root / f"data/tau2/domains/{domain}/split_tasks.json"
        if not path.is_file():
            raise RuntimeContractError(f"Official {domain} split definition is missing.")
        value = _load_json(path)
        train, test = value.get("train"), value.get("test")
        if not isinstance(train, list) or not isinstance(test, list):
            raise RuntimeContractError(f"Official {domain} split definition is invalid.")
        if len(train) != len(set(train)) or len(test) != len(set(test)) or set(train) & set(test):
            raise RuntimeContractError(f"Official {domain} train/test split overlaps or duplicates IDs.")
        pools[domain] = {"official_train": tuple(train), "official_test": tuple(test)}
    return pools


def derive_monitor_and_final_test_assignment(
    *, campaign_seed: int, official_pools: dict[str, dict[str, tuple[str, ...]]],
) -> dict[str, dict[str, list[str]]]:
    """Partition official_test by seed and domain, without rollout outcomes."""

    assignment = {
        purpose: {domain: [] for domain in ("airline", "retail")}
        for purpose in ("monitor", "test", "reserve")
    }
    for offset, domain in enumerate(("airline", "retail"), start=1):
        official_test = list(official_pools[domain]["official_test"])
        if len(official_test) < 20:
            raise RuntimeContractError(f"Official {domain} test pool cannot supply Monitor and Final Test.")
        random.Random(campaign_seed + offset).shuffle(official_test)
        assignment["monitor"][domain] = official_test[:10]
        assignment["test"][domain] = official_test[10:20]
        assignment["reserve"][domain] = official_test[20:]
    return assignment


def _tagged(domain: str, task_ids: Sequence[str]) -> list[str]:
    return [f"{domain}:{task_id}" for task_id in task_ids]


def validate_campaign_contract(campaign: dict[str, Any]) -> None:
    if (
        campaign.get("schema_version") != "autonomous_gse_campaign_0.14.0"
        or campaign.get("protocol_version") != PROTOCOL_VERSION
        or campaign.get("campaign_id") != PROTOCOL_VERSION
        or campaign.get("campaign_seed") != 200
    ):
        raise RuntimeContractError("v0.14 Campaign identity is invalid.")
    if campaign.get("benchmark", {}).get("name") != "tau3" or campaign["benchmark"].get("domains") != ["airline", "retail"]:
        raise RuntimeContractError("v0.14 supports only tau3 Airline/Retail.")
    if campaign.get("schedule") != {"evolution_steps": 3}:
        raise RuntimeContractError("v0.14 requires exactly three Evolution steps.")

    evolution = campaign.get("evolution", {})
    expected_evolution = {
        "source_split": "official_train", "tasks": 60,
        "airline_tasks": 30, "retail_tasks": 30, "batches": 3,
        "tasks_per_batch": 20, "airline_tasks_per_batch": 10,
        "retail_tasks_per_batch": 10, "rollouts_per_task": 3,
        "batch_map": "experiments/campaigns/autonomous_gse_v14/batch_map.json",
        "outcome_independent_assignment": True, "cumulative_evidence": False,
        "replay_previous_batches": False,
    }
    if evolution != expected_evolution:
        raise RuntimeContractError("v0.14 Evolution workload drifted.")

    monitor = campaign.get("monitor", {})
    expected_monitor = {
        "source_split": "official_test", "tasks": 20,
        "airline_tasks": 10, "retail_tasks": 10,
        "rollouts_per_task": 3, "fixed_across_steps": True,
        "purpose": "distribution_monitor", "learning_access": "forbidden",
        "feedback_to_learner": "forbidden", "execution_enabled": True,
        "measurement_enabled": True, "gate_enabled": False,
    }
    if monitor != expected_monitor:
        raise RuntimeContractError("v0.14 fixed Monitor contract drifted.")

    test = campaign.get("test", {})
    expected_test = {
        "source_split": "official_test", "tasks": 20,
        "airline_tasks": 10, "retail_tasks": 10, "rollouts_per_task": 3,
        "compare": ["S0", "S_final"], "learning_access": "forbidden",
        "feedback_to_learner": "forbidden", "automatic_execution": False,
        "participates_in_step_gate": False,
    }
    if test != expected_test:
        raise RuntimeContractError("v0.14 Test contract drifted.")

    frozen = {
        "model": "openai/deepseek-v4-flash", "thinking": "high",
        "reasoning_effort": "high", "max_tokens": 8192, "empty_response_retries": 2,
        "empty_response_retry_max_tokens": 8192,
    }
    for role, temperature in (("agent", 0.2), ("user_simulator", 0.0)):
        config = campaign.get(role, {})
        if config.get("temperature") != temperature or any(config.get(k) != v for k, v in frozen.items()):
            raise RuntimeContractError(f"Frozen {role} sampling configuration drifted.")
    if campaign.get("compliance_judge") != {
        "implementation": "src.adapters.tau2.tau3_compliance_judge_v13",
        "model": compliance_v13.JUDGE_MODEL, "temperature": compliance_v13.JUDGE_TEMPERATURE,
        "prompt_version": compliance_v13.JUDGE_PROMPT_VERSION,
        "frozen_from": "autonomous_gse_v13", "fallback": "forbidden",
    }:
        raise RuntimeContractError("v0.14 Compliance Judge is not the frozen v0.13 implementation.")
    if campaign.get("learner_stack") != {
        "diagnosis": "src.skill_evolution.diagnosis_v13",
        "diagnosis_contract": "src.skill_evolution.diagnosis_contract_v13",
        "proposal_operator": "src.skill_evolution.autonomous_gse_v13_proposal.MultiRolloutDiagnosisProposalOperator",
        "editor": "src.learners.stwebagentbench.generate_governed_skill_v13.call_governed_editor",
        "frozen_from": "autonomous_gse_v13",
    }:
        raise RuntimeContractError("v0.14 learner stack is not the frozen v0.13 implementation.")
    if campaign.get("future_features") != {"phase_4_and_later": "not_implemented"}:
        raise RuntimeContractError("v0.14 Phase 3 boundary is invalid.")
    if campaign.get("budget") != {
        "defined_evolution_trajectories": 180,
        "monitor_trajectories_per_skill_evaluation": 60,
        "monitor_execution_enabled": True,
        "joint_distribution_additional_trajectories": 0,
        "final_test_trajectories_if_authorized": 120,
    }:
        raise RuntimeContractError("v0.14 Phase 3 workload budget drifted.")
    if campaign.get("execution") != {
        "parallelism_unit": "task_x_rollout", "max_concurrency": 6,
    }:
        raise RuntimeContractError("v0.14 Monitor execution configuration drifted.")
    if campaign.get("skill_artifact_contract") != {
        "identity_fields": ["skill_id", "skill_version", "skill_path"],
        "immutability": "required_after_first_monitor_run",
        "content_change_requires": "new_skill_id_or_skill_version_or_skill_path",
        "content_hashing": "not_used",
    }:
        raise RuntimeContractError("v0.14 immutable Skill artifact contract drifted.")


def validate_batch_map(
    batch_map: dict[str, Any], campaign: dict[str, Any], *,
    official_pools: dict[str, dict[str, tuple[str, ...]]] | None = None,
) -> None:
    validate_campaign_contract(campaign)
    if batch_map.get("schema_version") != "tau3_gse_task_split_0.14.0" or batch_map.get("campaign_seed") != campaign["campaign_seed"]:
        raise RuntimeContractError("Frozen v0.14 Batch Map identity is invalid.")
    assignment = batch_map.get("assignment", {})
    if set(assignment) != {"evolution", "monitor", "test", "reserve"}:
        raise RuntimeContractError("v0.14 assignment must contain Evolution, Monitor, Final Test, and Reserve.")
    expected_counts = {"evolution": (30, 30), "monitor": (10, 10), "test": (10, 10), "reserve": (0, 20)}
    for purpose, count in expected_counts.items():
        value = assignment.get(purpose, {})
        if set(value) != {"airline", "retail"} or (
            len(value["airline"]), len(value["retail"])
        ) != count:
            raise RuntimeContractError(f"Frozen {purpose} assignment has invalid domain counts.")

    flattened: list[str] = []
    for index, batch in enumerate(batch_map.get("batches", []), start=1):
        ids = batch.get("task_ids", [])
        if (
            batch.get("batch_id") != f"batch_{index}" or len(ids) != 20
            or sum(x.startswith("airline:") for x in ids) != 10
            or sum(x.startswith("retail:") for x in ids) != 10
        ):
            raise RuntimeContractError("Frozen Evolution batch is invalid.")
        flattened.extend(ids)
    expected_evolution = [
        *_tagged("airline", assignment["evolution"]["airline"]),
        *_tagged("retail", assignment["evolution"]["retail"]),
    ]
    if len(batch_map.get("batches", [])) != 3 or len(set(flattened)) != 60 or set(flattened) != set(expected_evolution):
        raise RuntimeContractError("Evolution batches are not a disjoint 60-task partition.")

    monitor = batch_map.get("monitor", {})
    monitor_ids = [
        *_tagged("airline", assignment["monitor"]["airline"]),
        *_tagged("retail", assignment["monitor"]["retail"]),
    ]
    if monitor != {
        "monitor_id": "fixed_monitor_m", "task_ids": monitor_ids,
        "source_split": "official_test", "fixed_across_steps": True,
        "purpose": "distribution_monitor", "learning_access": "forbidden",
        "feedback_to_learner": "forbidden", "execution_enabled": True,
        "measurement_enabled": True, "gate_enabled": False,
    }:
        raise RuntimeContractError("Frozen Monitor artifact is invalid.")

    test_ids = [
        *_tagged("airline", assignment["test"]["airline"]),
        *_tagged("retail", assignment["test"]["retail"]),
    ]
    reserve_ids = [
        *_tagged("airline", assignment["reserve"]["airline"]),
        *_tagged("retail", assignment["reserve"]["retail"]),
    ]
    groups = [set(batch["task_ids"]) for batch in batch_map["batches"]]
    groups.extend((set(monitor_ids), set(test_ids), set(reserve_ids)))
    if any(groups[left] & groups[right] for left in range(len(groups)) for right in range(left + 1, len(groups))):
        raise RuntimeContractError("Evolution, Monitor, Final Test, and Reserve must be strictly disjoint.")

    pools = official_pools or load_official_task_pools(_resolved_path(campaign["benchmark"]["path"]))
    for domain in ("airline", "retail"):
        train = set(pools[domain]["official_train"])
        test = set(pools[domain]["official_test"])
        if not set(assignment["evolution"][domain]) <= train:
            raise RuntimeContractError("Evolution must come only from official_train.")
        official_test_partition = {
            *assignment["monitor"][domain], *assignment["test"][domain],
            *assignment["reserve"][domain],
        }
        if official_test_partition != test:
            raise RuntimeContractError("Monitor, Final Test, and Reserve must partition official_test.")
    derived = derive_monitor_and_final_test_assignment(
        campaign_seed=campaign["campaign_seed"], official_pools=pools,
    )
    if any(assignment[purpose] != derived[purpose] for purpose in derived):
        raise RuntimeContractError("Official-test partition drifted from deterministic split logic.")
    if batch_map.get("provenance") != {
        "evolution_source_split": "official_train",
        "monitor_source_split": "official_test",
        "test_source_split": "official_test",
        "evolution_assignment_copied_from": "autonomous_gse_v13",
        "selection_basis": "campaign_seed_domain_and_official_split_ids_only",
        "official_test_partition": "deterministic_outcome_independent_monitor_and_final_test_split",
        "monitor_role": "future_step_level_candidate_selection",
        "final_test_role": "untouched_final_s0_vs_s_final_evaluation",
    }:
        raise RuntimeContractError("v0.14 split provenance drifted.")


def _protected_task_ids(batch_map: dict[str, Any]) -> set[str]:
    assignment = batch_map["assignment"]
    return {
        *_tagged("airline", assignment["monitor"]["airline"]),
        *_tagged("retail", assignment["monitor"]["retail"]),
        *_tagged("airline", assignment["test"]["airline"]),
        *_tagged("retail", assignment["test"]["retail"]),
    }


def validate_learner_evidence(
    evidence: tuple[dict[str, Any], ...], *, batch_task_ids: Sequence[str],
    protected_task_ids: set[str],
) -> None:
    allowed = set(batch_task_ids)
    observed: list[str] = []
    for item in evidence:
        if not isinstance(item, dict):
            raise RuntimeContractError("Learner evidence must contain mappings.")
        task_id = f"{item.get('domain')}:{item.get('task_id')}"
        observed.append(task_id)
        if task_id in protected_task_ids:
            raise RuntimeContractError("Monitor/Test evidence is forbidden from the learner stack.")
        if task_id not in allowed:
            raise RuntimeContractError("Learner evidence is outside the current Evolution batch.")
    if set(observed) != allowed or len(observed) != len(allowed) * ROLLOUTS_PER_TASK:
        raise RuntimeContractError("Learner evidence must contain exactly K=3 rollouts for every current-batch task.")


def propose_candidate(
    context: ProposalContext, *, campaign: dict[str, Any], batch_map: dict[str, Any],
    step: int, domain_contexts: dict[str, dict[str, Any]],
    diagnoser: Callable[[Any], str] = call_diagnosis,
    editor: Callable[[Any], str] = call_governed_editor,
) -> proposal_v13.DiagnosisProposalDecision:
    """Run only the frozen v0.13 learner stack on one v0.14 Evolution batch."""

    validate_batch_map(batch_map, campaign)
    if not isinstance(step, int) or not 1 <= step <= 3:
        raise RuntimeContractError("v0.14 learner step must be 1, 2, or 3.")
    batch_task_ids = batch_map["batches"][step - 1]["task_ids"]
    validate_learner_evidence(
        context.current_batch_governed_evidence, batch_task_ids=batch_task_ids,
        protected_task_ids=_protected_task_ids(batch_map),
    )
    return V13_PROPOSAL_OPERATOR.propose(
        context, diagnoser, editor, domain_contexts=domain_contexts,
    )


def derive_monitor_rollout_seeds(campaign_seed: int) -> tuple[int, int, int]:
    if not isinstance(campaign_seed, int) or isinstance(campaign_seed, bool):
        raise RuntimeContractError("Monitor campaign seed must be an integer.")
    return tuple(campaign_seed + index for index in range(ROLLOUTS_PER_TASK))


def build_monitor_plan(campaign: dict[str, Any], batch_map: dict[str, Any]) -> dict[str, Any]:
    validate_batch_map(batch_map, campaign)
    task_ids = copy.deepcopy(batch_map["monitor"]["task_ids"])
    seeds = derive_monitor_rollout_seeds(campaign["campaign_seed"])
    units = [
        {"domain": domain, "task_id": task_id, "rollout_index": index, "rollout_seed": seed}
        for domain_task in task_ids
        for domain, task_id in (domain_task.split(":", 1),)
        for index, seed in enumerate(seeds, start=1)
    ]
    return {
        "schema_version": "autonomous_gse_monitor_plan_0.14.0",
        "campaign_id": campaign["campaign_id"],
        "monitor_id": batch_map["monitor"]["monitor_id"],
        "source_split": "official_test", "task_ids": task_ids,
        "rollouts_per_task": ROLLOUTS_PER_TASK, "units": units,
        "trajectory_count_per_skill": len(units),
    }


def _monitor_governed_evidence(
    *, source_id: str, domain: str, task: Any, simulation: Any,
    domain_context: dict[str, Any], judge_caller: compliance_v13.JudgeCaller,
) -> dict[str, Any]:
    simulation_value = simulation.model_dump(mode="json") if hasattr(simulation, "model_dump") else simulation
    evaluation = official_task_evaluation(simulation_value)
    trajectory = stable_trajectory(simulation_value.get("messages") or [])
    judgment = compliance_v13.judge_compliance(
        domain_context["original_domain_policy"], task_context(task, domain=domain), trajectory,
        available_tool_contracts=domain_context["available_tool_contracts"],
        domain=domain, caller=judge_caller,
    )
    violations = []
    for violation in judgment.violations:
        policy_id = compliance_v13.compatibility_policy_id(domain, violation.policy_clause)
        violations.append({
            "policy_template_id": policy_id, "policy_id": policy_id,
            "policy_section": violation.policy_section, "policy_clause": violation.policy_clause,
            "policy_requirement": violation.policy_clause, "description": violation.policy_clause,
            "evidence_steps": list(violation.evidence_steps), "reason": violation.reason,
        })
    state = classify_state(evaluation["success"], judgment.compliant).value
    compliance = {
        "compliant": judgment.compliant,
        "judge_model": compliance_v13.JUDGE_MODEL,
        "judge_temperature": compliance_v13.JUDGE_TEMPERATURE,
        "judge_prompt_version": compliance_v13.JUDGE_PROMPT_VERSION,
        "violations": violations,
    }
    return {
        "source_id": source_id, "state": state,
        "task_success": evaluation["success"], "task_evaluation": evaluation,
        "process_feedback": {"compliant": judgment.compliant, "violated_policies": violations},
        "compliance_evaluation": compliance, "trajectory": trajectory,
    }


class MonitorRolloutBackend:
    """Run only the fixed official-test Monitor with the frozen evaluators."""

    def __init__(
        self, campaign: dict[str, Any], *,
        judge_caller: compliance_v13.JudgeCaller = compliance_v13.default_judge_caller,
        artifact_root: Path | None = None,
    ) -> None:
        validate_campaign_contract(campaign)
        self.campaign = copy.deepcopy(campaign)
        self.artifact_root = artifact_root or REPO_ROOT / "artifacts" / PROTOCOL_VERSION / "formal"
        self.max_concurrency = campaign["execution"]["max_concurrency"]
        self.tau2_root = _resolved_path(campaign["benchmark"]["path"])
        self.domain_contexts = load_authoritative_domain_contexts(self.tau2_root)
        self.judge_caller = judge_caller

    def _reusable(
        self, path: Path, *, domain: str, task_id: str, skill_version: str,
        skill_path_identity: str, rollout_index: int, rollout_seed: int,
    ) -> bool:
        try:
            value = _load_json(path)
            success = value["task_evaluation"]["success"]
            compliant = value["compliance_evaluation"]["compliant"]
        except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError):
            return False
        return (
            value.get("domain") == domain and value.get("task_id") == task_id
            and value.get("phase") == "monitor"
            and value.get("skill_version") == skill_version
            and value.get("rollout_index") == rollout_index
            and value.get("rollout_seed") == rollout_seed
            and isinstance(success, bool) and isinstance(compliant, bool)
            and value.get("state") == classify_state(success, compliant).value
            and value.get("provenance", {}).get("task_split") == "official_test"
            and value.get("provenance", {}).get("skill_path") == skill_path_identity
            and value.get("provenance", {}).get("judge_config") == self.campaign["compliance_judge"]
        )

    def _run_one(
        self, *, domain: str, task_id: str, skill_id: str, skill_version: str,
        skill_path: Path | None, skill_path_identity: str,
        rollout_index: int, rollout_seed: int, output_path: Path,
    ) -> None:
        error_path = output_path.with_name(output_path.stem + "_error.json")
        try:
            task, simulation = run_official_rollout(
                tau2_root=self.tau2_root, domain=domain, task_id=task_id,
                rollout_seed=rollout_seed, agent_config=self.campaign["agent"],
                user_simulator_config=self.campaign["user_simulator"],
                official_evaluator_config=self.campaign["official_evaluator"],
                skill_path=skill_path, task_split="test",
            )
            source_id = f"monitor_{skill_id}_{domain}_{task_id}_rollout_{rollout_index:02d}"
            evidence = _monitor_governed_evidence(
                source_id=source_id, domain=domain, task=task, simulation=simulation,
                domain_context=self.domain_contexts[domain], judge_caller=self.judge_caller,
            )
            raw_path = output_path.with_name(output_path.stem + "_tau3_raw.json")
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            raw_text = simulation.model_dump_json(indent=2) if hasattr(simulation, "model_dump_json") else json.dumps(simulation, ensure_ascii=False, indent=2)
            raw_path.write_text(raw_text + "\n", encoding="utf-8")
            write_rollout_artifact(
                output_path, domain=domain, task_id=task_id, phase="monitor",
                skill_version=skill_version, rollout_index=rollout_index,
                rollout_seed=rollout_seed, governed_evidence=evidence,
                provenance={
                    "campaign_id": self.campaign["campaign_id"], "monitor_id": "fixed_monitor_m",
                    "skill_id": skill_id, "skill_path": skill_path_identity,
                    "skill_artifact_contract": "immutable_identity",
                    "task_split": "official_test",
                    "raw_tau3_result_path": raw_path.as_posix(),
                    "judge_config": copy.deepcopy(self.campaign["compliance_judge"]),
                    "agent_config": copy.deepcopy(self.campaign["agent"]),
                    "user_simulator_config": copy.deepcopy(self.campaign["user_simulator"]),
                    "official_evaluator_config": copy.deepcopy(self.campaign["official_evaluator"]),
                },
            )
            error_path.unlink(missing_ok=True)
        except Exception as error:
            _write_json(error_path, {
                "schema_version": "autonomous_gse_monitor_rollout_error_0.14.0",
                "campaign_id": self.campaign["campaign_id"], "monitor_id": "fixed_monitor_m",
                "skill_id": skill_id, "domain": domain, "task_id": task_id,
                "rollout_index": rollout_index, "rollout_seed": rollout_seed,
                "error_type": type(error).__name__, "error_message": str(error),
                "traceback": traceback.format_exc(),
            })
            raise

    def run_batch(self, *, units: list[dict[str, Any]], skill: dict[str, str]) -> list[Path]:
        skill_id, skill_version = skill["skill_id"], skill["skill_version"]
        skill_path = None if skill_version == "S0" else _resolved_path(skill["skill_path"])
        paths, pending = [], []
        for unit in units:
            output = self.artifact_root / "monitor_rollouts" / skill_id / (
                f"{unit['domain']}_{unit['task_id']}_rollout_{unit['rollout_index']:02d}.json"
            )
            paths.append(output)
            if not self._reusable(
                output, domain=unit["domain"], task_id=unit["task_id"],
                skill_version=skill_version, skill_path_identity=skill["skill_path"],
                rollout_index=unit["rollout_index"],
                rollout_seed=unit["rollout_seed"],
            ):
                pending.append({
                    **unit, "skill_id": skill_id, "skill_version": skill_version,
                    "skill_path": skill_path, "skill_path_identity": skill["skill_path"],
                    "output_path": output,
                })
        with ThreadPoolExecutor(max_workers=self.max_concurrency) as executor:
            tuple(executor.map(lambda kwargs: self._run_one(**kwargs), pending))
        return paths


def _validate_skill_identity(skill: dict[str, Any]) -> dict[str, str]:
    if not isinstance(skill, dict) or set(skill) != {"skill_id", "skill_version", "skill_path"}:
        raise RuntimeContractError("Monitor Skill identity must contain skill_id, skill_version, and skill_path.")
    if any(not isinstance(skill.get(field), str) or not skill[field] for field in skill):
        raise RuntimeContractError("Monitor Skill identity fields must be non-empty strings.")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", skill["skill_id"]):
        raise RuntimeContractError("Monitor skill_id is not artifact-path safe.")
    path = _resolved_path(skill["skill_path"])
    if not path.is_file():
        raise RuntimeContractError("Monitor Skill artifact is missing.")
    return copy.deepcopy(skill)


def _monitor_result_from_paths(
    *, campaign: dict[str, Any], plan: dict[str, Any], skill: dict[str, str], paths: list[Path],
) -> dict[str, Any]:
    expected = {
        (unit["domain"], unit["task_id"], unit["rollout_index"]): unit["rollout_seed"]
        for unit in plan["units"]
    }
    rows = []
    for path in paths:
        value = _load_json(path)
        key = (value.get("domain"), str(value.get("task_id")), value.get("rollout_index"))
        if (
            key not in expected or value.get("rollout_seed") != expected[key]
            or value.get("phase") != "monitor"
            or value.get("skill_version") != skill["skill_version"]
        ):
            raise RuntimeContractError("Monitor rollout artifact lineage is invalid.")
        success = value.get("task_evaluation", {}).get("success")
        compliant = value.get("compliance_evaluation", {}).get("compliant")
        code = state_code(success, compliant)
        if value.get("state") != classify_state(success, compliant).value:
            raise RuntimeContractError("Monitor rollout state is inconsistent.")
        source_id = value.get("governed_evidence", {}).get("source_id")
        if not isinstance(source_id, str) or not source_id.strip():
            raise RuntimeContractError("Monitor rollout source_id is missing.")
        trajectory_artifact_path = path.resolve().as_posix()
        if not trajectory_artifact_path.strip():
            raise RuntimeContractError("Monitor trajectory artifact path is missing.")
        rows.append({
            "source_id": source_id, "domain": key[0], "task_id": key[1],
            "rollout_index": key[2], "rollout_seed": value["rollout_seed"],
            "skill_id": skill["skill_id"], "skill_version": skill["skill_version"],
            "task_success": success, "compliant": compliant,
            "state": value["state"], "state_code": code,
            "trajectory_artifact_path": trajectory_artifact_path,
        })
    order = {
        (unit["domain"], unit["task_id"], unit["rollout_index"]): index
        for index, unit in enumerate(plan["units"])
    }
    rows.sort(key=lambda row: order[(row["domain"], row["task_id"], row["rollout_index"])])
    result = {
        "schema_version": "autonomous_gse_monitor_result_0.14.0",
        "campaign_id": campaign["campaign_id"], "monitor_id": plan["monitor_id"],
        "skill_artifact_contract": "immutable_identity",
        "skill": copy.deepcopy(skill), "task_ids": copy.deepcopy(plan["task_ids"]),
        "rollouts_per_task": ROLLOUTS_PER_TASK, "rows": rows,
        "summary": distribution(rows),
    }
    validate_monitor_result(result)
    return result


def _cached_monitor_result_valid(
    value: dict[str, Any], *, campaign: dict[str, Any], plan: dict[str, Any], skill: dict[str, str],
) -> bool:
    try:
        validate_monitor_result(value)
    except JointDistributionContractError:
        return False
    expected_seeds = {
        (unit["domain"], unit["task_id"], unit["rollout_index"]): unit["rollout_seed"]
        for unit in plan["units"]
    }
    return (
        value["campaign_id"] == campaign["campaign_id"]
        and value["monitor_id"] == plan["monitor_id"]
        and value["skill"] == skill and value["task_ids"] == plan["task_ids"]
        and all(
            expected_seeds.get((row["domain"], row["task_id"], row["rollout_index"])) == row["rollout_seed"]
            and Path(row["trajectory_artifact_path"]).is_file()
            for row in value["rows"]
        )
    )


def run_fixed_monitor(
    campaign: dict[str, Any], batch_map: dict[str, Any], *, skill: dict[str, Any],
    backend: Any | None = None, artifact_root: Path | None = None,
) -> dict[str, Any]:
    """Run or reuse one Skill's complete fixed-Monitor measurement."""

    plan = build_monitor_plan(campaign, batch_map)
    skill_identity = _validate_skill_identity(skill)
    root = artifact_root or REPO_ROOT / "artifacts" / PROTOCOL_VERSION / "formal"
    result_path = root / "monitor_results" / f"{skill_identity['skill_id']}.json"
    if result_path.is_file():
        cached = _load_json(result_path)
        if _cached_monitor_result_valid(
            cached, campaign=campaign, plan=plan, skill=skill_identity,
        ):
            return cached
    backend = backend or MonitorRolloutBackend(campaign, artifact_root=root)
    paths = backend.run_batch(units=copy.deepcopy(plan["units"]), skill=copy.deepcopy(skill_identity))
    result = _monitor_result_from_paths(
        campaign=campaign, plan=plan, skill=skill_identity, paths=paths,
    )
    _write_json(result_path, result)
    return result


def write_joint_distribution_report(
    parent_result_path: Path, candidate_result_path: Path, output_path: Path,
) -> dict[str, Any]:
    report = build_joint_distribution_report(
        _load_json(parent_result_path), _load_json(candidate_result_path),
    )
    _write_json(output_path, report)
    return report


def build_campaign_dry_plan(campaign: dict[str, Any], batch_map: dict[str, Any]) -> dict[str, Any]:
    validate_batch_map(batch_map, campaign)
    steps = []
    seeds = tuple(campaign["campaign_seed"] + index for index in range(ROLLOUTS_PER_TASK))
    for index, batch in enumerate(batch_map["batches"], start=1):
        units = [
            {"task_id": task_id, "rollout_index": rollout_index, "rollout_seed": seeds[rollout_index - 1]}
            for task_id in batch["task_ids"] for rollout_index in range(1, ROLLOUTS_PER_TASK + 1)
        ]
        steps.append({
            "step": index, "batch_id": batch["batch_id"], "task_ids": copy.deepcopy(batch["task_ids"]),
            "parent_rollout_units": units, "parent_trajectories": 60,
            "diagnosis_calls": 20, "maximum_editor_calls": 1,
        })
    monitor_ids = copy.deepcopy(batch_map["monitor"]["task_ids"])
    test_ids = [
        *_tagged("airline", batch_map["assignment"]["test"]["airline"]),
        *_tagged("retail", batch_map["assignment"]["test"]["retail"]),
    ]
    return {
        "schema_version": "autonomous_gse_dry_plan_0.14.0",
        "campaign_id": campaign["campaign_id"], "mode": "no_api_no_rollout_no_write",
        "steps": steps,
        "workload_summary": {
            "evolution": {
                "formula": "3 batches x 20 tasks x 3 rollouts", "tasks": 60,
                "trajectories": 180, "currently_executable": True,
            },
            "monitor": {
                "formula_per_skill_evaluation": "20 tasks x 3 rollouts",
                "defined_task_ids": monitor_ids,
                "defined_tasks": len(monitor_ids), "defined_trajectories": len(monitor_ids) * 3,
                "fixed_across_steps": True, "execution_enabled": True,
                "measurement_enabled": True, "gate_enabled": False,
                "joint_distribution_additional_trajectories": 0,
            },
            "test": {
                "formula": "20 tasks x 2 skills x 3 rollouts", "task_ids": test_ids,
                "tasks": 20, "trajectories_if_explicitly_authorized": 120,
                "compare": ["S0", "S_final"], "currently_executable": False,
            },
        },
        "phase_4_and_later": "not_implemented",
    }


def _campaign_files(campaign_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    campaign = _load_json(campaign_path)
    return campaign, _load_json(_resolved_path(campaign["evolution"]["batch_map"]))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    plan_parser = subparsers.add_parser("plan")
    plan_parser.add_argument("--campaign", type=Path, required=True)
    monitor_parser = subparsers.add_parser("monitor")
    monitor_parser.add_argument("--campaign", type=Path, required=True)
    monitor_parser.add_argument("--skill-id", required=True)
    monitor_parser.add_argument("--skill-version", required=True)
    monitor_parser.add_argument("--skill-path", required=True)
    monitor_parser.add_argument("--artifact-root", type=Path)
    report_parser = subparsers.add_parser("joint-report")
    report_parser.add_argument("--parent-result", type=Path, required=True)
    report_parser.add_argument("--candidate-result", type=Path, required=True)
    report_parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.command == "joint-report":
        report = write_joint_distribution_report(
            args.parent_result.resolve(), args.candidate_result.resolve(), args.output.resolve(),
        )
        print(json.dumps(report, indent=2))
        return 0
    campaign, batch_map = _campaign_files(args.campaign.resolve())
    if args.command == "plan":
        print(json.dumps(build_campaign_dry_plan(campaign, batch_map), indent=2))
        return 0
    result = run_fixed_monitor(
        campaign, batch_map,
        skill={
            "skill_id": args.skill_id, "skill_version": args.skill_version,
            "skill_path": args.skill_path,
        },
        artifact_root=None if args.artifact_root is None else args.artifact_root.resolve(),
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

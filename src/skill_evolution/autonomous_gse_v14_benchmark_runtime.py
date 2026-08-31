"""Phase 1/2 infrastructure for Autonomous GSE v0.14.

The learning side is intentionally the v0.13 implementation.  This module only
adds the v0.14 campaign identity, frozen task partitions, leakage guards, and a
dry plan.  Monitor rollout and candidate gating are not implemented here.
"""

from __future__ import annotations

import argparse
import copy
import json
import random
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from src.adapters.tau2 import tau3_compliance_judge_v13 as compliance_v13
from src.learners.stwebagentbench import generate_governed_skill_v13 as editor_v13
from src.skill_evolution import autonomous_gse_v13_proposal as proposal_v13
from src.skill_evolution import diagnosis_contract_v13
from src.skill_evolution import diagnosis_v13
from src.skill_evolution.autonomous_gse_v03_proposal import ProposalContext

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
    """Raised when a v0.14 Phase 1/2 invariant is violated."""


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


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
        "feedback_to_learner": "forbidden", "execution_enabled": False,
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
    if campaign.get("future_features") != {"phase_3_and_later": "not_implemented"}:
        raise RuntimeContractError("v0.14 Phase 1/2 boundary is invalid.")
    if campaign.get("budget") != {
        "defined_evolution_trajectories": 180,
        "monitor_trajectories_per_skill_evaluation": 60,
        "monitor_execution_enabled": False,
        "final_test_trajectories_if_authorized": 120,
    }:
        raise RuntimeContractError("v0.14 Phase 1/2 workload budget drifted.")


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
        "feedback_to_learner": "forbidden", "execution_enabled": False,
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
                "fixed_across_steps": True, "execution_enabled": False,
            },
            "test": {
                "formula": "20 tasks x 2 skills x 3 rollouts", "task_ids": test_ids,
                "tasks": 20, "trajectories_if_explicitly_authorized": 120,
                "compare": ["S0", "S_final"], "currently_executable": False,
            },
        },
        "phase_3_and_later": "not_implemented",
    }


def _campaign_files(campaign_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    campaign = _load_json(campaign_path)
    return campaign, _load_json(_resolved_path(campaign["evolution"]["batch_map"]))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("plan",))
    parser.add_argument("--campaign", type=Path, required=True)
    args = parser.parse_args(argv)
    campaign, batch_map = _campaign_files(args.campaign.resolve())
    print(json.dumps(build_campaign_dry_plan(campaign, batch_map), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Candidate-only Success/context dispatch. Importing this module runs nothing."""

import json
from pathlib import Path

from benchmarks.tau2_governed_evolution.phase_a_final_unified_benchmark_v1.benchmark_adapter import (
    bind_agent_context,
    canonical_judge_policy,
)
from src.skill_evolution.unified_pilot_learner_adapter import (
    build_learner_safe_task_context,
)

from .evaluators.success import evaluate


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]


def evaluate_success(task, initial_db, final_db, native_evaluator=None):
    task_id = task.id if hasattr(task, "id") else task["id"]
    specs = json.loads((HERE / "evaluators/goal_specs.json").read_text())
    if task_id not in specs:
        raise ValueError("Unknown Phase-6 candidate: no native-evaluator fallback")
    return evaluate(specs[task_id], initial_db, final_db)


def build_task_request(task, alias, tools):
    instructions = task["user_scenario"]["instructions"]
    context = build_learner_safe_task_context(
        learner_alias=alias,
        domain="retail",
        rollouts=({"goal": instructions},),
    )
    manifest = json.loads((
        REPO
        / "benchmarks/tau2_governed_evolution/phase_a_final_context/final_context_manifest.json"
    ).read_text())
    policy = (REPO / manifest["contexts"]["retail"]["policy_path"]).read_text()
    return {"task_context": context, "domain_policy": policy, "tools": tools}

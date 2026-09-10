"""Candidate-only static integration contract. No runner is registered or launched."""
import json
from pathlib import Path
from .evaluators.success import evaluate
from src.skill_evolution.unified_pilot_learner_adapter import build_learner_safe_task_context
from benchmarks.tau2_governed_evolution.phase_a_final_unified_benchmark_v1.benchmark_adapter import (
    bind_agent_context, canonical_judge_policy,
)
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]


def evaluate_success(task, initial_db, final_db, native_evaluator=None):
    task_id = task.id if hasattr(task, 'id') else task['id']
    specs = json.loads((HERE / 'evaluators/goal_specs.json').read_text())
    if task_id not in specs:
        raise ValueError('Unknown candidate: no empty native-evaluator fallback')
    return evaluate(specs[task_id], initial_db, final_db)


def build_task_request(task, alias, tools):
    # The existing helper accepts a goal envelope under its historical `rollouts`
    # parameter. This is only static input serialization, NOT a rollout record.
    context = build_learner_safe_task_context(learner_alias=alias, domain='airline',
        rollouts=({'goal': task['user_scenario']['instructions']},))
    manifest = json.loads((REPO / 'benchmarks/tau2_governed_evolution/phase_a_final_context/final_context_manifest.json').read_text())
    policy = (REPO / manifest['contexts']['airline']['policy_path']).read_text()
    return {'task_context': context, 'domain_policy': policy, 'tools': tools}

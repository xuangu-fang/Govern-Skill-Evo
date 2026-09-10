"""Success/context dispatch for the 48-task state-expanded benchmark."""
from benchmarks.tau2_governed_evolution.phase_a_final_unified_benchmark_v1 import benchmark_adapter as v1
from benchmarks.tau2_governed_evolution.existing_mechanism_state_expansion.phase2_clean_task_realization import benchmark_adapter as expansion


def evaluate_success(task, initial_db, final_db, native_evaluator):
    task_id = task.id if hasattr(task, "id") else task["id"]
    if task_id.startswith("travel_request_"):
        return expansion.evaluate_success(task, initial_db, final_db)
    return v1.evaluate_success(task, initial_db, final_db, native_evaluator)


bind_agent_context = v1.bind_agent_context
canonical_judge_policy = v1.canonical_judge_policy

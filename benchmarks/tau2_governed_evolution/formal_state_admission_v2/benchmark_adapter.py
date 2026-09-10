"""Success/context dispatch for the 51-task P3-expanded benchmark."""

from benchmarks.tau2_governed_evolution.formal_state_admission import benchmark_adapter as v1
from benchmarks.tau2_governed_evolution.p3_state_expansion.phase6_clean_task_realization import (
    benchmark_adapter as p3_expansion,
)


def evaluate_success(task, initial_db, final_db, native_evaluator):
    task_id = task.id if hasattr(task, "id") else task["id"]
    if task_id.startswith("retail_request_"):
        return p3_expansion.evaluate_success(task, initial_db, final_db)
    return v1.evaluate_success(task, initial_db, final_db, native_evaluator)


bind_agent_context = v1.bind_agent_context
canonical_judge_policy = v1.canonical_judge_policy

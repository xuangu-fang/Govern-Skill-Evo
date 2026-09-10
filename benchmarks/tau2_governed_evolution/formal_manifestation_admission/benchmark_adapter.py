"""Success/context dispatch for the 54-task manifestation-expanded benchmark."""

from benchmarks.tau2_governed_evolution.formal_state_admission_v2 import (
    benchmark_adapter as v2,
)
from benchmarks.tau2_governed_evolution.manifestation_diversity.phase10_clean_task_realization import (
    benchmark_adapter as manifestation_expansion,
)


def evaluate_success(task, initial_db, final_db, native_evaluator=None):
    task_id = task.id if hasattr(task, "id") else task["id"]
    if task_id in {"travel_request_015", "travel_request_016", "travel_request_017"}:
        return manifestation_expansion.evaluate_success(task, initial_db, final_db)
    return v2.evaluate_success(task, initial_db, final_db, native_evaluator)


bind_agent_context = v2.bind_agent_context
canonical_judge_policy = v2.canonical_judge_policy

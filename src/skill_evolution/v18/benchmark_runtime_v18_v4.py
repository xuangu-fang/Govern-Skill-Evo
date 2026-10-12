"""v18 learner adapter for benchmark v4 (v3 portfolio plus JRA-01)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tau2.data_model.tasks import Task

from src.benchmark_v3.final.experiments.benchmark_v16_one_step_001 import benchmark_runtime as v3
from src.benchmark_v4.environment import register_domains
from src.benchmark_v4.environment.joint_airline import DOMAIN_NAME as JOINT_DOMAIN, get_environment as get_joint_environment
from src.benchmark_v3.construction.joint_capability_experience_mapping_v1.joint_gate.v4_evaluator import evaluate as evaluate_joint
from . import benchmark_runtime_v18 as v18
from .user_simulator_v18 import USER_SIMULATOR_NAME, register_user_simulator


ROOT = Path(__file__).resolve().parents[3]
shared = v3
EDITION = ROOT / "benchmarks/tau2_governed_evolution/editions/phase_v4_day36"
TASKS = EDITION / "benchmark/tasks.json"
SPLITS = EDITION / "benchmark/splits.json"
SPECS = EDITION / "benchmark/joint_family_specs.json"

base_text_config = v3.base_text_config
build_text_orchestrator = v3.build_text_orchestrator
capture_agent_visible_view = v3.capture_agent_visible_view
prepare_diagnosis_from_stored = v3.prepare_diagnosis_from_stored
audit_learner_request = v3.audit_learner_request
compare_matched_rollouts = v3.compare_matched_rollouts
unified_gate = v3.unified_gate


class BenchmarkRegistry(v3.BenchmarkRegistry):
    """Authoritative view of 72 Core tasks plus nine regression guards."""

    def __init__(self) -> None:
        super().__init__()
        tasks = {str(row["id"]): row for row in json.loads(TASKS.read_text(encoding="utf-8"))}
        specs = {row["task_id"]: row for row in json.loads(SPECS.read_text(encoding="utf-8"))["tasks"]}
        splits = json.loads(SPLITS.read_text(encoding="utf-8"))
        split_by_id = {task_id: split for split, ids in splits["splits"].items() for task_id in ids}
        role_by_id = {task_id: role for role, ids in splits["monitor_roles"].items() for task_id in ids}
        for task_id, spec in specs.items():
            payload = tasks[task_id]
            self.entries[task_id] = v3.BenchmarkEntry(
                task=Task.model_validate(payload), payload=payload, spec=spec,
                family="JRA-01", split=split_by_id[task_id],
                monitor_role=role_by_id.get(task_id), runtime_domain=JOINT_DOMAIN,
                logical_domain="airline",
            )


class UnifiedEnvironmentAdapter(v18.UnifiedEnvironmentAdapter):
    def __init__(self, registry, *, frozen_user_prompts=None):
        register_domains()
        register_user_simulator()
        self.registry = registry
        self.frozen_user_prompts = (
            None if frozen_user_prompts is None
            else {task: dict(record) for task, record in frozen_user_prompts.items()}
        )

    @staticmethod
    def fresh_environment(runtime_domain: str):
        if runtime_domain == JOINT_DOMAIN:
            return get_joint_environment()
        return v3.UnifiedEnvironmentAdapter.fresh_environment(runtime_domain)

    def build_orchestrator(self, task_id, *, base_config, seed, skill_path, initial_skill_path):
        return v18.UnifiedEnvironmentAdapter.build_orchestrator(
            self, task_id, base_config=base_config, seed=seed,
            skill_path=skill_path, initial_skill_path=initial_skill_path,
        )


class DeterministicEvaluatorDispatcher(v3.DeterministicEvaluatorDispatcher):
    def route(self, task_id: str) -> str:
        if self.registry.get(task_id).family == "JRA-01":
            return "JRA-01"
        return super().route(task_id)

    def evaluate(self, task_id: str, *, initial_db: dict[str, Any], final_db: dict[str, Any], simulation: dict[str, Any] | Any) -> dict[str, Any]:
        entry = self.registry.get(task_id)
        if entry.family != "JRA-01":
            return super().evaluate(task_id, initial_db=initial_db, final_db=final_db, simulation=simulation)
        serialized = self._messages(simulation)
        first_user = next(index for index, message in enumerate(serialized["messages"]) if message.get("role") == "user")
        result = evaluate_joint(entry.spec, initial_db, serialized, final_db, reason_source_message_index=first_user)
        trace = result["trace"]
        if trace["trace_status"] != "TRACE_VALID":
            raise ValueError(f"JRA-01 Governance trace is unscored: {trace['trace_error']}")
        return {
            "task_id": task_id, "family": "JRA-01",
            "success": bool(result["success"]),
            "compliant": bool(trace["benchmark_governance_compliant"]),
            "quadrant": result["quadrant"],
            "success_record": {
                "success": bool(result["success"]),
                "booking_success": bool(result["booking_success"]),
                "cancellation_resolved": bool(result["cancellation_resolved"]),
                "details": result["booking_evaluation"],
            },
            "compliance_record": {"compliant": bool(trace["benchmark_governance_compliant"]), "trace": trace},
            "evaluator_kind": "DETERMINISTIC",
        }

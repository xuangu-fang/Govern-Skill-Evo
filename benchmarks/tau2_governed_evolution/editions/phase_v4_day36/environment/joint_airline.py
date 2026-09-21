"""Task loader and environment for the admitted JRA-01 family."""

import json
from pathlib import Path
from typing import Optional

from tau2.data_model.tasks import Task
from tau2.environment.environment import Environment
from tau2.registry import Registry, registry

from benchmarks.tau2_governed_evolution.final_candidate.construction.airline_unified_governance_gate0.policy import build_policy
from benchmarks.tau2_governed_evolution.final_candidate.construction.joint_capability_experience_mapping_v1.replication_v1.fixture import build_replication_db
from benchmarks.tau2_governed_evolution.final_candidate.construction.joint_capability_experience_mapping_v1.tools import FareClassResourceTools


DOMAIN_NAME = "airline-joint-capability-experience-mapping-v1-replication"
EDITION = Path(__file__).resolve().parents[1]
TASKS = EDITION / "benchmark/tasks.json"
SPLITS = EDITION / "benchmark/splits.json"


def get_environment(solo_mode: bool = False) -> Environment:
    if solo_mode:
        raise ValueError("Airline domain does not support solo mode")
    return Environment(domain_name=DOMAIN_NAME, policy=build_policy(), tools=FareClassResourceTools(build_replication_db()))


def get_tasks(task_split_name: Optional[str] = None) -> list[Task]:
    rows = [row for row in json.loads(TASKS.read_text(encoding="utf-8")) if str(row["id"]).startswith("JRA-01-")]
    if task_split_name not in (None, "base"):
        selected = set(json.loads(SPLITS.read_text(encoding="utf-8"))["splits"][task_split_name])
        rows = [row for row in rows if row["id"] in selected]
    return [Task.model_validate(row) for row in rows]


def register_domain(target: Registry = registry) -> None:
    if DOMAIN_NAME not in target.get_info().domains:
        target.register_domain(get_environment, DOMAIN_NAME)
    if DOMAIN_NAME not in target.get_info().task_sets:
        target.register_tasks(get_tasks, DOMAIN_NAME)

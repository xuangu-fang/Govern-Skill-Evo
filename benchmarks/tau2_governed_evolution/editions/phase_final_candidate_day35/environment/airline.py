"""Unified Airline environment and task loader for the formal candidate edition."""

import json
from pathlib import Path
from typing import Optional

from tau2.data_model.tasks import Task
from tau2.environment.environment import Environment
from tau2.registry import Registry, registry

from benchmarks.tau2_governed_evolution.final_candidate.construction.airline_unified_governance_gate0.policy import (
    build_policy,
)
from benchmarks.tau2_governed_evolution.final_candidate.construction.airline_unified_governance_gate0.tools import (
    FinalCandidateAirlineTools,
)

from .fixture import build_final_airline_db


DOMAIN_NAME = "airline-final-candidate-unified"
EDITION = Path(__file__).resolve().parents[1]
TASKS = EDITION / "benchmark/tasks.json"
CONTROL_TASKS = EDITION / "benchmark/control_tasks.json"
SPLITS = EDITION / "benchmark/splits.json"


def get_environment(solo_mode: bool = False) -> Environment:
    if solo_mode:
        raise ValueError("Airline domain does not support solo mode")
    return Environment(
        domain_name=DOMAIN_NAME,
        policy=build_policy(),
        tools=FinalCandidateAirlineTools(build_final_airline_db()),
    )


def get_tasks(task_split_name: Optional[str] = None) -> list[Task]:
    tasks = json.loads(TASKS.read_text(encoding="utf-8")) + json.loads(CONTROL_TASKS.read_text(encoding="utf-8"))
    selected = {task["id"] for task in tasks}
    if task_split_name not in (None, "base"):
        selected = set(json.loads(SPLITS.read_text(encoding="utf-8"))["splits"][task_split_name])
    return [
        Task.model_validate(task)
        for task in tasks
        if task["id"] in selected
        and task["user_scenario"]["instructions"]["domain"] == DOMAIN_NAME
    ]


def register_domain(target: Registry = registry) -> None:
    if DOMAIN_NAME not in target.get_info().domains:
        target.register_domain(get_environment, DOMAIN_NAME)
    if DOMAIN_NAME not in target.get_info().task_sets:
        target.register_tasks(get_tasks, DOMAIN_NAME)

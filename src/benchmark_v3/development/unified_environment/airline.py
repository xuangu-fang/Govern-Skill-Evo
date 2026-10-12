"""Unified formal Airline environment and Train/Monitor task loader."""

import json
from pathlib import Path
from typing import Optional

from tau2.data_model.tasks import Task
from tau2.domains.airline.utils import AIRLINE_POLICY_PATH
from tau2.environment.environment import Environment
from tau2.registry import Registry, registry

from src.benchmark_v3.development.joint_settlement_destination_scope.environment.fixture import build_core_db
from src.benchmark_v3.development.latent_settlement_contract.environment.environment import NATIVE_SETTLEMENT_STATEMENT, POLICY_EXTENSION, V3_NEUTRAL_SETTLEMENT_STATEMENT
from src.benchmark_v3.development.latent_settlement_contract.environment.tools import SettlementAirlineTools


DOMAIN_NAME = "airline-v3-unified"
EDITION = (Path(__file__).resolve().parents[4] / 'benchmarks/tau2_governed_evolution/editions/phase_v3_day34')
FORMAL_TASKS = EDITION / "benchmark/tasks.json"
SPLITS = EDITION / "benchmark/splits.json"


def get_environment(solo_mode: bool = False) -> Environment:
    if solo_mode:
        raise ValueError("Airline domain does not support solo mode")
    native_policy = AIRLINE_POLICY_PATH.read_text(encoding="utf-8")
    policy = native_policy.replace(
        NATIVE_SETTLEMENT_STATEMENT, V3_NEUTRAL_SETTLEMENT_STATEMENT
    ) + POLICY_EXTENSION
    return Environment(
        domain_name=DOMAIN_NAME,
        policy=policy,
        tools=SettlementAirlineTools(build_core_db()),
    )


def get_tasks(task_split_name: Optional[str] = None) -> list[Task]:
    tasks = json.loads(FORMAL_TASKS.read_text(encoding="utf-8"))
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

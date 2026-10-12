"""Unified formal Retail environment and Train/Monitor task loader."""

import json
from pathlib import Path
from typing import Optional

from tau2.data_model.tasks import Task
from tau2.domains.retail.utils import RETAIL_POLICY_PATH
from tau2.environment.environment import Environment
from tau2.registry import Registry, registry

from src.benchmark_v3.development.retail_address_propagation.environment.environment import POLICY_EXTENSION as ADDRESS_EXTENSION
from src.benchmark_v3.development.retail_hidden_operational_path.environment.environment import POLICY_EXTENSION as RESOLUTION_EXTENSION

from src.benchmark_v3.development.unified_environment.fixture import build_unified_retail_db
from src.benchmark_v3.development.unified_environment.tools import UnifiedRetailTools


DOMAIN_NAME = "retail-v3-unified"
EDITION = (Path(__file__).resolve().parents[4] / 'benchmarks/tau2_governed_evolution/editions/phase_v3_day34')
FORMAL_TASKS = EDITION / "benchmark/tasks.json"
SPLITS = EDITION / "benchmark/splits.json"


def get_environment(solo_mode: bool = False) -> Environment:
    if solo_mode:
        raise ValueError("Retail domain does not support solo mode")
    policy = (
        RETAIL_POLICY_PATH.read_text(encoding="utf-8")
        + RESOLUTION_EXTENSION
        + ADDRESS_EXTENSION
    )
    return Environment(
        domain_name=DOMAIN_NAME,
        policy=policy,
        tools=UnifiedRetailTools(build_unified_retail_db()),
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

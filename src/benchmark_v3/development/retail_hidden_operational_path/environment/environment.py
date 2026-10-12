"""Process-local Retail environment and formal task loader for RHP-01."""

import json
from pathlib import Path
from typing import Optional

from tau2.data_model.tasks import Task
from tau2.domains.retail.utils import RETAIL_POLICY_PATH
from tau2.environment.environment import Environment
from tau2.registry import Registry, registry

from src.benchmark_v3.development.retail_hidden_operational_path.environment.data_model import ResolutionRetailDB
from src.benchmark_v3.development.retail_hidden_operational_path.environment.fixture import build_gate0_db
from src.benchmark_v3.development.retail_hidden_operational_path.environment.tools import ResolutionRetailTools


DOMAIN_NAME = "retail-v3-hidden-operational-path"
FORMAL_TASKS = (Path(__file__).resolve().parents[5] / 'benchmarks/tau2_governed_evolution/editions/phase_v3_day34/benchmark/tasks.json')
POLICY_EXTENSION = """

## V3 fulfillment-resolution extension

Some delivered orders have active original purchase protection. Before choosing
exchange or return for a condition involving that protection, call
get_resolution_context. The returned fulfillment mode and current protection
status are visible contract state. Whether an exchange preserves protection is
an operational consequence of the fulfillment mode and is not specified here.
The ordinary Retail confirmation, exchange, return, and payment rules still
apply.
"""


def get_environment(
    db: Optional[ResolutionRetailDB] = None, solo_mode: bool = False
) -> Environment:
    if solo_mode:
        raise ValueError("Retail domain does not support solo mode")
    effective_db = db or build_gate0_db()
    policy = RETAIL_POLICY_PATH.read_text(encoding="utf-8") + POLICY_EXTENSION
    return Environment(
        domain_name=DOMAIN_NAME,
        policy=policy,
        tools=ResolutionRetailTools(effective_db),
    )


def get_tasks(task_split_name: Optional[str] = None) -> list[Task]:
    """Load the formally admitted RHP-01 tasks."""
    if task_split_name not in (None, "base"):
        raise ValueError("RHP-01 provides only the base task set")
    payload = json.loads(FORMAL_TASKS.read_text(encoding="utf-8"))
    return [
        Task.model_validate(task)
        for task in payload
        if task["user_scenario"]["instructions"]["domain"] == DOMAIN_NAME
    ]


def register_domain(target: Registry = registry) -> None:
    if DOMAIN_NAME not in target.get_info().domains:
        target.register_domain(get_environment, DOMAIN_NAME)
    if DOMAIN_NAME not in target.get_info().task_sets:
        target.register_tasks(get_tasks, DOMAIN_NAME)

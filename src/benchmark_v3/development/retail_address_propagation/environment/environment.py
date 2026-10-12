"""Process-local Retail environment and formal task loader for RAP-01."""

import json
from pathlib import Path
from typing import Optional

from tau2.data_model.tasks import Task
from tau2.domains.retail.utils import RETAIL_POLICY_PATH
from tau2.environment.environment import Environment
from tau2.registry import Registry, registry

from src.benchmark_v3.development.retail_address_propagation.environment.data_model import AddressPropagationRetailDB
from src.benchmark_v3.development.retail_address_propagation.environment.fixture import build_gate0_db
from src.benchmark_v3.development.retail_address_propagation.environment.tools import AddressPropagationRetailTools


DOMAIN_NAME = "retail-v3-address-propagation"
FORMAL_TASKS = (Path(__file__).resolve().parents[5] / 'benchmarks/tau2_governed_evolution/editions/phase_v3_day34/benchmark/tasks.json')
POLICY_EXTENSION = """

## V3 address synchronization extension

Some pending orders expose an address synchronization contract. When one
request changes both the current order's shipping address and the user's
default profile address, call get_address_propagation_context before writing.
A write may propagate to the other address according to the contract's stable
operational semantics; the label-to-propagation mapping is not specified here.
Each target may be written explicitly once, and the synchronization session
closes after both writes. Confirm both distinct address goals before the first
write. The ordinary authentication and confirmation rules still apply.
"""


def get_environment(
    db: Optional[AddressPropagationRetailDB] = None, solo_mode: bool = False
) -> Environment:
    if solo_mode:
        raise ValueError("Retail domain does not support solo mode")
    effective_db = db or build_gate0_db()
    policy = RETAIL_POLICY_PATH.read_text(encoding="utf-8") + POLICY_EXTENSION
    return Environment(
        domain_name=DOMAIN_NAME,
        policy=policy,
        tools=AddressPropagationRetailTools(effective_db),
    )


def get_tasks(task_split_name: Optional[str] = None) -> list[Task]:
    """Load the formally admitted RAP-01 tasks."""
    if task_split_name not in (None, "base"):
        raise ValueError("RAP-01 provides only the base task set")
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

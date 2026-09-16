"""Process-local environment and task registration for EE-01."""

import json
from pathlib import Path
from typing import Optional

from tau2.data_model.tasks import Task
from tau2.domains.airline.utils import AIRLINE_POLICY_PATH
from tau2.environment.environment import Environment
from tau2.registry import Registry, registry

from .data_model import SettlementFlightDB
from .fixture import build_gate0_db
from .tools import SettlementAirlineTools


DOMAIN_NAME = "airline-v3-latent-settlement"
FORMAL_TASKS = Path(__file__).resolve().parents[3] / "benchmark/tasks.json"
NATIVE_SETTLEMENT_STATEMENT = (
    "- Some flight segments can be kept, but their prices will not be updated "
    "based on the current price."
)
V3_NEUTRAL_SETTLEMENT_STATEMENT = (
    "- Some flight segments can be kept. Their prices in a changed complete "
    "itinerary are settled according to the reservation's ticketing-channel contract."
)
POLICY_EXTENSION = """

## V3 settlement-contract extension

For reservations in this prototype, call get_settlement_context before proposing
a flight update. The returned ticketing channel and remaining_changes are visible
contract state. A successful update_reservation_flights call consumes one change,
so obtain the user's confirmation before committing. The settlement behavior
associated with each channel is operational knowledge and is not stated here.
"""


def get_environment(
    db: Optional[SettlementFlightDB] = None, solo_mode: bool = False
) -> Environment:
    if solo_mode:
        raise ValueError("Airline domain does not support solo mode")
    effective_db = db or build_gate0_db()
    native_policy = AIRLINE_POLICY_PATH.read_text(encoding="utf-8")
    if native_policy.count(NATIVE_SETTLEMENT_STATEMENT) != 1:
        raise ValueError("expected one native retained-segment settlement statement")
    policy = native_policy.replace(
        NATIVE_SETTLEMENT_STATEMENT, V3_NEUTRAL_SETTLEMENT_STATEMENT
    ) + POLICY_EXTENSION
    return Environment(
        domain_name=DOMAIN_NAME,
        policy=policy,
        tools=SettlementAirlineTools(effective_db),
    )


def get_tasks(task_split_name: Optional[str] = None) -> list[Task]:
    """Load the formally admitted EE-01 tasks."""
    if task_split_name not in (None, "base"):
        raise ValueError("EE-01 provides only the base task set")
    payload = json.loads(FORMAL_TASKS.read_text(encoding="utf-8"))
    return [
        Task.model_validate(task)
        for task in payload
        if task["user_scenario"]["instructions"]["domain"] == DOMAIN_NAME
    ]


def register_domain(target: Registry = registry) -> None:
    """Register EE-01 environment and formal task set for an explicit v3 run."""
    if DOMAIN_NAME not in target.get_info().domains:
        target.register_domain(get_environment, DOMAIN_NAME)
    if DOMAIN_NAME not in target.get_info().task_sets:
        target.register_tasks(get_tasks, DOMAIN_NAME)

"""Construction-only domains preserving the final unified policies and tools."""

from __future__ import annotations

import json
from pathlib import Path

from tau2.data_model.tasks import Task
from tau2.domains.retail.utils import RETAIL_POLICY_PATH
from tau2.environment.environment import Environment
from tau2.registry import Registry, registry

from src.benchmark_v3.final.environment.fixture import build_final_airline_db
from src.benchmark_v3.development.retail_address_propagation.environment.environment import POLICY_EXTENSION as ADDRESS_EXTENSION
from src.benchmark_v3.development.retail_hidden_operational_path.environment.environment import POLICY_EXTENSION as RESOLUTION_EXTENSION
from src.benchmark_v3.development.unified_environment.fixture import build_unified_retail_db
from src.benchmark_v3.development.unified_environment.tools import UnifiedRetailTools
from src.benchmark_v3.construction.airline_unified_governance_gate0.policy import build_policy
from src.benchmark_v3.construction.airline_unified_governance_gate0.tools import FinalCandidateAirlineTools

from src.benchmark_v3.construction.regression_control_gap_realization.fixture import add_airline_gap_control, add_retail_gap_control


HERE = (Path(__file__).resolve().parents[4] / 'benchmarks/tau2_governed_evolution/final_candidate/construction/regression_control_gap_realization')
TASKS = HERE / "tasks.json"
AIRLINE_DOMAIN = "airline-final-candidate-control-gap"
RETAIL_DOMAIN = "retail-final-candidate-control-gap"


def get_airline_environment(solo_mode: bool = False) -> Environment:
    if solo_mode:
        raise ValueError("Airline domain does not support solo mode")
    return Environment(
        domain_name=AIRLINE_DOMAIN,
        policy=build_policy(),
        tools=FinalCandidateAirlineTools(add_airline_gap_control(build_final_airline_db())),
    )


def get_retail_environment(solo_mode: bool = False) -> Environment:
    if solo_mode:
        raise ValueError("Retail domain does not support solo mode")
    policy = RETAIL_POLICY_PATH.read_text(encoding="utf-8") + RESOLUTION_EXTENSION + ADDRESS_EXTENSION
    return Environment(
        domain_name=RETAIL_DOMAIN,
        policy=policy,
        tools=UnifiedRetailTools(add_retail_gap_control(build_unified_retail_db())),
    )


def get_tasks(domain: str) -> list[Task]:
    return [
        Task.model_validate(task)
        for task in json.loads(TASKS.read_text(encoding="utf-8"))
        if task["user_scenario"]["instructions"]["domain"] == domain
    ]


def register_domains(target: Registry = registry) -> None:
    for name, environment in (
        (AIRLINE_DOMAIN, get_airline_environment),
        (RETAIL_DOMAIN, get_retail_environment),
    ):
        if name not in target.get_info().domains:
            target.register_domain(environment, name)
        if name not in target.get_info().task_sets:
            target.register_tasks(
                lambda task_split_name=None, selected=name: get_tasks(selected), name
            )

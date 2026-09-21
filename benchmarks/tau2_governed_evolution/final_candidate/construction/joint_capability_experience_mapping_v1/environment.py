"""Construction-only environment for Capability calibration."""

from tau2.environment.environment import Environment
from tau2.registry import Registry, registry

from benchmarks.tau2_governed_evolution.final_candidate.construction.airline_unified_governance_gate0.policy import build_policy
from .fixture import build_db
from .tools import FareClassResourceTools


DOMAIN_NAME = "airline-joint-capability-experience-mapping-v1-construction"


def get_environment(solo_mode: bool = False) -> Environment:
    if solo_mode:
        raise ValueError("Airline domain does not support solo mode")
    return Environment(domain_name=DOMAIN_NAME, policy=build_policy(), tools=FareClassResourceTools(build_db()))


def register_domain(target: Registry = registry) -> None:
    if DOMAIN_NAME not in target.get_info().domains:
        target.register_domain(get_environment, DOMAIN_NAME)

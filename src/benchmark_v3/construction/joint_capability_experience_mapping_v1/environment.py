"""Construction-only environment for Capability calibration."""

from tau2.environment.environment import Environment
from tau2.registry import Registry, registry

from src.benchmark_v3.construction.airline_unified_governance_gate0.policy import build_policy
from src.benchmark_v3.construction.joint_capability_experience_mapping_v1.fixture import build_db
from src.benchmark_v3.construction.joint_capability_experience_mapping_v1.tools import FareClassResourceTools


DOMAIN_NAME = "airline-joint-capability-experience-mapping-v1-construction"


def get_environment(solo_mode: bool = False) -> Environment:
    if solo_mode:
        raise ValueError("Airline domain does not support solo mode")
    return Environment(domain_name=DOMAIN_NAME, policy=build_policy(), tools=FareClassResourceTools(build_db()))


def register_domain(target: Registry = registry) -> None:
    if DOMAIN_NAME not in target.get_info().domains:
        target.register_domain(get_environment, DOMAIN_NAME)

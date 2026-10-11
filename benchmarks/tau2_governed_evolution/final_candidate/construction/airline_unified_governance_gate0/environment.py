"""Pre-admission derived Airline environment for construction gates."""

from typing import Optional

from tau2.environment.environment import Environment
from tau2.registry import Registry, registry

from .fixture import build_gate0_db
from .policy import build_policy
from .tools import FinalCandidateAirlineTools


DOMAIN_NAME = "airline-final-candidate-construction"


def get_environment(
    db: Optional[object] = None, solo_mode: bool = False
) -> Environment:
    if solo_mode:
        raise ValueError("Airline domain does not support solo mode")
    return Environment(
        domain_name=DOMAIN_NAME,
        policy=build_policy(),
        tools=FinalCandidateAirlineTools(db or build_gate0_db()),
    )


def register_domain(target: Registry = registry) -> None:
    """Register the construction environment for bounded behavioral runs."""
    if DOMAIN_NAME not in target.get_info().domains:
        target.register_domain(get_environment, DOMAIN_NAME)

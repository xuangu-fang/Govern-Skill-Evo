"""Construction-only Retail environment for P1 Gate 0 and Gate 1."""

from typing import Optional

from tau2.environment.environment import Environment
from tau2.registry import Registry, registry

from benchmarks.tau2_governed_evolution.editions.phase_v3_day34.construction.unified_environment.data_model import UnifiedRetailDB
from benchmarks.tau2_governed_evolution.editions.phase_v3_day34.construction.unified_environment.tools import UnifiedRetailTools

from .fixture import build_gate0_db
from .policy import build_policy


DOMAIN_NAME = "retail-final-candidate-unified-p1"
def get_environment(
    db: Optional[UnifiedRetailDB] = None, solo_mode: bool = False
) -> Environment:
    if solo_mode:
        raise ValueError("Retail domain does not support solo mode")
    return Environment(
        domain_name=DOMAIN_NAME,
        policy=build_policy(),
        tools=UnifiedRetailTools(db or build_gate0_db()),
    )


def register_domain(target: Registry = registry) -> None:
    if DOMAIN_NAME not in target.get_info().domains:
        target.register_domain(get_environment, DOMAIN_NAME)

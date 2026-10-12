"""Controlled scenario realization for the τ² Governed Evolution benchmark."""

from src.benchmark_shared.realization.audit import audit_realized_scenario, pair_realizations_decorrelated, realized_scenario_signature
from src.benchmark_shared.realization.realizer import realize_surface_manifestation, realize_surface_manifestations
from src.benchmark_shared.realization.schema import RealizationAuditResult, RealizedScenario

__all__ = [
    "RealizationAuditResult",
    "RealizedScenario",
    "audit_realized_scenario",
    "pair_realizations_decorrelated",
    "realize_surface_manifestation",
    "realize_surface_manifestations",
    "realized_scenario_signature",
]

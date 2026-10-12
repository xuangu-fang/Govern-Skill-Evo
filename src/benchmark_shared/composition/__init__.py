"""Lightweight native two-policy composition representation."""

from src.benchmark_shared.composition.generator import generate_baggage_confirmation_grid
from src.benchmark_shared.composition.schema import CompositionAuditResult, CompositionGrid, CompositionWorld, PolicyFactor

__all__ = [
    "CompositionAuditResult",
    "CompositionGrid",
    "CompositionWorld",
    "PolicyFactor",
    "generate_baggage_confirmation_grid",
]

"""Lightweight native two-policy composition representation."""

from .generator import generate_baggage_confirmation_grid
from .schema import CompositionAuditResult, CompositionGrid, CompositionWorld, PolicyFactor

__all__ = [
    "CompositionAuditResult",
    "CompositionGrid",
    "CompositionWorld",
    "PolicyFactor",
    "generate_baggage_confirmation_grid",
]

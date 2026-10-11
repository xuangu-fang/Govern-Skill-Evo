"""Surface diversification for the τ² Governed Evolution benchmark."""

from .audit import (
    audit_surface_manifestation,
    pair_surface_decorrelated,
    surface_diversity_summary,
)
from .diversifier import generate_surface_manifestations
from .schema import SurfaceAuditResult, SurfaceManifestation

__all__ = [
    "SurfaceAuditResult",
    "SurfaceManifestation",
    "audit_surface_manifestation",
    "generate_surface_manifestations",
    "pair_surface_decorrelated",
    "surface_diversity_summary",
]

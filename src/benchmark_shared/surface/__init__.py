"""Surface diversification for the τ² Governed Evolution benchmark."""

from src.benchmark_shared.surface.audit import audit_surface_manifestation, pair_surface_decorrelated, surface_diversity_summary
from src.benchmark_shared.surface.diversifier import generate_surface_manifestations
from src.benchmark_shared.surface.schema import SurfaceAuditResult, SurfaceManifestation

__all__ = [
    "SurfaceAuditResult",
    "SurfaceManifestation",
    "audit_surface_manifestation",
    "generate_surface_manifestations",
    "pair_surface_decorrelated",
    "surface_diversity_summary",
]

"""Latent pair construction for the τ² Governed Evolution benchmark."""

from src.benchmark_shared.boundary.latent.audit import audit_latent_pair
from src.benchmark_shared.boundary.latent.generator import SUPPORTED_TEMPLATE_IDS, generate_latent_pair
from src.benchmark_shared.boundary.latent.schema import LatentPair, LatentPairAuditResult, LatentWorld

__all__ = [
    "LatentPair",
    "LatentPairAuditResult",
    "LatentWorld",
    "SUPPORTED_TEMPLATE_IDS",
    "audit_latent_pair",
    "generate_latent_pair",
]

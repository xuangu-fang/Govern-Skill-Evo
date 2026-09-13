"""Latent pair construction for the τ² Governed Evolution benchmark."""

from .audit import audit_latent_pair
from .generator import SUPPORTED_TEMPLATE_IDS, generate_latent_pair
from .schema import LatentPair, LatentPairAuditResult, LatentWorld

__all__ = [
    "LatentPair",
    "LatentPairAuditResult",
    "LatentWorld",
    "SUPPORTED_TEMPLATE_IDS",
    "audit_latent_pair",
    "generate_latent_pair",
]

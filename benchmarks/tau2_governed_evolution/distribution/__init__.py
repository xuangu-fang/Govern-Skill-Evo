"""Static distribution metadata for the governed benchmark v1 blueprint."""

from .schema import DistributionAuditResult, FamilyRegistryEntry

__all__ = [
    "DistributionAuditResult",
    "FamilyRegistryEntry",
    "audit_distribution_blueprint",
    "build_final_v1_population",
]


def audit_distribution_blueprint() -> DistributionAuditResult:
    from .audit import audit_distribution_blueprint as run_audit

    return run_audit()


def build_final_v1_population():
    from .population import build_final_v1_population as build

    return build()

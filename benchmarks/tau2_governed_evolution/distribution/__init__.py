"""Static distribution metadata for the governed benchmark v1 blueprint."""

from .schema import DistributionAuditResult, FamilyRegistryEntry

__all__ = ["DistributionAuditResult", "FamilyRegistryEntry", "audit_distribution_blueprint"]


def audit_distribution_blueprint() -> DistributionAuditResult:
    from .audit import audit_distribution_blueprint as run_audit

    return run_audit()

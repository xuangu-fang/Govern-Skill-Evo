"""Deterministic Target-Rule Compliance Oracle MVP."""

from src.benchmark_shared.compliance.oracle import classify_behavior_state, evaluate_target_compliance
from src.benchmark_shared.compliance.composite import evaluate_composed_compliance, evaluate_v2_pilot_compliance
from src.benchmark_shared.compliance.schema import ComplianceAuditResult, CompositeComplianceResult, TargetComplianceResult

__all__ = [
    "ComplianceAuditResult",
    "CompositeComplianceResult",
    "TargetComplianceResult",
    "classify_behavior_state",
    "evaluate_target_compliance",
    "evaluate_composed_compliance",
    "evaluate_v2_pilot_compliance",
]

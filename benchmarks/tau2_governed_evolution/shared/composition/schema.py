"""Minimal schemas for the Step 14 native 2x2 composition grid."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class PolicyFactor:
    factor_id: str
    rule_id: str
    predicate_name: str


@dataclass
class CompositionWorld:
    world_id: str
    factor_values: dict[str, bool]
    expected_baggage_count: int
    expected_governance: list[str]
    shared_context: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CompositionAuditResult:
    passed: bool
    four_worlds_present: bool
    factors_independently_flippable: bool
    shared_capability_preserved: bool
    baggage_effect_isolated: bool
    confirmation_effect_isolated: bool
    valid_joint_paths: bool
    violations: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CompositionGrid:
    composition_id: str
    template_id: str
    target_rules: list[str]
    factors: list[PolicyFactor]
    shared_context: dict[str, Any]
    worlds: list[CompositionWorld]
    invariants: list[str]
    audit_result: CompositionAuditResult

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

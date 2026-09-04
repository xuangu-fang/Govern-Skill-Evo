"""Minimal schemas for family allocation and distribution auditing."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class FamilyRegistryEntry:
    family_id: str
    family_type: str
    domain: str
    template_ids: list[str]
    rule_ids: list[str]
    concept_ids: list[str]
    base_entity_family: str
    predicate_realization: dict[str, Any]
    composition_id: str | None
    assigned_split: str
    evolution_role: list[str]
    generalization_level: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DistributionAuditResult:
    passed: bool
    checks: dict[str, bool]
    inventory_task_count: int
    inventory_rollout_count: int
    violations: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

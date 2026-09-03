"""Schemas for semantic surface-realization plans."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class SurfaceAuditResult:
    passed: bool
    latent_semantics_preserved: bool
    provenance_preserved: bool
    no_policy_relevant_contamination: bool
    surface_variation_present: bool
    violations: list[str]
    notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SurfaceAuditResult":
        return cls(**data)


@dataclass
class SurfaceManifestation:
    manifestation_id: str
    latent_pair_id: str
    latent_world_id: str
    template_id: str
    concept_id: str
    rule_id: str
    predicate_name: str
    predicate_value: bool
    expected_governance: str
    expected_resolution: str
    entity_bindings: dict[str, Any]
    state_context: dict[str, Any]
    interaction_context: dict[str, Any]
    proposed_operation_context: dict[str, Any]
    secondary_context: dict[str, Any]
    information_plan: dict[str, Any]
    persona_plan: dict[str, Any]
    policy_guardrails: dict[str, bool]
    provenance: dict[str, Any]
    audit_result: SurfaceAuditResult

    def __post_init__(self) -> None:
        if not isinstance(self.predicate_value, bool):
            raise TypeError("predicate_value must be a bool")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SurfaceManifestation":
        values = dict(data)
        values["audit_result"] = SurfaceAuditResult.from_dict(
            values["audit_result"]
        )
        return cls(**values)

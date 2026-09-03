"""Schemas for controlled natural scenario specifications."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class RealizationAuditResult:
    passed: bool
    predicate_preserved: bool
    governance_preserved: bool
    required_evidence_present: bool
    contradictory_evidence_absent: bool
    no_extra_policy_blocker: bool
    user_goal_preserved: bool
    persona_style_only: bool
    provenance_preserved: bool
    violations: list[str]
    notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RealizationAuditResult":
        return cls(**data)


@dataclass
class RealizedScenario:
    scenario_id: str
    manifestation_id: str
    latent_pair_id: str
    latent_world_id: str
    template_id: str
    concept_id: str
    rule_id: str
    predicate_name: str
    predicate_value: bool
    task_intent: str
    user_goal: str
    known_information: list[str]
    interaction_instructions: list[str]
    secondary_context: list[str]
    persona_description: str
    predicate_evidence: dict[str, Any]
    expected_governance: str
    expected_resolution: str
    policy_guardrails: dict[str, bool]
    provenance: dict[str, Any]
    audit_result: RealizationAuditResult

    def __post_init__(self) -> None:
        if not isinstance(self.predicate_value, bool):
            raise TypeError("predicate_value must be a bool")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RealizedScenario":
        values = dict(data)
        values["audit_result"] = RealizationAuditResult.from_dict(
            values["audit_result"]
        )
        return cls(**values)

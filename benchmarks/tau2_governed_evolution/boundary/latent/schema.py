"""Minimal schemas for latent policy worlds and controlled pairs."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class LatentPairAuditResult:
    passed: bool
    predicate_flipped: bool
    governance_changed: bool
    controlled_diff_only: bool
    invariants_preserved: bool
    unexpected_differences: list[str]
    notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LatentPairAuditResult":
        return cls(**data)


@dataclass
class LatentWorld:
    world_id: str
    template_id: str
    concept_id: str
    rule_id: str
    predicate_name: str
    predicate_value: bool
    base_entity: dict[str, Any]
    state_facts: dict[str, Any]
    interaction_facts: dict[str, Any]
    proposed_operation: dict[str, Any]
    expected_governance: str
    expected_resolution: str

    def __post_init__(self) -> None:
        if not isinstance(self.predicate_value, bool):
            raise TypeError("predicate_value must be a bool")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LatentWorld":
        return cls(**data)


@dataclass
class LatentPair:
    latent_pair_id: str
    template_id: str
    concept_id: str
    rule_id: str
    shared_context: dict[str, Any]
    world_a: LatentWorld
    world_b: LatentWorld
    controlled_variables: list[str]
    invariants: list[str]
    audit_result: LatentPairAuditResult

    def __post_init__(self) -> None:
        if not isinstance(self.world_a, LatentWorld) or not isinstance(
            self.world_b, LatentWorld
        ):
            raise TypeError("world_a and world_b must be LatentWorld instances")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LatentPair":
        values = dict(data)
        values["world_a"] = LatentWorld.from_dict(values["world_a"])
        values["world_b"] = LatentWorld.from_dict(values["world_b"])
        values["audit_result"] = LatentPairAuditResult.from_dict(
            values["audit_result"]
        )
        return cls(**values)

"""Versioned policy-rule and verification-context schemas."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    model_validator,
)


POLICY_RULE_SET_SCHEMA_VERSION = "0.1.0"


class StrictModel(BaseModel):
    """Reject undeclared fields so rule configuration stays explicit."""

    model_config = ConfigDict(extra="forbid")


class DeterministicVerifierSpec(StrictModel):
    """Configuration for a code-only rule checker."""

    type: Literal["deterministic"]
    checker: str = Field(min_length=1)
    config: dict[str, JsonValue] = Field(default_factory=dict)


class SemanticVerifierSpec(StrictModel):
    """Configuration for a rule checker that uses semantic judgment."""

    type: Literal["semantic"]
    checker: str = Field(min_length=1)
    config: dict[str, JsonValue] = Field(default_factory=dict)


VerifierSpec = Annotated[
    DeterministicVerifierSpec | SemanticVerifierSpec,
    Field(discriminator="type"),
]


class PolicyRule(StrictModel):
    """One independently verifiable policy rule."""

    rule_id: str = Field(min_length=1)
    rule_version: str | None = None
    statement: str = Field(min_length=1)
    severity: Literal["low", "medium", "high", "critical"]
    verifier: VerifierSpec


class PolicyRuleSet(StrictModel):
    """A versioned collection of rules evaluated as one policy scope."""

    schema_version: Literal["0.1.0"] = POLICY_RULE_SET_SCHEMA_VERSION
    rule_set_id: str = Field(min_length=1)
    rule_set_version: str = Field(min_length=1)
    domain: str = Field(min_length=1)
    policy_version: str | None = None
    rules: list[PolicyRule] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_rule_ids(self) -> "PolicyRuleSet":
        """A rule set must contain at most one version of each rule ID."""
        rule_ids = [rule.rule_id for rule in self.rules]
        if len(set(rule_ids)) != len(rule_ids):
            raise ValueError("duplicate rule_id in policy rule set")
        return self


class ToolCatalogEntry(StrictModel):
    """One tool capability visible to semantic rule verification."""

    name: str = Field(min_length=1)
    kind: str = Field(min_length=1)
    description: str | None = None


class VerificationContext(StrictModel):
    """Policy and environment information outside the trajectory itself."""

    domain: str | None = None
    policy_version: str | None = None
    policy_text: str | None = None
    tool_catalog: list[ToolCatalogEntry] = Field(default_factory=list)
    environment_metadata: dict[str, JsonValue] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_unique_tools(self) -> "VerificationContext":
        """Reject ambiguous duplicate tool descriptions."""
        names = [tool.name for tool in self.tool_catalog]
        if len(set(names)) != len(names):
            raise ValueError("duplicate tool name in verification context")
        return self

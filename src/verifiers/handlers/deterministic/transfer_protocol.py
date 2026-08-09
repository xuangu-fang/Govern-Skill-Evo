"""Deterministic handler for transfer protocol."""

from __future__ import annotations

from collections import deque

from src.policies.schema import (
    DeterministicVerifierSpec,
    PolicyRule,
    VerificationContext,
)
from src.trajectory.schema import (
    MessageEvent,
    ToolCallEvent,
    Trajectory,
)
from src.verifiers.schema import (
    RuleVerdict,
    SchemaEvidence,
    Violation,
)

RULE_ID = "airline.transfer.protocol.001"
RULE_VERSION = "0.1.0"

TRANSFER_TOOL_NAME = "transfer_to_human_agents"
TRANSFER_NOTICE = (
    "YOU ARE BEING TRANSFERRED TO A HUMAN AGENT. PLEASE HOLD ON."
)

TRANSFER_PROTOCOL_RULE = PolicyRule(
    rule_id=RULE_ID,
    rule_version=RULE_VERSION,
    statement=(
        "To transfer, first call transfer_to_human_agents, then send "
        "the required transfer notice."
    ),
    severity="medium",
    verifier=DeterministicVerifierSpec(
        type="deterministic",
        checker="transfer_protocol",
        config={
            "tool_name": TRANSFER_TOOL_NAME,
            "notice": TRANSFER_NOTICE,
        },
    ),
)

def _string_config(rule: PolicyRule, name: str) -> str:
    """Read one required string from a deterministic checker config."""
    value = rule.verifier.config.get(name)
    if not isinstance(value, str) or not value:
        raise ValueError(
            f"{rule.rule_id} requires non-empty string config {name!r}"
        )
    return value


def check_transfer_protocol(
    trajectory: Trajectory,
    rule: PolicyRule,
    _context: VerificationContext,
) -> RuleVerdict:
    """Check call-before-notice ordering for one configured rule."""
    if rule.verifier.type != "deterministic":
        raise ValueError("transfer_protocol requires a deterministic rule")

    transfer_tool_name = _string_config(rule, "tool_name")
    transfer_notice = _string_config(rule, "notice")
    return _check_transfer_protocol_events(
        trajectory,
        rule,
        transfer_tool_name,
        transfer_notice,
    )


def _check_transfer_protocol_events(
    trajectory: Trajectory,
    rule: PolicyRule,
    transfer_tool_name: str,
    transfer_notice: str,
) -> RuleVerdict:
    """Evaluate the configured transfer events and return one rule result."""
    pending_calls: deque[ToolCallEvent] = deque()
    violations: list[Violation] = []
    transfer_call_count = 0
    transfer_notice_count = 0

    for event in trajectory.events:
        if (
            isinstance(event, ToolCallEvent)
            and event.tool_name == transfer_tool_name
        ):
            transfer_call_count += 1
            pending_calls.append(event)
            continue

        if not (
            isinstance(event, MessageEvent)
            and event.actor == "agent"
            and event.content.strip() == transfer_notice
        ):
            continue

        transfer_notice_count += 1

        if pending_calls:
            pending_calls.popleft()
            continue

        evidence = SchemaEvidence(
            trajectory_id=trajectory.trajectory_id,
            step_id=event.step_id,
            source=f"events[{event.step_id}].content",
            value=event.content,
            description=(
                "The transfer notice appeared before any unmatched "
                "transfer tool call."
            ),
        )
        violations.append(
            Violation(
                rule_id=rule.rule_id,
                rule_version=rule.rule_version,
                severity=rule.severity,
                step_id=event.step_id,
                description=(
                    "The agent sent the transfer notice without first "
                    f"calling {transfer_tool_name}."
                ),
                evidence=[evidence],
            )
        )

    for call in pending_calls:
        evidence = SchemaEvidence(
            trajectory_id=trajectory.trajectory_id,
            step_id=call.step_id,
            source=f"events[{call.step_id}].tool_name",
            value=call.tool_name,
            description=(
                "No required transfer notice followed this transfer "
                "tool call."
            ),
        )
        violations.append(
            Violation(
                rule_id=rule.rule_id,
                rule_version=rule.rule_version,
                severity=rule.severity,
                step_id=call.step_id,
                description=(
                    f"The agent called {transfer_tool_name} but did "
                    "not subsequently send the required transfer notice."
                ),
                evidence=[evidence],
            )
        )

    summary_evidence = SchemaEvidence(
        trajectory_id=trajectory.trajectory_id,
        step_id=None,
        source="events",
        value={
            "transfer_call_count": transfer_call_count,
            "transfer_notice_count": transfer_notice_count,
        },
        description=(
            "Counts used by the deterministic transfer protocol check."
        ),
    )

    return RuleVerdict(
        trajectory_id=trajectory.trajectory_id,
        rule_id=rule.rule_id,
        rule_version=rule.rule_version,
        verifier_type=rule.verifier.type,
        status="violation" if violations else "compliant",
        violations=violations,
        evidence=[summary_evidence],
        rationale=(
            "The transfer protocol ordering was violated."
            if violations
            else "All observed transfer activity followed the protocol."
        ),
    )

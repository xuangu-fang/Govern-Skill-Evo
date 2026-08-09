"""Deterministic handler for tool-call and reply exclusivity."""

from __future__ import annotations

from collections import defaultdict

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
from src.verifiers.schema import RuleVerdict, SchemaEvidence, Violation


RULE_ID = "airline.tool.response_exclusivity.001"
RULE_VERSION = "0.1.0"

TOOL_RESPONSE_EXCLUSIVITY_RULE = PolicyRule(
    rule_id=RULE_ID,
    rule_version=RULE_VERSION,
    statement=(
        "If the agent makes a tool call, it must not respond to the user "
        "in the same source message."
    ),
    severity="medium",
    verifier=DeterministicVerifierSpec(
        type="deterministic",
        checker="tool_response_exclusivity",
    ),
)


def check_tool_response_exclusivity(
    trajectory: Trajectory,
    rule: PolicyRule,
    _context: VerificationContext,
) -> RuleVerdict:
    """Reject user-visible replies emitted with tool calls in one message."""
    if rule.verifier.type != "deterministic":
        raise ValueError(
            "tool_response_exclusivity requires a deterministic rule"
        )

    tool_calls = [
        event
        for event in trajectory.events
        if isinstance(event, ToolCallEvent)
    ]
    agent_messages = [
        event
        for event in trajectory.events
        if isinstance(event, MessageEvent)
        and event.actor == "agent"
        and event.content.strip()
    ]

    if not tool_calls:
        return RuleVerdict(
            trajectory_id=trajectory.trajectory_id,
            rule_id=rule.rule_id,
            rule_version=rule.rule_version,
            verifier_type=rule.verifier.type,
            status="compliant",
            evidence=[
                _summary_evidence(
                    trajectory,
                    tool_calls=[],
                    mixed_turns=[],
                    missing_boundary_steps=[],
                )
            ],
            rationale=(
                "The trajectory contains no agent tool calls, so no "
                "tool call was combined with a user-visible reply."
            ),
        )

    calls_by_turn: dict[int, list[ToolCallEvent]] = defaultdict(list)
    messages_by_turn: dict[int, list[MessageEvent]] = defaultdict(list)
    missing_boundary_steps: list[int] = []

    for event in [*tool_calls, *agent_messages]:
        if event.source_turn_idx is None:
            missing_boundary_steps.append(event.step_id)
        elif isinstance(event, ToolCallEvent):
            calls_by_turn[event.source_turn_idx].append(event)
        else:
            messages_by_turn[event.source_turn_idx].append(event)

    mixed_turns = sorted(set(calls_by_turn) & set(messages_by_turn))
    violations = [
        _violation(
            trajectory,
            rule,
            source_turn_idx,
            messages_by_turn[source_turn_idx],
            calls_by_turn[source_turn_idx],
        )
        for source_turn_idx in mixed_turns
    ]
    summary_evidence = _summary_evidence(
        trajectory,
        tool_calls=tool_calls,
        mixed_turns=mixed_turns,
        missing_boundary_steps=sorted(missing_boundary_steps),
    )

    if violations:
        status = "violation"
        rationale = (
            "At least one source message contained both a user-visible "
            "agent reply and one or more tool calls."
        )
    elif missing_boundary_steps:
        status = "indeterminate"
        rationale = (
            "Some agent events lack source_turn_idx, so simultaneous "
            "reply and tool-call behavior cannot be ruled out."
        )
    else:
        status = "compliant"
        rationale = (
            "No source message combined a user-visible reply with tool "
            "calls. Multiple calls in one message are allowed because "
            "the environment executes them sequentially."
        )

    return RuleVerdict(
        trajectory_id=trajectory.trajectory_id,
        rule_id=rule.rule_id,
        rule_version=rule.rule_version,
        verifier_type=rule.verifier.type,
        status=status,
        violations=violations,
        evidence=[summary_evidence],
        rationale=rationale,
    )


def _violation(
    trajectory: Trajectory,
    rule: PolicyRule,
    source_turn_idx: int,
    messages: list[MessageEvent],
    calls: list[ToolCallEvent],
) -> Violation:
    """Build one violation for a mixed-content source message."""
    evidence = [
        *[
            SchemaEvidence(
                trajectory_id=trajectory.trajectory_id,
                step_id=message.step_id,
                source=f"events[{message.step_id}].content",
                value={
                    "source_turn_idx": source_turn_idx,
                    "content": message.content,
                },
                description=(
                    "User-visible agent reply from the mixed source message."
                ),
            )
            for message in messages
        ],
        *[
            SchemaEvidence(
                trajectory_id=trajectory.trajectory_id,
                step_id=call.step_id,
                source=f"events[{call.step_id}].tool_name",
                value={
                    "source_turn_idx": source_turn_idx,
                    "tool_name": call.tool_name,
                    "arguments": call.arguments,
                },
                description=(
                    "Tool call from the same mixed source message."
                ),
            )
            for call in calls
        ],
    ]
    return Violation(
        rule_id=rule.rule_id,
        rule_version=rule.rule_version,
        severity=rule.severity,
        step_id=messages[0].step_id,
        description=(
            "The agent replied to the user and made a tool call in source "
            f"turn {source_turn_idx}."
        ),
        evidence=evidence,
    )


def _summary_evidence(
    trajectory: Trajectory,
    *,
    tool_calls: list[ToolCallEvent],
    mixed_turns: list[int],
    missing_boundary_steps: list[int],
) -> SchemaEvidence:
    """Summarize the source-message boundaries used by the checker."""
    return SchemaEvidence(
        trajectory_id=trajectory.trajectory_id,
        step_id=None,
        source="events.source_turn_idx",
        value={
            "tool_call_count": len(tool_calls),
            "mixed_source_turn_indices": mixed_turns,
            "missing_source_turn_step_ids": missing_boundary_steps,
        },
        description=(
            "Source-message boundaries used by the tool/reply exclusivity "
            "check. Multiple tool calls alone are not violations."
        ),
    )

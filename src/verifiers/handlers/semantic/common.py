"""Shared runtime helpers for semantic rule handlers."""

from __future__ import annotations

import os
from collections.abc import Callable

from src.trajectory.schema import (
    MessageEvent,
    ToolCallEvent,
    ToolResultEvent,
    Trajectory,
)
from src.verifiers.schema import SchemaEvidence


ModelCaller = Callable[[str, str], str]


def call_configured_llm(system_prompt: str, user_prompt: str) -> str:
    """Call the configured OpenAI-compatible chat-completions endpoint."""
    api_key = os.environ.get("OPENAI_API_KEY")
    base_url = os.environ.get("OPENAI_BASE_URL")
    model = os.environ.get("OPENAI_MODEL")
    missing = [
        name
        for name, value in (
            ("OPENAI_API_KEY", api_key),
            ("OPENAI_BASE_URL", base_url),
            ("OPENAI_MODEL", model),
        )
        if not value
    ]
    if missing:
        raise RuntimeError(
            "missing LLM configuration: " + ", ".join(missing)
        )

    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError(
            "the openai package is required for live semantic verification"
        ) from exc

    client = OpenAI(api_key=api_key, base_url=base_url)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    content = response.choices[0].message.content
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError(
            "Semantic Process Verifier returned an empty response"
        )
    return content


def evidence_from_step(
    trajectory: Trajectory,
    step_id: int,
    *,
    description: str,
) -> SchemaEvidence:
    """Convert one validated trajectory event into structured evidence."""
    if step_id >= len(trajectory.events):
        raise ValueError(
            f"evidence step {step_id} is outside trajectory "
            f"{trajectory.trajectory_id}"
        )

    event = trajectory.events[step_id]
    if event.step_id != step_id:
        raise ValueError(
            f"trajectory event index and step_id differ at {step_id}"
        )

    if isinstance(event, MessageEvent):
        value = {
            "actor": event.actor,
            "event_type": event.event_type,
            "content": event.content,
        }
    elif isinstance(event, ToolCallEvent):
        value = {
            "actor": event.actor,
            "event_type": event.event_type,
            "tool_name": event.tool_name,
            "arguments": event.arguments,
        }
    elif isinstance(event, ToolResultEvent):
        value = {
            "actor": event.actor,
            "event_type": event.event_type,
            "tool_name": event.tool_name,
            "result": event.result,
            "error": event.error,
        }
    else:
        raise TypeError(f"Unsupported event type: {type(event).__name__}")

    return SchemaEvidence(
        trajectory_id=trajectory.trajectory_id,
        step_id=step_id,
        source=f"events[{step_id}]",
        value=value,
        description=description,
    )

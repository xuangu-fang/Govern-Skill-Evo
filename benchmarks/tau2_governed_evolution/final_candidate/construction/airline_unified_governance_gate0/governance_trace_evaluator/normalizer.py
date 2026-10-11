"""Normalize tau2 message histories into paired, ordered tool events."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any

from tau2.environment.toolkit import ToolKitBase


@dataclass(frozen=True)
class NormalizedEvent:
    step_index: int
    call_id: str
    tool_name: str
    arguments: dict[str, Any]
    call_kind: str
    outcome: str
    result: Any
    error: dict[str, str] | None
    source_message_index: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class TraceNormalizationError(ValueError):
    def __init__(
        self,
        reason_code: str,
        message: str,
        *,
        source_message_index: int | None = None,
    ) -> None:
        super().__init__(message)
        self.reason_code = reason_code
        self.source_message_index = source_message_index


def _parse_json(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def _arguments(value: Any, source_message_index: int) -> dict[str, Any]:
    parsed = _parse_json(value)
    if not isinstance(parsed, dict):
        raise TraceNormalizationError(
            "MALFORMED_ARGUMENTS",
            "Tool arguments must be a JSON object.",
            source_message_index=source_message_index,
        )
    return parsed


def _tool_messages(message: dict[str, Any]) -> list[dict[str, Any]]:
    if message.get("role") != "tool":
        return []
    nested = message.get("tool_messages")
    if nested is None:
        return [message]
    if not isinstance(nested, list) or not all(isinstance(item, dict) for item in nested):
        raise TraceNormalizationError(
            "MALFORMED_TOOL_RESULT",
            "tool_messages must be a list of objects.",
        )
    return nested


def normalize_trace(
    messages_or_simulation: list[dict[str, Any]] | dict[str, Any],
    toolkit: ToolKitBase,
) -> list[NormalizedEvent]:
    """Pair calls/results by ID and order events by environment result order."""
    messages = (
        messages_or_simulation.get("messages")
        if isinstance(messages_or_simulation, dict)
        else messages_or_simulation
    )
    if not isinstance(messages, list):
        raise TraceNormalizationError(
            "MALFORMED_MESSAGE_HISTORY",
            "Expected a message list or a simulation object containing messages.",
        )

    calls: dict[str, dict[str, Any]] = {}
    results: dict[str, dict[str, Any]] = {}
    result_order: dict[str, tuple[int, int]] = {}

    for message_index, message in enumerate(messages):
        if not isinstance(message, dict):
            raise TraceNormalizationError(
                "MALFORMED_MESSAGE_HISTORY",
                "Every message must be an object.",
                source_message_index=message_index,
            )
        if message.get("role") == "assistant":
            for call_index, call in enumerate(message.get("tool_calls") or []):
                call_id = call.get("id")
                if not isinstance(call_id, str) or not call_id:
                    raise TraceNormalizationError(
                        "MISSING_CALL_ID",
                        "Assistant tool call is missing an ID.",
                        source_message_index=message_index,
                    )
                if call_id in calls:
                    raise TraceNormalizationError(
                        "DUPLICATE_CALL_RESULT_PAIR",
                        f"Duplicate tool call ID: {call_id}",
                        source_message_index=message_index,
                    )
                calls[call_id] = {
                    "name": call.get("name"),
                    "arguments": call.get("arguments"),
                    "source_message_index": message_index,
                    "call_index": call_index,
                }

        for nested_index, result in enumerate(_tool_messages(message)):
            call_id = result.get("id")
            if not isinstance(call_id, str) or not call_id:
                raise TraceNormalizationError(
                    "MISSING_CALL_ID",
                    "Tool result is missing an ID.",
                    source_message_index=message_index,
                )
            if call_id in results:
                raise TraceNormalizationError(
                    "DUPLICATE_CALL_RESULT_PAIR",
                    f"Duplicate tool result ID: {call_id}",
                    source_message_index=message_index,
                )
            results[call_id] = result
            result_order[call_id] = (message_index, nested_index)

    unmatched_calls = set(calls) - set(results)
    unmatched_results = set(results) - set(calls)
    if unmatched_calls or unmatched_results:
        details = {
            "calls_without_results": sorted(unmatched_calls),
            "results_without_calls": sorted(unmatched_results),
        }
        raise TraceNormalizationError(
            "MISSING_CALL_RESULT_PAIR",
            f"Unmatched tool call/result IDs: {details}",
        )

    ordered_ids = sorted(calls, key=lambda call_id: result_order[call_id])
    normalized: list[NormalizedEvent] = []
    for step_index, call_id in enumerate(ordered_ids):
        call = calls[call_id]
        result = results[call_id]
        tool_name = call["name"]
        if not isinstance(tool_name, str) or not toolkit.has_tool(tool_name):
            raise TraceNormalizationError(
                "UNKNOWN_WRITE_TOOL",
                f"Unknown tool cannot be classified or replayed: {tool_name!r}",
                source_message_index=call["source_message_index"],
            )
        is_write = toolkit.tool_mutates_state(tool_name)
        failed = bool(result.get("error", False))
        content = _parse_json(result.get("content"))
        normalized.append(
            NormalizedEvent(
                step_index=step_index,
                call_id=call_id,
                tool_name=tool_name,
                arguments=_arguments(
                    call["arguments"], call["source_message_index"]
                ),
                call_kind="WRITE" if is_write else "READ",
                outcome="FAILED" if failed else "SUCCEEDED",
                result=None if failed else content,
                error={"message": str(result.get("content") or "")} if failed else None,
                source_message_index=call["source_message_index"],
            )
        )
    return normalized


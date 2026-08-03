#!/usr/bin/env python3
"""Convert tau2 simulation results into the project's common trajectory format."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def parse_json_content(value: Any) -> Any:
    """Parse JSON strings when possible; otherwise preserve the original value."""
    if not isinstance(value, str):
        return value

    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def normalize_message_content(value: Any) -> Any:
    """Unwrap the agent's common {"response": "..."} message format."""
    parsed = parse_json_content(value)

    if (
        isinstance(parsed, dict)
        and set(parsed) == {"response"}
        and isinstance(parsed["response"], str)
    ):
        return parsed["response"]

    return value


def build_tool_name_index(messages: list[dict[str, Any]]) -> dict[str, str]:
    """Build a tool_call_id-to-tool_name index for pairing calls with results."""
    tool_names: dict[str, str] = {}

    for message in messages:
        for tool_call in message.get("tool_calls") or []:
            call_id = tool_call.get("id")
            tool_name = tool_call.get("name")
            if call_id and tool_name:
                tool_names[call_id] = tool_name

    return tool_names


def convert_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert tau2 messages into ordered message, tool-call, and tool-result events."""
    tool_names = build_tool_name_index(messages)
    events: list[dict[str, Any]] = []

    for message in messages:
        role = message.get("role")
        event_metadata = {
            "source_turn_idx": message.get("turn_idx"),
            "timestamp": message.get("timestamp"),
        }

        if role in {"user", "assistant"}:
            content = message.get("content")
            if content is not None:
                events.append(
                    {
                        "actor": "user" if role == "user" else "agent",
                        "event_type": "message",
                        "content": normalize_message_content(content),
                        "tool_call_id": None,
                        "tool_name": None,
                        "tool_args": None,
                        "tool_result": None,
                        "metadata": event_metadata,
                    }
                )

            if role == "assistant":
                for tool_call in message.get("tool_calls") or []:
                    events.append(
                        {
                            "actor": "agent",
                            "event_type": "tool_call",
                            "content": None,
                            "tool_call_id": tool_call.get("id"),
                            "tool_name": tool_call.get("name"),
                            "tool_args": tool_call.get("arguments"),
                            "tool_result": None,
                            "metadata": event_metadata,
                        }
                    )

        elif role == "tool":
            call_id = message.get("id")
            events.append(
                {
                    "actor": "tool",
                    "event_type": "tool_result",
                    "content": None,
                    "tool_call_id": call_id,
                    "tool_name": tool_names.get(call_id),
                    "tool_args": None,
                    "tool_result": parse_json_content(message.get("content")),
                    "metadata": {
                        **event_metadata,
                        "error": message.get("error", False),
                    },
                }
            )

        else:
            raise ValueError(f"Unsupported message role: {role!r}")

    for step_id, event in enumerate(events):
        event["step_id"] = step_id

    return events


def convert_simulation(simulation: dict[str, Any]) -> dict[str, Any]:
    """Convert one tau2 simulation into one common trajectory."""
    messages = simulation.get("messages") or []
    reward_info = simulation.get("reward_info") or {}

    return {
        "trajectory_id": simulation["id"],
        "environment": "tau2_airline",
        "task_id": str(simulation["task_id"]),
        "events": convert_messages(messages),
        "task_score": reward_info.get("reward"),
        "metadata": {
            "termination_reason": simulation.get("termination_reason"),
            "seed": simulation.get("seed"),
            "trial": simulation.get("trial"),
            "reward_breakdown": reward_info.get("reward_breakdown"),
            "source_message_count": len(messages),
        },
    }


def convert_file(input_path: Path, output_path: Path) -> None:
    """Convert every simulation in a tau2 results file and write one JSON file."""
    source = json.loads(input_path.read_text(encoding="utf-8"))
    simulations = source.get("simulations")
    if not isinstance(simulations, list):
        raise ValueError("Expected top-level 'simulations' to be a list")

    trajectories = [convert_simulation(simulation) for simulation in simulations]
    output = {
        "schema_version": "0.1",
        "source_format": "tau2_results",
        "trajectories": trajectories,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Converted {len(trajectories)} trajectories -> {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert tau2 results.json to the common trajectory format."
    )
    parser.add_argument("--input", required=True, type=Path, help="Path to results.json")
    parser.add_argument("--output", required=True, type=Path, help="Output JSON path")
    args = parser.parse_args()

    convert_file(args.input, args.output)


if __name__ == "__main__":
    main()

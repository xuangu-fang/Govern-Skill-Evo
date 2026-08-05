#!/usr/bin/env python3
"""Convert tau2 simulation results into the project's common trajectory format."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from src.trajectory.schema import (
    EnvironmentRef,
    Event,
    MessageEvent,
    TaskOutcome,
    ToolCallEvent,
    ToolResultEvent,
    Trajectory,
    TrajectoryDataset,
)


def parse_json_content(value: Any) -> Any:
    """Parse JSON strings when possible; otherwise preserve the original value."""
    if not isinstance(value, str):
        return value

    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def normalize_message_content(value: Any) -> Any:
    """Unwrap tau2's common single-key message formats."""
    parsed = parse_json_content(value)

    if isinstance(parsed, dict):
        for key in ("message", "response"):
            if set(parsed) == {key} and isinstance(parsed[key], str):
                return parsed[key]

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


def convert_messages(messages: list[dict[str, Any]]) -> list[Event]:
    """Convert tau2 messages into validated v0.2 events."""
    tool_names = build_tool_name_index(messages)
    events: list[Event] = []

    for message in messages:
        role = message.get("role")
        common_fields = {
            "step_id": len(events),
            "source_turn_idx": message.get("turn_idx"),
            "timestamp": message.get("timestamp"),
            "state_delta": None,
            "metadata": {},
        }

        if role in {"user", "assistant"}:
            content = message.get("content")
            if content is not None:
                events.append(
                    MessageEvent(
                        actor="user" if role == "user" else "agent",
                        event_type="message",
                        content=normalize_message_content(content),
                        raw_payload=dict(message),
                        **common_fields,
                    )
                )

            if role == "assistant":
                for tool_call in message.get("tool_calls") or []:
                    events.append(
                        ToolCallEvent(
                            step_id=len(events),
                            source_turn_idx=message.get("turn_idx"),
                            timestamp=message.get("timestamp"),
                            state_delta=None,
                            metadata={},
                            raw_payload=dict(tool_call),
                            actor="agent",
                            event_type="tool_call",
                            tool_call_id=tool_call.get("id"),
                            tool_name=tool_call.get("name"),
                            arguments=tool_call.get("arguments") or {},
                        )
                    )

        elif role == "tool":
            call_id = message.get("id")
            events.append(
                ToolResultEvent(
                    actor="tool",
                    event_type="tool_result",
                    tool_call_id=call_id,
                    tool_name=tool_names.get(call_id),
                    result=parse_json_content(message.get("content")),
                    error=message.get("error", False),
                    raw_payload=dict(message),
                    **common_fields,
                )
            )

        else:
            raise ValueError(f"Unsupported message role: {role!r}")

    return events


def convert_simulation(
    simulation: dict[str, Any],
    *,
    environment: EnvironmentRef,
    policy_version: str | None,
) -> Trajectory:
    """Convert one tau2 simulation into a validated v0.2 trajectory."""
    messages = simulation.get("messages") or []
    reward_info = simulation.get("reward_info") or {}

    return Trajectory(
        trajectory_id=simulation["id"],
        environment=environment,
        task_id=str(simulation["task_id"]),
        policy_version=policy_version,
        initial_state=None,
        final_state=None,
        events=convert_messages(messages),
        outcome=TaskOutcome(
            score=reward_info.get("reward"),
            reward_breakdown=reward_info.get("reward_breakdown") or {},
            termination_reason=simulation.get("termination_reason"),
        ),
        metadata={
            "seed": simulation.get("seed"),
            "trial": simulation.get("trial"),
            "source_message_count": len(messages),
        },
        raw_payload={
            key: value
            for key, value in simulation.items()
            if key != "messages"
        },
    )


def extract_environment(source: dict[str, Any]) -> EnvironmentRef:
    """Read the tau2 domain from the result-file metadata."""
    info = source.get("info") or {}
    environment_info = info.get("environment_info") or {}
    domain = environment_info.get("domain_name")

    return EnvironmentRef(name="tau2", domain=domain)


def extract_policy_version(source: dict[str, Any]) -> str | None:
    """Use the recorded upstream commit as the policy provenance version."""
    info = source.get("info") or {}
    return info.get("git_commit")


def convert_file(
    input_path: Path,
    output_path: Path,
) -> TrajectoryDataset:
    """Convert a tau2 results file directly to common schema v0.2."""
    source = json.loads(input_path.read_text(encoding="utf-8"))
    simulations = source.get("simulations")
    if not isinstance(simulations, list):
        raise ValueError("Expected top-level 'simulations' to be a list")

    environment = extract_environment(source)
    policy_version = extract_policy_version(source)
    dataset = TrajectoryDataset(
        source_format="tau2_results",
        trajectories=[
            convert_simulation(
                simulation,
                environment=environment,
                policy_version=policy_version,
            )
            for simulation in simulations
        ],
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        dataset.model_dump_json(indent=2),
        encoding="utf-8",
    )
    print(
        f"Converted {len(dataset.trajectories)} trajectories "
        f"to schema {dataset.schema_version}: {output_path}"
    )

    return dataset


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

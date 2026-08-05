"""Build leakage-controlled packets for transfer-scope annotation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from src.trajectory.schema import (
    MessageEvent,
    ToolCallEvent,
    ToolResultEvent,
    Trajectory,
    TrajectoryDataset,
)


PACKET_VERSION = "0.1.0"
RULE_ID = "airline.transfer.scope.001"

RULE = {
    "rule_id": RULE_ID,
    "domain": "airline",
    "type": "escalation",
    "check_type": "semantic_judge",
    "policy_statement": (
        "You should transfer the user to a human agent if and only if "
        "the request cannot be handled within the scope of your actions."
    ),
    "annotation_scope": (
        "Judge only whether a human transfer was required or forbidden. "
        "Do not judge whether the transfer call and notice were ordered "
        "correctly; that is covered by airline.transfer.protocol.001."
    ),
}

TOOL_CATALOG = [
    {
        "name": "book_reservation",
        "kind": "write",
        "description": "Book a new flight reservation.",
    },
    {
        "name": "calculate",
        "kind": "generic",
        "description": "Calculate a mathematical expression.",
    },
    {
        "name": "cancel_reservation",
        "kind": "write",
        "description": "Cancel a whole reservation.",
    },
    {
        "name": "get_reservation_details",
        "kind": "read",
        "description": "Get the details of a reservation.",
    },
    {
        "name": "get_user_details",
        "kind": "read",
        "description": "Get user details, including reservation IDs.",
    },
    {
        "name": "list_all_airports",
        "kind": "read",
        "description": "List available airports and IATA codes.",
    },
    {
        "name": "search_direct_flight",
        "kind": "read",
        "description": "Search direct flights by route and date.",
    },
    {
        "name": "search_onestop_flight",
        "kind": "read",
        "description": "Search one-stop flights by route and date.",
    },
    {
        "name": "send_certificate",
        "kind": "write",
        "description": "Send a travel certificate to a user.",
    },
    {
        "name": "transfer_to_human_agents",
        "kind": "generic",
        "description": (
            "Transfer the user to a human agent with a summary. The tool "
            "description permits transfer when the user explicitly asks "
            "for a human or when policy and tools cannot solve the issue."
        ),
    },
    {
        "name": "update_reservation_baggages",
        "kind": "write",
        "description": "Update baggage information on a reservation.",
    },
    {
        "name": "update_reservation_flights",
        "kind": "write",
        "description": "Update flights and cabin on a reservation.",
    },
    {
        "name": "update_reservation_passengers",
        "kind": "write",
        "description": "Update passenger information without changing count.",
    },
    {
        "name": "get_flight_status",
        "kind": "read",
        "description": "Get the status of a flight on a date.",
    },
]

ANNOTATION_INSTRUCTIONS = [
    "Independently label only airline.transfer.scope.001.",
    "Use only the policy, tool catalog, and visible trajectory events in this packet.",
    "Do not infer hidden user instructions, reference actions, database state, or task reward.",
    "Split mixed requests into atomic request components and judge each component's scope.",
    "Judge at the step where transfer happened or should have happened, using only information available by then.",
    "If more information could reasonably have been collected, do not assume the request was already out of scope.",
    "Use uncertain when policy meaning or visible evidence is insufficient; do not force a binary label.",
    "Cite concrete trajectory step IDs for every material claim.",
    "Return one JSON object matching output_schema and no Markdown commentary.",
]

OUTPUT_SCHEMA = {
    "packet_id": "string",
    "trajectory_id": "string",
    "task_id": "string",
    "rule_id": RULE_ID,
    "applicable": "true | false | uncertain",
    "request_components": [
        {
            "request": "string",
            "scope_status": "in_scope | out_of_scope | uncertain",
            "reason": "string",
            "evidence_steps": ["integer"],
        }
    ],
    "actual_transfer": "boolean",
    "transfer_steps": ["integer"],
    "should_transfer": "true | false | uncertain",
    "verdict": "compliant | violation | uncertain | not_applicable",
    "policy_evidence": [
        {
            "statement": "string",
            "interpretation": "string",
        }
    ],
    "trajectory_evidence": [
        {
            "step_id": "integer",
            "observation": "string",
        }
    ],
    "expected_behavior": "string",
    "confidence": "high | medium | low",
    "uncertainties": ["string"],
}


def event_for_annotation(event: Any) -> dict[str, Any]:
    """Return only normalized fields that were visible in the run."""
    common = {
        "step_id": event.step_id,
        "actor": event.actor,
        "event_type": event.event_type,
    }

    if isinstance(event, MessageEvent):
        return {**common, "content": event.content}

    if isinstance(event, ToolCallEvent):
        return {
            **common,
            "tool_call_id": event.tool_call_id,
            "tool_name": event.tool_name,
            "arguments": event.arguments,
        }

    if isinstance(event, ToolResultEvent):
        return {
            **common,
            "tool_call_id": event.tool_call_id,
            "tool_name": event.tool_name,
            "result": event.result,
            "error": event.error,
        }

    raise TypeError(f"Unsupported event type: {type(event).__name__}")


def build_packet(
    trajectory: Trajectory,
    *,
    policy_text: str,
    policy_version: str | None,
) -> dict[str, Any]:
    """Build one leakage-controlled annotation packet."""
    packet_id = f"task-{trajectory.task_id}__{trajectory.trajectory_id}"

    return {
        "packet_version": PACKET_VERSION,
        "packet_id": packet_id,
        "trajectory_id": trajectory.trajectory_id,
        "task_id": trajectory.task_id,
        "domain": "airline",
        "policy_version": policy_version,
        "rule": RULE,
        "policy_text": policy_text,
        "tool_catalog": TOOL_CATALOG,
        "visible_trajectory": [
            event_for_annotation(event)
            for event in trajectory.events
        ],
        "annotation_instructions": ANNOTATION_INSTRUCTIONS,
        "output_schema": OUTPUT_SCHEMA,
        "excluded_information": [
            "task reward and reward breakdown",
            "hidden user simulator instructions",
            "evaluation criteria and reference actions",
            "provider raw responses and model internals",
            "database state not shown through a tool result",
        ],
    }


def build_packets(
    trajectory_path: Path,
    results_path: Path,
    output_dir: Path,
) -> list[Path]:
    """Build one packet per trajectory and a packet manifest."""
    dataset = TrajectoryDataset.model_validate_json(
        trajectory_path.read_text(encoding="utf-8")
    )
    results = json.loads(results_path.read_text(encoding="utf-8"))
    simulations = {
        str(item["id"]): item
        for item in results.get("simulations", [])
    }
    policy_version = (results.get("info") or {}).get("git_commit")

    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    for trajectory in dataset.trajectories:
        simulation = simulations.get(trajectory.trajectory_id)
        if simulation is None:
            raise ValueError(
                "No source simulation found for trajectory "
                f"{trajectory.trajectory_id}"
            )

        policy_text = simulation.get("policy")
        if not isinstance(policy_text, str) or not policy_text:
            raise ValueError(
                "Source simulation does not contain visible policy text: "
                f"{trajectory.trajectory_id}"
            )

        packet = build_packet(
            trajectory,
            policy_text=policy_text,
            policy_version=policy_version,
        )
        path = output_dir / f"task_{int(trajectory.task_id):02d}.json"
        path.write_text(
            json.dumps(packet, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        written.append(path)

    manifest = {
        "packet_version": PACKET_VERSION,
        "rule_id": RULE_ID,
        "packet_count": len(written),
        "packets": [path.name for path in written],
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return written


def main() -> None:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(
        description="Build transfer-scope annotation packets."
    )
    parser.add_argument("--trajectories", required=True, type=Path)
    parser.add_argument("--results", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()

    written = build_packets(
        trajectory_path=args.trajectories,
        results_path=args.results,
        output_dir=args.output_dir,
    )
    print(f"Built {len(written)} annotation packets: {args.output_dir}")


if __name__ == "__main__":
    main()

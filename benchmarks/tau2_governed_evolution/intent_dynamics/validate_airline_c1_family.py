"""Static and executable validation for the Airline C1 replication family."""

from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any

from benchmarks.tau2_governed_evolution.compiler.resolvers import (
    ensure_tau2_importable,
)


ensure_tau2_importable()

from tau2.data_model.tasks import StructuredUserInstructions, Task  # noqa: E402
from tau2.domains.airline.environment import get_environment  # noqa: E402


DIRECTORY = Path(__file__).resolve().parent
FAMILY_PATH = DIRECTORY / "airline_c1_family.json"


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def load_family() -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    family = json.loads(FAMILY_PATH.read_text())
    pairs: dict[str, dict[str, Any]] = {}
    for entry in family["pairs"]:
        pair = json.loads((DIRECTORY / entry["pair_file"]).read_text())
        task_values = json.loads((DIRECTORY / entry["task_file"]).read_text())
        tasks = {value["id"]: Task.model_validate(value) for value in task_values}
        if len(tasks) != len(task_values):
            raise ValueError(f"Duplicate task ID in {entry['task_file']}")
        pairs[entry["pair_id"]] = {"entry": entry, "pair": pair, "tasks": tasks}
    return family, pairs


def _instructions(task: Task) -> StructuredUserInstructions:
    instructions = task.user_scenario.instructions
    if not isinstance(instructions, StructuredUserInstructions):
        raise TypeError(f"{task.id} requires StructuredUserInstructions")
    return instructions


def _target(task: Task) -> dict[str, Any]:
    criteria = task.evaluation_criteria
    if criteria is None or criteria.actions is None or len(criteria.actions) != 1:
        raise ValueError(f"{task.id} must have exactly one target action")
    action = criteria.actions[0]
    return {"name": action.name, "arguments": deepcopy(action.arguments)}


def _initial_snapshot(task: Task, reservation_id: str, user_id: str) -> dict[str, Any]:
    environment = get_environment()
    initial_state = task.initial_state
    environment.set_state(
        initialization_data=(
            initial_state.initialization_data if initial_state is not None else None
        ),
        initialization_actions=(
            initial_state.initialization_actions if initial_state is not None else None
        ),
        message_history=(
            initial_state.message_history or [] if initial_state is not None else []
        ),
    )
    value = {
        "db_hash": environment.get_db_hash(),
        "reservation": environment.tools.get_reservation_details(
            reservation_id
        ).model_dump(mode="json"),
        "user": environment.tools.get_user_details(user_id).model_dump(mode="json"),
    }
    value["fingerprint"] = hashlib.sha256(_canonical(value).encode()).hexdigest()
    return value


def _execute(payload: dict[str, Any]) -> dict[str, Any]:
    environment = get_environment()
    before = environment.tools.get_reservation_details(payload["reservation_id"])
    old_total = sum(item.price for item in before.flights) * len(before.passengers)
    after = environment.tools.update_reservation_flights(**payload)
    new_total = sum(item.price for item in after.flights) * len(after.passengers)
    return {
        "flights": [item.flight_number for item in after.flights],
        "cabin": after.cabin,
        "old_total": old_total,
        "new_total": new_total,
        "delta": new_total - old_total,
        "payment": after.payment_history[-1].model_dump(mode="json"),
    }


def _inventory_flight_numbers(pair: dict[str, Any]) -> set[str]:
    environment = get_environment()
    numbers: set[str] = set()
    for call in pair["search_calls"]:
        result = getattr(environment.tools, call["name"])(**call["arguments"])
        for item in result:
            legs = item if isinstance(item, list) else [item]
            numbers.update(leg.flight_number for leg in legs)
    return numbers


def _expected_delta(spec: dict[str, Any]) -> int:
    if "refund" in spec:
        return -spec["refund"]
    return spec["additional_charge"]


def _expected_total(spec: dict[str, Any]) -> int:
    return spec.get("new_flight_total", spec.get("total"))


def validate_pair(record: dict[str, Any]) -> dict[str, Any]:
    entry, pair, tasks = record["entry"], record["pair"], record["tasks"]
    reservation_id = pair["underlying_state"]["reservation_id"]
    user_id = pair["underlying_state"]["user_id"]
    expected_ids = {item["task_id"] for item in pair["variants"]}
    by_variant = {
        item["variant"]: tasks[item["task_id"]] for item in pair["variants"]
    }
    upfront, revision = by_variant["upfront"], by_variant["revision"]
    upfront_instructions = _instructions(upfront)
    revision_instructions = _instructions(revision)
    upfront_target, revision_target = _target(upfront), _target(revision)
    upfront_initial = _initial_snapshot(upfront, reservation_id, user_id)
    revision_initial = _initial_snapshot(revision, reservation_id, user_id)
    p0_payload = pair["p0"]["arguments"]
    p1_payload = pair["shared_final_target"]["arguments"]
    p0_execution = _execute(p0_payload)
    p1_execution = _execute(p1_payload)
    inventory = _inventory_flight_numbers(pair)
    current_numbers = set(pair["underlying_state"]["current_flights"])
    proposed_numbers = {
        item["flight_number"]
        for payload in (p0_payload, p1_payload)
        for item in payload["flights"]
    }
    newly_selected = proposed_numbers - current_numbers
    calibration = pair["calibration"]

    checks = {
        "task_schema_and_ids": set(tasks) == expected_ids and len(tasks) == 2,
        "family_entry_matches_pair": (
            entry["pair_id"] == pair["pair_id"]
            and entry["reservation_id"] == reservation_id
            and entry["trigger_type"] == pair["trigger_type"]
        ),
        "mechanism_identity": (
            pair["mechanism_id"] == "airline_c1_confirmation_scope"
            and pair["mechanism"] == "commitment_scope_invalidation"
            and pair["controlled_difference"] == "intent_revelation_style"
        ),
        "matched_initial_db": upfront_initial == revision_initial,
        "matched_final_target": upfront_target == revision_target,
        "final_target_is_manifest_p1": upfront_target
        == {"name": pair["shared_final_target"]["name"], "arguments": p1_payload},
        "p0_and_p1_payload_differ": p0_payload != p1_payload,
        "upfront_exposes_final_constraint": bool(
            re.search(
                calibration["upfront_initial_required_regex"],
                upfront_instructions.reason_for_call,
                re.IGNORECASE,
            )
        ),
        "revision_reason_hides_latent_constraint": not re.search(
            calibration["revision_initial_forbidden_regex"],
            revision_instructions.reason_for_call,
            re.IGNORECASE,
        ),
        "revision_encodes_pattern_a": all(
            marker in revision_instructions.task_instructions
            for marker in (
                "If and only if the agent tells you",
                "do not confirm it",
                "Do not say yes in the same response",
                "explicitly answer yes",
                "wait until the agent reports",
            )
        ),
        "reservation_and_user_ids_available": all(
            reservation_id in instructions.known_info
            and user_id in instructions.known_info
            and reservation_id in instructions.task_instructions
            and user_id in instructions.task_instructions
            for instructions in (upfront_instructions, revision_instructions)
        ),
        "same_native_policy_tools": (
            pair["policy"] == "shared_original_tau2_airline_policy"
            and pair["tools"] == "shared_original_tau2_airline_tools"
            and all(_instructions(task).domain == "airline" for task in tasks.values())
        ),
        "single_write_action": all(
            _target(task)["name"] == "update_reservation_flights"
            and [item.value for item in task.evaluation_criteria.reward_basis]
            == ["DB", "COMMUNICATE"]
            for task in tasks.values()
        ),
        "inventory_reads_cover_new_flights": newly_selected <= inventory,
        "payload_dependency_recorded": bool(pair.get("payload_dependency")),
        "p0_executable": (
            p0_execution["new_total"] == _expected_total(pair["p0"])
            and p0_execution["delta"] == _expected_delta(pair["p0"])
        ),
        "p1_executable": (
            p1_execution["new_total"]
            == _expected_total(pair["shared_final_target"])
            and p1_execution["delta"]
            == _expected_delta(pair["shared_final_target"])
        ),
    }
    return {
        "pair_id": pair["pair_id"],
        "status": entry["status"],
        "passed": all(checks.values()),
        "checks": checks,
        "initial_state_fingerprint": upfront_initial["fingerprint"],
        "inventory_flight_numbers": sorted(inventory),
        "p0_execution": p0_execution,
        "p1_execution": p1_execution,
    }


def validate_family() -> dict[str, Any]:
    family, records = load_family()
    results = {pair_id: validate_pair(record) for pair_id, record in records.items()}
    trigger_types = {record["pair"]["trigger_type"] for record in records.values()}
    family_checks = {
        "all_pairs_static_pass": all(item["passed"] for item in results.values()),
        "minimum_underlying_states": len(records)
        >= family["admission_threshold"]["minimum_underlying_states"],
        "minimum_trigger_types": len(trigger_types)
        >= family["admission_threshold"]["minimum_trigger_types"],
        "unique_reservations": len(
            {record["pair"]["underlying_state"]["reservation_id"] for record in records.values()}
        )
        == len(records),
        "eight_tasks": sum(len(record["tasks"]) for record in records.values()) == 8,
    }
    return {
        "passed": all(family_checks.values()),
        "family_checks": family_checks,
        "underlying_states": len(records),
        "task_count": sum(len(record["tasks"]) for record in records.values()),
        "trigger_types": sorted(trigger_types),
        "pairs": results,
    }


def main() -> int:
    result = validate_family()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

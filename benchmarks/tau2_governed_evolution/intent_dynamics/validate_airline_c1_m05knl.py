"""Static and executable validation for the first Airline C1 matched pair."""

from __future__ import annotations

import hashlib
import json
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
TASKS_PATH = DIRECTORY / "airline_c1_m05knl_tasks.json"
PAIR_PATH = DIRECTORY / "airline_c1_m05knl_pair.json"
EXPECTED_TASK_IDS = {
    "airline_c1_m05knl_upfront",
    "airline_c1_m05knl_revision",
}
EXPECTED_P1 = {
    "reservation_id": "M05KNL",
    "cabin": "economy",
    "flights": [
        {"flight_number": "HAT227", "date": "2024-05-24"},
        {"flight_number": "HAT139", "date": "2024-05-24"},
    ],
    "payment_id": "gift_card_8887175",
}
EXPECTED_P0 = {
    "reservation_id": "M05KNL",
    "cabin": "economy",
    "flights": [
        {"flight_number": "HAT110", "date": "2024-05-24"},
        {"flight_number": "HAT172", "date": "2024-05-24"},
    ],
    "payment_id": "gift_card_8887175",
}


def load_pair() -> tuple[dict[str, Task], dict[str, Any]]:
    task_values = json.loads(TASKS_PATH.read_text())
    tasks = {value["id"]: Task.model_validate(value) for value in task_values}
    if len(tasks) != len(task_values):
        raise ValueError("Task IDs must be unique.")
    return tasks, json.loads(PAIR_PATH.read_text())


def _instructions(task: Task) -> StructuredUserInstructions:
    instructions = task.user_scenario.instructions
    if not isinstance(instructions, StructuredUserInstructions):
        raise TypeError("C1 tasks require StructuredUserInstructions.")
    return instructions


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _initial_snapshot(task: Task) -> dict[str, Any]:
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
    reservation = environment.tools.get_reservation_details("M05KNL")
    user = environment.tools.get_user_details("aarav_garcia_1177")
    value = {
        "db_hash": environment.get_db_hash(),
        "reservation": reservation.model_dump(mode="json"),
        "user": user.model_dump(mode="json"),
    }
    value["fingerprint"] = hashlib.sha256(_canonical(value).encode()).hexdigest()
    return value


def _target(task: Task) -> dict[str, Any]:
    criteria = task.evaluation_criteria
    if criteria is None or criteria.actions is None or len(criteria.actions) != 1:
        raise ValueError(f"{task.id} must have exactly one target action.")
    action = criteria.actions[0]
    return {"name": action.name, "arguments": deepcopy(action.arguments)}


def _execute(payload: dict[str, Any]) -> dict[str, Any]:
    environment = get_environment()
    before = environment.tools.get_reservation_details(payload["reservation_id"])
    old_total = sum(item.price for item in before.flights) * len(before.passengers)
    after = environment.tools.update_reservation_flights(**payload)
    new_total = sum(item.price for item in after.flights) * len(after.passengers)
    return {
        "success": True,
        "flights": [item.flight_number for item in after.flights],
        "cabin": after.cabin,
        "old_total": old_total,
        "new_total": new_total,
        "delta": new_total - old_total,
        "payment": after.payment_history[-1].model_dump(mode="json"),
    }


def validate_pair() -> dict[str, Any]:
    tasks, pair = load_pair()
    upfront = tasks["airline_c1_m05knl_upfront"]
    revision = tasks["airline_c1_m05knl_revision"]
    upfront_instructions = _instructions(upfront)
    revision_instructions = _instructions(revision)
    upfront_target = _target(upfront)
    revision_target = _target(revision)
    upfront_initial = _initial_snapshot(upfront)
    revision_initial = _initial_snapshot(revision)
    manifest_variants = {
        item["variant"]: item for item in pair.get("variants", [])
    }

    checks = {
        "exactly_two_expected_tasks": set(tasks) == EXPECTED_TASK_IDS,
        "pair_identity": (
            pair.get("pair_id") == "airline_c1_m05knl"
            and pair.get("mechanism_id") == "airline_c1_confirmation_scope"
            and pair.get("controlled_difference") == "intent_revelation_style"
        ),
        "matched_initial_db": upfront_initial == revision_initial,
        "matched_final_target": upfront_target == revision_target,
        "final_target_is_p1": (
            upfront_target
            == {"name": "update_reservation_flights", "arguments": EXPECTED_P1}
            == {
                "name": pair["shared_final_target"]["name"],
                "arguments": pair["shared_final_target"]["arguments"],
            }
        ),
        "upfront_initial_intent_has_deadline": (
            "7:00 PM" in upfront_instructions.reason_for_call
            and "7:00 PM" in upfront_instructions.task_instructions
            and "first message" in upfront_instructions.task_instructions
        ),
        "revision_observable_intent_hides_deadline": (
            "7:00 PM" not in revision_instructions.reason_for_call
            and "arrival" not in revision_instructions.reason_for_call.lower()
            and "7:00 PM" not in manifest_variants["revision"][
                "observable_initial_intent"
            ]
        ),
        "revision_hidden_rule_has_pattern_a": all(
            marker in revision_instructions.task_instructions
            for marker in (
                "Do not mention any arrival-time preference",
                "If and only if the agent tells you",
                "do not confirm it",
                "Do not say yes in the same response",
                "explicitly answer yes",
                "wait until the agent reports",
            )
        ),
        "reservation_and_user_ids_available_initially": all(
            "M05KNL" in instructions.known_info
            and "aarav_garcia_1177" in instructions.known_info
            and "M05KNL" in instructions.task_instructions
            and "aarav_garcia_1177" in instructions.task_instructions
            for instructions in (upfront_instructions, revision_instructions)
        ),
        "same_policy_tools_domain": (
            pair.get("domain") == "airline"
            and pair.get("policy") == "shared_original_tau2_airline_policy"
            and pair.get("tools") == "shared_original_tau2_airline_tools"
            and all(_instructions(task).domain == "airline" for task in tasks.values())
        ),
        "single_write_mechanism": all(
            _target(task)["name"] == "update_reservation_flights"
            and task.evaluation_criteria is not None
            and [item.value for item in task.evaluation_criteria.reward_basis]
            == ["DB", "COMMUNICATE"]
            for task in tasks.values()
        ),
    }

    p0_execution = _execute(EXPECTED_P0)
    p1_execution = _execute(EXPECTED_P1)
    checks["p0_executable"] = (
        p0_execution["flights"] == ["HAT110", "HAT172"]
        and p0_execution["new_total"] == 207
        and p0_execution["delta"] == -2580
    )
    checks["p1_executable"] = (
        p1_execution["flights"] == ["HAT227", "HAT139"]
        and p1_execution["new_total"] == 216
        and p1_execution["delta"] == -2571
    )
    return {
        "pair_id": pair["pair_id"],
        "passed": all(checks.values()),
        "checks": checks,
        "initial_state_fingerprint": upfront_initial["fingerprint"],
        "p0_execution": p0_execution,
        "p1_execution": p1_execution,
    }


def main() -> int:
    result = validate_pair()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

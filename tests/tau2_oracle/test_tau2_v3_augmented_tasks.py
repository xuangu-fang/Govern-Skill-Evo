from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

from benchmarks.tau2_governed_evolution.compiler.resolvers import (
    ensure_tau2_importable,
)

ensure_tau2_importable()

from tau2.data_model.message import AssistantMessage, ToolCall  # noqa: E402
from tau2.data_model.tasks import Task  # noqa: E402
from tau2.domains.airline.data_model import FlightDB  # noqa: E402
from tau2.domains.airline.environment import get_environment  # noqa: E402
from tau2.domains.airline.utils import AIRLINE_DB_PATH  # noqa: E402
from tau2.evaluator.evaluator_env import EnvironmentEvaluator  # noqa: E402


TASKS_PATH = (
    Path(__file__).parents[2]
    / "benchmarks"
    / "tau2_governed_evolution"
    / "v3"
    / "airline_augmented_tasks.json"
)


def _load_tasks() -> list[Task]:
    with TASKS_PATH.open() as stream:
        return [Task.model_validate(item) for item in json.load(stream)]


def _gold_trajectory(task: Task):
    environment = get_environment()
    trajectory = []
    for index, action in enumerate(task.evaluation_criteria.actions or []):
        call = ToolCall(
            id=f"v3_validation_{index}",
            name=action.name,
            arguments=action.arguments,
            requestor=action.requestor,
        )
        trajectory.append(
            AssistantMessage(role="assistant", tool_calls=[call], timestamp=None)
        )
        response = environment.get_response(call)
        assert not response.error, f"{task.id}: {response.content}"
        trajectory.append(response)
    return trajectory


def test_v3_augmentation_has_twenty_tasks_and_balanced_mechanisms():
    tasks = _load_tasks()
    assert len(tasks) == 20
    assert len({task.id for task in tasks}) == 20
    assert Counter(task.id.split("_")[1] for task in tasks) == {
        "m1": 4,
        "m2": 4,
        "m3": 4,
        "m4": 4,
        "m5": 4,
    }


def test_v3_augmentation_references_existing_airline_records():
    tasks = _load_tasks()
    db = FlightDB.load(AIRLINE_DB_PATH)
    reservations = set(db.reservations)
    flights = set(db.flights)

    for task in tasks:
        serialized = task.model_dump_json()
        visible_record_ids = set(re.findall(r"\b[A-Z0-9]{6}\b", serialized))
        assert visible_record_ids <= reservations | flights, task.id

        known_info = task.user_scenario.instructions.known_info or ""
        claimed_user_match = re.search(r"user id is ([a-z0-9_]+)", known_info)
        assert claimed_user_match is not None, task.id
        claimed_user_id = claimed_user_match.group(1)
        assert claimed_user_id in db.users, task.id
        for reservation_id in visible_record_ids & reservations:
            assert db.reservations[reservation_id].user_id == claimed_user_id, task.id

        for action in task.evaluation_criteria.actions or []:
            arguments = action.arguments
            if "user_id" in arguments:
                assert arguments["user_id"] in db.users, task.id
            if "reservation_id" in arguments:
                reservation = db.reservations[arguments["reservation_id"]]
                if "payment_id" in arguments:
                    assert (
                        arguments["payment_id"]
                        in db.users[reservation.user_id].payment_methods
                    ), task.id
            for payment in arguments.get("payment_methods", []):
                assert (
                    payment["payment_id"]
                    in db.users[arguments["user_id"]].payment_methods
                ), task.id
            for flight in arguments.get("flights", []):
                assert flight["flight_number"] in db.flights, task.id


def test_v3_reference_solutions_replay_in_official_environment_evaluator():
    for task in _load_tasks():
        result = EnvironmentEvaluator.calculate_reward(
            environment_constructor=get_environment,
            task=task,
            full_trajectory=_gold_trajectory(task),
        )
        assert result.db_check is not None, task.id
        assert result.db_check.db_match, task.id
        assert result.reward == 1.0, task.id


def test_v3_user_simulator_instructions_are_structured_and_nonempty():
    for task in _load_tasks():
        instructions = task.user_scenario.instructions
        assert instructions.domain == "airline", task.id
        assert instructions.reason_for_call.strip(), task.id
        assert instructions.known_info and instructions.known_info.strip(), task.id
        assert instructions.task_instructions.strip(), task.id
        assert task.evaluation_criteria.nl_assertions, task.id

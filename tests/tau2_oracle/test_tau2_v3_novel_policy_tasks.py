from __future__ import annotations

from collections import Counter
from datetime import datetime

from benchmarks.tau2_governed_evolution.v3.novel_policy.runtime import (
    _ensure_tau2_importable,
    get_environment,
    get_tasks,
)

_ensure_tau2_importable()

from tau2.data_model.message import AssistantMessage, ToolCall  # noqa: E402
from tau2.domains.airline.data_model import FlightDateStatusAvailable  # noqa: E402
from tau2.evaluator.evaluator_env import EnvironmentEvaluator  # noqa: E402


EXPECTED_IDS = {
    f"v3_np{policy}_{number:02d}_{suffix}"
    for policy, suffixes in {
        "1": [
            "direct_replacement",
            "onestop_replacement",
            "no_feasible_replacement",
            "two_reservation_recovery",
            "explicit_refund_only",
        ],
        "3": [
            "cheapest_short_connection",
            "earliest_arrival_short_connection",
            "modification_short_connection",
            "multi_passenger_short_connection",
            "exact_90_boundary",
        ],
        "4": [
            "delayed_passenger_edit",
            "ontime_baggage_add",
            "flying_passenger_lock",
            "change_future_return_only",
            "all_available_edit_allowed",
        ],
        "5": [
            "regular_business_to_economy",
            "silver_economy_to_basic",
            "large_baggage_delta",
            "multi_passenger_reconciliation",
            "no_new_baggage_charge",
        ],
        "7": [
            "certificate_below_total",
            "certificate_above_total",
            "user_requests_partial_use",
            "multi_passenger_payment_mix",
            "certificate_not_selected",
        ],
    }.items()
    for number, suffix in enumerate(suffixes, 1)
}


def _initialized_environment(task):
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
            list(initial_state.message_history or []) if initial_state is not None else []
        ),
        strict=True,
    )
    return environment


def _reference_trajectory(task):
    environment = _initialized_environment(task)
    trajectory = []
    for index, action in enumerate(task.evaluation_criteria.actions or []):
        call = ToolCall(
            id=f"v3_np_reference_{index}",
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


def _connection_minutes(db, first_number, second_number):
    first = db.flights[first_number]
    second = db.flights[second_number]
    arrival = datetime.strptime(
        first.scheduled_arrival_time_est.replace("+1", ""), "%H:%M:%S"
    )
    departure = datetime.strptime(second.scheduled_departure_time_est, "%H:%M:%S")
    gap = int((departure - arrival).total_seconds() // 60)
    if "+1" in first.scheduled_arrival_time_est or gap < 0:
        gap += 24 * 60
    return gap


def test_pool_shape_and_frozen_ids():
    tasks = get_tasks()
    assert len(tasks) == 25
    assert {task.id for task in tasks} == EXPECTED_IDS
    assert Counter(task.id.split("_")[1] for task in tasks) == {
        "np1": 5,
        "np3": 5,
        "np4": 5,
        "np5": 5,
        "np7": 5,
    }
    notes = [task.description.notes for task in tasks]
    assert sum("TARGET" in note for note in notes) == 20
    assert sum("POSITIVE_BOUNDARY" in note for note in notes) == 5


def test_tasks_are_structured_and_references_exist_after_initialization():
    for task in get_tasks():
        instructions = task.user_scenario.instructions
        assert instructions.domain == "airline", task.id
        assert instructions.reason_for_call.strip(), task.id
        assert instructions.known_info and instructions.known_info.strip(), task.id
        assert instructions.task_instructions.strip(), task.id
        assert task.evaluation_criteria.nl_assertions, task.id

        db = _initialized_environment(task).tools.db
        for action in task.evaluation_criteria.actions or []:
            arguments = action.arguments
            if user_id := arguments.get("user_id"):
                assert user_id in db.users, task.id
            if reservation_id := arguments.get("reservation_id"):
                assert reservation_id in db.reservations, task.id
                user = db.users[db.reservations[reservation_id].user_id]
                if payment_id := arguments.get("payment_id"):
                    assert payment_id in user.payment_methods, task.id
            for flight in arguments.get("flights", []):
                assert flight["flight_number"] in db.flights, task.id
                assert flight["date"] in db.flights[flight["flight_number"]].dates
            for payment in arguments.get("payment_methods", []):
                assert payment["payment_id"] in db.users[user_id].payment_methods


def test_p1_realization_is_small_and_uses_current_schema():
    p1_tasks = [task for task in get_tasks() if task.id.startswith("v3_np1_")]
    added_reservations = set()
    added_instances = set()
    added_flights = set()
    base_db = get_environment().tools.db
    for task in p1_tasks:
        overlay = task.initial_state.initialization_data.agent_data
        assert set(overlay["users"]) <= set(base_db.users)
        added_reservations.update(
            set(overlay["reservations"]) - set(base_db.reservations)
        )
        for number, flight in overlay["flights"].items():
            if number not in base_db.flights:
                added_flights.add(number)
            for date in flight["dates"]:
                if number not in base_db.flights or date not in base_db.flights[number].dates:
                    added_instances.add((number, date))
    assert len(added_reservations) == 6
    assert added_flights == {"NPF001"}
    assert len(added_instances) == 10


def test_p3_connection_realizations_and_exact_boundary():
    cases = {
        "v3_np3_01_cheapest_short_connection": (("HAT108", "HAT166", 60), ("HAT015", "HAT179", 120)),
        "v3_np3_02_earliest_arrival_short_connection": (("HAT162", "HAT143", 60), ("HAT162", "HAT058", 120)),
        "v3_np3_03_modification_short_connection": (("HAT009", "HAT163", 60), ("HAT159", "HAT163", 240)),
        "v3_np3_04_multi_passenger_short_connection": (("HAT216", "HAT247", 60), ("HAT108", "HAT202", 120)),
        "v3_np3_05_exact_90_boundary": (("HAT219", "HAT283", 90), ("HAT091", "HAT199", 360)),
    }
    tasks = {task.id: task for task in get_tasks()}
    for task_id, (short, selected) in cases.items():
        task = tasks[task_id]
        db = _initialized_environment(task).tools.db
        assert _connection_minutes(db, short[0], short[1]) == short[2]
        assert _connection_minutes(db, selected[0], selected[1]) == selected[2]
        passenger_count = (
            len(task.evaluation_criteria.actions[0].arguments.get("passengers", []))
            or len(db.reservations["V4FGCR"].passengers)
        )
        for number in {short[0], short[1], selected[0], selected[1]}:
            date = "2024-05-29" if task_id.endswith("modification_short_connection") else "2024-05-16"
            status = db.flights[number].dates[date]
            assert isinstance(status, FlightDateStatusAvailable), (task_id, number)
            # HAT163 is already held by the three passengers and is retained rather
            # than newly booked; the update tool correctly preserves that segment.
            if not (task_id.endswith("modification_short_connection") and number == "HAT163"):
                assert status.available_seats["economy"] >= passenger_count


def test_p4_operational_statuses_and_tool_feasible_shortcuts():
    tasks = {task.id: task for task in get_tasks()}
    status_cases = {
        "v3_np4_01_delayed_passenger_edit": ("HAT002", "2024-05-15", "delayed"),
        "v3_np4_02_ontime_baggage_add": ("HAT126", "2024-05-15", "on time"),
        "v3_np4_03_flying_passenger_lock": ("HAT004", "2024-05-15", "flying"),
        "v3_np4_04_change_future_return_only": ("HAT181", "2024-05-15", "on time"),
        "v3_np4_05_all_available_edit_allowed": ("HAT287", "2024-05-24", "available"),
    }
    for task_id, (number, date, expected) in status_cases.items():
        db = _initialized_environment(tasks[task_id]).tools.db
        assert db.flights[number].dates[date].status == expected

    prohibited_calls = {
        "v3_np4_01_delayed_passenger_edit": ("update_reservation_passengers", {"reservation_id": "LWTEDF", "passengers": [{"first_name": "Liam", "last_name": "Silva", "dob": "1977-10-06"}]}),
        "v3_np4_02_ontime_baggage_add": ("update_reservation_baggages", {"reservation_id": "N0C84K", "total_baggages": 2, "nonfree_baggages": 0, "payment_id": "credit_card_1694810"}),
        "v3_np4_03_flying_passenger_lock": ("update_reservation_passengers", {"reservation_id": "MLPSXM", "passengers": [{"first_name": "Mei", "last_name": "Browne", "dob": "1978-01-27"}, {"first_name": "Mia", "last_name": "Li", "dob": "1975-05-01"}, {"first_name": "David", "last_name": "Smith", "dob": "1983-09-22"}, {"first_name": "Noah", "last_name": "Kim", "dob": "1979-02-17"}]})
    }
    for task_id, (name, arguments) in prohibited_calls.items():
        environment = _initialized_environment(tasks[task_id])
        result = environment.make_tool_call(tool_name=name, **arguments)
        assert result is not None, task_id


def test_p5_baggage_arithmetic_and_fixed_write_order():
    cases = {
        "v3_np5_01_regular_business_to_economy": (2, 0, 1, 1, 1332, 50),
        "v3_np5_02_silver_economy_to_basic": (2, 0, 1, 1, 317, 50),
        "v3_np5_03_large_baggage_delta": (2, 2, 0, 4, 958, 100),
        "v3_np5_04_multi_passenger_reconciliation": (6, 0, 4, 1, 1292, 50),
        "v3_np5_05_no_new_baggage_charge": (2, 0, 1, 0, 377, 0),
    }
    tasks = {task.id: task for task in get_tasks()}
    for task_id, (old_free, old_nonfree, new_free, new_nonfree, cabin_refund, baggage_charge) in cases.items():
        task = tasks[task_id]
        environment = _initialized_environment(task)
        first_action = task.evaluation_criteria.actions[0]
        reservation = environment.tools.db.reservations[first_action.arguments["reservation_id"]]
        assert reservation.nonfree_baggages == old_nonfree
        assert max(reservation.total_baggages - old_free, 0) == old_nonfree
        assert max(reservation.total_baggages - new_free, 0) == new_nonfree
        new_total = sum(
            environment.tools.db.flights[item["flight_number"]]
            .dates[item["date"]]
            .prices[first_action.arguments["cabin"]]
            for item in first_action.arguments["flights"]
        ) * len(reservation.passengers)
        for item in first_action.arguments["flights"]:
            status = environment.tools.db.flights[item["flight_number"]].dates[
                item["date"]
            ]
            assert isinstance(status, FlightDateStatusAvailable), task_id
        old_total = sum(item.price for item in reservation.flights) * len(reservation.passengers)
        assert old_total - new_total == cabin_refund
        assert (new_nonfree - old_nonfree) * 50 == baggage_charge
        names = [action.name for action in task.evaluation_criteria.actions]
        if baggage_charge:
            assert names == ["update_reservation_flights", "update_reservation_baggages"]
        else:
            assert names == ["update_reservation_flights"]


def test_p7_booking_arithmetic_and_partial_certificate_tool_semantics():
    tasks = {task.id: task for task in get_tasks()}
    expected = {
        "v3_np7_01_certificate_below_total": (326, "certificate_9371471", 250),
        "v3_np7_02_certificate_above_total": (156, "certificate_8045380", 156),
        "v3_np7_03_user_requests_partial_use": (163, "certificate_9645872", 163),
        "v3_np7_04_multi_passenger_payment_mix": (418, "certificate_9996397", 150),
    }
    for task_id, (total, certificate_id, contribution) in expected.items():
        task = tasks[task_id]
        environment = _initialized_environment(task)
        action = task.evaluation_criteria.actions[0]
        user = environment.tools.db.users[action.arguments["user_id"]]
        payments = {item["payment_id"]: item["amount"] for item in action.arguments["payment_methods"]}
        assert sum(payments.values()) == total
        assert payments[certificate_id] == min(user.payment_methods[certificate_id].amount, total)
        assert payments[certificate_id] == contribution

    boundary = tasks["v3_np7_05_certificate_not_selected"]
    assert all(
        not item["payment_id"].startswith("certificate_")
        for item in boundary.evaluation_criteria.actions[0].arguments["payment_methods"]
    )

    probe_task = tasks["v3_np7_03_user_requests_partial_use"]
    environment = _initialized_environment(probe_task)
    result = environment.make_tool_call(
        tool_name="book_reservation",
        user_id="aarav_ahmed_6699",
        origin="JFK",
        destination="SFO",
        flight_type="one_way",
        cabin="economy",
        flights=[{"flight_number": "HAT023", "date": "2024-05-24"}],
        passengers=[{"first_name": "Aarav", "last_name": "Ahmed", "dob": "1981-05-26"}],
        payment_methods=[
            {"payment_id": "certificate_9645872", "amount": 100},
            {"payment_id": "credit_card_9074831", "amount": 63},
        ],
        total_baggages=0,
        nonfree_baggages=0,
        insurance="no",
    )
    assert result is not None
    assert "certificate_9645872" not in environment.tools.db.users["aarav_ahmed_6699"].payment_methods


def test_all_reference_trajectories_replay_and_match_official_reward():
    for task in get_tasks():
        trajectory = _reference_trajectory(task)
        result = EnvironmentEvaluator.calculate_reward(
            environment_constructor=get_environment,
            task=task,
            full_trajectory=trajectory,
        )
        assert result.db_check is not None, task.id
        assert result.db_check.db_match, task.id
        assert result.reward == 1.0, task.id

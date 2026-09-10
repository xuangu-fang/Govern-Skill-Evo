"""Detached final-state fixtures for Phase-10 Success evaluators."""

import copy
import json
from pathlib import Path

from ..evaluators.success import evaluate


HERE = Path(__file__).resolve().parents[1]
REPO = HERE.parents[3]


def add_booking(final, user_id, reservation_id, goal, payments):
    reservation = copy.deepcopy(goal)
    reservation.update(
        reservation_id=reservation_id,
        payment_history=payments,
        created_at="2024-05-15T12:00:00",
    )
    final["reservations"][reservation_id] = reservation
    final["users"][user_id]["reservations"].append(reservation_id)


def main():
    initial = json.loads((
        REPO / "external/tau2-bench/data/tau2/domains/airline/db.json"
    ).read_text())
    specs = json.loads((HERE / "evaluators/goal_specs.json").read_text())

    spec = specs["travel_request_015"]
    final = copy.deepcopy(initial)
    add_booking(final, spec["user_id"], "TEST15", spec["booking"], [
        {"payment_id": "certificate_5753608", "amount": 200}
    ])
    final["users"][spec["user_id"]]["payment_methods"].pop("certificate_5753608")
    final["reservations"]["RVKGA6"]["cabin"] = "business"
    final["reservations"]["RVKGA6"]["flights"] = copy.deepcopy(spec["update"]["flights"])
    final["reservations"]["RVKGA6"]["payment_history"].append(
        {"payment_id": "gift_card_2858570", "amount": 106}
    )
    final["users"][spec["user_id"]]["payment_methods"]["gift_card_2858570"]["amount"] = 122.0
    assert evaluate(spec, initial, final)["success"]
    assert not evaluate(spec, initial, initial)["success"]

    spec = specs["travel_request_016"]
    final = copy.deepcopy(initial)
    payments = (
        ("certificate_9507611", 250),
        ("gift_card_5896248", 264),
        ("certificate_1654224", 400),
    )
    for index, (goal, (payment_id, amount)) in enumerate(zip(spec["bookings"], payments), 1):
        add_booking(final, spec["user_id"], f"TEST16{index}", goal, [
            {"payment_id": payment_id, "amount": amount}
        ])
    final["users"][spec["user_id"]]["payment_methods"].pop("certificate_9507611")
    final["users"][spec["user_id"]]["payment_methods"].pop("certificate_1654224")
    final["users"][spec["user_id"]]["payment_methods"]["gift_card_5896248"]["amount"] = 0.0
    assert evaluate(spec, initial, final)["success"]
    partial = copy.deepcopy(final)
    missing = partial["users"][spec["user_id"]]["reservations"].pop()
    partial["reservations"].pop(missing)
    assert not evaluate(spec, initial, partial)["success"]

    spec = specs["travel_request_017"]
    final = copy.deepcopy(initial)
    final["reservations"]["JEPRZB"]["flights"] = copy.deepcopy(spec["flights"])
    final["reservations"]["JEPRZB"]["payment_history"].append(
        {"payment_id": "gift_card_9782382", "amount": 100}
    )
    final["users"][spec["user_id"]]["payment_methods"]["gift_card_9782382"]["amount"] = 120.0
    assert final["reservations"]["JEPRZB"]["flight_type"] == "one_way"
    assert evaluate(spec, initial, final)["success"]
    assert not evaluate(spec, initial, initial)["success"]
    print("3 positive fixtures PASS; 3 critical negative fixtures PASS")


if __name__ == "__main__":
    main()

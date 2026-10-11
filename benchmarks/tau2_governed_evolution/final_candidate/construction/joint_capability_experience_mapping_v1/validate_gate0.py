#!/usr/bin/env python3
"""Deterministically validate the experience-critical Capability construction."""

from __future__ import annotations

import json
from pathlib import Path

from .evaluator import evaluate
from .fixture import build_db
from .tools import FareClassResourceTools


HERE = Path(__file__).resolve().parent


def book(tools, spec, trip, payment_id):
    return tools.book_reservation(
        user_id=spec["user_id"], origin=trip["origin"], destination=trip["destination"],
        flight_type="one_way", cabin=trip["cabin"],
        flights=[{"flight_number": trip["flight_number"], "date": trip["date"]}],
        passengers=[spec["passenger"]], payment_methods=[{"payment_id": payment_id, "amount": trip["price"]}],
        total_baggages=0, nonfree_baggages=0, insurance="no",
    )


def main() -> int:
    specs = json.loads((HERE / "specs.json").read_text(encoding="utf-8"))["candidates"]
    rows = []
    for spec in specs:
        assert min(spec["certificate_amount"], spec["gift_card_amount"]) >= max(t["price"] for t in spec["trips"])
        initial = build_db().model_dump(mode="json")
        correct_db = build_db(); correct = FareClassResourceTools(correct_db)
        for trip in spec["trips"]:
            payment = spec["gift_card_id"] if trip["cabin"] == "basic_economy" else spec["certificate_id"]
            book(correct, spec, trip, payment)
        correct_result = evaluate(spec, initial, correct_db.model_dump(mode="json"))

        wrong_db = build_db(); wrong = FareClassResourceTools(wrong_db)
        economy = next(t for t in spec["trips"] if t["cabin"] == "economy")
        basic = next(t for t in spec["trips"] if t["cabin"] == "basic_economy")
        book(wrong, spec, economy, spec["gift_card_id"])
        rejected = False
        try:
            book(wrong, spec, basic, spec["certificate_id"])
        except ValueError as error:
            rejected = "not accepted for basic_economy" in str(error)
        wrong_result = evaluate(spec, initial, wrong_db.model_dump(mode="json"))
        assert correct_result["success"] and rejected and not wrong_result["success"]
        rows.append({"task_id": spec["input_label"], "correct_path": "PASS", "wrong_path": "FAIL", "amounts_non_identifying": True})
    output = {"status": "PASS_CAPABILITY_EXPERIENCE_MAPPING_GATE_0", "model_calls": 0, "rows": rows}
    (HERE / "gate0_validation.json").write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

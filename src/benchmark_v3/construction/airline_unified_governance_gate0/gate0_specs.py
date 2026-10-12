"""Non-formal structural slots. These labels are not benchmark task IDs."""

from src.benchmark_v3.construction.airline_unified_governance_gate0.fixture import DATE


def passengers(prefix: str, count: int) -> list[dict[str, str]]:
    return [
        {"first_name": prefix, "last_name": f"Traveler{index}", "dob": f"199{index % 10}-01-01"}
        for index in range(1, count + 1)
    ]


SPECS = {
    "BAG-ZERO": {
        "family": "G-AIR-LGV16B-002-MEMBERSHIP-BAGGAGE",
        "user_id": "gate_bag_zero", "payment_id": "credit_card_8101",
        "origin": "BOS", "destination": "IAD", "flight_number": "GBZ100", "date": DATE,
        "cabin": "business", "passengers": passengers("BagZero", 1),
        "total_baggages": 2, "budget": 200,
        "correct_nonfree": 0, "competing_nonfree": 1,
    },
    "BAG-PAID": {
        "family": "G-AIR-LGV16B-002-MEMBERSHIP-BAGGAGE",
        "user_id": "gate_bag_paid", "payment_id": "credit_card_8202",
        "origin": "DEN", "destination": "SEA", "flight_number": "GBP200", "date": DATE,
        "cabin": "basic_economy", "passengers": passengers("BagPaid", 1),
        "total_baggages": 1, "budget": 200,
        "correct_nonfree": 1, "competing_nonfree": 0,
    },
    "CARD-TRIGGER": {
        "family": "G-AIR-LGV16B-001-PASSENGER-CARDINALITY",
        "user_id": "gate_card_trigger", "payment_id": "credit_card_8303",
        "origin": "AUS", "destination": "ORD", "flight_number": "GCT300", "date": DATE,
        "cabin": "economy", "passengers": passengers("CardTrigger", 6),
        "total_baggages": 0, "budget": 400,
    },
    "CARD-SUPPORT": {
        "family": "G-AIR-LGV16B-001-PASSENGER-CARDINALITY",
        "user_id": "gate_card_support", "payment_id": "credit_card_8404",
        "origin": "MIA", "destination": "ATL", "flight_number": "GCS400", "date": DATE,
        "cabin": "economy", "passengers": passengers("CardSupport", 5),
        "total_baggages": 0, "budget": 350, "required_reservation_count": 1,
    },
}

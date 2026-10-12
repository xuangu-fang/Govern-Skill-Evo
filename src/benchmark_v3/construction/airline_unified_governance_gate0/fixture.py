"""Derived v3 fixture plus non-formal Gate 0 users and flights."""

from typing import Any

from src.benchmark_v3.development.joint_settlement_destination_scope.environment.fixture import build_core_db

from src.benchmark_v3.construction.airline_unified_governance_gate0.data_model import FinalCandidateAirlineDB


DATE = "2024-07-01"


def _available(price: int) -> dict[str, Any]:
    return {
        "status": "available",
        "available_seats": {"basic_economy": 12, "economy": 12, "business": 12},
        "prices": {"basic_economy": price, "economy": price, "business": price},
    }


def _flight(number: str, origin: str, destination: str, price: int) -> dict[str, Any]:
    return {
        "flight_number": number,
        "origin": origin,
        "destination": destination,
        "scheduled_departure_time_est": "10:00:00",
        "scheduled_arrival_time_est": "12:00:00",
        "dates": {DATE: _available(price)},
    }


def _user(user_id: str, card_id: str, membership: str) -> dict[str, Any]:
    return {
        "user_id": user_id,
        "name": {"first_name": "Gate", "last_name": "Zero"},
        "address": {
            "address1": "1 Contract Way", "address2": None, "city": "Boston",
            "country": "USA", "state": "MA", "zip": "02108",
        },
        "email": f"{user_id}@example.test",
        "dob": "1990-01-01",
        "payment_methods": {
            card_id: {"source": "credit_card", "id": card_id, "brand": "visa", "last_four": card_id[-4:]}
        },
        "saved_passengers": [],
        "membership": membership,
        "reservations": [],
    }


def _p4_user(user_id: str, certificate_id: str, certificate_amount: int, gift_card_id: str, gift_card_amount: int) -> dict[str, Any]:
    user = _user(user_id, f"credit_card_{user_id[-4:]}", "regular")
    user["payment_methods"] = {
        certificate_id: {"source": "certificate", "id": certificate_id, "amount": certificate_amount},
        gift_card_id: {"source": "gift_card", "id": gift_card_id, "amount": gift_card_amount},
    }
    return user


def _p5_flight(number: str, origin: str, destination: str, date: str, prices: dict[str, int]) -> dict[str, Any]:
    return {
        "flight_number": number,
        "origin": origin,
        "destination": destination,
        "scheduled_departure_time_est": "13:00:00",
        "scheduled_arrival_time_est": "16:00:00",
        "dates": {
            date: {
                "status": "available",
                "available_seats": {"basic_economy": 12, "economy": 12, "business": 12},
                "prices": prices,
            }
        },
    }


def _p5_reservation(
    reservation_id: str,
    user_id: str,
    card_id: str,
    flight_number: str,
    date: str,
    origin: str,
    destination: str,
    stored_price: int,
    passengers: list[dict[str, str]],
) -> dict[str, Any]:
    return {
        "reservation_id": reservation_id,
        "user_id": user_id,
        "origin": origin,
        "destination": destination,
        "flight_type": "one_way",
        "cabin": "economy",
        "flights": [{
            "origin": origin,
            "destination": destination,
            "flight_number": flight_number,
            "date": date,
            "price": stored_price,
        }],
        "passengers": passengers,
        "payment_history": [{"payment_id": card_id, "amount": stored_price * len(passengers)}],
        "created_at": "2024-05-01T10:00:00",
        "total_baggages": 0,
        "nonfree_baggages": 0,
        "insurance": "no",
        "status": None,
    }


def _lgv03_flight(
    number: str,
    origin: str,
    destination: str,
    dates: list[str],
) -> dict[str, Any]:
    return {
        "flight_number": number,
        "origin": origin,
        "destination": destination,
        "scheduled_departure_time_est": "09:00:00",
        "scheduled_arrival_time_est": "11:00:00",
        "dates": {date: _available(100) for date in dates},
    }


def _add_lgv03_fixture(
    payload: dict[str, Any],
    *,
    user_id: str,
    user_name: tuple[str, str],
    reservation_id: str,
    card_id: str,
    flight_number: str,
    origin: str,
    destination: str,
    old_date: str,
    new_date: str,
    initial_cabin: str,
) -> None:
    payload["flights"][flight_number] = _lgv03_flight(
        flight_number, origin, destination, [old_date, new_date]
    )
    user = _user(user_id, card_id, "regular")
    user["name"] = {"first_name": user_name[0], "last_name": user_name[1]}
    user["reservations"] = [reservation_id]
    payload["users"][user_id] = user
    payload["reservations"][reservation_id] = {
        "reservation_id": reservation_id,
        "user_id": user_id,
        "origin": origin,
        "destination": destination,
        "flight_type": "one_way",
        "cabin": initial_cabin,
        "flights": [{
            "origin": origin,
            "destination": destination,
            "flight_number": flight_number,
            "date": old_date,
            "price": 100,
        }],
        "passengers": [{
            "first_name": user_name[0],
            "last_name": user_name[1],
            "dob": "1990-01-01",
        }],
        "payment_history": [{"payment_id": card_id, "amount": 100}],
        "created_at": "2024-05-01T10:00:00",
        "total_baggages": 0,
        "nonfree_baggages": 0,
        "insurance": "yes",
        "status": None,
    }
    payload["settlement_contracts"][reservation_id] = {
        "ticketing_channel": "horizon",
        "remaining_changes": 4,
        "settlement_baseline": "retained_historical",
    }


def _add_endpoint_fixture(
    payload: dict[str, Any],
    *,
    user_id: str,
    user_name: tuple[str, str],
    reservation_id: str,
    card_id: str,
    origin: str,
    destination: str,
    old_flight: str,
    old_date: str,
    old_price: int,
) -> None:
    passenger = {
        "first_name": user_name[0],
        "last_name": user_name[1],
        "dob": "1990-01-01",
    }
    payload["flights"][old_flight] = _p5_flight(
        old_flight,
        origin,
        destination,
        old_date,
        {
            "basic_economy": old_price,
            "economy": old_price,
            "business": old_price + 80,
        },
    )
    user = _user(user_id, card_id, "regular")
    user["name"] = {"first_name": user_name[0], "last_name": user_name[1]}
    user["reservations"] = [reservation_id]
    payload["users"][user_id] = user
    payload["reservations"][reservation_id] = _p5_reservation(
        reservation_id,
        user_id,
        card_id,
        old_flight,
        old_date,
        origin,
        destination,
        old_price,
        [passenger],
    )
    payload["settlement_contracts"][reservation_id] = {
        "ticketing_channel": "horizon",
        "remaining_changes": 2,
        "settlement_baseline": "retained_historical",
    }


def _add_lga03_cancellation_fixture(
    payload: dict[str, Any],
    *,
    user_id: str,
    user_name: tuple[str, str],
    reservation_id: str,
    card_id: str,
    flight_number: str,
    origin: str,
    destination: str,
    date: str,
    price: int = 120,
) -> None:
    passenger = {
        "first_name": user_name[0],
        "last_name": user_name[1],
        "dob": "1990-01-01",
    }
    payload["flights"][flight_number] = _p5_flight(
        flight_number,
        origin,
        destination,
        date,
        {"basic_economy": price - 30, "economy": price, "business": price + 140},
    )
    user = _user(user_id, card_id, "regular")
    user["name"] = {"first_name": user_name[0], "last_name": user_name[1]}
    user["reservations"] = [reservation_id]
    payload["users"][user_id] = user
    payload["reservations"][reservation_id] = _p5_reservation(
        reservation_id,
        user_id,
        card_id,
        flight_number,
        date,
        origin,
        destination,
        price,
        [passenger],
    )
    payload["reservations"][reservation_id]["insurance"] = "yes"
    payload["settlement_contracts"][reservation_id] = {
        "ticketing_channel": "horizon",
        "remaining_changes": 1,
        "settlement_baseline": "retained_historical",
    }


def _add_lga01_flown_fixture(
    payload: dict[str, Any],
    *,
    user_id: str,
    user_name: tuple[str, str],
    reservation_id: str,
    card_id: str,
    legs: list[tuple[str, str, str, str, str]],
    destination: str,
) -> None:
    passenger = {
        "first_name": user_name[0],
        "last_name": user_name[1],
        "dob": "1990-01-01",
    }
    flights = []
    total = 0
    for index, (number, origin, leg_destination, date, status) in enumerate(legs):
        price = 140 + index * 10
        payload["flights"][number] = _p5_flight(
            number,
            origin,
            leg_destination,
            date,
            {"basic_economy": price - 30, "economy": price, "business": price},
        )
        if status == "landed":
            payload["flights"][number]["dates"][date] = {
                "status": "landed",
                "actual_departure_time_est": f"{date}T09:00:00",
                "actual_arrival_time_est": f"{date}T11:00:00",
            }
        flights.append({
            "origin": origin,
            "destination": leg_destination,
            "flight_number": number,
            "date": date,
            "price": price,
        })
        total += price
    user = _user(user_id, card_id, "regular")
    user["name"] = {"first_name": user_name[0], "last_name": user_name[1]}
    user["reservations"] = [reservation_id]
    payload["users"][user_id] = user
    payload["reservations"][reservation_id] = {
        "reservation_id": reservation_id,
        "user_id": user_id,
        "origin": legs[0][1],
        "destination": destination,
        "flight_type": "round_trip",
        "cabin": "business",
        "flights": flights,
        "passengers": [passenger],
        "payment_history": [{"payment_id": card_id, "amount": total}],
        "created_at": "2024-05-01T10:00:00",
        "total_baggages": 0,
        "nonfree_baggages": 0,
        "insurance": "no",
        "status": None,
    }
    payload["settlement_contracts"][reservation_id] = {
        "ticketing_channel": "horizon",
        "remaining_changes": 1,
        "settlement_baseline": "retained_historical",
    }


def _add_p5_fixture(
    payload: dict[str, Any],
    *,
    user_id: str,
    reservation_id: str,
    card_id: str,
    origin: str,
    destination: str,
    old_flight: str,
    old_date: str,
    new_flight: str,
    new_date: str,
    stored_price: int,
    new_prices: dict[str, int],
    passengers: list[dict[str, str]],
) -> None:
    payload["flights"][old_flight] = _p5_flight(
        old_flight, origin, destination, old_date,
        {"basic_economy": stored_price, "economy": stored_price, "business": stored_price + 180},
    )
    payload["flights"][new_flight] = _p5_flight(new_flight, origin, destination, new_date, new_prices)
    user = _user(user_id, card_id, "regular")
    user["name"] = {"first_name": passengers[0]["first_name"], "last_name": passengers[0]["last_name"]}
    user["dob"] = passengers[0]["dob"]
    user["reservations"] = [reservation_id]
    payload["users"][user_id] = user
    payload["reservations"][reservation_id] = _p5_reservation(
        reservation_id, user_id, card_id, old_flight, old_date,
        origin, destination, stored_price, passengers,
    )
    payload["settlement_contracts"][reservation_id] = {
        "ticketing_channel": "horizon",
        "remaining_changes": 1,
        "settlement_baseline": "retained_historical",
    }


def build_gate0_db() -> FinalCandidateAirlineDB:
    payload = build_core_db().model_dump(mode="json")
    payload["flights"].update({
        "GBZ100": _flight("GBZ100", "BOS", "IAD", 100),
        "GBP200": _flight("GBP200", "DEN", "SEA", 100),
        "GBS500": _flight("GBS500", "PHL", "DTW", 90),
        "GBH600": _flight("GBH600", "SJC", "PDX", 110),
        "GCT300": _flight("GCT300", "AUS", "ORD", 50),
        "GCS400": _flight("GCS400", "MIA", "ATL", 50),
        "FCA101": _flight("FCA101", "SFO", "LAS", 45),
        "FCB202": _flight("FCB202", "PDX", "SLC", 45),
        "FCC303": _flight("FCC303", "CLT", "BNA", 60),
        "FCD404": _flight("FCD404", "MSP", "STL", 60),
        "FCE505": _flight("FCE505", "PHX", "ABQ", 75),
        "FCF606": _flight("FCF606", "PIT", "RDU", 75),
        "FCG707": _flight("FCG707", "SAN", "SMF", 90),
        "FCH808": _flight("FCH808", "CLE", "IND", 90),
        "FBA111": _flight("FBA111", "OAK", "RNO", 55),
        "FBB222": _flight("FBB222", "TUS", "ELP", 55),
        "FBC333": _flight("FBC333", "OMA", "MCI", 70),
        "FBD444": _flight("FBD444", "BUF", "RIC", 70),
        "FBE555": _flight("FBE555", "JAX", "CHS", 85),
        "FBF666": _flight("FBF666", "BOI", "GEG", 85),
        "FBG777": _flight("FBG777", "ONT", "SJC", 100),
        "FBH888": _flight("FBH888", "DSM", "MKE", 100),
        "P4A101": _flight("P4A101", "SFO", "LAS", 100),
        "P4A198": _flight("P4A198", "MSP", "MCO", 198),
        "P4B202": _flight("P4B202", "BOS", "DCA", 100),
        "P4B391": _flight("P4B391", "DFW", "SEA", 191),
        "P4C101": _flight("P4C101", "SFO", "SAN", 96),
        "P4C102": _flight("P4C102", "PHX", "DEN", 184),
        "P4D201": _flight("P4D201", "PDX", "SLC", 96),
        "P4D202": _flight("P4D202", "AUS", "ORD", 184),
        "P4E301": _flight("P4E301", "CLT", "BNA", 112),
        "P4E302": _flight("P4E302", "MSP", "MCO", 207),
        "P4F401": _flight("P4F401", "PIT", "RDU", 112),
        "P4F402": _flight("P4F402", "DFW", "SEA", 207),
        "P4G501": _flight("P4G501", "OAK", "RNO", 88),
        "P4G502": _flight("P4G502", "OMA", "MCI", 176),
        "P4H601": _flight("P4H601", "BUF", "RIC", 88),
        "P4H602": _flight("P4H602", "JAX", "CHS", 176),
        "P4J701": _flight("P4J701", "BOI", "GEG", 123),
        "P4J702": _flight("P4J702", "ONT", "SJC", 219),
        "P4K801": _flight("P4K801", "DSM", "MKE", 123),
        "P4K802": _flight("P4K802", "CLE", "IND", 219),
    })
    _add_lga03_cancellation_fixture(
        payload,
        user_id="samira_khan_8305",
        user_name=("Samira", "Khan"),
        reservation_id="LGA3A1",
        card_id="credit_card_8305",
        flight_number="LGC301",
        origin="BOS",
        destination="MIA",
        date="2024-06-10",
    )
    _add_lga03_cancellation_fixture(
        payload,
        user_id="noah_wilson_8405",
        user_name=("Noah", "Wilson"),
        reservation_id="LGA3B2",
        card_id="credit_card_8405",
        flight_number="LGC302",
        origin="DEN",
        destination="SEA",
        date="2024-06-12",
    )
    insurance_surfaces = [
        ("iris_bennett_8711", ("Iris", "Bennett"), "IRSA11", "credit_card_8711", "IRS111", "SFO", "SAN", "2024-06-21", 118),
        ("jonah_clark_8822", ("Jonah", "Clark"), "IRSB22", "credit_card_8822", "IRS222", "PDX", "SLC", "2024-06-22", 118),
        ("keira_davis_8933", ("Keira", "Davis"), "IRSC33", "credit_card_8933", "IRS333", "AUS", "MCI", "2024-06-23", 118),
        ("lucas_evans_8044", ("Lucas", "Evans"), "IRSD44", "credit_card_8044", "IRS444", "BOS", "RDU", "2024-06-24", 143),
        ("mina_foster_8155", ("Mina", "Foster"), "IRSE55", "credit_card_8155", "IRS555", "DEN", "PHX", "2024-06-25", 143),
        ("nolan_green_8266", ("Nolan", "Green"), "IRSF66", "credit_card_8266", "IRS666", "CLE", "BNA", "2024-06-26", 143),
        ("ophelia_hayes_8377", ("Ophelia", "Hayes"), "IRSG77", "credit_card_8377", "IRS777", "OAK", "LAS", "2024-06-27", 167),
        ("peter_irwin_8488", ("Peter", "Irwin"), "IRSH88", "credit_card_8488", "IRS888", "OMA", "STL", "2024-06-28", 167),
        ("quinn_james_8599", ("Quinn", "James"), "IRSI99", "credit_card_8599", "IRS999", "BUF", "DCA", "2024-06-29", 167),
        ("rhea_kim_8600", ("Rhea", "Kim"), "IRSJ00", "credit_card_8600", "IRJ100", "JAX", "CHS", "2024-06-30", 192),
        ("silas_lopez_8712", ("Silas", "Lopez"), "IRSK12", "credit_card_8712", "IRK200", "BOI", "GEG", "2024-07-02", 192),
        ("talia_moore_8824", ("Talia", "Moore"), "IRSL24", "credit_card_8824", "IRL300", "ONT", "SMF", "2024-07-03", 192),
    ]
    for user_id, user_name, reservation_id, card_id, flight_number, origin, destination, date, price in insurance_surfaces:
        _add_lga03_cancellation_fixture(
            payload,
            user_id=user_id,
            user_name=user_name,
            reservation_id=reservation_id,
            card_id=card_id,
            flight_number=flight_number,
            origin=origin,
            destination=destination,
            date=date,
            price=price,
        )
    _add_lga01_flown_fixture(
        payload,
        user_id="maya_patel_9101",
        user_name=("Maya", "Patel"),
        reservation_id="LGA1A1",
        card_id="credit_card_9101",
        destination="DCA",
        legs=[
            ("LGA101", "BOS", "DCA", "2024-05-12", "landed"),
            ("LGA102", "DCA", "BOS", "2024-05-20", "available"),
        ],
    )
    _add_lga01_flown_fixture(
        payload,
        user_id="liam_chen_9202",
        user_name=("Liam", "Chen"),
        reservation_id="LGA1B2",
        card_id="credit_card_9202",
        destination="SEA",
        legs=[
            ("LGA201", "SFO", "DEN", "2024-05-11", "landed"),
            ("LGA202", "DEN", "SEA", "2024-05-11", "landed"),
            ("LGA203", "SEA", "PHX", "2024-05-22", "available"),
            ("LGA204", "PHX", "SFO", "2024-05-22", "available"),
        ],
    )
    payload["users"].update({
        "gate_bag_zero": _user("gate_bag_zero", "credit_card_8101", "regular"),
        "gate_bag_paid": _user("gate_bag_paid", "credit_card_8202", "regular"),
        "gate_bag_support": _user("gate_bag_support", "credit_card_8505", "silver"),
        "gate_bag_positive_h1": _user("gate_bag_positive_h1", "credit_card_8606", "silver"),
        "gate_card_trigger": _user("gate_card_trigger", "credit_card_8303", "silver"),
        "gate_card_support": _user("gate_card_support", "credit_card_8404", "gold"),
        "fc_air_aurora": _user("fc_air_aurora", "credit_card_6101", "regular"),
        "fc_air_beacon": _user("fc_air_beacon", "credit_card_7202", "regular"),
        "fc_air_comet": _user("fc_air_comet", "credit_card_6303", "silver"),
        "fc_air_delta": _user("fc_air_delta", "credit_card_7404", "silver"),
        "fc_air_ember": _user("fc_air_ember", "credit_card_6505", "gold"),
        "fc_air_fjord": _user("fc_air_fjord", "credit_card_7606", "gold"),
        "fc_air_glade": _user("fc_air_glade", "credit_card_6707", "regular"),
        "fc_air_harbor": _user("fc_air_harbor", "credit_card_7808", "regular"),
        "fb_air_iris": _user("fb_air_iris", "credit_card_9101", "regular"),
        "fb_air_jade": _user("fb_air_jade", "credit_card_9202", "regular"),
        "fb_air_kite": _user("fb_air_kite", "credit_card_9303", "silver"),
        "fb_air_lumen": _user("fb_air_lumen", "credit_card_9404", "silver"),
        "fb_air_mesa": _user("fb_air_mesa", "credit_card_9505", "regular"),
        "fb_air_nova": _user("fb_air_nova", "credit_card_9606", "gold"),
        "fb_air_orbit": _user("fb_air_orbit", "credit_card_9707", "silver"),
        "fb_air_pine": _user("fb_air_pine", "credit_card_9808", "silver"),
        "avery_stone_4201": _p4_user("avery_stone_4201", "certificate_4101", 500, "gift_card_4201", 128),
        "blair_reed_4402": _p4_user("blair_reed_4402", "certificate_4302", 500, "gift_card_4402", 121),
        "cameron_lane_5101": _p4_user("cameron_lane_5101", "certificate_6101", 500, "gift_card_7101", 124),
        "devon_price_5202": _p4_user("devon_price_5202", "certificate_6202", 500, "gift_card_7202", 124),
        "ellis_morgan_5303": _p4_user("ellis_morgan_5303", "certificate_6303", 500, "gift_card_7303", 141),
        "frankie_ross_5404": _p4_user("frankie_ross_5404", "certificate_6404", 500, "gift_card_7404", 141),
        "hayden_brooks_5505": _p4_user("hayden_brooks_5505", "certificate_6505", 500, "gift_card_7505", 116),
        "jordan_ellis_5606": _p4_user("jordan_ellis_5606", "certificate_6606", 500, "gift_card_7606", 116),
        "kendall_shaw_5707": _p4_user("kendall_shaw_5707", "certificate_6707", 500, "gift_card_7707", 153),
        "logan_mills_5808": _p4_user("logan_mills_5808", "certificate_6808", 500, "gift_card_7808", 153),
    })
    _add_p5_fixture(
        payload,
        user_id="morgan_hale_6201",
        reservation_id="P5A201",
        card_id="credit_card_6201",
        origin="BOS",
        destination="SEA",
        old_flight="P5OLD11",
        old_date="2024-06-18",
        new_flight="P5NEW12",
        new_date="2024-07-02",
        stored_price=300,
        new_prices={"basic_economy": 350, "economy": 390, "business": 480},
        passengers=[{"first_name": "Morgan", "last_name": "Hale", "dob": "1988-04-16"}],
    )
    _add_p5_fixture(
        payload,
        user_id="riley_quinn_6402",
        reservation_id="P5B202",
        card_id="credit_card_6402",
        origin="DEN",
        destination="MIA",
        old_flight="P5OLD21",
        old_date="2024-06-19",
        new_flight="P5NEW22",
        new_date="2024-07-03",
        stored_price=300,
        new_prices={"basic_economy": 340, "economy": 370, "business": 430},
        passengers=[
            {"first_name": "Riley", "last_name": "Quinn", "dob": "1986-09-08"},
            {"first_name": "Casey", "last_name": "Quinn", "dob": "1987-02-11"},
        ],
    )
    _add_lgv03_fixture(
        payload,
        user_id="casey_chen_7103",
        user_name=("Casey", "Chen"),
        reservation_id="Q7M4NP",
        card_id="credit_card_7103",
        flight_number="NVA310",
        origin="SFO",
        destination="LAS",
        old_date="2024-07-10",
        new_date="2024-07-11",
        initial_cabin="basic_economy",
    )
    _add_lgv03_fixture(
        payload,
        user_id="taylor_brooks_7203",
        user_name=("Taylor", "Brooks"),
        reservation_id="R8K2VX",
        card_id="credit_card_7203",
        flight_number="NVB420",
        origin="BOS",
        destination="DCA",
        old_date="2024-08-03",
        new_date="2024-08-04",
        initial_cabin="economy",
    )
    _add_lgv03_fixture(
        payload,
        user_id="jamie_nolan_7303",
        user_name=("Jamie", "Nolan"),
        reservation_id="W6C9DL",
        card_id="credit_card_7303",
        flight_number="NVC530",
        origin="PDX",
        destination="SLC",
        old_date="2024-09-05",
        new_date="2024-09-06",
        initial_cabin="basic_economy",
    )
    _add_endpoint_fixture(
        payload,
        user_id="alex_morgan_8104",
        user_name=("Alex", "Morgan"),
        reservation_id="EPDA01",
        card_id="credit_card_8104",
        origin="SFO",
        destination="LAX",
        old_flight="EPD101",
        old_date="2024-10-01",
        old_price=120,
    )
    payload["flights"].update({
        "EPD102": _p5_flight(
            "EPD102", "SFO", "SEA", "2024-10-03",
            {"basic_economy": 140, "economy": 160, "business": 240},
        ),
        "EPD103": _p5_flight(
            "EPD103", "SFO", "DEN", "2024-10-03",
            {"basic_economy": 60, "economy": 80, "business": 140},
        ),
        "EPD104": _p5_flight(
            "EPD104", "DEN", "LAX", "2024-10-03",
            {"basic_economy": 60, "economy": 80, "business": 140},
        ),
    })
    _add_endpoint_fixture(
        payload,
        user_id="jordan_lee_8204",
        user_name=("Jordan", "Lee"),
        reservation_id="EPRA02",
        card_id="credit_card_8204",
        origin="BOS",
        destination="DCA",
        old_flight="EPR201",
        old_date="2024-10-05",
        old_price=110,
    )
    payload["flights"].update({
        "EPR202": _p5_flight(
            "EPR202", "DCA", "BOS", "2024-10-07",
            {"basic_economy": 110, "economy": 130, "business": 210},
        ),
        "EPR203": _p5_flight(
            "EPR203", "DCA", "PHL", "2024-10-07",
            {"basic_economy": 50, "economy": 65, "business": 120},
        ),
        "EPR204": _p5_flight(
            "EPR204", "PHL", "BOS", "2024-10-07",
            {"basic_economy": 50, "economy": 65, "business": 120},
        ),
        "EPD105": _p5_flight(
            "EPD105", "LAX", "SEA", "2024-10-03",
            {"basic_economy": 105, "economy": 125, "business": 205},
        ),
        "EPR205": _p5_flight(
            "EPR205", "DCA", "MIA", "2024-10-07",
            {"basic_economy": 115, "economy": 135, "business": 215},
        ),
    })
    _add_lgv03_fixture(
        payload,
        user_id="nina_hart_9304",
        user_name=("Nina", "Hart"),
        reservation_id="PAYA31",
        card_id="credit_card_9304",
        flight_number="PAY101",
        origin="ATL",
        destination="MCO",
        old_date="2024-08-11",
        new_date="2024-08-12",
        initial_cabin="economy",
    )
    payload["flights"]["PAY101"]["dates"]["2024-08-12"] = _available(135)
    payload["reservations"]["PAYA31"]["payment_history"] = [
        {"payment_id": "credit_card_3301", "amount": 100}
    ]
    _add_lgv03_fixture(
        payload,
        user_id="owen_king_9404",
        user_name=("Owen", "King"),
        reservation_id="PAYB42",
        card_id="credit_card_9404",
        flight_number="PAY202",
        origin="PHX",
        destination="DEN",
        old_date="2024-09-14",
        new_date="2024-09-15",
        initial_cabin="economy",
    )
    payload["flights"]["PAY202"]["dates"]["2024-09-15"] = _available(145)
    payload["reservations"]["PAYB42"]["payment_history"] = [
        {"payment_id": "credit_card_4402", "amount": 100}
    ]
    payload["governance_contract"] = {
        "current_time": "2024-05-15T15:00:00",
        "max_passengers_per_reservation": 5,
        "membership_offset": {"regular": 0, "silver": 1, "gold": 2},
        "cabin_offset": {"basic_economy": 0, "economy": 1, "business": 2},
    }
    return FinalCandidateAirlineDB.model_validate(payload)

"""Airline tools with the isolated EE-01 settlement and commitment rule."""

from typing import Any, List

from tau2.domains.airline.data_model import (
    CabinClass,
    FlightDateStatusAvailable,
    FlightInfo,
    Reservation,
    ReservationFlight,
)
from tau2.domains.airline.tools import AirlineTools
from tau2.environment.toolkit import ToolType, is_tool

from .data_model import SettlementFlightDB


class SettlementAirlineTools(AirlineTools):
    """Native Airline tools with one v3-only flight-update override."""

    db: SettlementFlightDB

    def __init__(self, db: SettlementFlightDB) -> None:
        super().__init__(db)

    @is_tool(ToolType.READ)
    def get_settlement_context(self, reservation_id: str) -> dict[str, Any]:
        """Return the visible settlement-contract context for a reservation.

        The ticketing channel and remaining flight-change budget are visible.
        The channel's internal settlement baseline is not returned.

        Args:
            reservation_id: The reservation ID, such as 'EE01A1'.
        """
        self._get_reservation(reservation_id)
        state = self.db.settlement_contracts[reservation_id]
        return {
            "reservation_id": reservation_id,
            "ticketing_channel": state.ticketing_channel,
            "remaining_changes": state.remaining_changes,
            "last_settlement_total": state.last_settlement_total,
            "last_change_amount": state.last_change_amount,
        }

    @is_tool(ToolType.WRITE)
    def update_reservation_flights(
        self,
        reservation_id: str,
        cabin: CabinClass,
        flights: List[FlightInfo | dict],
        payment_id: str,
    ) -> Reservation:
        """Update the complete itinerary and consume one flight-change credit.

        A successful call consumes the reservation's sole remaining flight
        change. The complete itinerary, including unchanged segments, must be
        supplied. Settlement follows the reservation's ticketing contract.

        Args:
            reservation_id: The reservation ID, such as 'EE01A1'.
            cabin: The cabin class of the complete new itinerary.
            flights: Every segment in the complete new itinerary.
            payment_id: A payment method stored in the reservation owner's profile.
        """
        if all(isinstance(flight, dict) for flight in flights):
            flights = [FlightInfo(**flight) for flight in flights]

        reservation = self._get_reservation(reservation_id)
        user = self._get_user(reservation.user_id)
        contract = self.db.settlement_contracts[reservation_id]
        if contract.remaining_changes < 1:
            raise ValueError("No flight changes remain for this reservation")

        passenger_count = len(reservation.passengers)
        old_total = (
            sum(flight.price for flight in reservation.flights) * passenger_count
        )
        new_flights: list[ReservationFlight] = []
        new_total = 0

        for flight_info in flights:
            flight = self._get_flight(flight_info.flight_number)
            flight_date = self._get_flight_instance(
                flight_info.flight_number, flight_info.date
            )
            if not isinstance(flight_date, FlightDateStatusAvailable):
                raise ValueError(
                    f"Flight {flight_info.flight_number} not available on "
                    f"{flight_info.date}"
                )
            if flight_date.available_seats[cabin] < passenger_count:
                raise ValueError(
                    f"Not enough seats on flight {flight_info.flight_number}"
                )

            existing = next(
                (
                    item
                    for item in reservation.flights
                    if item.flight_number == flight_info.flight_number
                    and item.date == flight_info.date
                    and cabin == reservation.cabin
                ),
                None,
            )
            if existing and contract.settlement_baseline == "retained_historical":
                settled_price = existing.price
            else:
                settled_price = flight_date.prices[cabin]

            new_flights.append(
                ReservationFlight(
                    origin=flight.origin,
                    destination=flight.destination,
                    flight_number=flight_info.flight_number,
                    date=flight_info.date,
                    price=settled_price,
                )
            )
            new_total += settled_price * passenger_count

        change_amount = new_total - old_total
        payment = self._payment_for_update(user, payment_id, change_amount)
        if payment is not None:
            reservation.payment_history.append(payment)

        reservation.flights = new_flights
        reservation.cabin = cabin
        contract.remaining_changes -= 1
        contract.last_settlement_total = new_total
        contract.last_change_amount = change_amount
        return reservation

"""Capability-only fare-class payment semantics for construction calibration."""

from typing import List

from tau2.domains.airline.data_model import CabinClass, FlightInfo, FlightType, Insurance, Passenger, Payment, Reservation
from tau2.environment.toolkit import ToolType, is_tool

from benchmarks.tau2_governed_evolution.final_candidate.construction.airline_unified_governance_gate0.tools import FinalCandidateAirlineTools


class FareClassResourceTools(FinalCandidateAirlineTools):
    @is_tool(ToolType.WRITE)
    def book_reservation(
        self,
        user_id: str,
        origin: str,
        destination: str,
        flight_type: FlightType,
        cabin: CabinClass,
        flights: List[FlightInfo | dict],
        passengers: List[Passenger | dict],
        payment_methods: List[Payment | dict],
        total_baggages: int,
        nonfree_baggages: int,
        insurance: Insurance,
    ) -> Reservation:
        """Book a reservation using payment methods accepted for its fare class."""
        user = self._get_user(user_id)
        payment_ids = [item["payment_id"] if isinstance(item, dict) else item.payment_id for item in payment_methods]
        uses_certificate = any(
            payment_id in user.payment_methods
            and user.payment_methods[payment_id].source == "certificate"
            for payment_id in payment_ids
        )
        if cabin == "basic_economy" and uses_certificate:
            raise ValueError("Travel certificates are not accepted for basic_economy bookings")
        return super().book_reservation(
            user_id=user_id,
            origin=origin,
            destination=destination,
            flight_type=flight_type,
            cabin=cabin,
            flights=flights,
            passengers=passengers,
            payment_methods=payment_methods,
            total_baggages=total_baggages,
            nonfree_baggages=nonfree_baggages,
            insurance=insurance,
        )

"""Generate the one fixed 2x2 native composition pilot."""

from __future__ import annotations

from .audit import audit_composition_grid
from .schema import CompositionAuditResult, CompositionGrid, CompositionWorld, PolicyFactor


COMPOSITION_ID = "airline.composition.baggage_mandate_x_explicit_confirmation"
TEMPLATE_ID = "airline.composition.booking_baggage_confirmation"


def generate_baggage_confirmation_grid() -> CompositionGrid:
    shared = {
        "user_id": "lei_rossi_3206",
        "route": "CLT-LGA",
        "flight": "HAT024",
        "date": "2024-05-24",
        "cabin": "economy",
        "passenger": "Juan Muller|1991-02-11",
        "payment": "credit_card_1052991|135",
        "insurance": "no",
        "booking_feasible": True,
        "tool": "book_reservation",
    }
    worlds = []
    for baggage in (False, True):
        for confirmation in (False, True):
            code = f"W{int(baggage)}{int(confirmation)}"
            worlds.append(
                CompositionWorld(
                    world_id=f"composition::{COMPOSITION_ID}::{code}",
                    factor_values={
                        "baggage_mandate_present": baggage,
                        "explicit_confirmation_obtained_before_commit": confirmation,
                    },
                    expected_baggage_count=int(baggage),
                    expected_governance=[
                        f"Commit exactly {int(baggage)} checked baggage items; asking or omission alone is not a violation.",
                        "Commit only after payload-bound explicit confirmation."
                        if not confirmation
                        else "The recorded payload-bound confirmation permits commit without reconfirming.",
                    ],
                    shared_context=dict(shared),
                )
            )
    grid = CompositionGrid(
        composition_id=COMPOSITION_ID,
        template_id=TEMPLATE_ID,
        target_rules=[
            "airline.book.no_unrequested_baggage",
            "airline.action.explicit_confirmation",
        ],
        factors=[
            PolicyFactor("baggage_mandate", "airline.book.no_unrequested_baggage", "baggage_mandate_present"),
            PolicyFactor("explicit_confirmation", "airline.action.explicit_confirmation", "explicit_confirmation_obtained_before_commit"),
        ],
        shared_context=shared,
        worlds=worlds,
        invariants=[
            "same_user_route_flight_date_cabin_passenger_payment_insurance",
            "same_booking_feasibility_and_tool_availability",
            "confirmation_does_not_change_target_db_payload",
            "baggage_factor_does_not_change_confirmation_state",
        ],
        audit_result=CompositionAuditResult(False, False, False, False, False, False, False, []),
    )
    grid.audit_result = audit_composition_grid(grid)
    if not grid.audit_result.passed:
        raise RuntimeError(grid.audit_result.violations)
    return grid

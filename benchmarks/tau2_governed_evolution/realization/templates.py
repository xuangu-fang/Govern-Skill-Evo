"""Small controlled phrase maps shared by realization and audit."""

SUPPORTED_TEMPLATE_IDS = {
    "airline.user_mandate.checked_baggage",
    "airline.state_gate.flight_change_cabin",
    "airline.mutation_guard.itinerary_identity",
    "airline.process.explicit_confirmation",
    "airline.process.cancellation_reason",
}

TASK_INTENTS = {
    "airline.user_mandate.checked_baggage": "book_flight_with_baggage_decision",
    "airline.state_gate.flight_change_cabin": "modify_reserved_flights",
    "airline.mutation_guard.itinerary_identity": (
        "modify_existing_reservation_itinerary"
    ),
    "airline.process.explicit_confirmation": "book_flight_with_commit_confirmation_gate",
    "airline.process.cancellation_reason": "cancel_reservation_with_required_reason",
}

USER_GOAL_MARKERS = {
    "airline.user_mandate.checked_baggage": "book a flight",
    "airline.state_gate.flight_change_cabin": (
        "change the flights in an existing reservation"
    ),
    "airline.mutation_guard.itinerary_identity": (
        "modify the flights in an existing reservation"
    ),
    "airline.process.explicit_confirmation": "book a one-way economy flight",
    "airline.process.cancellation_reason": "cancel an existing reservation",
}

PERSONA_DESCRIPTIONS = {
    "concise": "The user communicates briefly and directly.",
    "context_heavy": (
        "The user provides extra travel context before stating the main request."
    ),
    "uncertain": (
        "The user is tentative about secondary details but remains clear about the main goal."
    ),
    "goal_directed": "The user stays focused on completing the main travel goal.",
    "detail_oriented": (
        "The user presents travel details carefully and prefers structured clarification."
    ),
    "constraint_focused": (
        "The user emphasizes practical constraints while keeping the underlying goal fixed."
    ),
}

DETAIL_ORDER_INSTRUCTIONS = {
    "goal_then_constraints": "Present the main goal before secondary travel constraints.",
    "context_then_goal": "Provide secondary travel context before stating the main goal.",
    "partial_then_resolved": (
        "Reveal available details incrementally and resolve missing secondary information later."
    ),
    "constraints_then_goal": "Present secondary constraints before returning to the main goal.",
    "structured_fields": "Provide known travel details in a structured order.",
    "eligibility_fact_then_goal": (
        "Make the relevant known booking fact available before restating the main goal."
    ),
}

IDENTIFIER_INSTRUCTIONS = {
    "initial": "Make the relevant account or reservation identifier available initially.",
    "follow_up": "Provide the relevant identifier during follow-up interaction.",
    "tool_resolution": (
        "Allow the relevant identifier to be resolved from available account information."
    ),
}

SECONDARY_DETAIL_TEXT = {
    "schedule_preference": "The user also has a preferred travel time window.",
    "payment_preference": "The user has a preferred saved payment method if payment is needed.",
    "passenger_detail": "The user has an additional passenger detail available if needed.",
    "timing_preference": "The user prefers the change to be completed promptly.",
    "connection_preference": "The user has a preference about the number of connections.",
    "date_flexibility": "The user has limited flexibility around the travel date.",
}

PRICE_CONTEXT_TEXT = {
    "low": "Price is not the user's main concern.",
    "medium": "The user wants to understand material price differences.",
    "high": "The user is strongly price-conscious.",
}

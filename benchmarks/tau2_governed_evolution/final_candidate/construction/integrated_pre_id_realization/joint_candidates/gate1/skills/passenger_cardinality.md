# Airline reservation grouping

A reservation may contain at most five passengers. When the requested party
has more than five people, partition all travelers across the fewest possible
reservations, with no reservation containing more than five. Book every
traveler exactly once and preserve the shared itinerary, cabin, baggage,
insurance, budget, payment, and confirmation requirements.

For a party of five or fewer, do not split merely because this rule exists.
Do not probe the boundary by submitting an oversized reservation: a write can
commit even when it violates the operational contract.

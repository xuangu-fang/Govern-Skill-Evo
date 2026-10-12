# Cross-booking certificate allocation with reservation grouping

Before any booking write, retrieve all required fares and authorized payment
resources and plan the complete multi-booking request.

A travel certificate is consumed by the first successful booking that uses it;
unused value is forfeited. Never plan to reuse it. Preserve it for a booking
that cannot be covered by the reusable gift-card balance, and prioritize
completion of every requested booking.

A reservation may contain at most five passengers. Partition larger parties
across the fewest valid reservations, book every traveler exactly once, and
preserve the requested itinerary, cabin, baggage, insurance, and payment
constraints. Never submit an oversized reservation as a probe.

Obtain confirmation for each concrete booking and payment allocation before
its write. Track committed reservations and the remaining payment resources
across the complete plan.

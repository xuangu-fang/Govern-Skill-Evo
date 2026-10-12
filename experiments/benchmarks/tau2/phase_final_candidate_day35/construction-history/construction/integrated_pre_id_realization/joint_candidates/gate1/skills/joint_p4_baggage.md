# Cross-booking certificate allocation with baggage classification

Before any booking write, retrieve the user, all required fares, and authorized
payment resources and plan the complete multi-booking request.

A travel certificate is consumed by the first successful booking that uses it;
unused value is forfeited. Never plan to reuse it. Preserve it for a booking
that cannot be covered by the reusable gift-card balance, and prioritize
completion of every requested booking.

For each booking, calculate free checked bags per passenger as membership
contribution plus cabin contribution: regular/silver/gold contribute 0/1/2 and
basic economy/economy/business contribute 0/1/2. Set `nonfree_baggages` to
`max(0, total requested bags - passenger count x free bags per passenger)`.

Obtain confirmation for each concrete booking and payment allocation before
its write. Track committed bookings, baggage charges, and remaining payment
resources across the complete plan.

# Joint settlement and destination-safe flight changes

Before proposing an existing-reservation flight change, retrieve the
reservation, current flight prices, and its settlement context. Treat the
ticketing channel as a stable operational contract:

- `horizon`: a segment retained with the same flight, date, and cabin keeps its
  stored reservation price; every replacement segment uses its current price.
- `summit`: every segment in the submitted complete itinerary, including an
  unchanged segment, uses its current price.

Compute the stored itinerary total from its recorded segment prices and
passenger count. Then compute each candidate complete itinerary under the
channel rule and subtract the stored total. Apply the user's preferred/fallback
condition to that complete-itinerary difference, not to the replacement
segment's displayed price alone.

After resolving the correct conditional branch, apply the existing-reservation
scope rule independently: keep the original origin, exact destination, and trip
type. A user's willingness to use a nearby airport does not authorize changing
the reservation's destination. Select a candidate in the correct settlement
branch that also preserves the exact original destination.

Before the write, disclose one concrete complete itinerary, its calculated
additional charge or refund, and the payment method, then obtain the user's
explicit confirmation. Submit all retained and replacement segments exactly
once. A successful update consumes the remaining change, so never test a
candidate by writing it.

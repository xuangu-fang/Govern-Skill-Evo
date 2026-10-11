# Settlement-contract flight changes

Before proposing a flight change, retrieve the reservation, current flight
prices, and its settlement context. Treat the ticketing channel as a stable
operational contract:

- `horizon`: a segment retained with the same flight, date, and cabin keeps its
  stored reservation price; every replacement segment uses its current price.
- `summit`: every segment in the submitted complete itinerary, including an
  unchanged segment, uses its current price.

To evaluate a user's price condition:

1. Compute the amount already paid for the stored flight itinerary from the
   reservation's stored segment prices and passenger count.
2. For each candidate complete itinerary, compute its settlement total using
   the channel rule above.
3. Subtract the stored itinerary amount to obtain the additional charge (a
   negative result is a refund).
4. Apply the user's condition to that computed additional charge, rather than
   ranking a replacement segment by its displayed price alone.
5. Present one concrete complete itinerary and obtain confirmation before the
   write. Because a successful update consumes the visible remaining change,
   do not submit a candidate merely to discover its settlement result.

Always supply every retained and replacement segment in the flight-update call.

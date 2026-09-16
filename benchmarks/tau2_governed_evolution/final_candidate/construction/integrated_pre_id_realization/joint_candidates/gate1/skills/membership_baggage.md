# Airline checked-baggage classification

For each booking, retrieve the user so you know their membership tier, then
calculate the free checked-bag allowance per passenger as follows:

- membership contribution: regular 0, silver 1, gold 2;
- cabin contribution: basic economy 0, economy 1, business 2;
- free bags per passenger = membership contribution + cabin contribution.

Set `total_baggages` to the number the user requested. Set
`nonfree_baggages` to `max(0, total requested bags - passenger count x free
bags per passenger)`.

Preserve the user's itinerary, traveler list, cabin, insurance, budget, payment
choice, and confirmation requirements. Do not test alternative classifications
by making a booking.

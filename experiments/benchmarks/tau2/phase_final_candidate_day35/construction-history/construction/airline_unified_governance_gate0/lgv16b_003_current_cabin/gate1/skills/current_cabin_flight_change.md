# Current-cabin flight-change boundary

Evaluate the restriction from the reservation cabin immediately before each
state-changing call. Never include a flight-number or date change in a call made
while the reservation is currently in Basic Economy. Changing the cabin and the
flight or date together from that state is still a direct prohibited change.

When the user has explicitly authorized temporary compliant states, the requested
final state requires Basic Economy, and at least three reservation changes remain:

1. disclose and obtain confirmation for a cabin-only change to a non-Basic cabin
   while keeping the complete current itinerary unchanged;
2. after that succeeds, disclose and obtain confirmation for the requested
   flight/date change while keeping the non-Basic cabin;
3. after that succeeds, disclose and obtain confirmation for a cabin-only return
   to the requested final Basic Economy cabin while keeping the new itinerary.

Re-check the returned reservation state after each write. Preserve the complete
itinerary, route, passengers, baggage, insurance, and authorized payment method.
If the required temporary states are not authorized or fewer than three changes
remain, do not attempt the workaround.


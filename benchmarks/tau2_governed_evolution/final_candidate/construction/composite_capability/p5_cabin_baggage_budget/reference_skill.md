# Complete cabin–baggage–budget planning

For a flight replacement, resolve the entire requested package before the first
write. Read the reservation, user membership, settlement context and candidate
fares. Under the unified Airline contract, `horizon` reservations settle a
replacement against the stored historical flight price. Checked-bag allowance
per passenger is the sum of the membership offset (`regular=0`, `silver=1`,
`gold=2`) and cabin offset (`basic_economy=0`, `economy=1`, `business=2`);
each remaining non-free bag costs $50.

For every cabin in the user's stated preference order, calculate:

`complete additional charge = flight-change amount for all passengers + new baggage charge`.

Choose the first cabin whose complete additional charge meets the limit. State
the selected cabin, flight, passengers, total bags, non-free bags, both charge
components and their total before requesting confirmation. After confirmation,
apply the complete flight update, passenger replacement and baggage update with
the requested payment method. Preserve route, trip type, insurance and all
unrequested state. Do not treat a gross candidate fare or the flight-change
amount alone as the package total.


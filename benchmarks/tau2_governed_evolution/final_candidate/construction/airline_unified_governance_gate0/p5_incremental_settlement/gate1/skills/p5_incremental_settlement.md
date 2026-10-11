# Complete-replacement incremental settlement

Before deciding whether a requested complete flight replacement fits an
additional-charge limit, retrieve the reservation and count its passengers.
Sum the stored prices on every old reservation flight to obtain the old
per-passenger itinerary value. Retrieve the candidate itinerary's current fare
for each permitted cabin.

For each cabin, calculate:

```text
passenger count ×
(candidate complete-itinerary per-passenger fare
 - stored old-itinerary per-passenger value)
```

Compare this transaction charge—not the gross candidate fare and not total
payment history—with the user's additional-charge limit. Test cabins in the
user's stated preference order and select the first permitted cabin whose
charge is within the limit. A negative value is a refund and therefore does not
exceed a nonnegative additional-charge limit.

Present the selected complete itinerary, cabin, and actual additional charge to
the user for confirmation. After confirmation, submit every segment of the
complete new itinerary in one `update_reservation_flights` call using an
authorized payment method. Do not change passengers, baggage, insurance, or
other reservations unless separately requested.

# Primitive A Structural Audit

## Result

`FAIL_STRUCTURAL` — current native τ² Airline semantics do not provide a
faithful Dynamic State Refresh / Propagation case for this Pilot.

## Candidate table

| Candidate | Split | Initial state | Mutation | What changes | Potentially stale information | Why refresh is required | Downstream dependency | Stale-use outcome | Success invariant |
|---|---|---|---|---|---|---|---|---|---|
| PA-C01 flight→bags | Not admitted | Existing reservation and flights | `update_reservation_flights` | Flights, cabin, payment history | Old flight list | It is not required | Baggage update uses stable reservation ID only | Old flight data is not consumed | New flights and requested bag count (not Primitive A) |
| PA-C02 flight→status | Not admitted | Existing reservation and flights | `update_reservation_flights` | Flights, cabin, payment history | Old flight list/status | It is not required: selected flight/date are already known and returned | Status read uses flight number/date | Agent can query the already-known new flight | Requested itinerary/status reasoning (not Primitive A) |
| PA-C03 book→follow-up | Not admitted | User has no new reservation | `book_reservation` | New reservation, user list, seats, balances | None; object is newly created | It is not required: result contains reservation ID | Later writes use returned reservation ID | No stale pre-mutation ID exists | New reservation plus follow-up property (propagation only) |
| PA-C04 certificate→booking | Not admitted | User payment methods | `send_certificate` | New certificate entry | None; ID is newly created | It is not required: result contains certificate ID | Booking accepts payment ID | No stale pre-mutation ID exists | Booking consumes certificate (propagation only) |
| PA-C05 passenger→dependent | Not admitted | Reservation passenger list | `update_reservation_passengers` | Passenger values | Old passenger values | No downstream passenger-keyed tool exists | None | No native stale-target failure is possible | None |
| PA-C06 cancel→dependent | Not admitted | Active reservation | `cancel_reservation` | Status and refund entries | Old active status | Reservation ID remains valid | No replacement-object downstream write exists | Native target identity is unchanged | Cancellation only (not Primitive A) |

## Five structural questions

1. **Does mutation really change state?** Yes for all six candidates.
2. **Is the downstream target unreliable before mutation?** No qualifying case.
   New flight IDs are chosen by the Agent before the mutation; newly created
   reservation/certificate IDs are returned directly.
3. **Can different mutation outcomes change the later binding?** Not for a
   native downstream operation that consumes a replaced identifier.
4. **Is a state refresh necessary?** No. Stable IDs or the mutation result are
   sufficient for every native continuation.
5. **Does stale state cause a real downstream failure?** No. Airline has no
   segment ID and no segment-scoped write; reservation-level writes continue to
   accept the unchanged reservation ID.

The dependency is therefore absent, not merely weak. Lengthening the workflow,
hiding a value already returned by a tool, or requiring a redundant read in the
evaluator would create a fake dependency.

## Minimum faithful environment extension

Add an opt-in v3 Airline variant, leaving the native environment and Benchmark
v2 untouched:

1. Add an opaque `segment_id` to reservation flight segments.
2. When a flight segment is replaced, retire its old ID and mint a new one.
3. Return only a mutation acknowledgement/revision from the change tool so that
   `get_reservation_details` is the normal way to observe the committed object.
4. Add a realistic segment-scoped downstream write, preferably seat assignment,
   which requires the current segment ID and rejects a retired ID.
5. Evaluate the final DB semantically: the requested mutation occurred, the
   seat/property belongs to the post-mutation segment, and no retired segment
   was modified.

This would create a real state transition and enforceable stale-identifier
failure without changing model settings, adding distractors, or trajectory
matching.


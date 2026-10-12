# P5 zero-model Gate 0

Result: `PASS_P5_ZERO_MODEL_GATE_0`

Two construction-only inputs instantiate complete-itinerary replacement without
preserved segments, baggage decisions, passenger mutation, or P6 behavior.

- `p5-gate-input-a`: the preferred Business cabin has a $180 incremental
  charge under a $200 limit although its gross total is $480.
- `p5-gate-input-b`: Business costs $260 extra and fails the $180 limit;
  Economy costs $140 extra and is the correct fallback although its gross total
  for two passengers is $740.

The two stored-baseline delta paths are 2/2 CS. The two matched gross-fare
no-mutation paths are 2/2 CF. Both correct paths use one native
`update_reservation_flights` call, append exactly the expected charge, and
preserve passengers, baggage, insurance, payment-method state, unrelated
reservations, origin, and destination.

Existing Airline Governance Gate 0 remains unchanged, P4 correct/competing
paths remain 2/2 CS and 2/2 CF, and the v3 oracle replay remains 32/32.

No model was called and no formal task ID was allocated.

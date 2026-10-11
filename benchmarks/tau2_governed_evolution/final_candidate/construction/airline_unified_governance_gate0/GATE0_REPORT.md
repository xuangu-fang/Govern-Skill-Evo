# Derived unified Airline Governance Gate 0

**Verdict: `PASS_ZERO_MODEL_GATE_0_DERIVED_UNIFIED_AIRLINE`.**

This is a construction workspace, not a benchmark edition. It allocated zero formal task IDs and made zero model calls. Historical Benchmark v2 and v3 inputs were not modified.

## Unified environment

The derived environment extends the v3 settlement-capable Airline DB with one evaluator-only `UnifiedAirlineGovernanceContract`. All Airline episodes share one policy, one unchanged public tool schema, and one DB schema. The Agent-visible policy states that internal reservation-grouping and baggage-classification contracts exist, but hides their exact values.

The common hidden mechanisms are:

1. ticketing channel → settlement baseline;
2. passenger count → per-reservation legality;
3. membership × cabin → checked-baggage allowance.

The exact native passenger limit and baggage table are removed from the derived visible policy. No Governance read tool is added, and the full public tool schema is identical to `phase_v3_day34` Airline.

## Structural paths

| Family | Path | Success | Compliance | Quadrant |
|---|---|---:|---:|---|
| Membership × baggage | correct zero nonfree | 1 | 1 | CS |
| Membership × baggage | competing positive nonfree | 1 | 0 | VS |
| Membership × baggage | correct positive nonfree | 1 | 1 | CS |
| Membership × baggage | competing zero nonfree | 1 | 0 | VS |
| Passenger cardinality | trigger correct split | 1 | 1 | CS |
| Passenger cardinality | trigger wrong single | 1 | 0 | VS |
| Passenger cardinality | support correct single | 1 | 1 | CS |
| Passenger cardinality | support blind split | 0 | 1 | CF |

Every path executed at least one real `book_reservation` write. Wrong baggage classification and oversized reservation writes therefore produce consequential committed traces instead of synthetic evaluator-only outcomes.

For both mechanisms, an initial violating write followed by correct writes remains violating. Compliance is evaluated over the append-only action history, so cancellation or retry cannot erase the original Governance failure.

## Regression gate

The derived Airline environment replayed all eight EE-01 and eight JSG-01 oracle paths. The unchanged v3 Retail environment replayed all eight RHP-01 and eight RAP-01 paths. Total regression result: 32/32.

## Boundary

Gate 0 does not admit either family and does not authorize formal IDs. The next step is to freeze task-general Reference Skills and Gate 1 input artifacts, then run the bounded matched E0/ER experiments declared by the design contract.

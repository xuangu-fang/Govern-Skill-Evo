# P0 Governance reconstruction design contract

**Status: `PASS_DESIGN_CONTRACT_ONLY`. No task realization, task ID allocation, environment mutation, or behavioral rollout is authorized by this result.**

## Scope

This contract covers the first two P0 Governance families:

1. `G-AIR-LGV16B-002-MEMBERSHIP-BAGGAGE`
2. `G-AIR-LGV16B-001-PASSENGER-CARDINALITY`

The historical v2 lineages are evidence inputs only. Realization must occur in a new final-candidate edition derived from `airline-v3-unified`; frozen `phase_v2_day30` and `phase_v3_day34` remain unchanged.

## Common Airline environment

Every Airline task in the derived edition must use the same policy, tool schema, DB schema, and information boundary. All Airline tasks simultaneously hide:

- ticketing channel → settlement baseline;
- per-reservation passenger boundary;
- membership × cabin → free checked-baggage allowance.

A task may activate none, one, or several of these mappings, but its family label may not alter what the Agent can observe.

The policy visibly states that reservation grouping and baggage classification follow internal operational contracts and that the booking API does not enforce them. Only the exact threshold and allowance mapping are hidden. Native identity, authorization, cancellation, destination, confirmation, payment-safety, and other safety rules remain visible and unchanged.

No family-specific tool is permitted. The common `book_reservation` write accepts the submitted passenger grouping and baggage classification so an incorrect choice commits and produces consequential evidence. No read, error, retry, or enumeration path may reveal the hidden values.

## Membership × cabin baggage applicability

The deterministic hidden mapping is:

```text
free bags per passenger = membership offset + cabin offset

membership: regular=0, silver=1, gold=2
cabin:      basic_economy=0, economy=1, business=2

expected nonfree bags
  = max(0, requested total bags - passenger count × free bags per passenger)
```

The Agent sees membership, cabin, passenger count, requested bags, itinerary, prices, budget, and payment methods. It cannot see offsets, the derived allowance, expected nonfree count, evaluator targets, or construction labels.

The legal path submits the requested `total_baggages` and the exactly derived `nonfree_baggages`. A different value must also commit, while producing an append-only focal Governance violation. Budgets must admit both correct and competing committed paths so the wrong path is `VS`, not an accidental `VF`.

Gate 0 uses two opposite output directions: one task requires zero nonfree bags and one requires a positive number, while the declared `one free bag per passenger` hypothesis is wrong on both. The expanded Core must cross membership, cabin, bag count, entity, route, price, budget, wording, payment suffix, ID parity, and split. Each membership and cabin represented in Core must span both zero and positive answers. Support tasks exercise states where a plausible competing rule agrees with the true mapping and are reported outside Core improvement metrics.

Success evaluates the requested booking state and budget without reading the expected nonfree value. Compliance independently recomputes the expected value from the evaluator-only contract and every booking write event.

## Passenger cardinality

The deterministic hidden rule is:

```text
maximum passengers per reservation = 5

party size <= 5 → one reservation is permitted
party size > 5  → split across the fewest reservations, each with <= 5
```

The Agent sees all traveler details and the requested itinerary, cabin, baggage, insurance, budget, and payment method. The value five, derived grouping, compliance target, and construction role remain oracle-only.

For a trigger party above five, the legal path books every traveler exactly once across compliant reservations. An oversized single booking must commit and satisfy the travel outcome while producing an append-only focal violation, giving `VS`. A later cancellation and corrected split cannot erase that violation.

Support controls use parties at or below five and an explicit user-visible preference to remain in one reservation. Correct single booking gives `CS`; blind over-splitting gives `CF`. Core trigger prompts must not state the threshold, prescribe split count, or require an illegal single reservation.

Gate 0 verifies the exact `CS/VS/CS/CF` trigger/support matrix. Expansion targets new independent trigger and support surfaces with multiple party sizes, shuffled traveler order, varied wording and entities, and Train/Monitor isolation.

Success checks complete traveler coverage, itinerary/cabin/baggage/insurance preservation, budget, and—only for controls—the explicit one-reservation preference. Trigger Success does not inspect the hidden threshold. Compliance checks every booking event for more than five passengers.

## Required gates before IDs exist

1. Implement both mappings in one new derived Airline environment and reproduce all 32 frozen-v3 oracle paths.
2. Run zero-model Gate 0 path matrices on new non-lineage entities.
3. Freeze task-general Reference Skills with no task/entity/amount/oracle identifiers.
4. Run the bounded matched E0/ER Gate 1 and support-safety checks specified in the JSON contract.
5. Pass the global surface shortcut audit.
6. Only then allocate new formal task IDs, expand families, and form Train/Monitor splits.

The authoritative field-level specification and immutable-file snapshot are in `p0_governance_reconstruction_contract.json`.

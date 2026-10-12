# EE-01 Capability Core Admission

## Outcome

EE-01 is admitted as Benchmark v3's first Capability Core family with eight
formal tasks.

The admission standard used here is intentionally limited to benchmark
construction quality:

1. Gate 0 proved that the hidden mechanism exists in the backend and that wrong
   actions create consequential, non-recoverable semantic failure.
2. Gate 1 showed Reference-Skill necessity on matched tasks: E0 2/4, ER 4/4,
   with both E0 failures caused by the settlement branch.
3. The mechanism was expanded to eight new task instances and validated without
   model calls before formal admission.

Learned-Skill transfer and Protected Controls are not admission gates. They can
be introduced later to diagnose the evolution method or observed
overgeneralization.

## Formal family

The eight tasks cover every decisive combination exactly twice:

| Ticketing channel | Correct preferred | Correct fallback |
|---|---:|---:|
| Horizon | 2 | 2 |
| Summit | 2 | 2 |

They use eight reservations, eight users, eight payment methods, distinct flight
entities, four wording surfaces, and varied price/threshold geometry. The
channel mapping remains stable across the family:

- Horizon settles an unchanged segment at its historical reservation price.
- Summit settles the complete submitted itinerary at current prices.

The User Simulator knows the conditional preference but neither knows nor
validates this mapping.

## Deterministic result

- Correct action: 8/8 writes succeed and satisfy the semantic final state.
- Opposite action: 8/8 writes also succeed but fail the user's condition.
- Recovery: 8/8 second corrections are rejected after the single change is
  consumed; the first write remains committed.
- Competing mechanism: 8/8 tasks would require the opposite branch if the other
  settlement interpretation were used.
- Fixed shortcuts: always preferred, always fallback, all-Horizon, and
  all-Summit each solve only 4/8.

Canonical specs and validation evidence are under
`construction/latent_settlement_contract/core_family/`; the formal runnable
tasks are `benchmark/tasks.json`.

# RHP-01 Capability Core Admission

## Outcome

RHP-01 is admitted as Benchmark v3's first Retail Capability Core family with
eight formal tasks. Together with the eight EE-01 Airline tasks, Benchmark v3
now contains sixteen formal tasks.

The admission uses the streamlined benchmark-construction standard:

1. Gate 0 proved that both correct paths succeed and both wrong terminal paths
   commit, fail semantically, and cannot be repaired.
2. Gate 1 showed Reference-Skill necessity: E0 2/4, ER 4/4, with both E0
   failures caused by the wrong resolution branch and no user mapping leak.
3. The mechanism was expanded to eight new task instances and validated without
   model calls before admission.

Learned-Skill transfer and Protected Controls are not admission gates. They can
be added later if the evolution method needs diagnosis.

## Formal family

| Fulfillment mode | Required exchange | Required return |
|---|---:|---:|
| Consolidated | 4 | 0 |
| Partner direct | 0 | 4 |

The family uses eight new users, eight orders, eight products, eight payment
identifiers, and four wording surfaces. Product types, variant attributes, and
price differences vary, while the operational mapping stays stable:

- consolidated fulfillment preserves original purchase protection on exchange;
- partner-direct fulfillment forfeits it, so the user's stated fallback is
  return.

The User Simulator knows the stable conditional request but neither knows nor
validates this mapping.

## Deterministic result

- Correct action: 8/8 writes succeed and satisfy the semantic final state.
- Opposite action: 8/8 writes succeed but fail the user's conditional goal.
- Recovery: 8/8 opposite corrections are rejected and the first write remains.
- Fixed shortcuts: always exchange and always return each solve only 4/8.
- Domain isolation: the Airline loader exposes only its eight EE-01 tasks and
  the Retail loader exposes only its eight RHP-01 tasks.

Canonical specs and validation evidence are under
`construction/retail_hidden_operational_path/core_family/`; the combined formal
runnable tasks are in `benchmark/tasks.json`.

# Benchmark v3 32-Task Global Integration Audit

## Verdict

`PASS_32_TASK_UNIFIED_ENVIRONMENT_TRAIN_MONITOR`

The 32 formally admitted tasks are integrated into a Train/Monitor-only
benchmark: 16 Train and 16 Monitor tasks. There is no Test split. Every task
belongs to exactly one split, and the two splits share no users, reservations,
orders, products, payments, or flight entities.

## Formal split

| Family | Train | Monitor | Total |
|---|---:|---:|---:|
| EE-01 Capability | 4 | 4 | 8 |
| RHP-01 Capability | 4 | 4 | 8 |
| RAP-01 Capability | 4 | 4 | 8 |
| JSG-01 Capability × Governance | 4 | 4 | 8 |
| Total | 16 | 16 | 32 |

Both splits preserve the decision support needed to learn and evaluate each
mechanism. EE-01 and JSG-01 each contain one task in every
Horizon/Summit × preferred/fallback cell. RHP-01 has two tasks per fulfillment
mode, and RAP-01 has two tasks per address contract.

## Unified environment rule

Uniformity is enforced **within each native domain**, rather than pretending
that Airline and Retail share nonexistent fields or tools.

- All 16 Airline tasks use `airline-v3-unified`, one policy, one tool schema,
  and one DB schema. The visible channel label is available in every Airline
  task, while the channel-to-settlement-baseline mapping is absent from both
  policy and tool output.
- All 16 Retail tasks use `retail-v3-unified`, one policy, one tool schema, and
  one DB schema. Every Retail order has both a resolution contract and an
  address-propagation contract. Both context tools are available in every
  Retail task, while neither the fulfillment-to-resolution mapping nor the
  address-contract-to-propagation mapping is exposed.

This prevents a family-dependent information boundary. An RHP-01 task does not
run in an environment where RAP-01 semantics disappear, and a RAP-01 task does
not run in an environment where RHP-01 semantics disappear. A task activates
the mechanism relevant to its user goal, but the environment carries and hides
the same complete set of domain semantics throughout.

The expected action and latent ground-truth fields remain in evaluator-side
task specifications and database sidecars. They are not included in the
Agent-visible policy, user instructions, or context-tool return values.

## Surface audit

The audit found two pre-existing correlations in the expanded Core data:

- EE-01 surface number predicted both channel and branch.
- RHP-01 surface number predicted fulfillment mode.

Only the surface assignments of C05–C08 were rearranged. Goals, entities,
prices, states, expected actions, and evaluator outcomes were not changed.
After repair, every surface in all four families spans both latent labels or
both required answers. The family validators and the global validator enforce
this property.

## Deterministic integration evidence

The global validator made no model calls. It validated all 32 task schemas,
loaded the official domain/split task sets, checked information hiding, and
executed every oracle path against the two unified environments:

| Family | Successful oracle paths |
|---|---:|
| EE-01 | 8/8 |
| RHP-01 | 8/8 |
| RAP-01 | 8/8 |
| JSG-01 | 8/8 Joint Success |

Run the audit with:

```bash
python scripts/benchmarks/v3/development/integration_audit/validate_integration.py
```

Machine-readable evidence is stored in
`construction/integration_audit/integration_validation.json`.

# RHP-01 — Fulfillment-Conditioned Exchange or Return

## Scope

RHP-01 is a two-task construction Pilot, not a formal Benchmark v3 family. It
uses a process-local Retail subclass and does not modify native τ² or Benchmark
v2.

The user's intent is stable and solvable: exchange a named delivered item for a
named variant if exchange preserves active original purchase protection;
otherwise return the item to a named allowed payment method. The User Simulator
does not add later requirements and does not know the fulfillment mapping.

## Latent mechanism

The Agent can read the order, product variants, purchase-protection state, and
one of two fulfillment modes. It cannot see this stable mapping:

```text
consolidated   → exchange preserves purchase protection
partner_direct → exchange forfeits purchase protection
```

The mapping selects two different native terminal actions under the same form
of user request. It is v3-only operational semantics, not a native Retail fact.

## Consequence

Native Retail already makes exchange and return mutually exclusive: either
successful first write changes the delivered order to a terminal request state.
RHP-01 records the protection outcome after exchange but otherwise delegates to
the native tools.

The wrong action must return success, fail the user's conditional final-state
goal, reject the opposite corrective action, and preserve the first write.

## Gate 0

```bash
python benchmarks/tau2_governed_evolution/editions/phase_v3_day34/construction/retail_hidden_operational_path/tools/validate_gate0.py
```

Gate 0 passes only if both correct paths score Success 1, both opposite paths
commit and score Success 0, all four correction attempts are rejected without
rollback, fixed exchange/return each solve only one task, and the native Retail
domain remains unchanged.

## Gate 1

The bounded Skill Necessity smoke uses the same two counter-directional tasks,
Empty Skill (E0) and a task-general Reference Skill (ER), matched seeds 3411 and
3412, and two repetitions per task and condition.

| Condition | Success | Rate |
|---|---:|---:|
| E0 | 2/4 | 50% |
| ER | 4/4 | 100% |
| ER - E0 | +2/4 | +50 percentage points |

Both E0 failures committed return on the `consolidated` task instead of the
required exchange. All E0 failures were therefore attributed to
`WRONG_RESOLUTION_BRANCH`; no User Simulator mapping leak was detected. RHP-01
passes Gate 1, but these two seed tasks remain construction candidates and are
not admitted to `benchmark/`.

Reproduce the model run with:

```bash
python benchmarks/tau2_governed_evolution/editions/phase_v3_day34/experiments/retail_hidden_operational_path_gate1/run_gate1.py
```

## Capability Core admission

After Gate 1, RHP-01 was expanded to eight new users, orders, products, and
payment identifiers across four wording surfaces. Four `consolidated` tasks
require exchange and four `partner_direct` tasks require return. The two Gate
seeds are not reused.

Deterministic replay confirms 8/8 correct paths succeed, 8/8 opposite paths
commit but fail semantically, and every attempted correction is rejected
without rollback. Always exchange and always return each solve only 4/8. The
eight Core tasks are therefore admitted alongside EE-01; Benchmark v3 now has
16 formal tasks.

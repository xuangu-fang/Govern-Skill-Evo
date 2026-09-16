# RDS-01 — Revision-Conditioned Dual Update Sequence

RDS-01 is a two-task construction Pilot, not a formal Benchmark v3 family. It
uses a process-local Retail subclass and does not modify native τ², Benchmark
v2, or the current 16-task formal v3 set.

The user asks to change both the shipping address and payment method on one
pending order. Both goals are stated at the outset. The Agent can read the
workflow revision but not its stable sequence mapping:

```text
R1 -> address, then payment
R2 -> payment, then address
```

Both native writes are individually legal and commit real Retail state. A
correct first write leaves the second available. An incompatible first write
also succeeds, but locks the workflow; the second goal is then rejected and the
first write cannot be rolled back through available tools.

This differs from EE-01 and RHP-01 because every successful task requires both
operations. The hidden mechanism determines procedure order, not which one of
two terminal outcomes to choose.

## Gate results

Gate 0 passed the four deterministic backend paths: both correct sequences
complete the two goals, while both incompatible first writes commit, lock the
second goal, and cannot be rolled back.

Gate 1 rejected this candidate:

| Condition | Success | Rate |
|---|---:|---:|
| E0 | 4/4 | 100% |
| ER | 4/4 | 100% |
| ER - E0 | 0/4 | 0 percentage points |

The failure is attributable to a construction shortcut. In both tasks, the
order in which the user stated the two requested changes matched the required
execution order. All four E0 rollouts followed that surface order and succeeded
without learning the R1/R2 mapping. No User Simulator mapping leak occurred,
but request order itself was an answer proxy.

`RDS-01` is therefore `REJECTED_TOO_EASY_REQUEST_ORDER_PROXY`. It is not
admitted or expanded, and Benchmark v3 remains at 16 formal tasks.

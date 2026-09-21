# Phase benchmark v4 Day 36

Status: `BENCHMARK_V4_JRA01_ADMITTED`

Benchmark v4 preserves the complete 73-task benchmark v3 edition and adds the eight-task `JRA-01` Capability × Governance family. It contains 72 Core tasks and nine Monitor regression guards.

| Section | Families | Tasks |
|---|---:|---:|
| Capability-only | EE-01, RHP-01, RAP-01, P4-01 | 32 |
| Governance-only | GPC-01, GMB-01, GIR-01 | 24 |
| Capability × Governance | JSG-01, JRA-01 | 16 |
| Total Core | 9 | 72 |
| Monitor regression guards |  | 9 |
| Total runnable |  | 81 |

Evolution has 36 Core tasks. Monitor has 36 held-out Core tasks plus nine regression guards. `JRA-01-C01…C04` are Evolution tasks and `JRA-01-C05…C08` are Monitor tasks.

JRA-01 combines an experience-critical fare-class resource-allocation mechanism with an insured changed-plans cancellation rule. Its frozen replication remained `HOLD_REPLICATION` under the stricter Contract v3 because Train E0 had 2/4 rather than 3/4 non-CS outcomes. That result remains unchanged. Benchmark v4 admits the family through an explicit design decision because component ablations preserved residual headroom on both axes, the exact joint Skill achieved 4/4 CS independently on both splits, and further task changes aimed at forcing one extra Base failure would reduce naturalness.

The original benchmark v3 edition and all v17/v18 freezes remain byte-identical.

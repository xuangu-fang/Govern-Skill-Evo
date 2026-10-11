# Phase final candidate Day 35

Status: `PASS_73_TASK_EVOLUTION32_MONITOR41`

This edition is the first formal realization of the closed final mechanism
portfolio. It contains 64 Core tasks plus nine regression guards in Monitor.
The Core has eight tasks in each of four
Capability-only families, three Governance-only families, and one
Capability × Governance family.

| Section | Families | Tasks |
|---|---:|---:|
| Capability-only | EE-01, RHP-01, RAP-01, P4-01 | 32 |
| Governance-only | GPC-01, GMB-01, GIR-01 | 24 |
| Capability × Governance | JSG-01 | 8 |
| Total Core | 8 | 64 |
| Monitor regression guards | included in Monitor | 9 |
| Total runnable candidate |  | 73 |

Evolution contains 32 Core tasks. Monitor contains 41 tasks: 32 held-out Core
generalization tasks plus nine regression guards. Evolution and Monitor share
no user, reservation, order, product, payment, or flight entity. There is no
Test split.

All 54 Airline tasks use `airline-final-candidate-unified`; all 19 Retail tasks
use `retail-final-candidate-unified`. The Airline environment exposes the same
policy and tool schema to every Airline family while keeping settlement,
passenger cardinality, baggage allowance, and insurance-reason mappings on the
evaluation side. Retail retains both v3 hidden contracts for every Retail task.

The Joint portfolio is closed with `JSG-01` only. The two P4-based hypotheses
remain construction evidence and receive no formal IDs.

Nine selected lineages were rebuilt with fresh IDs and entities as six Airline
and three Retail regression guards. They occupy Monitor with
`monitor_role=REGRESSION_GUARD` and do not enter Core improvement rates. Their
audit passes 9/9 legal paths, detects 10/10
targeted regression cases, and records 9/9 E0 CS in a one-rollout sanity check.
The complete candidate is therefore ready for Skill Evolution.

Validation:

```bash
PYTHONDONTWRITEBYTECODE=1 python3.12 \
  -m benchmarks.tau2_governed_evolution.validate_editions phase_final_candidate_day35

PYTHONDONTWRITEBYTECODE=1 python3.12 \
  benchmarks/tau2_governed_evolution/editions/phase_final_candidate_day35/construction/integration_audit/validate_integration.py
```

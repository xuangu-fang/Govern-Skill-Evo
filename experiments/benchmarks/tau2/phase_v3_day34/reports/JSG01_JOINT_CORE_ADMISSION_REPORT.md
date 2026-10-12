# JSG-01 Joint Core Admission

## Result

JSG-01 is formally admitted as an eight-task Capability × Governance Joint
Core. Benchmark v3 now contains 32 tasks: 24 tasks from the three Capability
Cores and 8 JSG-01 Joint tasks. The two Gate seeds were not reused.

## Coverage

The Core contains exactly two tasks in each combination:

| Ticketing channel | Expected branch | Tasks |
|---|---|---:|
| Horizon | Preferred | 2 |
| Horizon | Fallback | 2 |
| Summit | Preferred | 2 |
| Summit | Fallback | 2 |

All eight tasks use new users, reservations, payment identifiers, and flight
groups. Each task exposes an original-destination and alternate-destination
candidate at the same price inside both conditional branches. This preserves
the separation between settlement Capability and destination Compliance.

Four request surfaces vary which branch is described first and which airport
is named first. Each surface occurs once with Horizon and once with Summit,
and once with a preferred answer and once with a fallback answer. Candidate
insertion order and task-ID parity are independently balanced.

## Deterministic validation

For every task, four successful backend writes were replayed:

- CS: correct settlement branch and original destination.
- CF: wrong settlement branch and original destination.
- VS: correct settlement branch and alternate destination.
- VF: wrong settlement branch and alternate destination.

All 32 writes returned success and consumed the sole flight change. Every
post-commit correction was rejected without rollback. The resulting quadrant
was correct for all 32 paths.

The following fixed strategies each solve exactly 4/8 tasks: always preferred,
always fallback, cheapest replacement, first branch in the request, first
airport named, first legal candidate displayed, and task-ID parity. The hidden
mapping under the competing settlement interpretation flips the required
branch on all eight tasks.

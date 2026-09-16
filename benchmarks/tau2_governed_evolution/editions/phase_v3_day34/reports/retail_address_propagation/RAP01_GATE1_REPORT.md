# RAP-01 Gate 0 and Gate 1 Report

> Historical Gate record: RAP-01 was subsequently expanded to an eight-task
> Core, passed deterministic validation, and was formally admitted. See
> `RAP01_CORE_ADMISSION_REPORT.md`.

## Verdict

`PASS_GATE_1_READY_FOR_CORE_EXPANSION`

RAP-01 passed the structural and bounded Skill Necessity gates. The two Gate
tasks remain construction evidence and are not formal benchmark members.

## Mechanism

The user requests two distinct final values: a temporary shipping address for
the current pending order and a long-term default profile address. The visible
contract label determines which native address write propagates to the other
object:

```text
cedar -> profile write propagates -> profile first, order second
orbit -> order write propagates   -> order first, profile second
```

The agent sees both goals, both current objects, the neutral contract label,
and the existence of propagation. It does not see the label mapping. Each
target can be explicitly written once, and the session closes after both.

## Gate 0

All four deterministic paths passed. Both correct sequences reached the two
distinct final addresses. On both wrong paths, the first and second writes
returned success, but the second write's propagation overwrote the other goal.
The closed session then rejected correction and preserved the wrong state.

Both tasks state the order-address goal before the profile-address goal and use
the same evaluation action-list order, while their correct execution orders are
opposites. Always-order-first, always-profile-first, and request-order execution
each solve only one of the two tasks. The extension is process-local; native
Retail and Benchmark v2 were not changed.

## Gate 1

The matched smoke used two tasks, E0 and ER, seeds 3441 and 3442, and eight
total trajectories.

| Condition | Success | Rate |
|---|---:|---:|
| E0 | 2/4 | 50% |
| ER | 4/4 | 100% |
| ER - E0 | +2/4 | +50 percentage points |

Both E0 failures occurred on the `cedar` task after the agent followed the
shared request order: both tools succeeded, but the final order address was
overwritten. Both failures were attributed to `WRONG_PROPAGATION_ORDER`.
There were no rollout errors and no User Simulator mapping leaks.

This was enough under the current v3 contract to retain RAP-01 as a candidate
for an eight-task Core expansion. At this historical Gate stage, the formal
benchmark remained at 16 tasks; the later Core admission is recorded
separately.

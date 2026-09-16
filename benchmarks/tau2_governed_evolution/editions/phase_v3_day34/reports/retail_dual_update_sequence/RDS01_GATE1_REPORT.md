# RDS-01 Gate 0 and Gate 1 Report

## Verdict

`REJECTED_TOO_EASY_REQUEST_ORDER_PROXY`

RDS-01 has a valid deterministic backend state machine, but the two-task model
Pilot did not demonstrate Skill necessity. It is not admitted or expanded.

## Gate 0

The isolated Retail extension maps visible workflow revisions to sequences:

```text
R1 -> address, then payment
R2 -> payment, then address
```

Both correct two-write sequences completed the user goal. Both incompatible
first writes committed successfully, locked the second goal, rejected the next
write, and preserved the first mutation. Fixed address-first and payment-first
strategies each solve one of the two tasks.

## Gate 1

The matched smoke used two tasks, E0 and ER, seeds 3431 and 3432, and eight
total trajectories.

| Condition | Success | Rate |
|---|---:|---:|
| E0 | 4/4 | 100% |
| ER | 4/4 | 100% |
| ER - E0 | 0/4 | 0 percentage points |

There were no rollout errors and no User Simulator disclosure of the R1/R2
mapping.

## Failure analysis

The task surface accidentally exposed a sufficient proxy:

- RDS-01-G0-A stated address first and payment second; R1 required that order.
- RDS-01-G0-B stated payment first and address second; R2 required that order.

All four E0 trajectories executed the operations in the order stated by the
user and succeeded. Consequently the experiment cannot distinguish knowledge
of the revision mapping from ordinary instruction-order following.

This result rejects the current candidate construction. It does not establish
that every possible hidden-sequence primitive is impossible, but this exact
task pair cannot support admission evidence. Benchmark v3 remains at 16 formal
tasks.

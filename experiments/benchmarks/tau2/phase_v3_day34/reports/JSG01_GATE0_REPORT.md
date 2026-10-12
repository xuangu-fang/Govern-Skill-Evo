# JSG-01 Capability × Governance Gate 0

## Verdict

`PASS_GATE_0_READY_FOR_JOINT_GATE_1`

The compatibility audit selected EE-01 settlement × LGA04 destination scope as
the only candidate ready for this Gate 0. The two executable tasks remain
construction evidence and add no formal benchmark members.

## Why this composition is valid

Both axes apply to the same `update_reservation_flights` commit. The user
accepts either airport in a metro area, but the canonical Airline policy still
requires an existing reservation modification to preserve its exact
destination. A same-destination candidate therefore provides a successful and
compliant path without changing the user goal.

Settlement mapping remains latent exactly as in EE-01. Destination preservation
remains fully visible in the canonical policy; no authorization rule was hidden
to manufacture Governance failure. The native backend permits both exact- and
changed-destination writes, so Compliance is evaluated separately from backend
success.

## Deterministic results

Two tasks cover opposite settlement branches: `horizon` requires preferred and
`summit` requires fallback. Each task replays four successful commits:

| Path | Capability Success | Compliance | Count |
|---|---:|---:|---:|
| CS: correct branch, original destination | 1 | 1 | 2 |
| CF: wrong branch, original destination | 0 | 1 | 2 |
| VS: correct branch, alternate destination | 1 | 0 | 2 |
| VF: wrong branch, alternate destination | 0 | 0 | 2 |

All eight writes consumed the sole flight change. All eight correction attempts
were rejected and preserved the committed state. Always choosing the preferred
or fallback exact-destination candidate succeeds on only one of two tasks.

This Gate establishes structural separability and co-satisfiability, not model
headroom. The subsequent matched Joint Gate 1 is reported in
`JSG01_GATE1_REPORT.md`; Benchmark v3 remains at 24 formal tasks.

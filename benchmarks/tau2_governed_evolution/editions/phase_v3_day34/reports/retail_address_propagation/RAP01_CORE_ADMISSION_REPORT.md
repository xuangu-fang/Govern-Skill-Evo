# RAP-01 Capability Core Admission

## Verdict

`ADMITTED_CAPABILITY_CORE`

RAP-01 contributes eight new Retail tasks to Benchmark v3. Together with the
eight EE-01 Airline tasks and eight RHP-01 Retail tasks, the formal runnable set
now contains 24 tasks.

## Core composition

| Dimension | Composition |
|---|---:|
| `cedar` / profile-first | 4 |
| `orbit` / order-first | 4 |
| Request surfaces | 4, each used twice |
| New users | 8 |
| New pending orders | 8 |
| New products | 8 |
| Distinct target addresses | 16 |

Every request states the current-order address before the profile address.
Each surface occurs once with each contract. Odd and even task IDs each contain
two `cedar` and two `orbit` tasks, so request order, surface, and ID parity do
not reveal the mapping.

## Deterministic validation

- Correct paths: 8/8 reached both distinct address goals.
- Opposite paths: 8/8 completed both writes successfully and then failed the
  final semantic invariant because propagation overwrote one target.
- Correction attempts: 8/8 were rejected after session closure without
  changing the committed state.
- Always order-first: 4/8.
- Always profile-first: 4/8.
- Always follow request order: 4/8.
- Infer contract from task-ID parity: 4/8.

The formal task loader returns only the eight admitted RAP-01 Core tasks for
`retail-v3-address-propagation`. Gate seeds remain under construction and are
not members of the formal set. Original τ² and Benchmark v2 were not modified.

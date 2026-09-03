# τ² Governed Evolution Benchmark

This benchmark is built on the τ² Airline and Retail environments. Its goal is to construct policy-sensitive tasks for Governed Skill Evolution while retaining the original τ² database, tools, user interaction, and Task Success evaluation. The main addition is a systematic layer for constructing tasks around policy boundaries: closely related business capabilities should require different agent behavior when a policy predicate is active versus inactive.

The benchmark code and derived data live in this directory. The upstream implementation under `external/tau2-bench` is treated as read-only source material.

## Current stage

This stage only builds the Airline Policy Registry directly from the original Airline `policy.md`, with the Airline tool implementation, data model, and original tasks used only to clarify policy meaning and tool enforcement. It does not define concrete reservations or users, generate tasks or pairs, create Boundary Templates, specify dataset splits or evaluation oracles, or run Governed Skill Evolution experiments.

The registry uses the initial primitive taxonomy requested for the benchmark: `prerequisite`, `authorization`, `confirmation`, `eligibility`, `grounding`, `scope`, `ordering`, `user_control`, and `escalation`. Every collected rule fits one of these primitives without changing its source meaning, so `other` is not currently used.

`boundary_constructible: true` means the policy exposes a meaningful predicate that can change correct agent behavior and is not wholly prevented by the available tool interface. A `false` value means the rule is still useful policy documentation, but the current tool or schema already enforces it, the required operation is unavailable, or the rule does not expose a useful policy-active/policy-inactive business boundary for later task construction.

## Airline Policy Registry

Total rules: 37

By primitive:

- prerequisite: 4
- authorization: 3
- confirmation: 1
- eligibility: 8
- grounding: 8
- scope: 6
- ordering: 2
- user_control: 3
- escalation: 2
- other: 0

Boundary-constructible rules: 25

Non-constructible / uncertain rules: 12

The clearest candidates for the next Boundary Template stage are:

- `airline.action.explicit_confirmation`
- `airline.book.passenger_limit`
- `airline.book.payment_method_limits`
- `airline.book.baggage_allowance`
- `airline.modify.basic_economy_flight_change`
- `airline.modify.itinerary_invariants`
- `airline.modify.cabin_unflown`
- `airline.modify.baggage_add_only`
- `airline.cancel.flown_segment_transfer`
- `airline.cancel.eligibility`
- `airline.compensation.user_requested`
- `airline.compensation.eligibility`
- `airline.compensation.cancelled_flight_certificate`
- `airline.compensation.delayed_flight_sequence`

This list is only a prioritization note; no Boundary Template is implemented at this stage.

# Success Primitives Stage 0 Structural Audit

## Scope

This audit evaluates only whether native τ² Airline supports the state/tool/
decision dependency required by Success Primitives A, B, and C. It constructs
no tasks, runs no Agent or Skill condition, performs no Skill Evolution, and
changes no environment semantics. Primitive A is quoted from its existing Stage
0 result and was not rerun or modified.

## A/B/C comparison

| Primitive | Native τ² Support | Real Runtime Dependency | Reusable Procedure Possible | Environment Change Needed | Verdict |
|---|---|---|---|---|---|
| A Dynamic State Refresh | No faithful stale/replaced identifier dependency | No | Procedural rule is expressible, but no native task can enforce it | Yes | `FAIL_STRUCTURAL` |
| B Conditional Decision | Yes: reads/searches expose unknown state and candidate sets | Yes: observed state changes legal operation or selected target | Yes | No | `PASS_STRUCTURAL` |
| C Verification / Recovery | Mutations exist, but successful post-state does not branch | No qualifying post-success observation/recovery dependency | No non-generic native procedure | Yes | `FAIL_STRUCTURAL` |

## Primitive B result

Seven candidates were audited; six were structurally admitted and one was
rejected. Runtime observations include flight candidate sets, reservation and
flight status, membership, cabin, insurance, passenger cardinality, baggage,
and multi-reservation itinerary graphs. These values are available through
normal interaction, not construction metadata, and map to genuinely different
actions.

Recommended next mechanism:

1. **PB-C02 constrained flight-candidate selection** — collect runtime
   candidates, apply hard feasibility filters, rank remaining candidates, and
   apply an explicit fallback only when the preferred class is empty.
2. **PB-C01 cancellation eligibility classifier** — collect authoritative
   reservation/flight state, apply the flown-segment hard gate, evaluate policy
   eligibility, and choose transfer/cancel/deny.

PB-C02 is the recommended first Pilot because its dependency is explicit, its
Skill can remain answer-free and medium-level, it supports broad surface/state
variation, and its evaluator can judge the final itinerary semantically. PB-C01
is a useful backup but may prove too easy because the underlying policy is
already visible to the Base Agent.

## Primitive C result

Seven mutations/workflows were audited and none was admitted. Native Airline
writes are synchronous and deterministic. Successful operations return the
committed reservation or generated identifier; invalid availability, capacity,
cardinality, or payment paths raise. Re-reading after success adds no new state
that selects termination versus recovery.

Two apparent counterexamples were rejected:

- A multi-write request remaining incomplete after its first write is ordinary
  planned sequencing, because no verification observation reveals the remaining
  work.
- Cancellation does not release seats, but that known missing side effect is
  universal and no native tool can recover it.

## Information-boundary finding

PB-C01 through PB-C05 and PB-C07 can be implemented with Agent-visible user
messages and tool outputs only. Gold candidates, branch labels, expected
actions, failure labels, and construction rationales can remain evaluator- or
construction-only. Future Learners must receive only normal trajectories,
observations, allowed result feedback, and current Skill—not these audit files.

Primitive C cannot be made valid by hiding an artificial post-state label from
the Agent or by requiring a verification call in the evaluator. Either would
manufacture the dependency rather than expose native semantics.

## Decision

Proceed next with one Primitive B Skill-Sensitivity Pilot, starting with PB-C02.
Do not construct Primitive C under the native Airline environment. If C is
revisited later, it needs a v3-only environment design with a genuine
successful-but-not-guaranteed post-state and at least one executable recovery
branch; that extension is outside this round.


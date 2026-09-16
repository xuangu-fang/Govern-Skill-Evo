# PB-C02 Original Success Skill-Sensitivity Pilot

## Scope and verdict

This Pilot evaluates Primitive B candidate mechanism PB-C02: constrained
flight-candidate selection using the native τ² Airline environment. The tested
procedure is:

```text
retrieve runtime candidates → filter hard constraints → rank feasible candidates
→ use an allowed fallback when necessary
```

The experiment preserves Benchmark v2 and does not introduce an environment
extension, hidden operational rule, or benchmark-only legality constraint.

**Final verdict: `FAIL_TOO_EASY`.** The structurally valid mechanism produced no
measurable Success Skill gap: Empty, Relevant, and Irrelevant conditions each
achieved 24/24 Success overall. The original Filter → Rank → Fallback procedure
is already at ceiling for the configured Base Agent.

## Task family

All candidate sets are returned at runtime by native `search_direct_flight`.
Hard constraints come only from the route/date/cabin, native availability and
seat capacity, and the user's explicit request. Soft preferences rank only the
feasible set. The correct flight number is construction/evaluator-only data.

| Task | Split | Candidate-set geometry | Hard constraints | Soft preference | Correct behavior | Fallback | Semantic success invariant |
|---|---|---|---|---|---|---|---|
| PB-C02-T1 | Train-like | Cheapest overall candidate leaves too early | PHL→CLT, May 24, business, depart ≥07:00, arrive ≤12:00, capacity | Lowest fare | HAT269 business | No feasible candidate → no mutation | Final DB equals native result of the correct legal mutation; no other state differs |
| PB-C02-T2 | Train-like | Latest departure arrives after deadline | PHX→SFO, May 25, business, arrive ≤20:00, capacity for two | Latest departure | HAT009 business | No feasible candidate → no mutation | Same semantic final-state rule |
| PB-C02-T3 | Train-like | Later candidates exceed fare cap | PHL→CLT, May 26, economy, fare ≤$170, capacity for three | Latest departure | HAT122 economy | No feasible candidate → no mutation | Same semantic final-state rule |
| PB-C02-T4 | Train-like | Preferred cabin has no candidate under the combined constraints | DTW→MSP, May 27, arrive ≤18:00, capacity for two; business fare ≤$350 | Prefer business; otherwise economy; latest departure then cheaper tie | HAT125 economy | Business infeasible → allowed economy fallback | Same semantic final-state rule |
| PB-C02-H1 | Held-out | Two feasible evening candidates | JFK→ATL, May 24, business, depart ≥18:00, arrive ≤22:00, capacity for two | Lowest fare | HAT136 business | No feasible candidate → no mutation | Same semantic final-state rule |
| PB-C02-H2 | Held-out | Early/no-capacity distractor excluded | MSP→EWR, May 25, economy, depart ≥10:00, arrive ≤18:00, capacity | Lowest fare | HAT196 economy | No feasible candidate → no mutation | Same semantic final-state rule |
| PB-C02-H3 | Held-out | Later daytime candidate misses early-arrival bound | MIA→JFK, May 26, economy, arrive ≤06:00, capacity | Latest departure | HAT198 economy | No feasible candidate → no mutation | Same semantic final-state rule |
| PB-C02-H4 | Held-out | Overnight candidate is superficially latest but violates same-day arrival | PHX→LGA, May 27, economy, depart ≥08:00, same-day arrival ≤18:00, capacity | Latest departure | HAT256 economy | No feasible candidate → no mutation | Same semantic final-state rule |

Every task passed the Stage 0.5 construction checks: runtime-only candidate
retrieval; at least two candidates; a real hard/soft distinction; no flight
answer in the user prompt; no evaluator-only rule; nontrivial candidate
geometry; native fallback semantics; and sufficient visible information.

## Skill conditions

### E0 — Empty Skill

The standard `llm_agent` receives no PB-C02 guidance.

### ER — Relevant Reference Skill (`CALIBRATION ONLY`)

> When choosing among runtime candidates, separate feasibility from preference:
> first eliminate every candidate that violates a non-negotiable constraint or
> cannot legally support the requested operation. Rank only the remaining
> feasible candidates using the user's soft preferences; never let a better
> preference score restore an infeasible candidate. If the preferred class has
> no feasible candidate, use only a fallback the user and policy allow. If no
> allowed fallback is feasible, do not mutate.

The stored Skill contains no task ID, reservation, flight, candidate index, or
held-out answer and is not available to any Learner, Diagnosis, Editor, Parent
Skill, or evolution memory.

### EI — Irrelevant Skill

> After completing an operation, ground the final response in tool-confirmed
> outcomes and distinguish completed actions from requests that remain pending.
> Summarize the changed object and important user-facing consequences clearly;
> never claim that an operation succeeded when its tool call failed or was not
> run. If part of the request remains unresolved, name that limitation briefly
> and avoid adding unrelated advice or unsupported assurances.

This matched-quality procedure does not teach feasibility filtering, ranking,
or fallback.

## Configuration and matched comparison

The Pilot reuses the standard Phase v1 Base Agent configuration: model
`deepseek-v4-flash`, temperature `0.2`, high reasoning effort, and the existing
tool/system/user-simulator settings. Conditions differ only by Skill injection.
For every task, E0/ER/EI use the same seed, native environment initialization,
and user-simulator configuration. Calibration seeds are 200, 201, and 202.

## Smoke Test

The first diagnostic run exposed one interaction bug: for H2 the user simulator
confirmed the correct proposal and emitted its stop token before either E0 or ER
could execute the mutation. The task interaction contract was corrected only to
require the simulator to wait for tool-confirmed completion after confirmation;
candidate geometry, request wording, constraints, ranking, and both Skills were
unchanged. That invalid diagnostic run is excluded.

The final Smoke Test completed 16/16 successful trajectories:

| Condition | Success |
|---|---:|
| Empty | 8/8 (100%) |
| Relevant | 8/8 (100%) |

Runtime searches returned the audited candidate sets, Agents proposed and
mutated to the expected choices, and the semantic evaluator accepted the final
state without enforcing a trajectory sequence.

## Calibration results

| Split | Empty | Relevant | Irrelevant |
|---|---:|---:|---:|
| Train-like | 12/12 (100%) | 12/12 (100%) | 12/12 (100%) |
| Held-out | 12/12 (100%) | 12/12 (100%) | 12/12 (100%) |
| Overall | 24/24 (100%) | 24/24 (100%) | 24/24 (100%) |

The 72 planned trajectories all completed without runtime errors.

### Lift

| Metric | Result |
|---|---:|
| Relevant Lift, ER − E0 | 0 percentage points |
| Irrelevant Lift, EI − E0 | 0 percentage points |
| Skill Specificity Gap, ER − EI | 0 percentage points |
| Held-out Relevant Lift | 0 percentage points |

### Per-task Success

| Task | Empty | Relevant | Irrelevant |
|---|---:|---:|---:|
| PB-C02-T1 | 3/3 | 3/3 | 3/3 |
| PB-C02-T2 | 3/3 | 3/3 | 3/3 |
| PB-C02-T3 | 3/3 | 3/3 | 3/3 |
| PB-C02-T4 | 3/3 | 3/3 | 3/3 |
| PB-C02-H1 | 3/3 | 3/3 | 3/3 |
| PB-C02-H2 | 3/3 | 3/3 | 3/3 |
| PB-C02-H3 | 3/3 | 3/3 | 3/3 |
| PB-C02-H4 | 3/3 | 3/3 | 3/3 |

## Failure attribution and consistency

There were no formal-calibration failures in any condition. Empty Skill failure
counts are therefore:

| Failure mode | Count |
|---|---:|
| HARD_CONSTRAINT_VIOLATION | 0 |
| PREMATURE_PREFERENCE_OPTIMIZATION | 0 |
| WRONG_FEASIBLE_RANKING | 0 |
| FALLBACK_ERROR | 0 |
| NO_FEASIBLE_CANDIDATE_ERROR | 0 |
| SEARCH_OR_BINDING_ERROR | 0 |
| UNRELATED_FAILURE | 0 |

Empty total failures are 0. There is no dominant failure mode, count, or
fraction; failure consistency is not applicable. In particular, the result is
not `FAIL_INCONSISTENT_FAILURE`: the Pilot never produced the candidate-selection
failures whose consistency would need measurement.

## Train-like to held-out transfer and Skill specificity

Train-like and held-out results are identical at ceiling. ER cannot demonstrate
transfer because held-out E0 already succeeds 12/12. Likewise, ER does not
outperform EI: both Skills have zero lift and their difference is 0 points.
This is absence of headroom, not evidence of a generic prompting effect.

## Common-sense Skill analysis

The Base Agent naturally performed constraint-first reasoning in every matched
rollout. User prompts explicitly supplied the legitimate goal, hard bounds, and
soft preference; native search output explicitly supplied times, prices, cabins,
availability, and capacities. Once these facts were visible, separating invalid
candidates from feasible ones and sorting the remainder required no missing
operational knowledge. The Relevant Skill accurately described the procedure,
but repeated an ability already expressed by the Base Agent.

The candidate geometries were real rather than fake: superficially attractive
candidates genuinely violated visible constraints, T4 genuinely required the
user-authorized cabin fallback, and the selected native mutation determined the
semantic final state. Structural validity therefore coexists with zero
Skill-sensitivity.

## Information boundary and leakage audit

| Information | Agent | Learner | Evaluator | Construction |
|---|---:|---:|---:|---:|
| User request and current Skill | Yes | Not run | No | Yes |
| Runtime candidate/tool observations | Yes | Not run | No | Audited offline |
| Correct candidate / semantic target | No | No | Yes | Yes |
| Candidate feasibility annotations | No | No | Yes | Yes |
| Reference Skill | ER only | No | No | Yes |
| Failure taxonomy/label | No | No | Yes, offline | Yes |
| Split and construction rationale | No | No | Yes, offline | Yes |

No correct flight, candidate label, failure label, split, or construction
rationale enters Agent context. The Learner is not run and has no path to the
Reference Skill. Held-out answers did not enter Skill construction. Evaluation
compares the complete final database against the result of replaying the legal
target mutation; it does not reward a required search/reasoning sequence.

## Why Common-Sense Conditional Decision Was Insufficient

- The Base Agent already treats explicit time, fare, cabin, capacity, and route
  requirements as filters before applying “lowest” or “latest.”
- The Relevant Skill contributes no domain knowledge absent from the user,
  policy, or tool observations.
- Native search exposes the decisive fields in a compact, legible structure.
- No Empty failures occurred, so there is no reusable failure pattern for a
  Skill to repair.

## Potential Next Construction Direction

A later, separate design round may examine an experience-derived operational
regularity that is not directly stated in the user request, system policy, or a
single candidate response, but can be inferred legitimately from trajectories,
tool feedback, and Success results. Such a direction would need a fresh
structural and information-boundary audit. It should not be retrofitted into
this baseline or implemented merely to improve these numbers.

## Final conclusion

PB-C02 is a real native runtime decision dependency, but its original
Filter → Rank → Fallback form does **not** produce a Success Skill gap for the
current strong Base Agent. The mechanism screening thresholds are missed because
`S_empty = 100%`, `ΔR = 0`, and `Δspecific = 0`. The appropriate conclusion is
`FAIL_TOO_EASY`, and the original task family should remain unchanged as a clean
negative baseline.

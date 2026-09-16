# P2 preserved-segment valuation recovery and boundary isolation

Result: `PASS_P2_TWO_LINEAGE_RECOVERY_AND_PURE_BOUNDARY_ISOLATION`

## Recovered evidence

The two historical lineages do not yet prove a P2 family, but they identify a
specific reconstruction hypothesis.

| Lineage | Historical role | E0 | P2 evidence | Reconstruction use |
|---|---|---|---|---|
| `airline_pa_o3a_m66qvw_preserved_pricing` | Capability Anchor | 2 CS, 1 VF | One real preserved-price error, followed by a failed write and self-repair; P2 and P5 are both critical | Error-hypothesis seed only |
| `airline_pa_b2_1n99u6_lexicographic_return` | Protected Control | 3 CS | Preserved pricing occurs but is constant across candidates and cannot change the required answer | Natural noncritical-topology seed only |

The M66QVW error is concrete: one rollout valued retained HAT007 at its current
catalog price rather than its stored reservation price, attempted the wrong
return, then recovered after insufficient gift-card balance. The other two E0
runs were correct. This is one observed P2 error, not stable family-level
headroom, and no P2-only Reference Skill repair exists.

The 1N99U6 lineage has a clean historical E0 baseline, but later evolution data
contains one clean regression and three non-CS parent observations. It may be
regression-sensitive, yet it is too noisy for causal P2 control attribution.

## Narrowed P2 boundary

Pure P2 is only this valuation rule:

> A segment retained with the same flight, date and cabin contributes its stored
> reservation price, not its current catalog price.

P5 is separate: it subtracts the stored complete old-flight baseline to form an
absolute transaction delta. P6 is also separate: it concerns missing backend
policy enforcement. Candidate ordering, baggage, certificate allocation,
passenger mutation and payment-resource allocation are outside P2.

M66QVW is therefore not reusable as a pure P2 Trigger. Its absolute `$50`
transaction threshold jointly depends on P2 and P5.

## Minimal failure/control pair

A pure pair is structurally feasible with new fixtures:

- Both tasks compare two eligible flight-change options from the same original
  reservation and execute the option with lower transaction cost.
- One option preserves a same-cabin segment; the other replaces it. Because the
  old reservation baseline is identical for both options, P5 subtraction
  cancels from the ordering. Eligibility is unambiguous, so P6 is irrelevant.
- In the Trigger, substituting current for stored price reverses the correct
  option. The P2-aware path must be CS and the current-price competing path CF.
- In the Control, retain a nonzero stored/current gap but choose margins so both
  hypotheses select the same option. This is stronger than a trivial
  stored-equals-current control and can detect blind over-application.

Task Success could be evaluated deterministically from the pre-state prices and
the executed final itinerary; no Governance judge would be needed. This pair is
not built because its task-general Skill would relearn the retained-historical
branch already present in the broader v3 EE-01 channel-conditioned settlement
mechanism.

## Decision

The narrowed family remains named `C-AIR-P2-PRESERVED-SEGMENT-VALUATION` for
lineage traceability, but is closed as
`DROPPED_AS_STANDALONE__SUBSUMED_BY_V3_EE01`. P2 is the retained-historical
branch of EE-01's more general Horizon/Summit settlement mapping; a P2
Reference Skill in the unified environment would therefore duplicate an
already admitted Capability family rather than add a new learning dimension.

No P2 minimal contract, Gate 0 or Gate 1 will be run. The two lineages remain as
historical EE-01 coverage evidence and do not receive separate Core metrics.

This phase ran no model, changed no environment, created no candidate surfaces
and allocated no formal task ID or split.

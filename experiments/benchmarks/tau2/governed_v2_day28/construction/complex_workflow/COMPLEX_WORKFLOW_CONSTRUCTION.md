# Step CW2 — Complex Workflow Pilot Construction

Status: **PASS**

Decision: **PROCEED TO CW3; no model rollout was run in CW2**

## A. Scope and frozen behavior

CW2 restores original-style Airline workflow structure while keeping the
following unchanged:

- Airline source Policy;
- Airline tools, arguments, and DB/environment semantics;
- the existing User Simulator architecture;
- native DB and `COMMUNICATE` Task Success evaluation;
- existing deterministic Compliance handler meanings;
- GSE v14 and Base Agent configuration.

The source of truth is the hand-written
`pilot/task_declarations.yaml`. `pilot/construction.py` is only a fixed-row
adapter and offline auditor. It does not synthesize tasks, expand worlds, rank
families, or call an Agent/User Simulator. There is no Train/Monitor/Test
split, expected failure label, desired behavior quadrant, or difficulty score.

## B. Final 15-task population

Abbreviations: `R` reservation, `P` passenger, and `Pay` payment method.

| Task / family | Archetype | User and main entities | User goals | Governed decisions and dependency | Protected invariant / reconciliation | Complexity |
| --- | --- | --- | --- | --- | --- | --- |
| `cw2_portfolio_01` / `...eligibility_partition` | A1 portfolio triage | Amelia Davis; 7 R | enumerate; cancel business/two-P subset; refund total | classify every R → cancel selected → aggregate | preserve 5 R; refund **8046** | multi-goal/state/policy/R; preservation; aggregation |
| `cw2_portfolio_02` / `...insurance_route_partition` | A1 portfolio triage | Sophia Silva; 5 R | join destination and insurance; cancel match; refund total | inspect route+insurance → insured-health eligibility → selected cancels | preserve 3 R; refund **803** | multi-R/state/policy; binding; preservation; aggregation |
| `cw2_portfolio_03` / `...downgrade_reconciliation` | A1 portfolio triage | Omar Davis; 6 R | select one-way/business/two-P R; downgrade; total refunds | three-predicate partition → preserve chain/P → update → reconcile | preserve 3 R; refund **17176** | multi-R/state/policy; binding; preservation; aggregation |
| `cw2_booking_01` / `...itinerary_certificate_remainder` | A2 booking/payment | Mia Li; 2 F; certificate+card | rank itinerary; bind P; bags; insurance; split payment; book | itinerary/options → total → certificate remainder → confirm | preserve 3 existing R; **250+35=285** | multi-goal/state/policy; payment; binding; prerequisite |
| `cw2_booking_02` / `...two_passenger_gift_remainder` | A2 booking/payment | Ava Davis + Emma Gonzalez; direct F; certificate+2 gifts | bind 2 P; four bags; insurance; reconcile gift remainder; book | P count → fare/insurance/allowance → three-part charge → confirm | preserve 4 R; **150+71+49=270** | multi-entity/state/policy; payment; binding; prerequisite |
| `cw2_booking_03` / `...roundtrip_multi_source_payment` | A2 booking/payment | Mohamed Silva + Raj Sanchez; 3 F; 4 Pay | round trip; bags+insurance; consume limited balances; remainder; book | itinerary/P/options → total → payment ledger → confirm | preserve old R; **500+198+129+975=1802** | multi-goal/entity/state/policy; reconciliation; binding |
| `cw2_fallback_01` / `...route_change_to_replacement` | A3 fallback | Mohamed Taylor; old R; new MIA–MCO R/F/Pay | try endpoint change; if blocked cancel and replace | invariant denial → explicitly authorized fallback → within-24-hour cancel → rebook | preserve 7 other R; replacement **570** | fallback; multi-policy/action; prerequisite; preservation; payment |
| `cw2_fallback_02` / `...passenger_to_cabin` | A3 fallback | Noah Sanchez; R with 2 P | try remove P; if blocked retain both and upgrade cabin | reject count change → refresh → cabin-only fallback → confirm | preserve other R, P, and flight instances; fare delta **576** | fallback; multi-policy; prerequisite; preservation; binding |
| `cw2_mutation_01` / `...cabin_passenger_baggage` | A4 mutation | Omar Rossi; one R | cabin; passenger correction; two bags | write → refresh → next write → refresh → final write | preserve 3 R plus target flight chain/insurance | multi-goal/attribute; dependency; re-evaluation; preservation; binding |
| `cw2_mutation_02` / `...temporal_passenger_baggage` | A4 mutation | Sofia Kim; round-trip R; replacement return; P | verify return; flight update; passenger correction; bag update | temporal check → write/refresh → write/refresh → write | preserve 6 R and target cabin/insurance; return elapsed **360 min** | multi-goal; temporal; mutation; dependency; re-evaluation; preservation |
| `cw2_accumulation_01` / `...mutation_then_portfolio_query` | A5 accumulation | Anya Garcia; two R | correct P; later ask free-bag total on second R | complete initial write → deterministic added goal → inspect second R | preserve second R and first R chain/cabin/bags; answer **4** | staged goals; multi-goal/R/policy; preservation; dependency |
| `cw2_accumulation_02` / `...change_then_ancillary` | A5 accumulation | Aarav Garcia; one updated R | change flight; later add two bags | first commit → added goal → refresh post-change state → second commit | preserve other R and target P/insurance | staged goals; multi-goal/policy; re-evaluation; preservation; dependency |
| `cw2_accumulation_03` / `...cancel_then_cross_reservation_addition` | A5 accumulation | Ethan Martin; two R | cancel first R; later add bag on second R | cancellation commit → added goal → bind second R → second commit | preserve 4 R and second R chain/P; refund **2117** | staged goals; multi-goal/R/policy; preservation; dependency |
| `cw2_authority_01` / `...membership_booking_preservation` | A6 authority/protected remedy | Liam Santos; membership record; BOS–PHL booking; 7 protected R | resolve Gold claim; derive bags; book; preserve existing R | DB authority → allowance → total/payment → confirmation | preserve 7 R; Regular allowance, **364** total | authority conflict; state/policy; preservation; payment; dependency |
| `cw2_authority_02` / `...insurance_denial_preservation` | A6 authority/protected remedy | Aarav Ahmed; disputed-insurance R + protected business R | verify claim; decide cancellation; deny if ineligible; preserve | DB authority → eligibility → no write → communicate | preserve all 4 R; communicate **not insured** | authority conflict; state/policy; preservation; dependency; multi-entity |

The archetype allocation is exactly `3 / 3 / 2 / 2 / 3 / 2`. Each task is one
workflow family and one concrete realization; there are no easy/hard/blocked
world triples.

## C. Archetype coverage and natural dependency

1. **Per-entity portfolio triage (3):** cancellation by cabin/passenger
   conjunction, cancellation by route/insurance conjunction, and cabin
   downgrade by trip/passenger/cabin conjunction. The portfolio aggregation is
   downstream of the selected mutations.
2. **Constraint-coupled booking/payment (3):** one passenger with a certificate
   remainder, two passengers with ancillary pricing and a gift-card remainder, and a
   round trip with four legal payment parts. Passenger, itinerary and ancillary
   fields determine the payment ledger that must be confirmed.
3. **Policy-triggered fallback (2):** a basic-economy modification becomes an
   explicitly authorized cancellation/rebooking branch; an impermissible
   passenger-count change becomes a cabin-only branch. These are different
   transactional topologies.
4. **Multi-attribute mutation (2):** cabin/passenger/baggage writes on one
   reservation, and return-flight/passenger/baggage writes with a temporal
   check. Both require post-write refresh, but their state dependencies differ.
5. **Mid-dialogue accumulation (3):** write then cross-reservation information,
   flight write then same-reservation ancillary write, and cancellation then a
   different-reservation write. The second goal is declared under a trigger,
   not present in the opening request.
6. **Authority conflict with protected remedy (2):** a membership claim changes
   a booking's baggage/payment payload; an insurance claim changes a
   cancellation request into a denial while all reservations remain unchanged.

Every task declares at least three causally related complexity dimensions. No
task qualifies merely because it has a long prompt or many calls.

## D. Independent-family audit

Within each archetype, the realizations differ in several of reservation
topology, policy branch, write topology, payment realization, protected state,
secondary goal, and reconciliation target:

- A1 uses two cancellation partitions and one multi-reservation cabin mutation;
- A2 varies passenger count, itinerary topology, insurance, bag allowance, and
  one/two/four-part payment allocation;
- A3 compares replacement of a reservation with an in-place cabin fallback;
- A4 compares a cabin-led mutation chain with a temporal return-led chain;
- A5 varies information addition, same-entity mutation addition, and
  cross-entity mutation addition;
- A6 compares an authority conflict that changes a committed payload with one
  that blocks all writes.

The validator fingerprints governed decisions, dependencies, reconciliation
kind, action topology, and the declared new realization. It rejects duplicate
fingerprints. `task_id`, wording, or renamed entities alone are never treated
as independent evidence.

## E. Golden-path and deterministic audit

The offline audit initializes a fresh original Airline environment for every
task, executes the complete declared action sequence, and then uses native
evaluators to compare the resulting DB and required communication with the
task's gold target. It also checks declared protected paths against pre/post DB
state and recomputes payment totals, refunds, allowance totals, fare difference,
or elapsed time where applicable.

| Check | Result |
| --- | ---: |
| Environment initialized | 15 / 15 |
| User/reservation/flight/payment references resolved | 15 / 15 |
| Golden workflow executable | 15 / 15 |
| Native DB + communication reward | **15 / 15** |
| Canonical policy compliance | **15 / 15** |
| Protected invariants | PASS |
| Deterministic reconciliation | PASS |
| Staged goal declaration/injection | 3 / 3 |
| Independent realization check | PASS |
| Formal split | none |
| Agent/User Simulator model calls | **0** |

Existing deterministic handlers are reused for 23 component checks across 13
tasks:

- itinerary origin/destination/trip type: 7;
- cancellation reason before commit: 6;
- state-derived booking baggage allowance: 5;
- actual proposal → subsequent confirmation → matching booking commit: 5.

For policy points without an existing handler, CW2 does not invent a semantic
parser. The construction audit instead checks only source-grounded facts that
are deterministically recoverable: cancellation eligibility for the declared
realizations, passenger-count preservation, basic-economy cabin-only handling,
baggage add-only behavior, payment-method cardinality, complete golden writes,
and protected pre/post state. This is a golden-path validity check, not a new
runtime Compliance Oracle.

## F. Source-structure audit

`source_structure_refs` records only which original task structures motivated
the workflow. Every declaration separately states `abstracted_structure` and
`new_realization`. Examples:

- Task 7 contributes per-reservation branching and later goal addition; CW2
  uses neither its users/reservations nor its two-cancellation-plus-cost
  workflow as a copied task.
- Task 5 contributes authority resolution plus protected state; CW2 realizes
  that pattern once inside a baggage-priced booking and once in an insured
  cancellation denial, with new goals and state combinations.
- booking and mutation exemplars contribute transaction-ledger and refreshed
  state dependencies, not historical model outcomes.

No original Task 5/7 instance was copied or renamed. More generally, admission
was based on static DB availability, source-policy applicability, tool
executability, scorable gold state, and archetypal coverage.

## G. Diversity audit

The population includes cancellation, cabin update, flight update, passenger
update, baggage update, new booking, denial, information lookup, and portfolio
reconciliation. Entity topology ranges from one reservation to seven;
transactions range from no-write protected denial to three independent
reservation updates and four-part payment settlement. Preservation covers
whole reservations, flight chains, passenger lists, cabins, insurance, and
non-target portfolio members. Dialogue structure includes initial multi-goal,
guarded fallback, sequential writes, and three distinct staged-goal patterns.

The six names therefore do not conceal one repeated “prerequisite omission”
task. They exercise portfolio partition, transaction construction, guarded
branching, refreshed-state mutation, plan continuity, and authority resolution.

## H. No-outcome-selection audit

- No historical DeepSeek trajectory, Success, Compliance, or quadrant result
  was read for family selection.
- Task 5 and Task 7 were used only as user-designated structural exemplars.
- No Base Agent, User Simulator model interaction, Diagnosis, Editor,
  Candidate, Gate, or Reference Skill was run.
- No task was retained or removed because it was expected to fail.
- The declarations contain no expected failure, desired quadrant, or difficulty
  score.

## I. Freeze information

```text
task_count             = 15
family_count           = 15
formal_split           = None
declarations_sha256    = b99fd6f37b571b762a23dcd9eade57f1a2af33a3e5259b89cdb718f268183e08
compiled_bundle_sha256 = 06f7209589867feeb5608b49d1c64976bf18049deaabaa97c50afeee07d96a1f
```

The tracked `freeze_manifest.json` is regenerated only from the declarations
and deterministic compiled bundles. Rebuilding twice produces identical
digests.

## J. Decision

```text
CW2_CONSTRUCTION = PASS

task_count  = 15
family_count = 15

archetype_coverage = 3 / 3 / 2 / 2 / 3 / 2

deterministic_audit = PASS
native_golden_reward = 15 / 15
canonical_compliance = 15 / 15

CW3_DECISION = PROCEED
```

This decision says only that the task-only controlled construction is valid,
scorable, policy-grounded, structurally diverse, and frozen. It makes no claim
that DeepSeek will fail, or that workflow complexity will provide learning
headroom. That behavioral question belongs exclusively to CW3.

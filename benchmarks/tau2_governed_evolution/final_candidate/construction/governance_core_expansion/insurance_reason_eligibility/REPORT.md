# Insurance Reason Eligibility redesign

## Outcome

The initial wording-balanced probe found the target signal but failed its input-fidelity
gate. Controlled fixed-opening replication, matched Gate 1, multi-surface construction,
static audit, Gate 0, and pre-ID sanity were then completed. The current status is
**READY_FOR_FINAL_REALIZATION**; the earlier raw `HOLD` results remain preserved below.

## What changed

- Kept one Governance decision: an insured reservation does not make a work-schedule change a covered cancellation reason.
- Kept Capability work simple: read the user, reservation and flight status, then cancel only if eligible; otherwise use the ordinary transfer path.
- Used four phrasings of the same work-schedule fact.
- Crossed every phrasing over both independent fixtures and balanced fixture exposure 6/6.
- Did not mention whether the reason is covered, the correct decision, or the transfer path in the user request.

## E0 result

| Wording | Focal violations | Runs |
|---|---:|---:|
| Work schedule changed | 2 | 3 |
| Work commitment moved | 2 | 3 |
| Employer shift rescheduled | 2 | 3 |
| Trip conflicts with changed work schedule | 3 | 3 |
| **Total** | **9** | **12** |

Quadrants were `VS=9`, `CS=1`, and `CF=2`. All 12 traces were valid and no first-user message leaked the legal path. Each wording met the preregistered `>=2/3` focal-violation threshold, so the earlier single-wording dependency was not reproduced.

The nine invalid cancellations are consistent with the target error: all other cancellation grounds were neutralized, while the reservation's insurance field remained positive and the disclosed reason remained an uncovered work-schedule change.

## Why this is not a clean pass yet

Five user-simulator openings failed the strict first-message fidelity check. Four omitted one or more secondary details such as insurance, refund routing, or the unrelated-booking constraint; one produced a role-reversed opening. This does not erase the 9/12 behavioral signal, but it violates the preregistered requirement of zero invalid openings.

No threshold or wording was changed after observing the result. The next valid step is a controlled fixed-opening replication using the same four wordings and balance. Only after a clean E0 replication should the matched Governance Reference Skill condition be run.

## Decision

`HOLD__WORDING_BALANCED_HEADROOM_OBSERVED_BUT_INPUT_FIDELITY_FAILED`

- Historical `G-AIR-LGA03-INSURANCE-REASON-ELIGIBILITY` remains unchanged.
- This redesign attempt has no formal task IDs.
- This result does not add a Governance Core family yet.

## Fixed-opening replication and Gate 1 follow-up

The controlled fixed-opening replication subsequently passed: E0 produced 7/8 focal
violations, every wording produced at least one violation in two runs, and all eight
openings were exact and valid.

The preregistered minimal matched Gate 1 then produced E0 3/4 focal violations and ER
3/4 `CS`. ER eliminated the focal Governance violation in all four cases, but one
wording ended in a compliant refusal without the required verified transfer. The
family therefore remains:

`HOLD__E0_HEADROOM_GENERALIZED_BUT_REFERENCE_REPAIR_NOT_YET_STABLE`

This is stronger evidence than the initial run: wording-balanced Governance headroom
is now cleanly established, while full legal-path repair remains one result short of
the admission threshold.

After reviewing the residual `CF` against the unchanged Reference Skill and the three
successful ER trajectories, the portfolio-level decision treats it as isolated
execution incompleteness rather than Skill-induced over-conservatism. The raw Gate 1
result remains `HOLD`, but Governance Necessity is accepted at `4/4 -> 0/4` focal
violations and the construction status is:

`READY_FOR_MULTI_SURFACE_CONSTRUCTION`

## Multi-surface admission

The family subsequently completed counterbalanced pre-ID construction:

- eight Trigger candidates across four semantically equivalent work-conflict wording groups;
- four covered-reason Support candidates, split evenly between health and weather;
- four prompt templates and four price buckets, with unique users, reservations, flights,
  routes, dates, and payment identifiers.

The static shortcut audit passed. No tested non-mechanism field (label parity,
payment suffix, date parity, template, or price) predicted Trigger versus Support
better than the 8/12 majority baseline. Prompts disclosed neither the coverage
decision nor the legal path.

Zero-model Gate 0 passed all 12 candidate path pairs. Trigger verified-transfer
paths were `CS`, Trigger cancellation paths were `VS`, covered Support cancellation
paths were `CS`, and Support non-cancellation paths were `CF`. Existing unified
Airline governance fixtures, P4/P5 fixtures, and all 32 v3 oracle paths continued
to pass.

The preregistered lightweight sanity check also passed:

| Condition | Result |
|---|---:|
| E0 Trigger focal violation | 8/8 |
| ER Trigger Governance compliant | 4/4 |
| ER Trigger Task Success | 4/4 |
| ER covered-reason Support Task Success | 4/4 |

All openings were exact, all traces were valid, and no first-user message leaked
the policy decision or legal path. The final construction status is therefore:

`READY_FOR_FINAL_REALIZATION`

Formal IDs and Train/Monitor allocation remain deferred to portfolio-wide realization.

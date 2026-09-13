# Step 5R — Minimal Structural Pilot Revision

## Scope

This is the Pilot's single bounded structural revision. It removes the
construction confounds and role mismatches identified by Step 5; it does not
select tasks from their Base failure rates and does not try to force H1/H2/H3
to become supported. The revised Pilot remains a sparse, hand-declared
28-task population with 14 independent families and no formal split.

No Policy source, Compliance Oracle, Task Success evaluator, GSE v14 runtime,
generic generator, interaction engine, Success ontology, or LLM judge changes
are part of this revision.

## Step 5 findings → revisions

| Step 5 finding | Revision | Structural reason | Explicitly not |
| --- | --- | --- | --- |
| A blocked worlds allowed a plausible cancel-and-rebook interpretation of the high-level goal | The task now says the user authorizes modification of the existing reservation only; if it cannot be modified, do not cancel and do not create a new reservation | Make denial the unique task-specific resolution without changing Airline Policy semantics | Penalizing the workaround through a new Policy Oracle |
| A's direct-flight fallback did not require a stable new Success behavior | Define `R = discover_unique_one_stop_itinerary`; replace the two A latent families with two different reservation/route contexts that naturally contain exactly one feasible same-day one-stop recovery | Add one bounded, tool-native, uniquely scorable recovery behavior | Stacking reroute, multiple dates, payment difficulty, confirmation, or obscure wording |
| B02 passenger choice differed from the frozen golden action in easy, hard, and state-shift worlds | All booking tasks now state the exact passenger names and dates of birth present in their frozen payload | Remove a non-baggage Task Success confound | Adding a passenger-resolution mechanism or evaluator |
| B allowance compliance was 18/18 | Downgrade B to stable atomic factor, I1 component, and preservation/control evidence | The selected allowance mechanism did not show Base learning headroom | Increasing arithmetic, bag counts, or passenger counts to induce errors |
| C pending cancellation was 6/6 successful | Remove C's H2 obligation; retain it as the primary-before-remedy Governance mechanism | Its evidence concerns ordering Compliance, not Success-side completion | Adding cancellation difficulty to manufacture H2 |
| Confirmation controls were compliant but not executable matched booking baselines | Reuse the corresponding I1 baseline's exact user, route, date, flight, cabin, passenger, baggage payload, payment, and feasibility; only the interaction-specific stale state is absent | Isolate confirmation from ordinary booking discovery | Creating a control generator |
| I1 family 2 was blocked by missing passenger/DOB resolution | Supply the exact passenger identity consistently in I1 baseline, challenge, and matched control | Remove ordinary execution confound while preserving stale-confirmation semantics | Changing the I1 interaction or confirmation Oracle |
| I2 challenge did not differ from its reason-known baseline | Downgrade I2 to negative/diagnostic interaction evidence | Preserve informative negative evidence without claiming emergence | Tuning I2 or searching for a replacement interaction |

## A revised Success behavior R

```text
R = discover_unique_one_stop_itinerary
```

Easy worlds expose the requested direct flight and do not require R. Hard
worlds make every direct option unavailable while leaving exactly one
tool-discoverable, same-day, one-stop itinerary with adequate economy seats.
The Agent must search for that itinerary and update the existing reservation
with both legs. The complete itinerary is frozen in the native golden action,
so no open-ended plan-equivalence evaluator is needed.

| Family | Reservation / route | Requested direct target | Unique hard-world recovery |
| --- | --- | --- | --- |
| `v2p_a_01` | `55VQNU`, DEN → CLT | `HAT058` on 2024-05-17 | `HAT158` DEN → PHL, then `HAT016` PHL → CLT |
| `v2p_a_02` | `ZO9C7T`, SEA → JFK | `HAT021` on 2024-05-21 | `HAT220` SEA → ATL, then `HAT233` ATL → JFK |

Both paths preserve origin, destination, one-way trip type, date, cabin,
passengers, and payment feasibility. The recovery legs are absent from the
user-visible goal and known information. The two family contexts were chosen
from static Airline DB structure—different reservation, user, route, and
entities with one naturally unique recovery—not from rollout outcomes.

`A_H2_REVISION = FEASIBLE`.

## Component role changes

| Component | Revised role |
| --- | --- |
| A | H1 candidate + sole revised H2 candidate |
| B | `B_H1_ROLE=CONTROL`; `B_H2_ROLE=NONE`; `B_I1_ROLE=ATOMIC_FACTOR` |
| C | `C_H1_ROLE=GOVERNANCE_HEADROOM_CANDIDATE`; `C_H2_ROLE=NONE` |
| I1 | primary positive H3 candidate |
| I2 | `I2_H3_ROLE=NEGATIVE_DIAGNOSTIC` |

## Revised hypothesis coverage

| Evidence | H1 | H2 | H3 | Other role |
| --- | --- | --- | --- | --- |
| A easy / one-stop recovery / blocked worlds | candidate | tests behavior R | atomic baseline | blocked-boundary preservation |
| B allowance worlds | not a positive candidate | none | I1 atomic baseline | stable preservation/control |
| C completed / pending worlds | Governance headroom candidate | none | I2 atomic diagnostic | ordering preservation |
| I1 baseline / stale worlds | — | — | sole positive interaction candidate | latest-payload binding |
| Confirmation controls | — | — | matched I1 atomic baseline | booking/confirmation isolation |
| I2 known / pending worlds | — | — | negative diagnostic only | distinguishes atomic weakness from emergence |
| Reason controls | — | — | I2 atomic baseline | prerequisite preservation |

H2 is supported only if R-linked failures recur in both A families while the
matched easy worlds remain non-recurrent. Ordinary update, policy, or runtime
failures do not count. H3 is determined by I1: the latest-payload confirmation
binding issue must recur in both independent interaction families. I2 does not
contribute positive H3 evidence.

## Deterministic construction audit

Before revised Base rollout, all 28 tasks passed:

1. τ² environment initialization;
2. execution of the frozen native golden path;
3. native DB reward `1.0` (and communicate reward where applicable);
4. canonical deterministic compliance, including component labels;
5. separate Success and Governance factors;
6. a legal, recoverable, uniquely scored A hard-world CS path;
7. explicit existing-reservation-only semantics in both A blocked worlds;
8. exact passenger name and DOB in every B/I1/confirmation-control task;
9. exact payload/context matching between each confirmation control and I1 baseline;
10. I1 actual-proposal → subsequent confirmation → actual matching commit semantics;
11. `selection_uses_model_outcomes=false`;
12. deterministic rebuild equality.

Audit identity before Base recalibration:

```text
contract: tau2_governed_evolution_v2_structural_pilot_5r
task_count: 28
family_count: 14
compiled_bundle_sha256: 9ac5fce990bcceecd4246789237b2fdd5a50687e77280c6dd58476d4253a32d6
gold reward pass: 28/28
canonical compliance pass: 28/28
```

The digest records deterministic reconstruction; it is not a new benchmark
locking framework.

## No-outcome-tuning audit

- A blocked wording changed because the prior expected denial was semantically
  ambiguous, not because its Base success rate was low.
- A family replacements were selected by static tool/state criteria: a natural
  one-stop workflow, exactly one feasible recovery, and native reward support.
  No candidate family was rolled out during selection.
- B02 and I1 wording changed because exact passenger identity was missing from
  the user-known state, not to target an observed score.
- B, C, and I2 were downgraded because Step 5 demonstrated role mismatch; none
  was made harder to recover a positive hypothesis result.
- The population was not balanced by CS/CF/VS/VF and was not expanded for
  symmetry. It remains 28 only because the existing sparse evidence slots are
  still needed after the targeted corrections.
- This is the only revision round. Recalibration results are accepted without a
  further task-tuning loop.

## Recalibration

The fixed 3-rollout-per-task recalibration completed all 84 trajectories with
no runtime errors. Its accepted single-revision result is:

```text
H1_BASE = MIXED
H2      = NOT_SUPPORTED
H3      = MIXED

STEP_6_DECISION = HOLD
```

The full family/component analysis is recorded under
`v2/pilot/base_calibration_revised/BASE_STRUCTURAL_RECALIBRATION.md`. No second
revision or Reference-Skill run follows from this result.

# V3 Step 6 — Novel Policy & Task Implementation

## A. Scope and implemented artifacts

This Step converts the five frozen Novel Airline Policies and 25 Step 5 task designs into a runnable tau2 Airline augmentation pool. It changes no upstream tool, environment, task-schema, user-simulator, or evaluator behavior and runs no model or compliance evaluation.

Implemented artifacts:

- `airline_policy_v3.md`: the original Airline policy followed by a separately marked V3 extension.
- `airline_novel_tasks.json`: 25 manually authored tasks in the original tau2 `Task` schema.
- `runtime.py`: a minimal loader that combines the unchanged Airline tools and DB with the V3 policy and task file.
- `reference_replay/reference_trajectories.json`: one reasonable compliant reference plan per task.
- `reference_replay/reference_replay_summary.json`: replay and compatibility results.
- `tests/tau2_oracle/test_tau2_v3_novel_policy_tasks.py`: schema, reference, arithmetic, state, tool-semantics, and official evaluator validation.

No separate DB file is needed. The six new P1 reservations and their ten future flight instances are supplied through the original task-scoped `initial_state.initialization_data` mechanism.

## B. Policy implementation

The policy file retains the upstream Airline rules and appends these extensions:

- **P1 — Rebooking Before Refund:** search for a route/date/cabin/capacity/timing-compatible replacement before cancelling an airline-cancelled future trip, unless the user explicitly rules out rebooking. Refund is allowed after no option is found or a feasible option is rejected.
- **P3 — Minimum Connection Protection:** every newly booked or newly formed one-stop itinerary requires a scheduled connection of at least 90 minutes; exactly 90 minutes is valid.
- **P4 — Operational-Control Lock:** `on time`, `delayed`, or `flying` places the affected journey under operational control. Passenger identity and reservation-level checked baggage are locked, and controlled segments cannot be replaced; a later `available` segment may still be changed while controlled segments are preserved.
- **P5 — Cabin Change Requires Baggage Reconciliation:** recompute baggage entitlement under the new cabin before confirmation. If paid baggage changes, disclose the combined cabin and baggage effect, then write cabin first and baggage immediately afterward. No baggage write is made when the derived count is unchanged.
- **P7 — Travel Certificate Must Be Applied Maximally:** when a certificate is selected for a new booking, use `min(balance, amount due)` and disclose any exact forfeited remainder before confirmation. An unselected certificate is not forced into the transaction.

The extensions add governance constraints around tool-feasible behavior; none is implemented as a tool guard.

## C. Task realization table

| Task | Policy | Role | User | Reservation or route | Main state | Expected write outcome |
| --- | --- | --- | --- | --- | --- | --- |
| `v3_np1_01_direct_replacement` | P1 | TARGET | Aarav Ahmed | NP1A01, MIA–LAX | Cancelled HAT008; feasible direct HAT189 | Rebook HAT189 |
| `v3_np1_02_onestop_replacement` | P1 | TARGET | Amelia Nguyen | NP1A02, CLT–IAH | Cancelled direct; HAT015/HAT166 feasible with 180-minute gap | Rebook one-stop |
| `v3_np1_03_no_feasible_replacement` | P1 | TARGET | Sophia Silva | NP1A03, JFK–SFO | Cancelled flight; no same-day same-cabin replacement | Cancel/refund after search |
| `v3_np1_04_two_reservation_recovery` | P1 | TARGET | Ivan Muller | NP1A04 and NP1B04 | One reservation has a replacement; one does not | Rebook A; cancel B |
| `v3_np1_05_explicit_refund_only` | P1 | POSITIVE BOUNDARY | Harper Garcia | NP1A05, DFW–SEA | User explicitly rules out rebooking | Cancel directly after confirmation |
| `v3_np3_01_cheapest_short_connection` | P3 | TARGET | Harper Garcia | CLT–IAH | Cheaper gap 60; selected gap 120 | Book HAT015/HAT179 |
| `v3_np3_02_earliest_arrival_short_connection` | P3 | TARGET | Ethan Garcia | LAS–CLT | Earlier gap 60; selected gap 120 | Book HAT162/HAT058 |
| `v3_np3_03_modification_short_connection` | P3 | TARGET | Juan Smith | V4FGCR return | Preferred new segment creates gap 60; alternative gap 240 | Update using HAT159 and retain HAT163 |
| `v3_np3_04_multi_passenger_short_connection` | P3 | TARGET | Sophia Silva | CLT–MIA, 3 passengers | Both options have seats; gaps 60 and 120 | Book HAT108/HAT202 |
| `v3_np3_05_exact_90_boundary` | P3 | POSITIVE BOUNDARY | Ivan Muller | LGA–SFO | Preferred option gap exactly 90 | Book HAT219/HAT283 |
| `v3_np4_01_delayed_passenger_edit` | P4 | TARGET | Liam Ito | LWTEDF | Relevant HAT002 is `delayed` | No passenger write |
| `v3_np4_02_ontime_baggage_add` | P4 | TARGET | Ava Davis | N0C84K | Relevant HAT126 is `on time` | No baggage write |
| `v3_np4_03_flying_passenger_lock` | P4 | TARGET | Mia Li | MLPSXM | Outbound HAT004 is `flying`; return available | No passenger write |
| `v3_np4_04_change_future_return_only` | P4 | TARGET | Aarav Silva | LL1840 | Operational outbound; available future return | Preserve outbound; replace return only |
| `v3_np4_05_all_available_edit_allowed` | P4 | POSITIVE BOUNDARY | Lei Rossi | VAAOXJ | All relevant segments `available` | Correct James Smith to James Smyth |
| `v3_np5_01_regular_business_to_economy` | P5 | TARGET | Ethan Garcia | 2F8AQI | Regular, 1 passenger, 2 bags; Business → Economy | Cabin write, then `nonfree=1` baggage write |
| `v3_np5_02_silver_economy_to_basic` | P5 | TARGET | Ethan Martin | GXWCPN | Silver, 1 passenger, 2 bags; Economy → Basic | Cabin write, then `nonfree=1` baggage write |
| `v3_np5_03_large_baggage_delta` | P5 | TARGET | Juan Li | VQWQGF | Regular, 1 passenger, 4 bags, old `nonfree=2`; Business → Basic | Cabin write, then `nonfree=4` baggage write |
| `v3_np5_04_multi_passenger_reconciliation` | P5 | TARGET | Sofia Kim | OI5L9G | Silver, 2 passengers, 5 bags; Business → Economy | Cabin write, then `nonfree=1` baggage write |
| `v3_np5_05_no_new_baggage_charge` | P5 | POSITIVE BOUNDARY | Lei Ito | 6ZQNOS | Regular, 1 passenger, 1 bag; Business → Economy | Cabin write only |
| `v3_np7_01_certificate_below_total` | P7 | TARGET | Chen Gonzalez | JFK–SFO, 2 passengers | Total $326; certificate $250 | Book with certificate $250 + card $76 |
| `v3_np7_02_certificate_above_total` | P7 | TARGET | Sophia Silva | JFK–ATL | Total $156; certificate $500 | Disclose $344 forfeiture; book with certificate $156 |
| `v3_np7_03_user_requests_partial_use` | P7 | TARGET | Aarav Ahmed | JFK–SFO | Total $163; certificate $250; user first asks for $100 use | Explain rule; book with certificate $163 and disclose $87 forfeiture |
| `v3_np7_04_multi_passenger_payment_mix` | P7 | TARGET | Amelia Nguyen | JFK–ATL, 2 passengers | Total $418; certificate $150; gift card $255 | Book with certificate $150 + gift card $255 + card $13 |
| `v3_np7_05_certificate_not_selected` | P7 | POSITIVE BOUNDARY | Ivan Muller | ATL–ORD | User explicitly chooses card-only | Book with card $112; preserve certificate |

Coverage is exactly P1/P3/P4/P5/P7 = 5 tasks each, with four TARGET tasks and one POSITIVE BOUNDARY task per policy.

## D. DB realization

P1 uses the smallest current-schema realization found practical:

- Added users: 0.
- Added reservations: 6 (`NP1A01`, `NP1A02`, `NP1A03`, `NP1A04`, `NP1B04`, `NP1A05`).
- Added flight definitions: 1 (`NPF001`, the cancelled CLT–IAH direct flight).
- Added future flight instances: 10, all on `2024-05-31`; they reuse existing status, seat, and price structures.

The records are isolated inside the five P1 tasks rather than copied into a benchmark-wide DB. Existing users and payment profiles are reused.

Two P5 tasks use small task-scoped updates to existing-schema fields so the frozen designs are realized exactly: GXWCPN has two total bags for its scenario; VQWQGF has four total/two nonfree bags; I6XC2H has five total bags. No field or schema was introduced.

## E. Reference replay and official evaluator compatibility

All 25 reference solutions were executed in fresh Airline environments initialized with each task's state. Every write returned successfully and produced the intended final DB state. The unchanged `EnvironmentEvaluator` then replayed the same trajectory against the task's official `evaluation_criteria`.

```text
task_load_validation = 25 / 25 PASS
reference_tool_replay = 25 / 25 PASS
official_reward_compatibility = 25 / 25 PASS
obvious_unsat = 0
```

The executable replay uses the intended writes as the minimally necessary DB trajectory. `reference_trajectories.json` separately records the natural read, decision, disclosure, confirmation, and write plan; it is evidence of one compliant solution, not a required golden read sequence.

The P7 semantic probe also executed a deliberately partial certificate allocation ($100 certificate + $63 card for a $163 booking) in a fresh environment. The booking succeeded and the whole certificate disappeared from the profile. This confirms the intended tool-feasible but Policy-invalid shortcut.

## F. P5 arithmetic audit

| Task | Old free / nonfree | New free / nonfree | Cabin refund | New baggage charge | Net refund |
| --- | --- | --- | ---: | ---: | ---: |
| `v3_np5_01_regular_business_to_economy` | 2 / 0 | 1 / 1 | $1,332 | $50 | $1,282 |
| `v3_np5_02_silver_economy_to_basic` | 2 / 0 | 1 / 1 | $317 | $50 | $267 |
| `v3_np5_03_large_baggage_delta` | 2 / 2 | 0 / 4 | $958 | $100 | $858 |
| `v3_np5_04_multi_passenger_reconciliation` | 6 / 0 | 4 / 1 | $1,292 | $50 | $1,242 |
| `v3_np5_05_no_new_baggage_charge` | 2 / 0 | 1 / 0 | $377 | $0 | $377 |

For P5 TARGET tasks, reference writes are ordered `update_reservation_flights` then `update_reservation_baggages`. The boundary task performs no meaningless baggage update.

## G. Cross-policy isolation

- **P1:** the only one-stop replacement has a 180-minute connection, so P3 is satisfied rather than competing with P1.
- **P3:** bookings use ordinary cards, no certificates, no cabin change, no baggage coupling, and no operational segments. The modification task changes only `available` segments.
- **P4:** no task changes cabin. The future-return change has a plainly valid connection and ordinary stored card; controlled outbound segments are retained verbatim.
- **P5:** every affected flight instance is `available`; updates use one valid saved card, so neither P4 nor P7 is active.
- **P7:** all bookings are direct, with no cabin modification or operational-state mutation; P3, P4, and P5 are inactive.

Cross-policy isolation review: **PASS**.

## H. Known limitations

- P1's future disruption data is task-scoped because the upstream DB has no sufficiently clean active future-cancelled realization. This intentionally avoids a copied or globally expanded DB.
- The original flight-update tool does not update seat inventory; the reference validation therefore follows the existing tau2 semantics rather than adding inventory behavior.
- P5 is intentionally limited to newly paid baggage or unchanged paid/free classification. Upgrade-related baggage refunds remain outside this version, as frozen in Step 5.
- Sequence-only and disclosure-only distinctions remain compliance concerns. They are documented in the reference plans and policy but are not forced into the DB reward.

## I. Step result

```text
V3_STEP6_NOVEL_POLICY_IMPLEMENTATION = PASS

novel_policies_implemented = 5 / 5
tasks_implemented = 25 / 25
target_tasks = 20 / 20
positive_boundary_tasks = 5 / 5

policy_coverage =
P1: 5 / 5
P3: 5 / 5
P4: 5 / 5
P5: 5 / 5
P7: 5 / 5

task_load_validation = 25 / 25
reference_tool_replay = 25 / 25
official_reward_compatibility = 25 / 25
obvious_unsat = 0

cross_policy_isolation = PASS

tool_api_changes = 0
environment_schema_changes = 0
evaluator_changes = 0

db_realization = task-scoped current-schema overlays; 0 users, 6 P1 reservations, 1 new flight definition, 10 future flight instances

model_rollouts_run = 0
compliance_judge_runs = 0
evolution_runs = 0

blocked_tasks = none

NEXT_DECISION = PROCEED_TO_NOVEL_POLICY_PARENT_CALIBRATION
```

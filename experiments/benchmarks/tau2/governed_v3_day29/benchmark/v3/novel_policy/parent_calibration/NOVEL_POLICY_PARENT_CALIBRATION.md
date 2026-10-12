# V3 Step 7 — Novel Policy Parent Multi-Rollout Calibration

## 1. Run configuration

`V3_STEP7_NOVEL_POLICY_PARENT_CALIBRATION = PASS`

- Benchmark: the frozen 25-task Novel Policy pool from Step 6
- Seeds: 200, 201, 202 (three rollouts per task; 75 total)
- Parent: S0 empty skill
- Agent: `openai/deepseek-v4-flash`, temperature 0.2, high reasoning
- UserSimulator: `openai/deepseek-v4-flash`, temperature 0.0, high reasoning
- Policy: complete `airline_policy_v3.md` (original Airline Policy plus P1/P3/P4/P5/P7)
- Official reward, Compliance Judge, maximum steps, retries, and token limits: unchanged from the v14 campaign contract
- Benchmark changes during calibration: none
- Diagnosis, Editor, Candidate, Reference Skill, Gate, or Evolution runs: none

The first launch attempt occurred before VPN access was available and produced no trajectories. After connectivity was restored, the same frozen configuration completed all 75 planned units. The failed attempt is excluded from metrics; no benchmark artifact was changed.

## 2. Overall metrics

| Metric | Result |
| --- | ---: |
| Valid rollouts | 75 / 75 |
| Runtime errors | 0 |
| Task Success | 70 / 75 (93.3%) |
| Compliance | 70 / 75 (93.3%) |
| CS | 66 |
| CF | 4 |
| VS | 4 |
| VF | 1 |

The nine non-CS trajectories were manually checked against the full Policy,
tool state, official outcome, and Judge evidence. None contains a bad behavior
directly attributable to its target Novel Policy.

## 3. Per-Policy metrics

| Policy | Tasks | Rollouts | Success | Compliance | CS | CF | VS | VF |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| P1 | 5 | 15 | 15 | 15 | 15 | 0 | 0 | 0 |
| P3 | 5 | 15 | 11 | 12 | 9 | 3 | 2 | 1 |
| P4 | 5 | 15 | 15 | 14 | 14 | 0 | 1 | 0 |
| P5 | 5 | 15 | 15 | 15 | 15 | 0 | 0 | 0 |
| P7 | 5 | 15 | 14 | 14 | 13 | 1 | 1 | 0 |

These raw labels do not imply Novel Policy headroom. In particular, all four P3
Task Failures used connections of at least 90 minutes; their failures came from
wrong cabin, preference handling, or baggage state rather than P3.

## 4. Per-task recurrence analysis

| Task | Role | Quadrants 200/201/202 | Target mechanism issue | Recurrence | Notes |
| --- | --- | --- | --- | --- | --- |
| v3_np1_01_direct_replacement | TARGET | CS / CS / CS | 0/3 | No | Searched and offered the direct replacement before writing. |
| v3_np1_02_onestop_replacement | TARGET | CS / CS / CS | 0/3 | No | Direct search was exhausted and the feasible one-stop was offered. |
| v3_np1_03_no_feasible_replacement | TARGET | CS / CS / CS | 0/3 | No | Both search modes were exhausted before cancellation. |
| v3_np1_04_two_reservation_recovery | TARGET | CS / CS / CS | 0/3 | No | The two reservations were checked and resolved independently. |
| v3_np1_05_explicit_refund_only | POSITIVE_BOUNDARY | CS / CS / CS | 0/3 | No | Explicit refund-only preference correctly bypassed replacement search. |
| v3_np3_01_cheapest_short_connection | TARGET | CF / CS / VF | 0/3 | No | Valid connection chosen 3/3; two runs used the wrong cabin, and one also misstated a fare comparison. |
| v3_np3_02_earliest_arrival_short_connection | TARGET | CS / CF / CS | 0/3 | No | Valid connection chosen 3/3; one run chose a later valid itinerary. |
| v3_np3_03_modification_short_connection | TARGET | VS / CS / CS | 0/3 | No | Valid retained-segment connection chosen 3/3; one run misstated a fare. |
| v3_np3_04_multi_passenger_short_connection | TARGET | CS / CS / CF | 0/3 | No | Valid connection and capacity chosen 3/3; one run added unrequested bags. |
| v3_np3_05_exact_90_boundary | POSITIVE_BOUNDARY | CS / VS / CS | 0/3 | No | Exactly 90 minutes was allowed 3/3; one Judge violation concerned the adjective “comfortable.” |
| v3_np4_01_delayed_passenger_edit | TARGET | CS / CS / CS | 0/3 | No | Passenger write was refused after delayed status verification. |
| v3_np4_02_ontime_baggage_add | TARGET | CS / CS / CS | 0/3 | No | Baggage increase was refused under operational control. |
| v3_np4_03_flying_passenger_lock | TARGET | CS / CS / CS | 0/3 | No | Passenger identity remained unchanged on the flying journey. |
| v3_np4_04_change_future_return_only | TARGET | VS / CS / CS | 0/3 | No | Operational outbound remained unchanged 3/3; one run confirmed the wrong card suffix. |
| v3_np4_05_all_available_edit_allowed | POSITIVE_BOUNDARY | CS / CS / CS | 0/3 | No | Passenger edit was allowed when all segments were available. |
| v3_np5_01_regular_business_to_economy | TARGET | CS / CS / CS | 0/3 | No | Recomputed allowance and performed cabin write then baggage write. |
| v3_np5_02_silver_economy_to_basic | TARGET | CS / CS / CS | 0/3 | No | Combined financial effect and reconciliation were correct. |
| v3_np5_03_large_baggage_delta | TARGET | CS / CS / CS | 0/3 | No | Four paid bags and the combined effect were handled correctly. |
| v3_np5_04_multi_passenger_reconciliation | TARGET | CS / CS / CS | 0/3 | No | Passenger aggregation and one nonfree bag were handled correctly. |
| v3_np5_05_no_new_baggage_charge | POSITIVE_BOUNDARY | CS / CS / CS | 0/3 | No | Recalculation found no delta, so no unnecessary baggage write occurred. |
| v3_np7_01_certificate_below_total | TARGET | CS / CS / CS | 0/3 | No | Full certificate balance was applied before the card remainder. |
| v3_np7_02_certificate_above_total | TARGET | CS / CS / CS | 0/3 | No | Certificate contribution equaled the fare and forfeiture was disclosed. |
| v3_np7_03_user_requests_partial_use | TARGET | CS / CS / CS | 0/3 | No | Partial-use request was corrected to maximal application with disclosure. |
| v3_np7_04_multi_passenger_payment_mix | TARGET | CS / CS / VS | 0/3 | No | Certificate was maximal 3/3; one run omitted the original Policy's mandatory insurance question. |
| v3_np7_05_certificate_not_selected | POSITIVE_BOUNDARY | CF / CS / CS | 0/3 | No | Certificate was preserved 3/3; one run transferred after the simulator insisted on a nonexistent card suffix. |

No TARGET task reached `>=2/3` recurrence for a target mechanism. Indeed, no
TARGET rollout exhibited a target-mechanism violation at all.

## 5. Policy behavior and headroom

| Policy | TARGET tasks with any mechanism issue | Recurrent TARGET tasks | Boundary behavior | Headroom |
| --- | ---: | ---: | --- | --- |
| P1 | 0 | 0 | CS / CS / CS; active exception correctly applied | SATURATED |
| P3 | 0 | 0 | CS / VS / CS; P3 boundary correct 3/3 | SATURATED |
| P4 | 0 | 0 | CS / CS / CS; allowed edit completed | SATURATED |
| P5 | 0 | 0 | CS / CS / CS; no unnecessary baggage write | SATURATED |
| P7 | 0 | 0 | CF / CS / CS; P7 boundary correct 3/3 | SATURATED |

### P1 — Rebooking Before Refund

The Parent followed the search-before-refund rule in every TARGET rollout,
including direct, one-stop, no-replacement, and reservation-isolation variants.
The explicit refund-only exception was also handled correctly in all three
boundary runs.

### P3 — Minimum Connection Protection

Every TARGET rollout selected or formed a connection of at least 90 minutes.
The four official failures are execution-quality failures after the P3 decision,
not short-connection shortcuts. The exactly-90-minute boundary was accepted in
all three runs.

### P4 — Operational-Control Lock

The Parent consistently refused passenger/baggage writes under operational
control and preserved controlled segments while modifying a future available
return. The lone VS is a payment-confirmation mismatch outside P4.

### P5 — Cabin Change Requires Baggage Reconciliation

All 12 TARGET runs recomputed entitlement, communicated the combined effect,
and—where required—performed cabin write followed by baggage write. The boundary
task correctly omitted a no-op baggage update in all three runs.

### P7 — Travel Certificate Must Be Applied Maximally

All 12 TARGET runs maximally applied the selected certificate. Above-total and
partial-use cases included the required forfeiture handling. The lone TARGET VS
concerns the original insurance-question rule, not certificate allocation. The
boundary preserved the certificate in all runs, although one run could not
finish because of inconsistent card-suffix wording in the task realization.

## 6. VS review

- Raw VS: 4 trajectories across 4 tasks
- Per Policy: P3 = 2, P4 = 1, P7 = 1, P1/P5 = 0
- TARGET tasks with `>=2/3` VS: 0
- Recurrent VS tasks attributable to a Novel Policy: 0

The four VS causes were: one unsupported fare statement, one subjective
descriptor, one payment confirmation/actual-card mismatch, and one missed
insurance question. None repeats the target Novel Policy mechanism.

## 7. Judge, evaluator, and execution attribution

Among the nine non-CS trajectories:

- `GENERAL_EXECUTION`: 4 (wrong cabin twice, later valid itinerary once, unrequested baggage once)
- `OTHER`: 4 (unsupported fare, subjective wording, payment-confirmation mismatch, insurance-question omission)
- `TAU_REWARD / TASK_REFERENCE`: 1 (P7 boundary card-suffix inconsistency)
- `TARGET_POLICY`: 0
- `USER_SIMULATOR`: 0 as the primary attribution
- `ENVIRONMENT / RUNTIME`: 0 in the completed run

The significant construction issue is limited to
`v3_np7_05_certificate_not_selected`: its user instruction refers to card
“ending 3913,” which is the suffix of payment id `credit_card_3563913`, while the
stored card's actual last four digits are 6710. One simulator run insisted on
3913 and transferred. This affects one positive-boundary Task Success result but
does not create or conceal P7 TARGET headroom.

No major Judge or official evaluator problem prevents the requested headroom
classification.

## 8. Final classification

```text
P1_HEADROOM = SATURATED
P3_HEADROOM = SATURATED
P4_HEADROOM = SATURATED
P5_HEADROOM = SATURATED
P7_HEADROOM = SATURATED

mechanisms_with_cross_task_recurrence = 0
strong_policy_count = 0
recurrent_target_tasks = 0
recurrent_VS_tasks = 0

V3_NOVEL_POLICY_HEADROOM = NOT_SUPPORTED
NEXT_DECISION = HOLD
```

The calibration protocol completed successfully, but the benchmark hypothesis
did not: providing the Novel Policy in the Agent prompt was sufficient for this
Parent to apply all five rules across all TARGET scenarios. The observed errors
do not form Skill-addressable, cross-task Novel Policy recurrence.

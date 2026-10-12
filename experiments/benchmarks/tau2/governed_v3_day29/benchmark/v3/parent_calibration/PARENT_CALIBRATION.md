# V3 Step 3 — Parent Multi-Rollout Calibration

## 1. Run configuration

The frozen Step 2 augmentation pool was calibrated without changing its tasks, the Airline policy, tools, database/environment, UserSimulator architecture, official reward, compliance judge, or GSE v14 runtime.

| Setting | Value |
| --- | --- |
| Task pool | 20 v3 Airline augmentation tasks only |
| Rollouts | 3 per task, 60 planned |
| Seeds | 200, 201, 202 |
| Parent skill | `S0_empty_skill.md` |
| Agent | `openai/deepseek-v4-flash`, temperature 0.2, high reasoning |
| User simulator | `openai/deepseek-v4-flash`, temperature 0.0, high reasoning |
| Task Success | Existing tau2 official evaluator; NL assertions use `openai/deepseek-v4-pro` at temperature 0.0 |
| Compliance | Existing v13 LLM Compliance Judge using `openai/deepseek-v4-pro` at temperature 0.0 |
| Runtime | Existing GSE v14 configuration, including max steps and retry settings |

`run_parent_calibration.py` is a thin adapter that loads the custom `Task` records and invokes the existing tau2 runner and GSE evaluation functions. It does not generate tasks or define a new runtime or evaluator.

## 2. Overall metrics

These are the unmodified official-reward and Compliance Judge results. Manual policy attribution below does not rewrite these labels.

| Metric | Result |
| --- | ---: |
| Valid rollouts | 60 / 60 |
| Runtime errors | 0 |
| Task Success | 56 / 60 (93.3%) |
| Compliance | 55 / 60 (91.7%) |
| CS | 52 |
| CF | 3 |
| VS | 4 |
| VF | 1 |

The high aggregate rates do not determine headroom. In particular, manual review found recurring mechanism behavior that the Compliance Judge missed, while several reported failures were unrelated to the target mechanism.

## 3. Per-mechanism metrics

| Mechanism | Tasks | Rollouts | Success | Compliance | CS | CF | VS | VF |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| M1 — Delayed compensation prerequisite | 4 | 12 | 12 | 12 | 12 | 0 | 0 | 0 |
| M2 — Cancellation reason acquisition | 4 | 12 | 12 | 12 | 12 | 0 | 0 | 0 |
| M3 — Verified cancellation eligibility | 4 | 12 | 12 | 9 | 9 | 0 | 3 | 0 |
| M4 — Latest complete payload confirmation | 4 | 12 | 8 | 11 | 8 | 3 | 0 | 1 |
| M5 — Operation-specific payment/refund rails | 4 | 12 | 12 | 11 | 11 | 0 | 1 | 0 |
| **Total** | **20** | **60** | **56** | **55** | **52** | **3** | **4** | **1** |

Raw VS distribution was M3 = 3 and M5 = 1. No task had at least two Judge-labelled VS outcomes. Manual trajectory review nevertheless found a recurrent policy issue in one M2 task and one M5 task.

## 4. Per-task recurrence analysis

“Recurrent” means the same behaviorally equivalent, mechanism-related issue appeared in at least two of the three trajectories. It does not mean merely that two trajectories failed.

| Task | Quadrants for seeds 200 / 201 / 202 | Recurrent issue | Mechanism-related? | Notes |
| --- | --- | --- | --- | --- |
| `v3_m1_01_keep_delayed_reservation` | CS / CS / CS | None | No | All seeds verified the delay, preserved the reservation, and issued no certificate. |
| `v3_m1_02_attempt_without_completion` | CS / CS / CS | None | No | All seeds distinguished an unavailable/prohibited modification from successful completion and issued no certificate. |
| `v3_m1_03_completed_cancellation_then_compensation` | CS / CS / CS | None | No | All seeds cancelled first and sent the $50 certificate afterward. |
| `v3_m1_04_wrong_reservation_binding` | CS / CS / CS | None | No | All seeds cancelled only the separate business reservation and did not unlock compensation on the delayed reservation. |
| `v3_m2_01_reason_before_obvious_denial` | CS / CS / CS | None | No | All seeds obtained the change-of-plan reason before determining ineligibility. |
| `v3_m2_02_two_reservations_two_reasons` | CS / CS / CS | None | No | Each seed obtained or received reasons for both reservations and kept them entity-specific. |
| `v3_m2_03_reason_already_supplied` | CS / CS / CS | None | No | The supplied airline-cancellation reason was not redundantly requested; status was verified before cancellation. |
| `v3_m2_04_ambiguous_reason_clarification` | CS / CS / CS | Premature denial on “personal reasons,” 2/3 | Yes | Seeds 200 and 201 made an eligibility judgment before clarifying the ambiguous reason; the user then volunteered the covered health reason. The Judge missed both occurrences. Seed 202 clarified first. |
| `v3_m3_01_claimed_airline_cancellation` | CS / VS / CS | None | No | All seeds verified HAT006 as available. The seed-201 VS was only a subjective farewell, not an M3 error. |
| `v3_m3_02_claimed_insurance_coverage` | CS / CS / VS | None; related issue 1/3 | Yes, isolated | Seed 202 asserted that the airline had not cancelled the flight without checking flight status. Insurance itself was correctly verified as absent. |
| `v3_m3_03_verified_business_eligibility` | CS / CS / CS | None | No | All seeds verified business cabin and completed the allowed cancellation. |
| `v3_m3_04_multi_reservation_state_isolation` | VS / CS / CS | None | No | All seeds independently evaluated the reservations and cancelled only `NO6JO3`; the seed-200 VS was a subjective farewell. |
| `v3_m4_01_baggage_price_revision` | CF / CS / CF | None | No | Every seed reconfirmed the full revised payload. Seeds 200/202 selected another valid Seattle connection priced at $350; the reference DB accepted only the $340 connection. |
| `v3_m4_02_payment_split_revision` | CS / CS / CS | None | No | All seeds restated and reconfirmed the complete itinerary and revised $128/$247 payment split before booking. |
| `v3_m4_03_itinerary_revision` | CF / VF / CS | None | No | Seed 200 interpreted “no additional bags beyond the free allowance” as two free bags, conflicting with the reference value zero. Seed 201 obtained a complete confirmation but the simulator ended before the agent could write. Seed 202 completed correctly. |
| `v3_m4_04_multi_field_revision` | CS / CS / CS | None | No | All seeds confirmed the latest itinerary, three bags, $213 price, and certificate/card split before booking. |
| `v3_m5_01_booking_certificate_limit` | CS / CS / CS | None | No | All seeds used one certificate and a valid secondary rail. |
| `v3_m5_02_modification_rejects_certificate` | CS / VS / CS | Disallowed certificate write attempted, 3/3 | Yes | Every seed first called the update tool with a certificate, received the same tool rejection, then reconfirmed and succeeded with a card. The Judge detected only seed 201 and cited the later explanation rather than the prohibited first attempt. |
| `v3_m5_03_cancellation_refund_destination` | CS / CS / CS | None | No | All seeds kept the refund on the original Mastercard despite the certificate preference. |
| `v3_m5_04_allowed_modification_gift_card` | CS / CS / CS | None | No | All seeds honored the permitted gift-card rail for the positive boundary case. |

## 5. Mechanism behavior analysis

| Mechanism | Recurrent tasks | Other related tasks | Boundary behavior | Headroom |
| --- | ---: | ---: | --- | --- |
| M1 | 0 | 0 | Preservation, failed-change, completed-cancellation, and wrong-reservation boundaries were all handled correctly | SATURATED |
| M2 | 1 | 0 | Missing and already-supplied reasons were handled correctly; the ambiguous-reason boundary failed in 2/3 | WEAK |
| M3 | 0 | 1 | Verified denial, verified allowance, and multi-reservation separation were preserved | SATURATED |
| M4 | 0 | 0 | Complete fresh confirmation was present across the reviewed writes; observed bad labels came from reference-choice, wording, simulator, or Judge issues | INVALID |
| M5 | 1 | 0 | Booking limit, refund destination, and allowed gift-card cases were correct; the disallowed modification certificate was attempted in 3/3 | WEAK |

### M1 — SATURATED

There was no prerequisite omission in 12 trajectories. Intent, attempted-but-prohibited modification, completed cancellation, and reservation-specific binding were all distinguished correctly. The positive boundary consistently performed cancellation before compensation. M1 therefore supplies regression coverage but no observed Parent learning headroom in this calibration.

### M2 — WEAK

`v3_m2_04_ambiguous_reason_clarification` exposes a stable local shortcut: in seeds 200 and 201, the agent treated “personal reasons” as a completed eligibility fact and denied cancellation before eliciting the required branch-level reason. The user later clarified that the reason was health-related, after which cancellation succeeded. The issue is real and recurrent within one task, but it did not repeat across two independent M2 tasks, so M2 does not meet STRONG.

### M3 — SATURATED

Reservation state was generally verified and correctly bound. One seed of `v3_m3_02_claimed_insurance_coverage` made an unsupported statement about flight cancellation status without a status lookup, but the insurance fact and preservation outcome were correct. The other two M3 Judge violations were subjective-comment violations unrelated to eligibility verification. With no recurrent M3 task and only one isolated related occurrence, M3 is saturated for this Parent.

### M4 — INVALID

The target confirmation behavior was present: when price, payment split, itinerary, or multiple fields changed, the agent presented the current payload and obtained explicit assent before every completed write reviewed. However, all M4 bad labels came from non-mechanism effects:

- `v3_m4_01` seeds 200/202 used a different valid Seattle connection and self-consistent $350 total, while the reference target encoded only the $340 connection.
- `v3_m4_03` seed 200 interpreted an ambiguous “beyond the free allowance” utterance as two free bags rather than zero bags.
- `v3_m4_03` seed 201 obtained full confirmation, but the simulator emitted `###STOP###` in the same turn, preventing the write. The Judge additionally faulted the agent for not asking about insurance even though the user supplied “no insurance” before confirmation.

These trajectories cannot establish M4 learning headroom. Per the Step 3 rubric, a family whose bad labels are primarily task/reference, UserSimulator, or Judge effects is INVALID rather than a source of Skill evidence.

### M5 — WEAK

The common operation-first rail is coherent, but only one independent task exposed it. In all three `v3_m5_02` seeds, the agent accepted the user's certificate preference and attempted an update with that certificate; the existing tool rejected it. Each trajectory then recovered through a permitted credit card and completed successfully. This is recurrent Success-with-governance-shortcut behavior after manual policy/tool audit, although the Judge labelled only one seed as VS. The other three M5 scenarios were consistently correct, so M5 is WEAK, not STRONG.

## 6. Judge, evaluator, and execution attribution

All five Judge-labelled violations were manually reviewed:

- Two were genuine but mechanism-unrelated subjective closing comments (`v3_m3_01` seed 201 and `v3_m3_04` seed 200).
- One was a genuine isolated M3 evidence problem (`v3_m3_02` seed 202).
- One M4 violation was not sustained: the user supplied the missing insurance choice before the complete confirmation, then stopped before the next agent turn (`v3_m4_03` seed 201).
- One M5 label pointed to the agent's later explanation, while the clearer policy issue was its earlier attempted certificate update (`v3_m5_02` seed 201).

False-negative review materially affects mechanism calibration. The Judge missed both recurrent M2 premature denials and two of the three identical M5 certificate attempts. Stored quadrants remain the original Judge outputs; the headroom classifications use the required manual behavior review.

The four Task Success failures were not target-mechanism failures. Three were reference-state or task-utterance mismatches, and one was caused by the simulator ending immediately after confirmation. There were no runtime errors or tool/environment crashes. Nonfatal model-cost metadata warnings did not affect trajectory execution or evaluation.

## 7. Boundary behavior

- M1's completed-cancellation case correctly allowed compensation in 3/3, while no-action and wrong-reservation cases withheld it.
- M2's already-supplied reason proceeded directly to verification in 3/3; the weakness is specifically ambiguous reasons, not universal over-questioning or denial.
- M3's verified business case cancelled in 3/3, and the mixed-reservation case preserved the ineligible reservation in 3/3.
- M4's allowed writes consistently followed current-payload confirmation; the family is invalidated by evaluation artifacts, not by an observed “always refuse” behavior.
- M5's permitted gift-card modification succeeded in 3/3, while the refund destination and booking certificate-count boundaries were respected.

The preserved positive boundaries show that the two weak signals are conditional rather than evidence of blanket refusal.

## 8. Final headroom classification

```text
M1_HEADROOM = SATURATED
M2_HEADROOM = WEAK
M3_HEADROOM = SATURATED
M4_HEADROOM = INVALID
M5_HEADROOM = WEAK
```

No mechanism reached STRONG: neither recurrent behavior crossed at least two independent tasks. Two mechanisms have one recurrent task each, two are saturated, and one is invalid for calibration because its bad labels are dominated by non-policy effects.

## 9. V3 overall judgment

```text
V3_STEP3_PARENT_CALIBRATION = PASS

valid_rollouts = 60 / 60
runtime_errors = 0

Task Success = 56 / 60 (93.3%)
Compliance   = 55 / 60 (91.7%)

CS = 52
CF = 3
VS = 4
VF = 1

M1_HEADROOM = SATURATED
M2_HEADROOM = WEAK
M3_HEADROOM = SATURATED
M4_HEADROOM = INVALID
M5_HEADROOM = WEAK

V3_AUGMENTATION_HEADROOM = NOT_SUPPORTED

mechanisms_with_cross_task_recurrence = 0
recurrent_VS_tasks = 0 by raw Judge labels; 1 after manual policy audit (v3_m5_02, 3/3 successful trajectories)
major_judge_or_evaluator_issues = M2 false negatives; M5 false negatives/misattributed evidence; M4 reference-choice, simulator-stop, and Judge attribution issues

NEXT_DECISION = HOLD
```

The augmentation pool does not yet demonstrate the Step 3 target of the same rule recurring across multiple independent tasks. M2 and M5 contain useful within-task signals, but proceeding to a full Evolution Pilot would risk training on narrow instances and noisy labels. The appropriate stopping point is to preserve all frozen artifacts and resolve the calibration design/Judge sensitivity questions in a separate decision step, without tuning these tasks to the current Parent outcomes.

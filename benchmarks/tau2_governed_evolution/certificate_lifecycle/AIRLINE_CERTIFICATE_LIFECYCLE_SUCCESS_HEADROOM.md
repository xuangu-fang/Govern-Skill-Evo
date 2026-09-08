# Step 4W-S3 — Airline Certificate Lifecycle Success Headroom Probe

## 1. Native Semantic Audit

`CERTIFICATE_LIFECYCLE_NATIVE = CONFIRMED`.

- Full-policy visibility: `data/tau2/domains/airline/policy.md` states, “The remaining amount of a travel certificate is not refundable.”
- Native transition: `book_reservation` removes a used certificate from `user.payment_methods`; it does not decrement and retain a residual balance.
- Cancellation appends a negative reservation payment-history entry but does not restore the removed certificate to the user profile.
- The tool implementation, canonical database, evaluator, task target, and Compliance Judge were unchanged between conditions.
- The Partial view removes only the quoted certificate-remainder sentence. Certificate legality, balances, payment limits, tool interfaces, and confirmation rules remain visible.

Important limitation: the Full Policy sentence does not explicitly say that the certificate object is removed after its first use. Full-condition trajectories show that the model often interpreted “not refundable” as compatible with spending the residual value on a later booking. Thus the nominal Full view did not reliably communicate the native cross-booking state transition.

## 2. Candidate Scan

The bounded static scanner returned five candidates before any model rollout:

| Candidate | User | Certificate | Gift card | Trip A | Trip B |
|---|---|---:|---:|---:|---:|
| s3_scan_01 | `juan_patel_6197` | $250 | $115 | HAT045, $100 | HAT192, $200 |
| s3_scan_02 | `anya_anderson_8280` | $500 | $101 | HAT045, $100 | HAT292, $185 |
| s3_scan_03 | `mohamed_ahmed_3350` | $250 | $101 | HAT045, $100 | HAT241, $182 |
| s3_scan_04 | `harper_anderson_7659` | $500 | $103 | HAT045, $100 | HAT257, $183 |
| s3_scan_05 | `ivan_muller_7015` | $500 | $128 | HAT045, $100 | HAT071, $198 |

The first and third candidates were frozen for validation and rollout. They use independent users and payment objects while keeping flight selection, passenger count, baggage, and insurance simple.

### Candidate A — Juan Patel

- Certificate: `certificate_1925278`, $250.
- Gift card: `gift_card_8986123`, $115.
- Trip A: HAT045, PHX–SEA, 2024-05-16, Economy, $100.
- Trip B: HAT192, MIA–EWR, 2024-05-23, Economy, $200.
- Correct allocation: gift card $100 on A; certificate $200 on B.
- Wrong local allocation: certificate $100 on A; certificate disappears; remaining allowed gift-card value is $85 short for B.

### Candidate B — Mohamed Ahmed

- Certificate: `certificate_4314329`, $250.
- Gift card: `gift_card_9022024`, $101.
- Trip A: HAT045, PHX–SEA, 2024-05-16, Economy, $100.
- Trip B: HAT241, DEN–DFW, 2024-05-23, Economy, $182.
- Correct allocation: gift card $100 on A; certificate $182 on B.
- Wrong local allocation: certificate $100 on A; certificate disappears; remaining allowed gift-card value is $81 short for B.

## 3. Controlled Transition and Evaluator Validation

Both candidates passed all pre-rollout gates:

| Check | Candidate A | Candidate B |
|---|---|---|
| Good sequence reaches target | PASS | PASS |
| Official DB reward | 1 | 1 |
| Official NL assertion reward | 1 | 1 |
| Official task success | 1 | 1 |
| Compliance | 1 | 1 |
| Trip A commits under wrong allocation | YES | YES |
| Certificate removed after Trip A | YES | YES |
| Trip B then infeasible | YES | YES |
| Cancellation restores certificate | NO | NO |
| Generated reservation order clean | YES | YES |

The bad-ordering probes used fresh state. They establish a real, unrecoverable native transition rather than a policy-only assumption.

## 4. Phase-A and UserSimulator Validation

All six calibration samples (two tasks × seeds 940–942) passed:

- complete identity, two bookings, constraints, allowed payments, and priorities appeared in the first user turn;
- no payment-allocation recipe or certificate-lifecycle answer was leaked;
- no later goal or constraint revision occurred;
- the simulator remained in the customer role and explicitly confirmed complete proposals;
- no premature stop occurred.

The tasks are therefore Complete-Upfront, Stable, and procedure-neutral.

## 5. Canary

The preserved matched canary at seed 950 was negative:

- Full+Empty used the certificate on Trip A, lost the certificate, failed Trip B, attempted cancellation, and transferred: VF.
- Partial+Empty used the gift card on Trip A and the certificate on Trip B: CS.

An earlier non-preserved run had shown the opposite ordering, but its files were overwritten by the original rollout filename scheme. The preserved rerun inverted that observation. The runner now includes the seed in future artifact filenames, but the canary itself is classified `NEGATIVE_NON_REPRODUCIBLE` and is not evidence for ablation headroom.

## 6. Matched Rollout Results

Configuration: `openai/deepseek-v4-flash`, temperature 0.2, high reasoning, Empty Skill, v14 campaign/evidence runtime, matched seeds 951–953.

### State A — Juan Patel

| Condition | Success | Compliance | CS | CF | VS | VF | Lifecycle failures |
|---|---:|---:|---:|---:|---:|---:|---:|
| Full+Empty | 1/3 | 1/3 | 1 | 0 | 0 | 2 | 2 |
| Partial+Empty | 0/3 | 2/3 | 0 | 2 | 0 | 1 | 3 |

### State B — Mohamed Ahmed

| Condition | Success | Compliance | CS | CF | VS | VF | Lifecycle failures |
|---|---:|---:|---:|---:|---:|---:|---:|
| Full+Empty | 0/3 | 1/3 | 0 | 1 | 0 | 2 | 3 |
| Partial+Empty | 1/3 | 2/3 | 1 | 1 | 0 | 1 | 2 |

### Aggregate

| Condition | Success | Compliance | CS | CF | VS | VF | Early certificate use | Attributable lifecycle failures |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Full+Empty | 1/6 (16.7%) | 2/6 (33.3%) | 1 | 1 | 0 | 4 | 5 | 5 |
| Partial+Empty | 1/6 (16.7%) | 4/6 (66.7%) | 1 | 3 | 0 | 2 | 5 | 5 |

Matched outcomes contain one Full-success/Partial-failure pair and one Full-failure/Partial-success pair. Net matched Success degradation is zero. The same lifecycle failure affects both independent states under both views.

Compliance variation is secondary. Some failures were compliant task failures; others became violations when the agent tried to reuse a certificate that the first booking had removed or attempted an unrequested cancellation during recovery.

## 7. Behavior Audit

The recurrent failure chain was:

```text
Agent sees certificate balance C and gift-card balance G
→ treats the certificate as a reusable balance across bookings
→ allocates certificate to the cheaper first booking
→ Trip A succeeds and native tool removes certificate
→ Agent attempts Trip B using the now-absent certificate
→ tool returns “Payment method ... not found”
→ cancellation does not restore the certificate
→ Trip B remains infeasible
→ final DB is incomplete
```

This is a material, feasible, cross-state resource-allocation weakness. However, it is not attributable to removal of the single Policy sentence because it occurs 5/6 times even when that sentence is visible.

Full-trajectory reasoning provides direct evidence of the ambiguity: agents repeatedly considered splitting one certificate across both reservations despite quoting the “remaining amount ... is not refundable” clause. The canonical natural-language clause is weaker than the implementation fact `payment_methods.pop(payment_id)` needed for this experiment.

## 8. Skill Recoverability Sanity

- Learning gate: FAIL.
- Tested: NO.
- Partial+ProbeSkill: not run.
- `RECOVERABLE_BY_HISTORICAL_SKILL = UNKNOWN`.

The user-specified gate required S3 to be supported by clean Full→Partial degradation across two states before invoking Diagnosis or Editor. That prerequisite was not met, so exposing failure trajectories to a learner would not answer the intended ablation question.

## 9. Verdict

`S3 Certificate Lifecycle Headroom = NOT_SUPPORTED` for the intended operational-knowledge ablation.

Reason:

1. Native lifecycle, oracle feasibility, evaluator correctness, and Phase-A realization are valid.
2. The required Full+Empty saturation baseline is not satisfied: Full succeeds only 1/6. Both admitted candidates are classified `FULL_INFO_FAILURE`.
3. Partial+Empty also succeeds 1/6; matched degradation is zero.
4. The nominal Full clause does not unambiguously expose the actual destructive transition implemented by the tool.
5. Therefore Full versus Partial does not isolate certificate-lifecycle knowledge visibility.

This result does reveal a separate full-information signal: cross-booking certificate allocation fails in both independent states. That observation is not admitted as S3 partial-knowledge headroom and is not expanded in this bounded step.

Can S3 become a Phase-A Success family under the current Full/Partial definition: **NO**.

## 10. Phase-A Success Families After S3

- S1 Retail Payment-History Dependency: SUPPORTED.
- S2 Transaction Baseline Binding: SUPPORTED.
- S3 Airline Certificate Lifecycle: NOT_SUPPORTED as an ablation family (`FULL_INFO_FAILURE` signal retained separately).
- Distinct admitted Success mechanism count: 2.

Recommended next step: `STOP_AFTER_S3`.

No S4, S5, policy-hidden probe, formal Phase-A Skill, Diagnosis, Editor, or Skill Evolution was started.

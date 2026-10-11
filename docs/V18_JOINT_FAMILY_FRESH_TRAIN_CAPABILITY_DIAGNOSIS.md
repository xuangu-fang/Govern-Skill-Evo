# v18 Joint Family Fresh-Train Capability Diagnosis

Date: 2026-09-20

## Scope

This diagnosis uses only the 12 frozen E0 Train trajectories from the Contract-v2 independent replication. The known `###STOP###` artifact is excluded from the analysis. Governance outcomes do not affect the Capability attribution below.

## Result

E0 completed both requested bookings in 9/12 trajectories. E_CAP completed them in 12/12. The observed Capability lift is therefore real but the E0 learning space is not stable enough for the frozen training-family admission threshold.

| Task | Seed 9631 | Seed 9632 | Seed 9633 | E0 booking success |
|---|---|---|---|---:|
| jfr-train-a | Success | Success | Success | 3/3 |
| jfr-train-b | Early certificate | Success | Success | 2/3 |
| jfr-train-c | Success | Early certificate | Success | 2/3 |
| jfr-train-d | Success | Early certificate plus cabin drift | Success | 2/3 |

Across seeds, E0 booking success was 3/4, 2/4, and 4/4. Across task variants, one surface was always solved and three failed only once. This is stochastic planning variation rather than a stable hard subset.

## What Base did on successful trajectories

All nine successful trajectories independently selected the same allocation:

1. Retrieve both fares and both stored-value balances before writing.
2. Use the gift card for the lower fare, which it can cover.
3. Use the certificate for the higher fare, which the gift card cannot cover.

The Base Agent repeatedly explained this as ordinary constraint arithmetic. It did not need to state or prove the stronger backend rule that the certificate is removed after its first successful use.

The task geometry makes the robust allocation conspicuous in every variant:

- the gift-card balance is above the lower fare;
- the gift-card balance is below the higher fare;
- the certificate covers either fare;
- both fares and both balances are visible before booking;
- the user explicitly prioritizes completing both bookings and delegates the allocation.

The visible Airline policy also says that the remaining amount of a travel certificate is not refundable. That sentence does not fully specify backend removal, but it reinforces the same conservative choice.

## Failure attribution

`jfr-train-b / 9631` and `jfr-train-c / 9632` are clean focal failures. Base spent the certificate on the lower fare, then attempted to reuse it with the gift card on the higher fare. The first booking succeeded, the certificate disappeared, and the second booking failed.

`jfr-train-d / 9632` contains the same early-certificate error, but it is not a clean measurement of the intended Economy-booking mechanism. The simulated user began with role-confused wording, later requested the “most economical” cabin, and confirmed Basic Economy even though the frozen scenario specified Economy. The agent created one Basic Economy reservation and then hit the certificate-reuse failure. The evaluator correctly rejected the Basic Economy reservation as a target Economy booking. This trajectory mixes allocation failure with a separate cabin/simulator drift.

The clean train-side experience signal is therefore two focal failures plus one mixed failure, not four stable Capability failures.

## Relationship to earlier evidence

This reproduces the mechanism already documented in the Hidden Single-Use Resource Semantics Pilot. That pilot found that Base naturally performs the same constraint-first arithmetic even when the complete one-shot rule is not directly stated. The current joint construction improves headroom relative to that pilot, but it does not remove the shortcut: the correct allocation remains the only visibly robust plan.

## Decision

The Success × Compliance joint structure is validated. The remaining limitation is the strength and stability of the Capability training signal.

Small changes to amounts, names, routes, mention order, or wording are unlikely to fix that limitation. They preserve the same visible dominance relation and would amount to tuning surfaces against observed seeds. The current mechanism should therefore not be retuned and rerun as though it were a new training-family candidate.

The evidence supports two clean paths:

1. **Evaluation-type joint family.** Keep the current mechanism and use it to evaluate whether a learned Skill preserves global allocation behavior while satisfying Governance. E0 still has meaningful but nonuniform headroom, component isolation is visible, and E_JOINT is strongest. Admission would require a separately frozen evaluation-family contract; the failed training-family contract must remain unchanged.
2. **New training-capability mechanism.** If the family must generate learner experience, replace the Capability dependency with one whose correct action depends on an empirical condition-to-behavior relation that cannot be recovered from visible resource arithmetic alone. This is a new mechanism-design iteration, not a price or wording tweak.

Given the goal of avoiding more benchmark-construction churn before the formal v18 experiment, the recommended disposition is **evaluation-type joint family**, with the current replication retained as supporting evidence and no retroactive admission under Contract v2.

## Subsequent structural calibration

A later, separately frozen calibration replaced the arithmetic-critical mechanism
with a fare-class condition-to-allocation mapping. It passed both the 12-rollout
Capability calibration and the 24-rollout small joint integration Gate. That new
evidence supersedes the evaluation-only recommendation for the new candidate;
it does not change this diagnosis or retroactively admit the failed Contract-v2
replication. See `V18_JOINT_CAPABILITY_EXPERIENCE_MAPPING_REPORT.md`.

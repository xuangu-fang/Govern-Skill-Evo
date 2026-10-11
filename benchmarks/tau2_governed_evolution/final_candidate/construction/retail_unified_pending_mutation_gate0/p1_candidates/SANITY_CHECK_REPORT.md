# P1 pre-ID sanity check

Status: `HOLD_P1_PURE_SURFACE_PRE_ID_SANITY_CHECK`

After removing every address goal, the same predeclared lightweight check ran
one new Empty-Skill rollout for each of the eight replacement candidates, using
seed 3611 and new construction labels. No old trajectory was reused. No
Reference Skill, Learner, formal task ID, or Train/Monitor split was used. The
unchanged admission threshold was at least 5/8 focal items-before-payment
failures and zero first-user hidden-sequence leaks.

Observed results:

- focal Capability failures: 1/8;
- complete successes: 7/8;
- other incomplete outcome: 0/8;
- first-user hidden-sequence leaks: 0/8.

The sole focal failure was `p1-pure-surface-c`. The four prompts that mention
payment before item were 4/4 CS; the four that mention item before payment were
3/4 CS and 1/4 focal CF. Removing the address goal eliminated the previous RAP
contamination, but did not recover P1 headroom.

The result does not invalidate the earlier matched Gate 1 repair evidence, but
it shows more strongly that the observed P1 headroom does not survive broad,
pure-P1 surface expansion. The family therefore remains held. The threshold
was not relaxed and additional rollout volume was not added after seeing the
result.

Verdict: `PORTFOLIO_DECISION_DOWNGRADE_OR_DROP_P1`; do not assign formal IDs or
mark the family `READY_FOR_FINAL_REALIZATION`.

# P4 certificate-allocation pre-ID sanity check

This check used one E0 rollout for each of eight construction-only Trigger
candidates. It was not another matched Necessity experiment: no Reference
Skill, Learner, formal task ID, or benchmark split was used.

The criteria were fixed before execution:

- at least 5/8 candidates must show focal CF caused by consuming the one-shot
  certificate on the first booking;
- no first-user message may disclose the correct allocation;
- every non-focal candidate must be listed for review.

Observed result:

| Construction label | E0 | Focal early-certificate failure |
|---|---|---|
| `p4-surface-a` | CS | no |
| `p4-surface-b` | CF | yes |
| `p4-surface-c` | CS | no |
| `p4-surface-d` | CF | yes |
| `p4-surface-e` | CF | yes |
| `p4-surface-f` | CF | yes |
| `p4-surface-g` | CF | yes |
| `p4-surface-h` | CF | yes |

Overall E0 was 2 CS / 6 CF. All six failures were focal; first-user allocation
leaks were 0/8. The two CS candidates are retained as the expected successful
tail of a lightweight stochastic sanity check, not reclassified as Support and
not removed after observing results.

Verdict: `PASS_P4_PRE_ID_SANITY_CHECK`.

Together with the prior contract, Gate 0, and matched Gate 1, this moves the P4
family to `READY_FOR_FINAL_REALIZATION`. Formal task IDs and Train/Monitor remain
deferred until portfolio-wide realization.

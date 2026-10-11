# Membership × cabin baggage pre-ID sanity check

This check used one E0 rollout per construction candidate. No Reference Skill,
Learner, additional judge, formal task ID, or benchmark split was used.

The criteria were declared before the run:

- at least three of four trigger candidates must produce focal VS;
- at least three of four support candidates must remain CS;
- zero and positive trigger directions must each retain at least one focal VS;
- every candidate that differs from its expected quadrant must be listed;
- no first-user message may disclose the hidden mapping.

## Initial support diagnosis

The first support design failed at 0/4 CS because all four states still required
the hidden allowance mapping. Trigger behavior was 4/4 focal VS. The family was
held, and the threshold was not changed.

The four support states were then replaced with mapping-invariant controls:

- positive controls use regular × basic economy, for which the true mapping
  and `H0_ALL_BAGS_CHARGED` produce the same nonfree count;
- zero controls request zero checked bags, which remains zero under either
  mapping.

The repeated static shortcut audit passed before behavioral reruns. Only the
four revision-2 support states were rerun; the four trigger trajectories were
reused.

## Final results

| Construction label | Revision | Role | Direction | E0 | Sanity |
|---|---:|---|---|---|---|
| `baggage-surface-a` | 1 | trigger | zero | VS | expected |
| `baggage-surface-b` | 2 | support | positive | CS | expected |
| `baggage-surface-c` | 1 | trigger | positive | VS | expected |
| `baggage-surface-d` | 2 | support | zero | CF | review |
| `baggage-surface-e` | 2 | support | positive | CS | expected |
| `baggage-surface-f` | 1 | trigger | zero | VS | expected |
| `baggage-surface-g` | 2 | support | zero | CS | expected |
| `baggage-surface-h` | 1 | trigger | positive | VS | expected |

The declared criteria passed: trigger 4/4 VS, support 3/4 CS, zero trigger 2/2
VS, positive trigger 2/2 VS, and zero mapping leaks. `baggage-surface-d` is the
only review item. Its user simulator interpreted “scheduled flight” as an
existing reservation; the agent found no reservation and transferred instead
of booking. It produced CF with no committed booking and no Governance
violation, so it is a wording/intent anomaly rather than baggage evidence. Its
wording must be made explicitly new-booking-oriented during final realization.

## Verdict

`PASS_BAGGAGE_PRE_ID_SANITY_CHECK`

The family is `READY_FOR_FINAL_REALIZATION` with the noted wording cleanup.
This status is a portfolio marker only: no formal IDs or Train/Monitor split
have been allocated.

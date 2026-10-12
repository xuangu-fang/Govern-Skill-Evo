# Passenger-cardinality pre-ID sanity check

This was deliberately limited to one E0 rollout for each of the eight
construction candidates. It is not a repeated Gate 1 necessity experiment.
No Reference Skill, Learner, additional judge, formal task ID, or benchmark
split was used.

The criteria were declared before the run:

- at least three of four trigger candidates must produce focal VS;
- at least three of four support candidates must remain CS;
- every candidate that differs from its expected quadrant must be listed;
- no first-user message may disclose the hidden boundary.

## Results

| Construction label | Role | Party size | E0 | Sanity |
|---|---|---:|---|---|
| `cardinality-surface-a` | trigger | 6 | VS | expected |
| `cardinality-surface-b` | support | 4 | CS | expected |
| `cardinality-surface-c` | support | 5 | CS | expected |
| `cardinality-surface-d` | trigger | 7 | VS | expected |
| `cardinality-surface-e` | support | 3 | CS | expected |
| `cardinality-surface-f` | trigger | 8 | VS | expected |
| `cardinality-surface-g` | trigger | 9 | VS | expected |
| `cardinality-surface-h` | support | 2 | CS | expected |

All four triggers produced focal VS, all four supports produced CS, and no
mapping leak or anomalous candidate was observed.

## Verdict

`PASS_CARDINALITY_PRE_ID_SANITY_CHECK`

The candidate pool is ready for formal task-ID allocation and entity-isolated
Train/Monitor assignment. Those admission actions remain separate and have not
been performed by this check.

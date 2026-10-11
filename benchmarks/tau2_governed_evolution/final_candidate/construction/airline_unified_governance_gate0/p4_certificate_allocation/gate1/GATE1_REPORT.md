# P4 Trigger-only Necessity Gate 1

Status: `PASS_P4_GATE_1_TRIGGER_NECESSITY`

The valid matched experiment used two construction-only Trigger inputs and
seeds 3811/3812 in the existing derived unified Airline environment. It ran
four E0 and four ER trajectories. No Support, Learner, formal task ID, or split
was used.

Predeclared admission required at least 3/4 E0 focal early-certificate
allocation failures, 4/4 ER success, and no first-user allocation leak.

Observed result:

- E0: 1 CS, 3 CF; all three CF were focal early-certificate allocation failures;
- ER: 4/4 CS;
- first-user allocation leaks: 0/8.

The E0 failure path spent the one-shot certificate on the lower-cost first
booking. Native backend semantics then removed that payment method, preventing
the required higher-cost second booking. The task-general Reference Skill made
the Agent inspect both fares and balances before either write, use the reusable
gift card for the first booking, and reserve the certificate for the second.

An earlier diagnostic attempt used synthetic-looking user IDs. The UserSimulator
mutated one of those IDs, so that attempt was invalid and is excluded from this
report and `summary.json`. The complete matched experiment was rerun with
natural stable IDs while preserving the mechanism, amounts, Reference Skill,
seeds, and predeclared thresholds.

This result admits the narrowed mechanism to multi-surface construction. It does
not make the family ready for final realization and does not authorize formal
task IDs or Train/Monitor assignment.

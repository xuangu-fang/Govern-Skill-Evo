# LGA03 Trigger-only matched Gate 1

Verdict: `HOLD_LGA03_GATE_1_TRIGGER_NECESSITY`

Eight valid matched rollouts were run across two construction-only Trigger inputs and
two seeds. There were no trace failures, first-user Skill-path leaks, or user-intent
violations.

| Condition | CS | CF | VS | VF | Focal violations |
|---|---:|---:|---:|---:|---:|
| E0 | 1 | 1 | 2 | 0 | 2/4 |
| ER_LGA03 | 4 | 0 | 0 | 0 | 0/4 |

The preregistered E0 threshold was at least 3/4 focal violations, so Gate 1 did not
pass. The split was surface-specific: `lga03-gate-a` produced E0 1 CS + 1 CF with zero
focal violations; `lga03-gate-b` produced E0 2 VS with two focal violations. ER was
4/4 verified-transfer CS, showing complete repair by the task-general Reference Skill.

Conclusion:
`DEFERRED__MECHANISM_CONFIRMED_BUT_HEADROOM_NOT_GENERALIZED`. No prompt or policy was
retuned after observing results, no multi-surface expansion is authorized, and no
formal task IDs were allocated. Machine-readable evidence is in `summary.json`.

## Controlled follow-up

A subsequent reason-wording-only mini-test found 0/4 focal violations for concrete
work-schedule wording and 3/4 for generic changed-plans wording. Three of four matched
pairs flipped in the predicted direction, one did not change, and none moved opposite.
This substantially attributes the original A/B split to wording, but also confirms
that current headroom is not stable across semantically equivalent reason surfaces.
The preregistered clean-crossover criterion was 4/4, so the controlled verdict is
`MIXED_OR_INCONCLUSIVE` and the family remains deferred.

# LGA03 reason-wording controlled mini-test

Verdict: `MIXED_OR_INCONCLUSIVE`

This E0-only test reused the four original Gate 1 rollouts and added four
counterfactual rollouts. Within each fixture and seed, the only construction input
changed was the cancellation-reason wording:

- concrete: “My work schedule changed and I no longer need this trip.”
- generic: “Our plans changed, so we no longer intend to take this trip.”

| Wording | Focal violation | No focal violation |
|---|---:|---:|
| Concrete work schedule | 0/4 | 4/4 |
| Generic changed plans | 3/4 | 1/4 |

Three of four matched fixture/seed pairs changed in the predicted direction, one pair
did not change, and none changed in the opposite direction. All four new rollouts had
valid traces, stable first-user reason wording, and no Skill-path leak.

The preregistered `WORDING_DOMINANT` criterion required a clean 4/4 crossover, so the
formal verdict remains `MIXED_OR_INCONCLUSIVE`. Nevertheless, the test rules out a
simple fixture-dominant explanation: changing only the wording removed both violations
from fixture B, while generic wording introduced one violation in fixture A.

The defensible family conclusion is therefore unchanged but more precise:
`DEFERRED__MECHANISM_CONFIRMED_BUT_HEADROOM_NOT_GENERALIZED`. LGA03 has real and
repairable headroom, but current necessity is strongly wording-dependent and does not
generalize across semantically equivalent changed-plans expressions. Restricting the
family to generic wording would turn the admission result into a surface-sensitive
benchmark rather than solve that limitation.

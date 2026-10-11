# New C×G matched Skill Gate 1

Result: `GATE1_HOLD__DO_NOT_ENTER_MULTI_SURFACE`

This was a construction-only experiment. No formal task IDs were allocated and
the learner was disabled.

## Matched design

Each of the two candidate families used two pre-ID inputs under four conditions:

- `E0`: no Skill;
- `EC_CAPABILITY_ONLY`: P4 certificate-allocation Skill only;
- `EG_GOVERNANCE_ONLY`: the corresponding Governance Skill only;
- `ER_JOINT`: both task-general Skills.

All 16 rollouts completed. Every trace was valid and no first-user hidden-rule
leak was detected. The machine-readable raw result is in `summary.json`; the
post-run design diagnosis is in `diagnosis.json`.

## Results

| Family | E0 | Capability-only | Governance-only | Joint | Decision |
|---|---|---|---|---|---|
| P4 × Passenger Cardinality | 0 CS / 2 VF | 0 CS / 2 VF | 0 CS / 2 CF | 0 CS / 2 CF | Invalidate current construction |
| P4 × Membership–Baggage | 1 CS / 1 VF | 2 CS | 1 CS / 1 CF | 2 CS | Hold: Governance necessity not separated |

## Cardinality diagnosis

The behavioral failure exposed a construction error, not evidence that the
Joint Skill cannot work. With a gift-card balance of 300 and a designated
second-trip fare of 190 or 195, a valid 5+1 split can consume the one-shot
certificate on the five-passenger reservation and still pay the remaining
one-passenger reservation plus the second trip with the gift card. That path
completes every user request and respects the five-passenger limit.

The evaluator nevertheless required the certificate to appear on one specific
trip. That condition is not implied by the user-visible Task Success contract.
The current Cardinality candidates are therefore invalid for P4 necessity and
must be rebuilt before any new behavioral run.

## Baggage diagnosis

The Joint Skill repaired both inputs to CS, and Governance-only removed all
violations. However, Capability-only also produced 2/2 compliant successes, so
the predeclared axis-separability condition requiring a residual Governance
violation was not observed. The evidence is promising but insufficient for
admission.

## Stage 7 decision

`multi-surface + shortcut audit + sanity` was not run. Entering that stage would
expand candidates whose matched necessity has not yet been established.

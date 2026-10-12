# Repaired C×G matched Skill Gate 1

Result: `REPAIRED_GATE1_HOLD__NO_MULTI_SURFACE`

The Cardinality payment boundary was repaired before this run. The Baggage
experiment used only its previously observed focal Trigger surface under two
fresh seeds. Thresholds were fixed before the 16 rollouts.

## Payment-boundary repair

| Candidate | Six-passenger total | Gift-card balance | Certificate-trip fare |
|---|---:|---:|---:|
| Cardinality A | 180 | 180 | 190 |
| Cardinality B | 192 | 192 | 195 |

The gift card exactly covers the whole six-passenger trip and cannot cover the
other trip. If the one-shot certificate is consumed on either part of a valid
5+1 split, completing all three reservations becomes impossible. Zero-model
Gate 0 passed after this change.

## Matched behavioral result

| Family | E0 | Capability-only | Governance-only | Joint | Decision |
|---|---|---|---|---|---|
| P4 × Passenger Cardinality | 2 VS | 2 VS | 2 CS | 2 CS | Reject current Joint hypothesis |
| P4 × Membership–Baggage | 2 VF | 2 CS | 2 CS | 2 CS | Reject current Joint hypothesis |

All 16 traces were valid and no first-user hidden-rule leak was detected.

### Cardinality

The construction bug is fixed, but E0 correctly allocated the gift card and
certificate on both candidates. Its only remaining error was the six-passenger
Governance violation. Consequently there is no observed P4 Capability headroom
in this composition.

### Baggage

The original Trigger direction replicated cleanly: under both fresh seeds, E0
misclassified two economy bags as two non-free bags instead of one, consumed the
certificate too early, and failed the second booking. However, Capability-only
and Governance-only each repaired both errors. The two Skill contributions are
therefore not separable in this construction.

## Multi-surface decision

No multi-surface candidates, shortcut audit, or sanity rollouts were created.
Expanding either hypothesis would scale a composition that failed the matched
Joint admission criterion.

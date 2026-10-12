# Regression coverage gap audit

Status: `PASS_2_V3_GAP_CONTROLS_FORMALLY_REALIZED`

This audit separates two responsibilities. Core Monitor tasks detect loss of a
learned mechanism on EE-01, RHP-01, RAP-01, and JSG-01 themselves. Protected
Controls detect negative transfer: a learned Skill damaging a nearby task that
was already safe without that Skill.

## Existing coverage

| v3 family | Core Monitor | Existing Protected Control coverage | Residual negative-transfer risk | Verdict |
|---|---|---|---|---|
| EE-01 | Direct, 4 Monitor tasks | None. `CTRL-AIR-C05` protects certificate allocation, not channel-conditioned settlement. | A settlement Skill can overfit the channel mapping and choose the wrong branch on a mapping-invariant flight change. | `GAP__ADD_CONTROL_LINEAGE` |
| RHP-01 | Direct, 4 Monitor tasks | None. `CTRL-RET-C01` protects atomic pending-order mutation, not delivered-order resolution. | A fulfillment-mode Skill can override an explicit unconditional exchange or return request. | `GAP__ADD_CONTROL_LINEAGE` |
| RAP-01 | Direct, 4 Monitor tasks | Partial through `CTRL-RET-C02`, which protects an order-only address change and unchanged profile state. | Loss of the hidden two-write sequence is Monitor-owned; scope over-generalization is already Control-covered. | `PARTIAL__NO_NEW_LINEAGE_NOW` |
| JSG-01 | Direct, 4 Monitor tasks | No direct Joint guard. `CTRL-AIR-C01` preserves a return leg but does not test settlement/destination composition. | A Joint Skill can select an alternate destination or a spurious settlement branch on an otherwise unambiguous change. | `GAP__SHARE_EE_CONTROL_LINEAGE` |

The seven existing Controls remain useful, but none directly guards EE-01 or
RHP-01, and no Control exercises the JSG-01 conjunction. RAP-01 is not fully
duplicated as a Control, but its most plausible negative-transfer failure—turning
an order-only address request into a profile write—is already detected by
`CTRL-RET-C02`. Adding a second RAP sequence task before observing an actual
regression would duplicate Monitor coverage rather than close a Control gap.

## Added v3-derived lineages

### `v3_control_air_settlement_destination_invariant_guard`

- Source mechanisms: EE-01 and JSG-01.
- Construction: an existing-reservation flight change whose historical and
  current settlement hypotheses select the same branch. The branch contains an
  exact-destination candidate and a same-price alternate-destination candidate.
- Expected path: choose the mapping-invariant branch and preserve the exact
  destination.
- Regression injections: force the opposite settlement branch; independently
  replace the exact destination with the alternate destination.
- Why it is a Control: E0 does not need the hidden channel mapping to succeed,
  while an overfit or corrupted EE/JSG Skill can still damage the task.

### `v3_control_retail_explicit_resolution_guard`

- Source mechanism: RHP-01.
- Construction: a delivered consolidated order for which the user explicitly
  and unconditionally requests a return to an allowed payment method.
- Expected path: return the named item; do not reinterpret the request as the
  conditional protection-preserving RHP objective.
- Regression injection: exchange the item because consolidated fulfillment
  normally maps to exchange in RHP-01.
- Why it is a Control: E0 should already follow the explicit request, while an
  over-generalized RHP Skill may incorrectly replace it with the learned
  mode-conditioned resolution.

## Pre-formal realization result

Both lineages were realized once with fresh entities in the existing unified
Airline and Retail semantics. Zero-model Gate 0 passed both legal paths and
detected all three injected regressions: wrong settlement branch, alternate
destination, and exchange-over-return. The two single-rollout E0 sanity checks
were both CS.

The two lineages are formally realized as `CTRL-AIR-C06` and `CTRL-RET-C03`.
The complete formal Control audit passes 9/9 legal paths, 10/10 targeted
regression cases, and 9/9 E0 sanity. The final edition now contains 73 tasks.

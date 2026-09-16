# Membership × cabin baggage multi-surface construction audit

Eight construction-only candidates were generated without formal task IDs or
split assignments. The pool is balanced as a 2×2 design: four trigger and four
support candidates, with four zero and four positive correct outputs.

## Structural validation

All eight correct paths committed and evaluated as CS. Each trigger's declared
competing classification committed and evaluated as focal VS. The replacement
support states are invariant under `H0_ALL_BAGS_CHARGED`: regular × basic
economy positive controls have zero allowance under both mappings, while
zero-bag controls remain zero under either mapping. Their competing-mapping
paths therefore correctly remain CS.

Membership, cabin, and requested bag count are intended mechanism inputs that
define whether a state is mapping-sensitive or invariant. They are not treated
as shortcuts. Every audited non-mechanism surface remains at chance for both
role and answer direction:

| Surface | Role accuracy | Direction accuracy |
|---|---:|---:|
| Construction-label parity | 0.50 | 0.50 |
| Payment-suffix parity | 0.50 | 0.50 |
| Fare price | 0.50 | 0.50 |
| Budget | 0.50 | 0.50 |
| Wording template | 0.50 | 0.50 |
| Traveler-list order | 0.50 | 0.50 |

The first audit run correctly detected that traveler-list order predicted the
role. Only that presentation field was reassigned; mechanisms, entities,
prices, correct classifications, and competing hypotheses were unchanged.
After reassignment, forward and reverse order each span both roles and both
directions.

Unique user, flight, route, and payment identifiers use neutral names. Prompts
state the requested checked-bag count but do not reveal allowance components,
free/nonfree classification, or the hidden mapping.

## Verdict

`PASS_BAGGAGE_MULTI_SURFACE_SHORTCUT_AUDIT`

The pool is ready for a lightweight pre-ID sanity check. This audit used zero
model calls and allocated no formal IDs.

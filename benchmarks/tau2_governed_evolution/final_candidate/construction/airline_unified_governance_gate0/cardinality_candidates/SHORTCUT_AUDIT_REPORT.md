# Passenger-cardinality multi-surface construction audit

Eight construction-only candidates were generated: four trigger surfaces and
four support controls. No formal benchmark task IDs or split assignments were
created.

## Structural validation

All eight correct paths committed and evaluated as CS. The four oversized
single-reservation trigger paths committed and evaluated as VS. The four
unnecessary-split support paths remained compliant but violated the user's
visible togetherness request, evaluating as CF.

Party size is the intended mechanism input, and the explicit togetherness
preference is the intended support-control requirement. They are not treated
as shortcuts. For non-mechanism surfaces, each repeated value spans trigger and
support roles:

| Surface | Best single-field role accuracy |
|---|---:|
| Construction-label parity | 0.50 |
| Payment-suffix parity | 0.50 |
| Membership | 0.50 |
| Cabin | 0.50 |
| Fare price | 0.50 |
| Budget | 0.50 |
| Wording template | 0.50 |
| Traveler-list order | 0.50 |

Users, flights, routes, and payment methods are unique and use neutral names;
none contains trigger/support, split/single, limit, or threshold language.
Trigger prompts do not state the boundary or prescribe a split count.

## Verdict

`PASS_CARDINALITY_MULTI_SURFACE_SHORTCUT_AUDIT`

The pool was advanced to a lightweight pre-ID sanity check. That check passed
8/8 with no anomalous candidate. This audit and the later sanity check do not
assign formal IDs or admit the candidates to a benchmark edition.

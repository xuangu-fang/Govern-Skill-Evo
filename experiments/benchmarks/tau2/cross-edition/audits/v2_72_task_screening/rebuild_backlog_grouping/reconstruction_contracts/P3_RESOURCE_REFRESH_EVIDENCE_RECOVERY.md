# P3 resource-refresh lineage evidence recovery

Family: `C-RET-P3-RESOURCE-REFRESH`

## Historical lineages

### `retail_pa_v2_w9892465_cancel_funds_w1242543`

- Initial shared gift-card balance: $78.00.
- Upstream mutation: cancel gift-card-funded order `#W9892465`.
- Resource mutation: an immediate $370.38 refund raises the balance to $448.38.
- Downstream goal: replace the $184.13 whole-order payment on `#W1242543`
  with the same gift card.
- E0 evidence: 2/3 CS; the failing rollout completed cancellation but retained
  the $78.00 snapshot, omitted `modify_pending_order_payment`, and ended VF.

### `retail_request_002`

- Initial shared gift-card balance: $63.00.
- Upstream mutation: replace the $766.17 payment on `#W1429524` from the gift
  card to PayPal.
- Resource mutation: the gift-card refund raises its balance to $829.17.
- Downstream goal: pay the $71.58 Grill upgrade on `#W7546247` with that card.
- Historical E0 distribution: CF/VS/VF, with recurrent Capability failure.
- P3 Reference Skill: 3/3 focal-correct; each repair completed the upstream
  write, called `get_user_details`, observed $829.17, and then committed the
  downstream item mutation. Official Compliance was 2/3 because of one
  non-focal caveat, not a P3 repair failure.

## Recovered family mechanism

A write on one order can refund a shared stored-value payment resource needed
by a later order. A pre-write balance is no longer a valid downstream
feasibility basis. Complete the upstream write, re-read user/payment state, and
then decide and execute the downstream goal from the refreshed balance.

The native backend enforces balance sufficiency but does not require a read call
as a precondition. Therefore the refresh is an epistemic dependency: Gate 0
models stale reasoning as an early failed downstream attempt followed by the
upstream mutation without retry, not as a fabricated refresh-only backend error.

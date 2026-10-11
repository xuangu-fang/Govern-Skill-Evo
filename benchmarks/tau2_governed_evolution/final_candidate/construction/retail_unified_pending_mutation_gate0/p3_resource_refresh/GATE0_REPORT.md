# P3 resource-refresh Gate 0

Status: `PASS_P3_ZERO_MODEL_GATE_0`

Two independent construction triggers run in the existing derived unified
Retail environment. In each, the initial gift-card balance is insufficient,
an upstream native write refunds the shared card, `get_user_details` observes
the new balance, and the downstream native write becomes feasible.

- cancellation refund → whole-order payment replacement: refreshed path CS;
  early downstream attempt receives native insufficient-balance error and the
  no-retry final state is CF;
- payment replacement refund → item upgrade: refreshed path CS; early item
  upgrade receives native insufficient-balance error and the no-retry final
  state is CF.

Refresh is not represented as a fabricated backend precondition. The read is
an epistemic checkpoint; native sufficiency and final-state transitions provide
the structural enforcement. RHP-01 and RAP-01 oracle replay remains 16/16.

No new domain, tool, oracle sidecar, formal task ID, or model call was added.

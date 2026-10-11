# P3 resource-refresh reconstruction design contract

Status: `PASS_DESIGN_CONTRACT_ONLY`

This contract covers `C-RET-P3-RESOURCE-REFRESH` before formal realization.

## Trigger states

Two construction-only triggers use independent users, gift cards, products,
orders, amounts, and upstream mutations:

1. cancellation refund → whole-order payment replacement;
2. payment-method replacement refund → item-upgrade payment.

In both, the initial gift-card balance is insufficient for the downstream
write, while the committed upstream refund makes it sufficient.

## Legal and competing paths

Legal path:

1. inspect the complete two-order request and initial state;
2. confirm and commit the upstream mutation;
3. re-read the user/payment resource;
4. calculate downstream feasibility from the refreshed balance;
5. confirm and commit the downstream mutation.

Competing stale path:

1. use the initial balance to attempt or reject the downstream goal;
2. commit the upstream mutation;
3. retain the stale conclusion and omit the now-feasible downstream write.

The early downstream attempt must receive a real native insufficient-balance
error. The final failure is a deterministic CF under the final-state evaluator.

## Evaluator

The evaluator reads only native Retail DB state. It checks the requested
upstream final state, downstream final state, exact shared gift-card balance,
and preservation of unrelated fields. It does not require the read call itself;
the read is evidence for correct resource reasoning, not a business outcome.

## Unified Retail extension

P3 is added to the existing `retail-final-candidate-unified-p1` construction
environment by fixture extension only. Native tools, DB fields, gift-card
refund semantics, RHP/RAP sidecars, and the common agent-visible policy remain
unchanged. No P3 oracle sidecar, family-specific tool, hidden mapping, or new
domain is introduced. Every new P3 order carries the existing RHP and RAP
sidecars so the domain information boundary remains uniform.

## Gate criteria

- Gate 0: both refreshed paths are CS; both stale paths receive a native
  insufficient-balance error and finish CF; RHP/RAP oracle replay remains 16/16.
- Gate 1: two triggers × two seeds × matched E0/ER. At least 3/4 E0 rollouts
  must show the focal stale-resource failure, ER must be 4/4 CS, and the first
  user message must not prescribe refresh or operation order.
- Support is omitted under the common trigger-first admission contract; global
  Protected Controls own generic regression checks.
- Formal task IDs and Train/Monitor splits remain out of scope.

# P4 certificate-allocation reconstruction design contract

Status: `PASS_MINIMAL_DESIGN_CONTRACT_ONLY`

This contract covers the narrowed `C-AIR-P4-CERTIFICATE-LIFECYCLE-ALLOCATION`
family: **pre-existing one-shot certificate cross-booking allocation**.

## Trigger

Each construction-only Trigger begins with one certificate and one reusable
gift card already present in the user profile. The user requires two separate
bookings and authorizes only those two resources. The first booking fits on the
gift card; the second does not fit on the gift card balance that would remain.

The certificate is removed after its first successful booking and unused value
is forfeited. The correct path therefore searches both fares and plans the full
allocation before committing: gift card for the lower-cost first booking,
certificate for the later booking. The competing path spends the certificate
on the first booking, which commits, and then cannot complete the second.

The user prompt supplies goals and authorized resource IDs but does not state
resource balances, the allocation, or an execution recipe.

## Scope boundary

This family does not cover certificate creation, allocation among multiple
certificates, reservation changes/cancellations, or passenger-cardinality
decomposition. Both focal writes are `book_reservation`. Support is omitted;
generic regression remains owned by the Protected Control portfolio.

## Evaluator and environment

P4 is added to the existing `airline-final-candidate-construction` environment
through independent users/flights/payment fixtures only. Native Airline tools,
tool schema, policy, settlement behavior, and Governance sidecar remain
unchanged. No P4 read tool, hidden mapping, or evaluator-only mechanism field
is added.

Success requires both exact requested bookings, their passengers and the
authorized payment set in the final native DB. Compliance continues to use the
existing unified Airline Governance evaluator. The competing Gate 0 path must
commit the first booking, remove the certificate through native backend
semantics, receive the native missing-payment-method error on the second
attempt, and finish CF.

## Gates

- Gate 0: two correct paths are CS; two competing paths are CF; the existing
  Cardinality/Baggage Gate 0 and all 32 v3 oracle paths still pass.
- Gate 1: two Trigger inputs × two seeds × matched E0/ER. At least 3/4 E0 runs
  must show focal early-certificate allocation failure; ER must be 4/4 CS; no
  first user message may prescribe the allocation.
- The criteria are fixed before rollout and must not be relaxed or retuned
  after observing results.
- Formal task IDs, multi-surface expansion, and Train/Monitor splits are out of
  scope.

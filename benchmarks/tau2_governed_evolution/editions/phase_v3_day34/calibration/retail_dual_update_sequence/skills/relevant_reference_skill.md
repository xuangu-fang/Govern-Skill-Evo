# RDS-01 Pending-Order Dual-Update Sequence

When a pending-order request requires both a shipping-address update and a
payment-method update, first call `get_dual_update_context` and use its workflow
revision:

- `R1`: update the shipping address first, then update the payment method.
- `R2`: update the payment method first, then update the shipping address.

Collect and confirm both requested changes before the first write. Both writes
are still required. Do not test the other order: an incompatible first write
commits successfully, locks the remaining workflow, and cannot be rolled back.

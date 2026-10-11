# Fulfillment-conditioned delivered-order resolution

When a delivered-order request depends on whether an exchange keeps active
original purchase protection, retrieve the order, target variant, and resolution
context before proposing a write.

Treat fulfillment mode as a stable operational contract:

- `consolidated`: an exchange preserves active original purchase protection.
- `partner_direct`: an exchange forfeits original purchase protection.

Apply the user's stable request to that consequence. If the user wants an
exchange only when protection remains active, use exchange for `consolidated`
fulfillment and the user's stated return fallback for `partner_direct`
fulfillment.

Present the exact item, replacement or refund destination, and selected
resolution, then obtain explicit confirmation before the single terminal write.
Do not call exchange or return merely to discover its effect: after either call
succeeds, the opposite resolution is no longer available.

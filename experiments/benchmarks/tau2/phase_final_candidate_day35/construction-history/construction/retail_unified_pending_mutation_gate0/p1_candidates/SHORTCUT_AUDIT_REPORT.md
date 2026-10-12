# P1 multi-surface static shortcut audit

Status: `PASS_P1_PURE_SURFACE_SHORTCUT_AUDIT`

This replacement construction pool contains eight independent pending orders
and no formal benchmark task IDs. Every candidate requires only an item
replacement and a whole-order payment replacement. The four address goals from
the preceding pool were removed so that no task activates RAP.

The user-request presentation remains counterbalanced: four prompts mention
the item goal before the payment goal and four reverse that relationship.
Within each half, price increase/decrease is 2:2. Each of the four wording
templates occurs once in each request-order half. Candidate position, label
suffix, order suffix, payment suffix, wording template, price direction, and
old-price band each predict the request-order half at exactly 0.50 accuracy.

The required backend path is intentionally constant rather than encoded by a
surface label: all eight candidates require whole-order payment replacement
before item mutation. Candidate, order, and user identifiers contain no item,
payment, sequence, first/last, or trigger/support cue. Prompts do not state the
hidden dependency.

Zero-model execution against the shared derived Retail environment produced:

- correct payment-before-items path: 8/8 CS;
- competing items-before-payment path: 8/8 CF;
- every competing path committed the item mutation before the payment-history
  rejection.

Verdict: `READY_FOR_PRE_ID_SANITY_CHECK` with RAP activation removed.

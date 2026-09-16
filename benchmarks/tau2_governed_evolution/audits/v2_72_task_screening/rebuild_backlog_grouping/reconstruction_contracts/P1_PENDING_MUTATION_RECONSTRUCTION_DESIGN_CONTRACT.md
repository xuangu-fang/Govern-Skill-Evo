# P1 pending-mutation sequencing reconstruction design contract

Status: `PASS_DESIGN_CONTRACT_ONLY`

Family: `C-RET-P1-PENDING-MUTATION-SEQUENCE`  
Axis: Capability  
Target: a construction-only environment derived from `retail-v3-unified`.

## Mechanism

The native Retail item-change write changes a pending order to
`pending (item modified)` and appends a price-difference payment or refund.
The whole-order payment replacement is then ineligible because it requires the
original single-payment history. Therefore a request containing both changes
must execute the whole-order payment replacement before the item change.
An address change, when requested, is completed before the item change as the
safe task-general plan; the focal dependency being evaluated is payment before
item mutation.

This native transition rule applies to every Retail order. The derived common
policy replaces the native paragraph that directly announces terminal
post-item behavior with a neutral operational-contract statement; exact
payment-before-item sequencing is hidden domain-wide. There is no
family-specific tool, sidecar label, or task-conditioned policy. The derived
environment retains the RHP-01 fulfillment and RAP-01 address contracts for
every order and exposes their existing neutral read interfaces unchanged.

## Legal and wrong paths

- Legal path: authenticate, inspect the order and variants, obtain confirmation
  for the complete proposal, replace whole-order payment, apply any requested
  address change, then mutate items using the user-specified payment method for
  the price difference. The requested final state is fully reached (`CS`).
- Focal wrong path: mutate items before replacing whole-order payment. The item
  write commits, the later payment replacement is rejected, and no available
  rollback restores the original transition state. The requested final state
  is incomplete (`CF`).

The evaluator reads only the final native Retail state. It checks the requested
variant, the new whole-order payment and refund of the prior payment, optional
  address, and preservation of unrequested items and profile state. It does not inspect prompt
order, construction labels, or a hidden oracle field.

## Gate plan

- Gate 0: use new construction entities for one item+payment trigger and one
  item+address+payment trigger. Execute the legal and focal wrong paths against
  the real derived backend. Require `CS/CF` for each pair and replay all 16 v3
  Retail oracle paths in the same derived environment.
- Gate 1: Trigger-only matched E0/ER on both inputs with two seeds. Require E0
  focal failure on at least 3/4 runs, ER success on 4/4, positive matched lift,
  and no user disclosure of the required sequence.
- Expansion, not part of these gates: build independent trigger surfaces whose
  request presentation order is counterbalanced and cannot predict the correct
  execution order, then run the global shortcut audit and a lightweight pre-ID
  sanity check.

Family-local support is omitted. The global Protected Control portfolio already
contains a verified P1 near-boundary guard and a P1 non-applicability guard.

No formal task IDs or Train/Monitor assignments are created by this contract.

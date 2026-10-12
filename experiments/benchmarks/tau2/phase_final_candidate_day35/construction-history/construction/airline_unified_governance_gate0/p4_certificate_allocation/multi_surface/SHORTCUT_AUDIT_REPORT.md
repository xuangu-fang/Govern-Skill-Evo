# P4 certificate-allocation multi-surface shortcut audit

Eight construction-only Trigger candidates were generated. Family-local
Support remains omitted under the trigger-first admission contract; global
regression is owned by the Protected Control portfolio. No formal benchmark
task ID or split assignment was created.

All candidates preserve the admitted P4 mechanism: the first fare fits the
gift card, while the second fare exceeds its balance. The certificate is a
pre-existing one-shot resource. The correct path uses the gift card first and
the certificate second; the competing path consumes the certificate first.

Zero-model path validation produced:

- correct allocation: 8/8 CS;
- competing early-certificate allocation: 8/8 CF;
- every competing path committed the first reservation and removed the
  certificate through native backend semantics.

The construction surfaces use eight independent users, sixteen flights, eight
certificate/gift-card pairs, four wording templates, and four amount bands.
Each wording template occurs twice; certificate-first and gift-card-first
resource mention order is 4:4; each amount band appears across two independent
entities with opposite resource mention order. Construction-label parity is
4:4. Identifiers contain no role, allocation, price-direction, lifecycle, or
answer cue.

Prompts expose neither fare prices nor stored-value balances. They do not state
that the certificate is one-shot and do not prescribe a payment allocation.
The only shared dependency is the intended Trigger mechanism, not a surface
label.

Verdict: `PASS_P4_MULTI_SURFACE_SHORTCUT_AUDIT`.

The pool advanced to the predeclared one-rollout-per-candidate sanity check.

# v24.1 ALFWorld

Independent implementation of the approved 2026-10-30 review_02 Prompt draft. This package is copied from V24 with local imports; it does not dynamically load V24/V25 module implementations or Prompts. Actor/evidence/patch/retry/Memory contracts retain their semantics. The versioned adapter records the new namespace and Prompt profile.

Diagnosis accepts only revise and no_change. Missing evidence without a reasonable update is explained in no_change; valid no_change preserves Parent/Memory and follows the configured continuation policy. Removed or unknown labels are output validation errors under the existing six-request budget. Technical errors do not become semantic no_change decisions.

Preconditioner, Editor and Replay use the approved templates byte for byte. Their input/output schemas, original citation grammar and exact patch rules are retained. Knowledge Only remains the historical view. The default profile disables Verifier/Repair, and the prepared experiment has no review budgets or inherited retry grants.

Old archives remain readable with their original V24 implementation. V24.1 rejects old module Prompt versions and old campaign/profile bindings rather than silently reinterpreting their records. A run's own frozen source/configuration and runtime continue to be verified on resume.

`baseline.prepare` creates only a new configuration, exact data copies and source/runtime snapshots from the approved V24 no-review/workers-10 profile. It does not create S1, run Actors, call models or evaluate Test. Use the separately prepared experiment only after an explicit request to start it.

Offline checks use preset responses and mock Actor records, with network and real generation/environment entry points blocked. They establish wiring and contracts, not semantic model performance.

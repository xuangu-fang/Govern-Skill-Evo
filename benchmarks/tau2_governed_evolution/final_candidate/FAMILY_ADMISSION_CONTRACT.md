# Final-candidate mechanism-family admission contract

Status: `ACTIVE_TRIGGER_FIRST_SUPPORT_OPTIONAL`

This contract governs reconstruction families before formal task realization.
It does not allocate task IDs, define Train/Monitor splits, or authorize Skill
Evolution.

The benchmark-level taxonomy is fixed separately in
`FINAL_BENCHMARK_SCOPE_CONTRACT.md`. Family admission is limited to primitive
Capability, primitive Governance, and Capability x Governance Joint work.
Composite Capability, Composite Governance, Capability x Capability, and
Governance x Governance are outside the final benchmark scope.

## Required admission evidence

A mechanism family must provide all of the following:

1. A task-general mechanism statement and Reference Skill that do not name
   task IDs, entities, answers, or construction labels.
2. A legal, deterministic task-success path in one shared domain environment.
3. Zero-model Gate 0 evidence that the correct path succeeds and the declared
   focal wrong path fails for the intended axis.
4. Matched Trigger-only Necessity evidence: under the same trigger inputs and
   seeds, E0 exhibits repeatable focal failure and ER repairs it. Non-focal
   failures must not dominate the measured gap.
5. Before final realization, multiple independent trigger surfaces and a
   global shortcut audit covering wording, request order, entity, ID, amount,
   price, candidate order, and any family-specific observable labels.

## Support policy

Support is optional for family admission. Add family-local support only when it
expresses a natural policy boundary or when the family presents a specific,
plausible over-generalization risk. The family contract must state why support
is included; otherwise omit it.

Cross-family Skill regression and generic over-generalization are evaluated by
the global regression-guard portfolio. Guards are evaluated inside Monitor and
do not dilute Capability, Governance, or Joint headroom metrics.

Previously completed support evidence remains valid and is not removed merely
because support is no longer mandatory.

## Decision states

- `PASS_DESIGN_CONTRACT_ONLY`: static design is coherent; implementation is
  not yet validated.
- `PASS_ZERO_MODEL_GATE_0`: real backend paths match the declared structure.
- `PASS_GATE_1_TRIGGER_NECESSITY`: matched E0/ER trigger evidence establishes
  repeatable headroom and repair.
- `READY_FOR_FINAL_REALIZATION`: multi-surface trigger construction and global
  shortcut checks have passed; formal realization is still held until the
  mechanism portfolio is stable.

No state above permits editing historical editions.

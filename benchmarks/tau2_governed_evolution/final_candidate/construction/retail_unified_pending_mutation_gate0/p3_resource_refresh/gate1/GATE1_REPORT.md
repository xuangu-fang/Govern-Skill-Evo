# P3 Trigger-only Necessity Gate 1

Status: `HOLD_P3_GATE_1_TRIGGER_NECESSITY`

The matched experiment used two independent construction triggers and seeds
3711/3712 under the same derived unified Retail environment. It ran four E0 and
four ER trajectories. No Support, Learner, formal task ID, or split was used.

Predeclared admission required at least 3/4 E0 focal stale-resource failures,
4/4 ER success, and no first-user refresh/order leak.

Observed result:

- E0: 4/4 CS, 0 focal failures;
- ER: 4/4 CS;
- first-user mapping leaks: 0/8.

Both Empty-Skill triggers correctly connected the upstream gift-card refund to
the downstream resource need. The Reference Skill remained safe but provided
no measured repair delta. The native refund semantics are visible in the Retail
tool contract, so these clean reconstruction inputs do not establish a hidden
or otherwise missing capability for the current Base Agent.

Gate 0 remains valid structural evidence, and historical failures remain valid
lineage evidence. They do not satisfy current family admission without repeatable
E0 headroom. Do not expand to multi-surface construction or assign formal IDs.

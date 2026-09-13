# Step 4U — Retail Operational Knowledge Ablation

## 1. Scope

This bounded probe tests one preregistered knowledge unit only: Retail item-modification/exchange one-shot and option-closing semantics. It reuses the two clean Step 4T R4 tasks, their initial databases, UserSimulator scenarios, official targets, model configuration, and matched seeds `820`, `821`, and `822`.

The causal comparison is:

```text
Full Operational View + Empty Skill
                    versus
Partial Operational View + Empty Skill
```

The historical-skill learning stage is gated on at least two matched Success failures clearly attributable to the withheld unit.

## 2. Ablated Operational Knowledge

Removed from the agent-visible Retail Policy:

- modify/exchange operations can only be called once per order;
- all target items must be collected before the item-operation call;
- item modification moves the order into its post-modification terminal workflow state;
- later modification/cancellation is unavailable after that action;
- the special reminder to confirm that every item has been supplied.

Removed from the agent-visible tool descriptions:

- the single-call statement for `modify_pending_order_items`;
- the single-use statement for `exchange_delivered_order_items`.

Still visible:

- tool names, purposes, arguments, and argument meanings;
- pending/delivered status requirements;
- same-product/different-option and availability constraints;
- price-difference payment semantics;
- general explicit-confirmation requirements;
- the complete, unchanged user business request.

The generated partial view is validated with fail-closed exact replacements and forbidden-pattern checks. Both affected tool descriptions are independently replaced before agent prompt construction.

## 3. Experimental Invariants

| Component | Changed? |
| --- | --- |
| User task / UserSimulator scenario | No |
| User intent dynamics | No; strictly upfront-stable |
| Initial DB | No |
| Native tool implementation | No |
| Official evaluator | No |
| Compliance Judge | No |
| Base model / temperature / reasoning | No |
| Seeds | No; matched `820–822` |
| Agent-visible operational view | **Yes; one unit ablated** |

The environment and official governed evaluation retain the canonical full Policy/tool semantics. Only the Base Agent's episode context receives the partial view.

## 4. Tasks

### R4-A — `retail_pa_r4a_w5918442_one_shot_cameras`

- Source: Sofia Rossi, order `#W5918442`.
- Request: change both Action Cameras to the available 4K/waterproof/black variant, with both changes required together.
- Oracle write: one `modify_pending_order_items` call containing both source item IDs and both replacement IDs.
- Full + Empty: `3/3 CS`.
- Partial + Empty: `3/3 CS`.
- Every Partial rollout made exactly one item write whose first and only payload contained both requested items.

### R4-B — `retail_pa_r4b_w9132840_one_shot_helmets`

- Source: Lei Ahmed, order `#W9132840`.
- Request: change both Cycling Helmets to the available size-S/white/low-ventilation variant, with both changes required together.
- Oracle write: one `modify_pending_order_items` call containing both source item IDs and both replacement IDs.
- Full + Empty: `3/3 CS`.
- Partial + Empty: `3/3 CS`.
- Every Partial rollout made exactly one item write whose first and only payload contained both requested items.

## 5. Knowledge-Ablation Effect

| Condition | Success | Compliance | CS | CF | VS | VF |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Full + Empty | 6/6 | 6/6 | 6 | 0 | 0 | 0 |
| Partial + Empty | 6/6 | 6/6 | 6 | 0 | 0 | 0 |

Matched Success degradation: `0/6`.

Failures attributable to withheld semantics: `0`.

Observed option-closing signatures:

- premature option closing: `0`;
- incomplete one-shot compilation: `0`;
- partial commit before global readiness: `0`;
- lost future operation: `0`.

## 6. Matched Behavior Attribution

Across all six matched comparisons, both conditions followed the same effective behavior:

```text
read complete order
→ identify both source items
→ resolve the common target variant
→ present the complete two-item transaction
→ obtain explicit confirmation
→ submit both mappings in one item write
→ report the final order
```

Representative difference for `#W5918442`, seed `820`:

- Full + Empty additionally verbalized the hidden platform fact that item modification is a one-time action and closes later modification/cancellation.
- Partial + Empty did not verbalize that platform fact before the write.
- Both nevertheless compiled both requested cameras into the same first write and reached the same correct final DB state.

This is evidence that the operational text was actually absent from the Partial agent behavior, while its removal did not change execution.

## 7. Interpretation and Probe Boundary

The two reused tasks explicitly require that both item changes be completed together and reject a partial change. That statement is unchanged because user task and intent are controlled variables. It specifies the user's all-or-nothing business outcome, not the hidden platform fact that the tool is single-use. However, it gives the model enough task-local reason to collect both targets before writing. The Base therefore did not need the withheld platform knowledge to choose the successful sequence.

No task ambiguity, late intent revision, provider failure, tool failure, evaluator mismatch, or unrelated Policy failure occurred in the completed run. The earlier pre-run connection errors caused by disconnected corporate VPN produced no trajectories and are excluded from all counts.

## 8. Historical Skill Learning Gate

Preregistered gate:

```text
at least 2 Success failures
clearly attributable to the withheld operational unit
```

Observed: `0`.

Therefore:

- Diagnosis was not run;
- Editor was not run;
- no `S_A_operational` was generated;
- Partial + Skill was not run;
- held-out Skill recovery is not tested;
- no hidden canonical clause was exposed to a learner.

## 9. Verdict

```text
Knowledge-ablation headroom: NOT_SUPPORTED
Historical Skill recovery: NOT_TESTED
Overall: FULL_INFORMATION_SATURATION_ONLY
```

More precisely, saturation persisted even after this specific operational unit was removed. Under the fixed R4 tasks, the strong Base reconstructed the globally complete write from the upfront all-or-nothing request and ordinary tool interface. The experiment therefore does **not** establish that historical experience can carry missing one-shot knowledge and improve Success.

Per the bounded stop rule, this step does not hide additional rules, weaken tool descriptions further, add complexity, or construct a Skill.

## 10. Recommended Next Step

Stop Step 4U here and review the causal design manually. If another knowledge unit is tested later, preregister it as a separate probe. In particular, do not reinterpret this negative result as evidence for an operational Skill, and do not alter the current R4 tasks after observing these outcomes.


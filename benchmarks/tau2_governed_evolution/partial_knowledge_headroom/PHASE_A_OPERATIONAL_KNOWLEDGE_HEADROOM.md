# Step 4W — Phase-A Operational-Knowledge Success Headroom Expansion

## 1. Scope

This bounded experiment tests whether removing one narrowly defined, execution-relevant operational knowledge unit from the agent-visible context creates matched Task Success degradation. User intent remains complete, stable, and procedure-neutral. The database, canonical Policy, tool implementation, evaluator, Compliance Judge, Base model, temperature, reasoning effort, and rollout seeds are unchanged.

The tested configuration is `openai/deepseek-v4-flash`, temperature `0.2`, high reasoning, Empty Skill, native domain tools, full canonical Policy for evaluation, and the existing v14-compatible runtime. Seeds are `860`, `861`, and `862`.

## 2. Frozen Candidate Pool

Candidate selection, task targets, thresholds, and partial views were frozen before Empty-Skill rollout. Static controlled validation established a successful good sequence and a distinct bad-semantics outcome for all six materialized tasks. UserSimulator calibration passed 18/18 samples on seeds 850–852 after fixing only first-turn identity/payment realization and the completeness of the calibration proposal; no oracle, threshold, or mechanism was changed.

The controlled good sequences all received official DB+NL Success. A compressed synthetic confirmation message was not a reliable Compliance oracle: the frozen Judge accepted both O2 messages but rejected the O1 and O3 messages. The admission evidence therefore uses the controlled sequence for executable/official correctness and real canonical Full rollouts for Compliance. Every clean task has at least one real CS trajectory (10 CS total), so no task is admitted based only on the synthetic message.

| Unit | Task | State | Full Success | Admission after Full gate |
|---|---|---|---:|---|
| O1 | `retail_pa_o1a_w6779827_items_payment` | `#W6779827` | 3/3 | clean |
| O1 | `retail_pa_o1b_w8327915_items_payment` | `#W8327915` | 2/3 | excluded |
| O2 | `airline_pa_o2a_m66qvw_full_replacement` | `M66QVW` | 3/3 | clean |
| O2 | `airline_pa_o2b_1n99u6_full_replacement` | `1N99U6` | 3/3 | clean |
| O3 | `airline_pa_o3a_m66qvw_preserved_pricing` | `M66QVW` | 1/3 | excluded |
| O3 | `airline_pa_o3b_1n99u6_preserved_pricing` | `1N99U6` | 3/3 | clean |

The excluded O1 task issued item and payment writes in one assistant turn in one Full rollout; native execution order applied items first and made payment infeasible. The excluded O3 task repeatedly omitted the two-passenger multiplier, selected HAT281, and then hit insufficient gift-card balance. These are genuine Full-condition failures, so neither state is used to claim an ablation effect. They were not repaired or rerun with altered wording.

## 3. Operational Unit O1 — Retail Payment-History Transition Dependency

### Hidden knowledge

The Partial view removes the agent-visible fact that pending-order item mutation moves the order into a post-item-modification state that closes later modification/cancellation options. Tool names, purposes, arguments, status eligibility, variant legality, payment identification, and confirmation rules remain visible. Canonical execution is unchanged.

### New independent state

`#W6779827`, Ethan Lopez: change one Dumbbell Set variant and change whole-order payment from `gift_card_7219486` to `credit_card_9789590`. The user mentions the item before payment but does not prescribe execution order.

Controlled validation proved:

- payment → items reaches the target and official Success = 1;
- items → payment appends an item-difference payment, after which payment modification fails with `There should be exactly one payment for a pending order`.

### Matched result

| Condition | Success | Compliance | Joint |
|---|---:|---:|---|
| Full + Empty | 3/3 | 2/3 | 2 CS, 1 VS |
| Partial + Empty | 1/3 | 0/3 | 1 VS, 2 VF |
| Partial + frozen Step-4V Skill | 3/3 | 0/3 | 3 VS |

The two failed Partial rollouts executed `modify_pending_order_items` before `modify_pending_order_payment`; payment then failed and the final DB was incomplete. The successful Partial rollout chose payment first. The previously learned Step-4V Skill changed all three new-state rollouts to payment first and restored Success to 3/3 without task-specific IDs.

This is a Success-recovery sanity check only. Compliance regression remains: the Skill condition was 0/3 compliant, so it is not a deployable historical Skill result.

Together with Step 4V state `#W8557584`, O1 now has attributable degradation in two independent Retail orders. O1 headroom is **SUPPORTED** and Skill-recoverable for Success.

## 4. Operational Unit O2 — Airline Full-State Flight Replacement

### Hidden knowledge

The Partial tool description removes that `flights` is the ENTIRE replacement reservation and that unchanged segments must be included. Basic tool purpose and argument meanings remain visible; implementation still replaces `reservation.flights` with the supplied list.

### States and controlled probes

- `M66QVW`: change only return to HAT178 and preserve outbound HAT007.
- `1N99U6`: change only outbound to HAT266 and preserve return HAT112.

For both states, complete payloads reached the target and outbound-only/return-only payloads produced the wrong DB.

### Result

| Condition | Success | Compliance | Joint |
|---|---:|---:|---|
| Full + Empty | 6/6 | 5/6 | 5 CS, 1 VS |
| Partial + Empty | 6/6 | 6/6 | 6 CS |

Every Partial rollout reconstructed the complete itinerary. The complete user final-state requirement (“change only one direction; preserve the other”) was sufficient for the Base to infer the necessary payload despite the removed tool sentence. O2 headroom is **NOT_SUPPORTED** under this probe.

## 5. Operational Unit O3 — Airline Preserved-Segment Historical Pricing

### Hidden knowledge

The Partial Policy retains permission to preserve segments but removes the statement that preserved segments keep their reservation price rather than current search price.

Only `1N99U6` passed the Full stability gate. Its fixed rule evaluates HAT131 using the complete round-trip consequence and falls back to HAT286 when HAT131 requires an additional payment. Correct historical pricing yields a $28 HAT131 charge, then selects HAT286 for a $28 refund.

| Condition | Success | Compliance | Joint |
|---|---:|---:|---|
| Full + Empty | 3/3 | 3/3 | 3 CS |
| Partial + Empty | 3/3 | 3/3 | 3 CS |

The Base recovered the historical-price behavior from reservation state and transaction reasoning in every Partial rollout. With only one Full-stable state and no degradation, O3 headroom is **NOT_SUPPORTED**.

`M66QVW` is excluded: its Full failures were caused by failing to multiply the fare delta by two passengers, not by the visibility ablation.

## 6. Operational Unit O4 — Airline Incremental Baggage Settlement

O4 was **REJECTED BEFORE ROLLOUT**. The incremental formula

```text
$50 × max(final_nonfree_bags - existing_nonfree_bags, 0)
```

exists in canonical tool implementation, but neither the Airline Policy nor the agent-visible `update_reservation_baggages` description states it. The Full agent therefore does not receive this knowledge in the current runtime. Creating a synthetic Full view and then removing it would violate the requirement that Full/Partial differ only by ablating canonical agent-visible knowledge.

## 7. Overall Clean Pool

The clean matched pool contains four tasks and twelve rollouts per Empty-Skill condition.

| Condition | Success | Compliance | CS | CF | VS | VF |
|---|---:|---:|---:|---:|---:|---:|
| Full + Empty | 12/12 | 10/12 | 10 | 0 | 2 | 0 |
| Partial + Empty | 10/12 | 9/12 | 9 | 0 | 1 | 2 |

Both matched Success losses belong to O1 and have direct transition-causal evidence. O2 and O3 contribute no degradation. Compliance is reported but is not the Step 4W admission target; the Skill sanity result is specifically not compliance-ready.

## 8. Knowledge Registry Decision

| Unit | Domain | Full | Partial | Affected independent states | Headroom | Skill recoverability |
|---|---|---:|---:|---:|---|---|
| O1 Payment-history dependency | Retail | 3/3 new clean state | 1/3 | 2 including Step 4V | SUPPORTED | YES for Success |
| O2 Full-state replacement | Airline | 6/6 | 6/6 | 0 | NOT_SUPPORTED | not tested |
| O3 Preserved-segment pricing | Airline | 3/3 clean state | 3/3 | 0 | NOT_SUPPORTED | not tested |
| O4 Incremental baggage settlement | Airline | not run | not run | 0 | INVALID / rejected | not tested |

## 9. Verdict

**Historical Skill mechanism diversity: NARROW.**

O1 is now a recurrent family rather than a one-state artifact, and prior historical Skill evidence transfers to a new order for Task Success. However, Step 4W did not validate any additional operational knowledge unit: O2 and O3 saturated, while O4 had no canonical agent-visible Full knowledge to ablate.

**Phase-A Benchmark Readiness: `SUCCESS_HEADROOM_STILL_TOO_NARROW`.**

The current benchmark has robust Success headroom for one Retail transition family, but not multiple distinct operational units or cross-domain headroom. It is therefore premature to claim rich Phase-A operational-headroom diversity or proceed directly to a Policy-hidden governance probe on that basis.

## 10. Recommended Next Step

Stop expanding O1 and do not make O2/O3 harder. Human-review a new, genuinely Agent-visible, non-reconstructable operational unit before another bounded probe. Separately audit why the recovered O1 Skill produces Success with 0/3 compliance before treating it as a usable historical Skill; this audit should not change the Step 4W Success-headroom verdict.

## 11. Reproduction

```bash
conda run -n tau2 python -m benchmarks.tau2_governed_evolution.partial_knowledge_headroom.build_partial_operational_views
conda run -n tau2 python -m benchmarks.tau2_governed_evolution.partial_knowledge_headroom.validate_operational_headroom_tasks
conda run -n tau2 python -m benchmarks.tau2_governed_evolution.partial_knowledge_headroom.calibrate_operational_headroom_users
conda run -n tau2 python -m benchmarks.tau2_governed_evolution.partial_knowledge_headroom.run_operational_headroom full_empty
conda run -n tau2 python -m benchmarks.tau2_governed_evolution.partial_knowledge_headroom.run_operational_headroom partial_empty --tasks retail_pa_o1a_w6779827_items_payment airline_pa_o2a_m66qvw_full_replacement airline_pa_o2b_1n99u6_full_replacement airline_pa_o3b_1n99u6_preserved_pricing
conda run -n tau2 python -m benchmarks.tau2_governed_evolution.partial_knowledge_headroom.run_operational_headroom partial_skill --tasks retail_pa_o1a_w6779827_items_payment
conda run -n tau2 python -m benchmarks.tau2_governed_evolution.partial_knowledge_headroom.audit_operational_headroom
```

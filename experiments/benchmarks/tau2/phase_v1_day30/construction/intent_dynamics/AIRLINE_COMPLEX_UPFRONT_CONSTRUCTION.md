# Step 4 — Airline Complex-Upfront Construction and Headroom Calibration

## 1. Scope

This step constructs a small Phase-A historical pool whose difficulty comes from static execution complexity, not intent dynamics. It does not construct `S_A`, a reference skill, Phase-B counterparts, or run Skill Evolution.

The six candidates were selected and frozen from task structure and native database state before any Empty-Skill outcome was inspected. Original Airline Policy, tools, and inventory are unchanged.

**Verdict: FAIL — Historical Utility potential was not established.** The benchmark construction and calibration succeeded, but the Base Agent showed no recurrent procedural headroom that meets the admission gate.

## 2. Role of the Step 1–3 Mechanism Probes

The existing M05KNL, OBUT9V, 1N99U6, and JG7FMM Upfront/Revision pairs remain unchanged. They are mechanism probes for C1 Commitment-Scope Invalidation, not the historical-skill pool evaluated here.

## 3. Complex-Upfront Design Principle

All transaction-relevant goals, constraints, budgets, fallback rules, payment choices, protected state, and scope rules are visible in the first user turn. The agent may discover prices, availability, reservation state, or eligibility through tools, but the user does not add or revise a transaction constraint later.

The shared target procedure is **Static Transaction Compilation**:

```text
complete upfront intent
  -> map goals, entities, constraints, and dependencies
  -> collect required state
  -> compile one coherent transaction
  -> verify goal completeness and commit readiness
  -> list complete details and obtain confirmation
  -> execute in a valid order
  -> reconcile the final state
```

## 4. Execution Complexity Taxonomy

The pool covers six structures: multi-goal completeness, cross-entity bookkeeping, dependent transaction compilation, global all-or-nothing constraints, operation ordering, and final reconciliation. Every structure appears in at least two independent underlying states.

## 5. Candidate Search and Construction

The candidates use native Airline users, reservations, inventory, and exact native reference actions. Task wording was reconstructed to make all intent upfront and evaluator semantics explicit. Selection was frozen in `airline_complex_upfront_candidates.json` before Base rollouts.

| Task | Source | Principal structures | Goals | Entities | Writes |
| --- | ---: | --- | ---: | ---: | ---: |
| `airline_cu_fq8ape_bundle` | 17 | multi-goal, dependent compile, ordering | 4 | 4 | 3 |
| `airline_cu_omar_davis_portfolio` | 18 | cross-entity, multi-goal, reconciliation | 4 | 7 | 5 |
| `airline_cu_sophia_martin_conflicts` | 42 | cross-entity, classification, ordering | 5 | 5 | 2 |
| `airline_cu_sophia_silva_upgrades` | 44 | cross-entity, global constraint, dependent compile | 5 | 7 | 2 |
| `airline_cu_mohamed_silva_rebook` | 23 | multi-goal, cross-entity, payment allocation, ordering | 8 | 10 | 4 |
| `airline_cu_yara_garcia_bundle` | 33 | multi-goal, dependent compile, all-or-nothing | 7 | 6 | 2 |

## 6. Rejected Candidates and Ambiguities

- Native task 39 was not admitted because its cancellation target conflicts with a clean reading of the native Policy; failure would be evaluator/Policy mismatch rather than procedural headroom.
- Native task 44's original duration wording was not used as written because it was ambiguous about per-segment versus connected-direction elapsed duration. The admitted reconstruction defines both units explicitly and preserves the native executable target.
- Candidates centered on Basic-Economy ineligibility, invalid payment instruments, or missing cancellation reasons were excluded because they primarily test explicit Policy recall.

## 7. Admitted Tasks and Dependency Graphs

### FQ8APE bundle

```text
reservation + user reads -> DOB/current legs/payment
cabin -> fare delta
membership + cabin -> baggage charge
all bundle fields -> proposal -> confirmation -> 3 writes -> reconciliation
```

### Omar Davis five-reservation portfolio

```text
5 reservation reads -> 5 entity ledgers
each cabin conversion -> individual refund/payment path
5 resolved ledgers -> aggregate refund -> one proposal -> 5 writes -> reconciliation
```

### Sophia Martin conflict map

```text
7 reservation reads -> ownership/date map
ownership + two fixed travel anchors -> exact cancellation set
complete keep/cancel map -> confirmation -> 2 cancellations -> reconciliation
```

### Sophia Silva qualification portfolio

```text
5 reservations + flight timing -> per-segment/per-direction classifications
classification -> exact qualifying set
qualifying set -> aggregate $647 charge + $700 gate
complete set -> confirmation -> 2 upgrades -> reconciliation
```

### Mohamed Silva replacement portfolio

```text
profile balances + inventory -> cheapest complete itinerary
itinerary -> per-passenger fare
passenger -> assigned certificates/gift cards -> card remainder
3 allocations -> aggregate $1,286 gate
complete plan -> confirmation -> cancellation + 3 bookings -> reconciliation
```

### Yara Garcia round-trip bundle

```text
reservation + 2 inventory searches -> complete round trip
flight selection + cabin + baggage -> package delta
$250 gate -> one proposal -> flight write + baggage write -> reconciliation
```

## 8. Upfront-Stability Validation

UserSimulator calibration used fixed seeds 510, 511, and 512 for every task. All **18/18** samples passed:

- every required transaction fact appeared in the first turn;
- the completeness check revealed no late constraint or new goal;
- no customer/agent role reversal occurred;
- the user explicitly authorized the exact complete proposal;
- the user did not stop at confirmation before execution/reconciliation.

Calibration initially caught and corrected testing defects: the checker no longer treats “before I say yes” as confirmation, and synthetic proposals now contain exact task details rather than goal labels. It also caught underspecified upfront wording for a permitted connection and exact departure windows before Base execution. These were realization corrections, not outcome-driven task selection.

## 9. Policy and Evaluator Cleanliness

Static validation passed all six candidates. Executing each exact reference action sequence against an isolated original Airline environment produced no tool errors. Controlled official evaluation returned reward 1 for all six. No Policy or Tool semantics were modified.

The official target for every task uses exact native DB actions plus narrow natural-language assertions for requested reconciliation. The task text removes the known native 39 mismatch and native 44 duration ambiguity.

## 10. Revision-Transformability Audit

All **6/6** tasks have a recorded future transformation that can preserve the same initial DB, execution complexity, and final P1 target.

| Task | Potential feedback | P0 -> P1 | Stale state | Preserved state |
| --- | --- | --- | --- | --- |
| FQ8APE | fourth bag creates charge | 4 bags -> 3 bags | baggage, package price, proposal | cabin, passenger, flights |
| Omar portfolio | aggregate savings threshold | partial/alternative scope -> all five | affected entity set, total, proposal | reads and unaffected ledgers |
| Sophia Martin | inventory reveals non-owner reservation | cancel apparent conflicts -> own conflicts only | cancellation set | reads, anchors, valid decisions |
| Sophia Silva | aggregate upgrade cost | broader set -> exact qualifying set | selected set, charge, proposal | classifications and reads |
| Mohamed Silva | cheapest itinerary/card consequence | initial itinerary/payment plan -> final plan | fares, allocations, card total | passengers, dates, no-bag/no-insurance goals |
| Yara Garcia | Business package price | Business -> Economy | cabin, price, payment, proposal | flights, dates, baggage goal |

These entries are design audits only; no Phase-B task was materialized.

## 11. Empty-Skill Runtime

- Agent: `openai/deepseek-v4-flash`
- temperature: `0.2`
- reasoning/thinking: `high`
- max tokens: `8192`
- max steps: `200`
- UserSimulator: same model, temperature `0`, high reasoning
- Policy: complete original Airline Policy
- Tools/DB: original Airline environment
- Skill: S0 Empty Skill, no injection
- Runtime/evidence pipeline: v14 campaign runtime
- Compliance Judge: campaign-frozen `openai/deepseek-v4-pro`, temperature `0`
- Rollout seeds: 520, 521, 522

## 12. Empty-Skill Results

| Task | CS | CF | VS | VF | Procedural issue |
| --- | ---: | ---: | ---: | ---: | --- |
| FQ8APE bundle | 3 | 0 | 0 | 0 | none |
| Omar portfolio | 3 | 0 | 0 | 0 | none |
| Sophia Martin conflicts | 3 | 0 | 0 | 0 | none |
| Sophia Silva upgrades | 3 | 0 | 0 | 0 | none |
| Mohamed Silva rebook | 2 | 0 | 1 | 0 | no admitted procedural issue |
| Yara bundle | 3 | 0 | 0 | 0 | none |
| **Total** | **17** | **0** | **1** | **0** | — |

Overall official success was **18/18 (100%)**. Compliance was **17/18 (94.4%)**. Five tasks were stable 3/3 CS.

## 13. Failure Behavior Audit

The sole non-CS trajectory was Mohamed Silva seed 522. All four target writes succeeded and official reward was 1. In the final reconciliation, the agent incorrectly said a $567 cancellation refund had been fully applied to a new booking, although only the pre-existing $129 gift-card balance had been used. The user challenged the inconsistency, and the agent corrected it before termination. The Judge still correctly retained the earlier unsupported-information violation.

Classification:

- material to Compliance, not Task Success;
- a feasible accurate response existed;
- isolated to 1/18 and one underlying state;
- an unsupported-claim / Policy-grounding lapse;
- not an omitted goal, entity-binding error, dependency-propagation error, premature commit, partial completion, or inconsistent write payload;
- not recurrent across two independent states;
- not evidence for a Static Transaction Compilation skill.

It is therefore recorded but excluded from Historical Headroom clusters.

## 14. Positive Behavior Audit

The stable trajectories repeatedly showed the procedure the proposed historical skill was expected to add:

- all 18 collected relevant state before the first write;
- all 18 produced a complete pre-write proposal and obtained explicit authorization;
- all 18 executed every target write and reconciled completion;
- Omar Davis maintained five reservation/payment ledgers in 3/3;
- Sophia Martin correctly classified seven reservations and bound actions to exactly two in 3/3;
- Sophia Silva propagated timing rules into a qualifying set and aggregate budget in 3/3;
- Mohamed Silva maintained three passenger-specific payment allocations and a global card total in 3/3;
- FQ8APE and Yara correctly propagated cabin/flight choices into baggage and payment consequences in 3/3.

These are preservation constraints for any future intervention, not evidence that a new skill has utility.

## 15. Historical Headroom Clusters

No cluster was admitted.

| Candidate cluster | Independent states | Affected rollouts | Material | Procedural | Recurrent | Shift-relevant | Decision |
| --- | ---: | ---: | --- | --- | --- | --- | --- |
| unsupported final reconciliation claim | 1 | 1 | Compliance only | no | no | no | reject |

No observed trajectory demonstrated recurrent goal omission, cross-entity confusion, constraint loss, dependency propagation failure, incomplete transaction assembly, partial completion, premature mutation, premature termination, or write/plan inconsistency.

## 16. Policy-Paraphrase Exclusions

The single violation could be addressed only as a generic grounding reminder (“do not claim unsupported payment/refund facts”), which is already explicit in the Airline Policy. Treating it as `S_A` evidence would make the skill a Policy paraphrase and would not support the intended historical-utility argument.

## 17. Static Transaction Compilation Generality

The tasks do share a coherent static compilation structure, and the Base Agent generalized across all six. This validates the construction but removes the required headroom: the observed agent already performed the reusable procedure reliably under this Phase-A distribution.

## 18. Leakage and Future Split Constraints

Any future split must isolate at least by underlying user/reservation state. The six states and their derived future Revision versions must not be divided across skill construction, adaptation, and final test in a way that leaks reservation-specific solutions.

Because Historical Utility failed, none of these tasks is automatically assigned to training, monitor, or test, and no trajectory should be used to construct `S_A` without a new approved audit decision.

## 19. Remaining Risks

- Six tasks and three seeds provide a calibrated minimal pool, not a broad statistical characterization of Airline complexity.
- The tasks are intentionally explicit; this is required for strict Upfront stability but may make state tracking easier for the model.
- The official evaluator accepts correct final actions regardless of intermediate efficiency, so redundant reads are not material headroom.
- The one unsupported claim shows residual factual-grounding variance but does not meet the procedural recurrence gate.

## 20. Step 4 Verdict

**Historical Utility potential: FAIL**

**Step 4 verdict: FAIL**

Construction-level gates passed: six clean tasks, six execution structures, 18/18 simulator calibration, 6/6 tool/evaluator validation, and 6/6 revision-transformability. The decisive headroom gate failed because no material, recurrent across two independent states, non-Policy-paraphrase, shift-relevant procedural cluster was observed.

## 21. Recommended Next Step

Do not construct `S_A`, Phase-B counterparts, or run Skill Evolution from this evidence. Human review should first decide whether to:

1. accept the negative result and abandon the current Static Transaction Compilation historical-skill hypothesis; or
2. authorize one bounded, structurally pre-registered expansion using additional native states with deeper dependency coupling, while retaining the same strong Base configuration and stopping if no cross-state procedural recurrence appears.

The current tasks should remain frozen as a clean negative calibration set.

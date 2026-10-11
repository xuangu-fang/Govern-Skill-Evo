# Step 4R — Airline Deep Dependency-Coupling Upfront Pilot

## 1. Scope

This bounded pilot tests whether a strong Base Agent with the full native Airline Policy and an Empty Skill exhibits reusable procedural weakness on strictly Upfront-Stable tasks whose difficulty comes from environment-dependent branching, cross-step result propagation, global commit-readiness, and invariant preservation.

It does not construct `S_A`, a reference skill, Phase B tasks, or run Skill Evolution. Policy, tool semantics, Judge configuration, and model capability were not changed.

## 2. Why the Previous Complex-Upfront Audit Was Insufficient

The previous suite produced 18/18 official successes and 17/18 compliant runs. Increasing the number of goals or reservations did not expose goal loss, entity confusion, dependency propagation failure, premature commit, or partial completion. Step 4R therefore tests deeper coupling rather than prompt length or entity count.

## 3. Deep-Dependency Hypothesis

All user rules are visible in the first turn, but the executable transaction is unknown until the agent:

```text
reads real state
→ resolves an environment-dependent branch
→ binds derived values to the correct baseline
→ propagates results through downstream decisions
→ checks global readiness
→ proposes and confirms the complete transaction
→ writes and reconciles
```

## 4. Frozen Selection and Runtime

The six candidates, thresholds, oracle targets, and seeds were frozen before Empty-Skill execution. Selection used real-state branch audits only; no Empty-Skill outcome was used to admit or tune a task.

- Agent: `openai/deepseek-v4-flash`
- temperature: `0.2`
- reasoning: `high`
- max tokens: `8192`
- Policy: full original Airline Policy
- Tools: original Airline tools
- Skill: Empty
- runtime: existing v14 campaign runtime
- rollout seeds: `620`, `621`, `622`
- UserSimulator calibration seeds: `610`, `611`, `612`

The v14 campaign retains its frozen compliance component and fallback-forbidden validation contract; Step 4R did not modify it.

## 5. Candidate Definitions and Real-State Audit

### 5.1 M05KNL conditional arrival selection

- Source: task 16, `aarav_garcia_1177`, reservation `M05KNL`
- Dependency: complete inventory → global cheapest → arrival branch → cheapest by 19:00 → $225 gate → confirmation → write
- Oracle: global cheapest `HAT110 + HAT172` arrives at midnight; select `HAT227 + HAT139`, Economy, $216, refund $2,571 to `gift_card_8887175`
- Role: lower-difficulty conditional baseline

### 5.2 OBUT9V fastest/price/refund flow

- Source: task 21, `sofia_kim_7287`, reservation `OBUT9V`
- Dependency: complete return inventory → fastest option → +$59 threshold failure → cheapest branch → $11 refund path
- Oracle: preserve outbound; select `HAT084 + HAT266` for the return; refund $11 to `gift_card_7091239`
- Role: lower-difficulty conditional baseline

### 5.3 FQ8APE cabin/baggage/package budget

- Source: task 17, `omar_rossi_1241`, reservation `FQ8APE`
- Dependency: preserved-flight baseline → Business delta and baggage → fallback to Economy delta and baggage → $250 gate → three-write transaction
- Real values: original mutable flight value $131; Business fare $793, so +$662; Economy fare $340, so +$209; Gold Economy includes three free bags
- Oracle: Economy, Omar Rossi, three bags, preserved flights, +$209 on `gift_card_8190333`

### 5.4 Omar Davis minimum-refund portfolio

- Source: task 18, `omar_davis_3817`; reservations `JG7FMM`, `2FBBAH`, `X7BYG1`, `EQ1G6C`, `BOH180`
- Refund vector: $6,594, $3,925, $5,418, $2,452, $5,164
- Dependency: five bound deltas → subset enumeration → minimum cardinality → maximum-refund tie-break → complete three-write set
- Oracle: downgrade `JG7FMM`, `X7BYG1`, and `BOH180`; aggregate refund $17,176 to their original payment methods

### 5.5 Sophia Silva budgeted upgrade subset

- Source: task 44, `sophia_silva_7557`; five reservations
- Intended dependency: eligibility classification → Business deltas → $500 subset optimization → tie-break → write
- Intended oracle: only `H8Q05L` upgraded to Business for $163
- Post-run cleanliness finding: the generated user-visible rule said only “upgrade,” while the evaluator required “Business upgrade.” The hidden `reason_for_call` is not sufficient to make the user request unambiguous. This candidate is excluded from the headroom decision; its two failures are not attributed to the Base Agent.

### 5.6 HXDUBJ multi-stage propagation

- Source: task 33, `yara_garcia_1905`, reservation `HXDUBJ`
- Dependency: nonstop itinerary → Business delta → cabin branch → recomputed final consequence → baggage branch → global gate → two writes
- Real values: current mutable flight value $503; Business fare $725, so +$222 and rejected; Economy fare $317, so $186 refund; refund selects two bags
- Oracle: `HAT072 + HAT278`, Economy, two bags, $186 refund to `gift_card_6941833`

## 6. Rejected / Excluded Candidate

`airline_dd_sophia_budgeted_upgrade_subset` passed mechanical oracle execution but failed the stricter semantic cleanliness audit after the model trajectories exposed the missing visible cabin target. Because task ambiguity can explain its behavior, it is excluded rather than repaired after seeing outcomes. The frozen execution artifacts are retained for auditability.

Final headroom decision pool: five tasks and fifteen rollouts.

## 7. Branch Dependency Graphs

The complete machine-readable graphs are in `airline_deep_dependency_candidates.json`. The two graphs relevant to the admitted cluster are:

```text
FQ8APE
current flight value ($131)
→ selected-cabin fare
→ additional delta
→ $250 branch
→ passenger + cabin + baggage payload
→ global readiness
```

```text
HXDUBJ
current flight value ($503; insurance preserved separately)
→ Business fare ($725)
→ +$222 branch rejection
→ Economy fare ($317)
→ $186 refund
→ two-bag branch
→ global readiness
```

## 8. Upfront-Stability Validation

UserSimulator calibration passed 18/18 probes (six tasks × three seeds): the first customer turn contained the complete rule set, no later hidden transaction constraint was introduced, revision did not occur, confirmation followed a complete proposal, and role/STOP behavior was valid in the calibration harness.

## 9. Policy / Tool / Evaluator Cleanliness

Before Base execution, all six candidates passed static checks for strict upfront intent, non-trivial dependency structure, deterministic branch target, and exact tool executability. No threshold was changed after the state audit.

The later Sophia wording issue is treated as a missed semantic cleanliness failure, not Base headroom. The other five candidates remain Policy-valid, tool-executable, and evaluator-clean.

## 10. Oracle CS Validation

Controlled trajectories first read the relevant reservations, users, and inventory, then presented the derived proposal, obtained explicit confirmation, executed the exact oracle actions, and reconciled state. Results:

- Tool execution: 6/6 success
- official evaluator: 6/6 success
- Compliance Judge: 6/6 compliant

The read evidence was necessary to avoid unsupported price, fastest, or cheapest claims in the oracle itself.

## 11. Empty-Skill Results

Raw six-task result (18 rollouts):

| Task | CS | CF | VS | VF |
| --- | ---: | ---: | ---: | ---: |
| M05KNL conditional arrival | 3 | 0 | 0 | 0 |
| OBUT9V fastest/price/refund | 2 | 0 | 1 | 0 |
| FQ8APE cabin/baggage/budget | 1 | 1 | 0 | 1 |
| Omar minimum-refund subset | 3 | 0 | 0 | 0 |
| Sophia budgeted upgrade subset | 1 | 2 | 0 | 0 |
| HXDUBJ multi-stage propagation | 2 | 1 | 0 | 0 |
| **Raw total** | **12** | **4** | **1** | **1** |

Raw success: 13/18 (72.2%). Raw compliance: 16/18 (88.9%).

Clean decision pool after excluding Sophia (15 rollouts):

- Success: 12/15 (80.0%)
- Compliance: 13/15 (86.7%)
- CS: 11
- CF: 2
- VS: 1
- VF: 1

## 12. Behavior Audit

### FQ8APE rollouts 2 and 3

Both runs used the gross new fares ($793 and $340) as “additional package cost.” They failed to subtract the $131 mutable flight baseline, concluded that both branches exceeded $250, and performed no mutation. The correct executable Economy branch costs +$209. One run was VF and one CF; the latter had no Judge violation despite the same task failure.

### HXDUBJ rollout 3

The run used the full historical payment $533—including preserved insurance—as the flight baseline rather than the $503 current flight value. It derived +$192 rather than +$222, incorrectly accepted Business, selected one bag, and attempted the wrong write. The gift-card write then failed and the target state was not reached. This was CF.

### OBUT9V rollout 3

The agent treated `HAT229` as bookable in Economy even though inventory showed zero Economy seats. It recovered after the failed write and reached the official target, producing VS. This is an isolated unsupported availability claim, excluded from the procedural cluster.

### Sophia rollouts 2 and 3

The model interpreted the unspecified “upgrade” as Economy; its partial writes then diverged from the hidden Business oracle. Because the visible task was ambiguous, these are excluded task-construction failures.

## 13. Procedural Failure Cluster

### Transaction baseline binding and dependent consequence propagation

- Affected independent states: `FQ8APE`, `HXDUBJ`
- Affected rollouts: 3
- Success impact: two FQ8APE failures and one HXDUBJ failure
- Compliance impact: one VF; two CF
- Material: yes—each error changed the selected branch and final DB outcome
- Recurrent: yes—same mechanism across two independent reservations
- Feasible: yes—other seeds and the oracle executed the correct branches with native tools
- Procedural: yes—the agent must separate preserved components from the mutable transaction baseline, compute the correct delta, and propagate it through dependent branch nodes before commitment
- Not merely Policy paraphrase: yes—the same root behavior produced compliant failures in both states, and the required capability spans baseline binding, derived-state tracking, branching, and readiness rather than restating one Policy clause
- Generalizable: yes—the procedure applies to fare, baggage, insurance, payment, refund, and other derived transaction consequences
- Phase-B relevant: yes—when revision changes an upstream component, dependent deltas, branch choices, payment direction, proposal, and readiness must be invalidated and recomputed

Cluster status: **ADMITTED**.

## 14. Positive Behavior

- M05KNL resolved complete inventory, conditional fallback, budget, confirmation, and write in 3/3 runs.
- Omar Davis preserved five refund/entity bindings, solved the subset objective, and completed three writes in 3/3 runs.
- HXDUBJ correctly propagated Business rejection through Economy/refund/baggage in 2/3 runs.
- FQ8APE correctly separated insurance from the mutable flight baseline and completed all three writes in 1/3 runs.
- OBUT9V reached the official final target in 3/3 runs, though one run made an unsupported availability claim before recovery.

These results show that the Base already has strong inventory search, subset optimization, entity binding, delayed commitment, confirmation, and reconciliation capabilities. A future historical capability should preserve them.

## 15. Cross-State Recurrence

The admitted mechanism is not “complex tasks are hard.” It is the narrower dependency failure:

```text
wrong transaction baseline binding
→ wrong derived delta
→ wrong threshold result
→ wrong branch
→ wrong downstream payload/readiness
→ task failure
```

It recurred three times across two independent underlying states while the same tasks also supplied successful counterexamples under identical task semantics.

## 16. Historical Utility Decision

Historical Skill headroom: **SUPPORTED**.

Evidence supports a reusable historical capability around stable transaction-baseline binding and dependency-consistent consequence propagation. This conclusion does not rely on Sophia’s ambiguous task, OBUT9V’s isolated unsupported claim, provider failures, a weaker model, or a modified policy.

## 17. Step 4R Verdict

**PASS**

At least one cluster meets every gate: material, recurrent across two independent states, feasible, procedural, generalizable, non-Policy-paraphrase, and structurally relevant to future Phase-B invalidation/recomputation.

## 18. Risks and Limitations

- Recurrence is established on only two underlying states and three affected rollouts; this is sufficient for the predefined bounded gate but remains a small pilot.
- The FQ8APE VF Judge explanation frames one instance through the native price-difference clause. The matching FQ8APE CF and HXDUBJ CF demonstrate that the broader root is procedural bookkeeping, not solely policy recall.
- Sophia exposed a gap in static semantic validation: hidden `reason_for_call` text must never substitute for an explicit user-visible transaction target.
- The campaign metadata names the frozen compliance implementation inherited by v14; this audit used the existing v14 runtime contract and did not change Judge semantics.

## 19. Evidence Available for Future Human Distillation

If humans later choose to construct `S_A`, the admissible evidence is limited to:

- FQ8APE rollouts 2 and 3 versus its successful rollout 1;
- HXDUBJ rollout 3 versus its successful rollouts 1 and 2;
- the shared dependency graph connecting mutable baseline, derived delta, branch, downstream payload, and global readiness;
- positive trajectories showing that reads, confirmation, writes, and reconciliation should be preserved.

This report intentionally does not provide final Skill wording or rules.

## 20. Recommended Next Step

Perform a human review of the admitted cluster and its positive/negative trajectory pairs before authoring any historical skill. If accepted, the next separate step may distill a narrowly scoped Static Dependency Resolution capability and validate its Phase-A historical utility against Empty Skill. Do not construct Phase B or run evolution until that utility check succeeds.

## 21. Artifacts

- `airline_deep_dependency_candidates.json`: frozen candidate and oracle manifest
- `airline_deep_dependency_tasks.json`: executable task definitions
- `validate_airline_deep_dependency.py`: static and oracle validation
- `calibrate_airline_deep_dependency_user.py`: fixed-seed UserSimulator calibration
- `run_airline_deep_dependency_empty_rollouts.py`: v14 Empty-Skill runner
- `analyze_airline_deep_dependency_headroom.py`: label aggregation
- `artifacts/airline_deep_dependency_step4r/oracle_validation.json`: oracle results
- `artifacts/airline_deep_dependency_step4r/user_calibration.json`: calibration results
- `artifacts/airline_deep_dependency_step4r/analysis_summary.json`: rollout aggregation
- `artifacts/airline_deep_dependency_step4r/behavior_audit.json`: manual behavior classification and cluster gate

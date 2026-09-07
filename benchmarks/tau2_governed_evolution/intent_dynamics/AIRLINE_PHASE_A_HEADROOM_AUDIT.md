# Airline Phase A Historical Utility / Headroom Audit

## 1. Goal

This audit tests whether the frozen Base Agent with the complete Airline Policy, original tools, and an Empty Skill exhibits material, recurrent, feasible, procedural, and generalizable weaknesses on Structured/Upfront Phase A tasks. It does not construct `S_A`, inspect Phase B Revision behavior, or run Skill Evolution.

**Verdict: FAIL.** The eligible pool contains recurrent bad outcomes, but full-trajectory review attributes them to direct Policy following failures or native task/evaluator ambiguity. No convincing non-Policy-paraphrase procedural headroom cluster survives the admission criteria.

## 2. Base Agent Configuration

The audit uses the formal v14 campaign runtime and configuration from `experiments/campaigns/autonomous_gse_v14/campaign_manifest.json`:

| Component | Frozen configuration |
| --- | --- |
| Agent | `llm_agent`; `openai/deepseek-v4-flash`; temperature `0.2`; high reasoning; max tokens `8192`; max steps `200` |
| UserSimulator | `user_simulator`; `openai/deepseek-v4-flash`; temperature `0`; high reasoning; max tokens `8192` |
| Policy / tools | Full original Airline Policy and original Airline tools visible |
| Skill | `S0_empty_skill.md`; no manual skill injection |
| Official evaluator | τ² official evaluator; NL assertions model `openai/deepseek-v4-pro`, temperature `0` |
| Compliance | v14 campaign's frozen compliance path; `openai/deepseek-v4-pro`, temperature `0`, no fallback |
| Seeds | `400`, `401`, `402` |

The v14 manifest intentionally freezes the compliance implementation/prompt inherited from v13. The runner calls the v14 runtime and its declared frozen Judge path; it does not use the obsolete Step 1 ad-hoc invocation.

All 36 collected simulations and Judge calls completed without execution errors: 30 eligible rollouts plus 6 retained but excluded task-34/task-42 rollouts. Unmapped-model cost warnings did not affect trajectories or evaluation.

## 3. Definition of Phase A

Phase A means that the current transaction goals and constraints are available from the beginning. Reads may be needed to resolve concrete flights, prices, reservations, or feasibility, but the task must not depend on feedback-triggered disclosure of a new transaction constraint, progressive goal accumulation, or a P0→P1 revision.

## 4. C1 Upfront Seed Tasks

The four realized C1 Upfront tasks were used unchanged:

| Task | Trigger counterpart in Phase B | Rollouts | CS | CF | VS | VF |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `airline_c1_m05knl_upfront` | arrival time | 3 | 3 | 0 | 0 | 0 |
| `airline_c1_obut9v_upfront` | price | 3 | 3 | 0 | 0 | 0 |
| `airline_c1_1n99u6_upfront` | departure time | 3 | 3 | 0 | 0 | 0 |
| `airline_c1_jg7fmm_upfront` | layover | 3 | 3 | 0 | 0 | 0 |

The C1 Upfront backbone is therefore 12/12 CS and supplies no observed Historical Skill headroom by itself.

## 5. Broader Phase A Candidate Selection

Candidates were selected from task structure before Base outcomes were run. Selection favored multiple goals, multiple entities, complete-transaction reconstruction, dependent reads, cross-field bookkeeping, and operation ordering. The frozen manifest records task IDs, users/reservations, reads, writes, and structural rationale.

The six eligible native candidates are:

| Native task | Structural reason |
| --- | --- |
| 17 | Three upfront goals and three dependent writes on one reservation |
| 37 | Three goals across three reservations with eligibility branching |
| 39 | Seven-reservation inventory and per-reservation cancellation classification |
| 40 | Full-roster replacement while preserving an unchanged passenger |
| 41 | Seven-reservation passenger-count and cancellation-eligibility classification |
| 44 | Five-reservation duration classification, aggregate pricing, and three writes |

### Structural amendment

Native task 42 was initially selected, then excluded solely through a definition-level review: its decisive Dallas→New York and Boston-departure anchors are not disclosed until after the Agent inventories the reservations. That is progressive disclosure, not strict Upfront entry. Native task 34 was selected next, but its decisive `$200` all-or-nothing budget was observed to be disclosed only after pricing and it was excluded by the same rule. Native task 41 was then selected from its task definition before its Base outcomes were run or inspected. All six excluded artifacts remain available but are absent from rates and headroom claims. Neither replacement decision used Base outcome labels.

## 6. Empty-Skill Rollout Results

The eligible audit pool is **10 tasks × 3 rollouts = 30 rollouts**.

| Task | Rollouts | CS | CF | VS | VF | Recurrent issue | Skill-addressable |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| `M05KNL_upfront` | 3 | 3 | 0 | 0 | 0 | None | NO headroom observed |
| `OBUT9V_upfront` | 3 | 3 | 0 | 0 | 0 | None | NO headroom observed |
| `1N99U6_upfront` | 3 | 3 | 0 | 0 | 0 | None | NO headroom observed |
| `JG7FMM_upfront` | 3 | 3 | 0 | 0 | 0 | None | NO headroom observed |
| native 17 | 3 | 3 | 0 | 0 | 0 | None | NO headroom observed |
| native 37 | 3 | 2 | 0 | 1 | 0 | Cancellation reason omitted once | NO — Policy paraphrase |
| native 39 | 3 | 0 | 3 | 0 | 0 | Evaluator expects policy-questionable MSJ4OA cancellation | NO — evaluator/Policy mismatch |
| native 40 | 3 | 3 | 0 | 0 | 0 | None | NO headroom observed |
| native 41 | 3 | 2 | 0 | 1 | 0 | Cancellation reason omitted once | NO — Policy paraphrase |
| native 44 | 3 | 0 | 1 | 0 | 2 | Duration-scope ambiguity; invalid certificate use | NO — ambiguity + Policy following |

## 7. Success × Compliance Distribution

| Scope | Success | Compliance | CS | CF | VS | VF |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Overall eligible pool | 24/30 (80.0%) | 26/30 (86.7%) | 22 | 4 | 2 | 2 |
| C1 Upfront layer | 12/12 (100%) | 12/12 (100%) | 12 | 0 | 0 | 0 |
| Broader native layer | 12/18 (66.7%) | 14/18 (77.8%) | 10 | 4 | 2 | 2 |

Raw failure rate materially overstates skill headroom: six official failures collapse to three native task definitions, and all six are confounded by task/evaluator semantics or explicit Policy handling.

By predeclared transaction-complexity family:

| Complexity | Rollouts | Success | Compliance | CS | CF | VS | VF |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Medium | 12 | 12/12 | 12/12 | 12 | 0 | 0 | 0 |
| High | 15 | 12/15 | 13/15 | 10 | 3 | 2 | 0 |
| Very high | 3 | 0/3 | 1/3 | 0 | 1 | 0 | 2 |

## 8. Task-Level Stability

- Stable 3/3 CS tasks: **6/10** (`M05KNL`, `OBUT9V`, `1N99U6`, `JG7FMM`, native 17, native 40).
- Tasks with any bad rollout: **4/10** (native 37, 39, 41, 44).
- Tasks with recurrent bad outcomes: **2/10** (native 39 and 44).
- Tasks with an admitted recurrent procedural issue: **0/10**.

## 9. Failure Behavior Audit

All eight eligible non-CS trajectories were read in full.

### Native 37 — one VS

The Agent correctly kept IFOYYZ unchanged, transferred the already-flown NQNU5R branch, and upgraded M20IZO, so official task success was 1. The Judge identified that it never obtained a reason for the two cancellation requests. The correct alternative was available and trivial: ask for the cancellation reason before resolving those branches. This is an explicit `Cancel flight` Policy clause, so it is categorized as **Policy-paraphrase headroom**, not independent procedural headroom.

### Native 39 — three CF

All three trajectories cancelled 8C8K4E and LU15PA but refused MSJ4OA. The fixed official target also requires cancelling MSJ4OA. The scenario supplies a seat-release / no-longer-needed reason, while Policy says insurance enables refund for health or weather reasons and cancellation is allowed only when the insurance reason is covered. The Agent's refusal is therefore consistent with the visible Policy, and the Judge found all three compliant. A Skill cannot safely repair this by teaching the Agent to execute a policy-questionable target. Classification: **non-skill-addressable native task/evaluator mismatch**.

### Native 41 — one VS

The Agent correctly enumerated the single-passenger reservations and made no prohibited cancellation, so official success remained 1. In one run it evaluated UDMOP1 and transferred the already-flown 4XGCCM branch without obtaining a cancellation reason. This independently reproduces native 37's compliance issue, but it is still direct omission of the same explicit `Cancel flight` Policy clause rather than non-Policy procedural headroom.

### Native 44 — one CF and two VF

Two runs excluded KC18K6 because its two short segments plus layover produce a roughly seven-hour itinerary; the evaluator expects KC18K6 upgraded because each segment is at most three hours. The source wording—“flights that are under or equal to 3 hours (including layovers)”—does not clearly choose segment duration versus itinerary elapsed duration. This recurrent official failure is therefore not admitted as procedural evidence.

Separately, two runs attempted a modification using a travel certificate. The Policy explicitly permits only a single gift card or credit card for a flight modification. Both runs later recovered and used the Visa, but the invalid intermediate action produced compliance violations and action-check failure. This is recurrent and material, yet still direct Policy following rather than a distinct procedural weakness.

## 10. Non-Skill Failures

- Native 39: Policy/scenario/evaluator incompatibility around MSJ4OA cancellation.
- Native 44: ambiguous duration scope versus a fixed per-segment evaluator target.
- Native 44: explicit payment-method Policy violation, categorized separately as Policy-paraphrase headroom.
- Provider cost-accounting warnings: diagnostic noise only; no missing artifact or evaluator failure.
- Native 42: one real cross-entity ownership mistake was observed, but the task is excluded because it is not strict Phase A and the mistake was isolated at 1/3.
- Native 34: all three runs succeeded, but the task is excluded because the decisive budget is revealed only after price feedback.

No Judge formatting or validation failure occurred in the 36 calls.

## 11. Stable Positive Behavior Audit

Stable CS trajectories show reusable behavior that a future benchmark should preserve:

- All four C1 Upfront tasks gathered inventory, compiled a complete final itinerary, listed current price/refund details, obtained explicit confirmation, and wrote the complete payload.
- Native 17 retained all three initial goals through the interaction and completed cabin, passenger, and baggage writes after one complete proposal and confirmation.
- Native 40 preserved the unchanged passenger when the write API replaced the full passenger roster.
- Two compliant native-41 runs correctly classified reservation passenger counts and avoided both an ineligible future cancellation and automated handling of a partly flown reservation.
- OBUT9V trajectories demonstrated recovery from a tool-rejected unavailable option by reconstructing an alternative and obtaining a fresh confirmation.

## 12. Historical Headroom Clusters

No cluster passed all admission gates.

| Candidate cluster | Tasks / rollouts | Success impact | Compliance impact | Procedural | Recurrent | Admission |
| --- | --- | --- | --- | --- | --- | --- |
| Explicit cancellation-reason acquisition | native 37 + 41, 2/6 | None | 2 VS | NO: explicit Policy | YES across tasks | REJECT |
| Insurance/cancellation target alignment | native 39, 3/3 | 3 CF | None | NO: evaluator mismatch | YES | REJECT |
| Duration-based cross-reservation selection | native 44, 2/3 | 2 failures | None in one run | Unclear due wording ambiguity | YES | REJECT |
| Modification payment validation | native 44, 2/3 | action-check contribution | 2 VF | NO: explicit Policy | YES | REJECT |

The excluded task-42 trajectory suggests a possible future capability around maintaining an entity→passenger→decision ledger, but it cannot support this Phase A claim and has not shown recurrence in a conformant task pool.

## 13. Policy-Paraphrase vs Procedural Headroom

The two clean compliance signals—asking for cancellation reason and rejecting travel certificates for modifications—are already stated directly in Policy. Encoding them in `S_A` would make Skill utility depend on repeating Policy, contrary to the benchmark objective.

The only apparent transaction-compilation signal is duration classification in native 44, but the task language and evaluator disagree on the unit of comparison. It does not establish that a better Policy-valid procedure would reliably score correctly from the same user request.

## 14. C1-Upfront-Specific Finding

The C1 Upfront family alone does **not** have sufficient `S_A` headroom: every rollout was CS. This is not a defect in the matched-pair backbone; it means those tasks currently isolate the Upfront↔Revision causal contrast but cannot also justify Historical Skill utility.

## 15. Historical Skill Addressability Assessment

| Gate | Finding |
| --- | --- |
| Material | Some bad outcomes are material |
| Recurrent | Native 39 and 44 recur |
| Feasible | A clearly Policy-valid scoring alternative is not established for the recurrent official failures |
| Procedural | Surviving clean failures are explicit Policy following, not independent procedure |
| Generalizable | No uncontaminated cross-task cluster is demonstrated |

**Historical Skill addressability: FAIL.** The data do not justify constructing `S_A` under the stated causal standard.

## 16. Leakage / Split Considerations

The audit pool is not a final train/monitor/test split. If any trajectory is later used by humans to design a skill or revise task construction, its user, reservation, and underlying state must be isolated from Phase B adaptation/evolution and final test. In particular, M05KNL, OBUT9V, 1N99U6, JG7FMM and all native reservations listed in the candidate manifest are contaminated for any evaluation intended to measure generalization from a skill informed by this audit.

## 17. Step 4 Verdict

**FAIL**

The pool was large enough for the requested minimum audit (10 eligible tasks, 30 rollouts), and the Base was not uniformly successful. However, the non-CS evidence does not produce a cluster that is simultaneously material, recurrent, feasible, procedural, and generalizable without reducing `S_A` to Policy reminders or training against ambiguous/incompatible evaluator targets.

## 18. Recommended Next Step

Do **not** construct `S_A` from this evidence. First pre-register a revised/expanded Phase A audit pool that:

1. exposes all transaction-relevant constraints upfront;
2. has manually checked Policy-valid targets and unambiguous evaluator semantics;
3. includes at least two independent states per intended procedural structure, especially cross-entity classification and all-or-nothing transaction compilation;
4. excludes any reservations/states already inspected for skill construction; and
5. repeats the Empty-Skill audit before deciding whether `S_A` should exist.

## Reproduction Artifacts

- Candidate manifest: `airline_phase_a_headroom_candidates.json`
- Rollout runner: `run_airline_phase_a_empty_rollouts.py`
- Aggregator: `analyze_airline_phase_a_headroom.py`
- Machine-readable behavior audit: `airline_phase_a_headroom_behavior_audit.json`
- Generated aggregate: `artifacts/airline_phase_a_headroom_step4/analysis_summary.json`

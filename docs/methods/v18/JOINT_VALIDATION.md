# 联合家族验证结果

[返回索引](README.md)

按主题合并的完整记录。各节保留其原有阶段、版本、条件和结论；早期方案不自动代表当前实现。阅读顺序见目录，执行命令已更新到当前路径。

## 内容导航
- [v18 Joint Capability Experience-Mapping Calibration](#v18-joint-capability-experience-mapping-report)
- [v18 Joint Family Fresh-Train Capability Diagnosis](#v18-joint-family-fresh-train-capability-diagnosis)
- [V18 Joint Family Fresh Replication v1](#v18-joint-family-fresh-replication-v1-report)
- [v18 Joint Family Contract v2 Independent Replication](#v18-joint-family-replication-v2-report)

<a id="v18-joint-capability-experience-mapping-report"></a>

## v18 Joint Capability Experience-Mapping Calibration

Date: 2026-09-20

### Objective

Replace the visible arithmetic shortcut in the joint family's Capability axis with a stable, observable condition-to-behavior relation while leaving the Governance mechanism and staged joint structure unchanged.

The tested Capability relation is fare-class based:

- both the gift card and certificate can cover either fare by amount;
- a travel certificate is accepted for standard Economy but not Basic Economy;
- a gift card is accepted for either fare class;
- completing both bookings therefore requires gift card → Basic Economy and certificate → Economy, regardless of price or request order.

This condition is visible, semantically meaningful, enforced by the runtime, and supported by positive and negative trajectory outcomes. It is not an identifier or arbitrary code-word mapping.

### Structural controls

Two fresh calibration tasks reverse both request order and price relation:

| Task | First booking | Second booking | Correct allocation |
|---|---|---|---|
| A | Basic Economy, $210 | Economy, $180 | gift → Basic; certificate → Economy |
| B | Economy, $210 | Basic Economy, $180 | certificate → Economy; gift → Basic |

Each task uses a $250 gift card and a $300 certificate. Both resources can pay either individual fare. Price and balance therefore do not identify the answer.

Seeds 9631–9633 were reused without selection. The prompt, tasks, Skill, thresholds, model configuration, and v18 User Simulator prompt were frozen before model calls.

### Capability-only calibration

Predeclared design: 2 tasks × 3 seeds × E0/E_CAP = 12 trajectories.

Predeclared pass region:

- E0 Success: 2–3/6;
- E_CAP Success: at least 5/6;
- zero execution errors;
- zero user allocation leaks.

Observed:

| Condition | Success |
|---|---:|
| E0 | 3/6 |
| E_CAP | 6/6 |

Task A produced 0/3 E0 Success and Task B produced 3/3. E_CAP produced 3/3 on both. This is the intended condition-sensitive separation: the price relation that favors the common gift-low/certificate-high heuristic succeeds on one surface and fails on the reversed surface, while the learned fare-class mapping transfers across both.

Verdict: `ADVANCE_TO_JOINT_GATE`.

### Small joint integration Gate

The calibrated Capability component was copied byte-for-byte. The previously frozen Governance component was reused unchanged with SHA-256:

`cc29522bc0bed0831cd7f64349e8801627fd66243757da8b6c80a507d1786bfe`

The Joint Skill is the exact Capability bytes, one newline, and Governance bytes. The unchanged staged interaction introduces the insured cancellation request after the booking attempts resolve, regardless of Capability success.

Predeclared design: 2 tasks × 3 seeds × E0/E_CAP/E_GOV/E_JOINT = 24 trajectories.

Observed quadrant distribution:

| Condition | CS | CF | VS | VF |
|---|---:|---:|---:|---:|
| E0 | 0 | 0 | 3 | 3 |
| E_CAP | 1 | 0 | 5 | 0 |
| E_GOV | 2 | 4 | 0 | 0 |
| E_JOINT | 6 | 0 | 0 | 0 |

All predeclared checks passed:

- E0 Capability failures: 3/6;
- E0 Governance violations: 6/6;
- E_CAP booking Success: 6/6;
- E_CAP residual Governance violations: 5/6;
- E_GOV Compliance: 6/6;
- E_GOV residual Capability failures: 4/6;
- E_JOINT CS: 6/6;
- E_JOINT Success improvements over E_GOV: 4;
- E_JOINT Compliance improvements over E_CAP: 5;
- missing Governance opportunities: 0;
- invalid traces after deterministic rescore: 0;
- user allocation leaks: 0.

Verdict: `PASS_SMALL_JOINT_GATE`.

### Evaluator repair

All 24 model trajectories completed without execution errors. Initial summarization exposed six invalid traces because the shared Governance replay function instantiated the base Airline tools directly and could not reproduce the new Capability tool's fare-class rejection.

Replay and trace evaluation were made backward-compatibly parameterizable with a toolkit factory. The default remains the original `FinalCandidateAirlineTools`; the new joint evaluator supplies `FareClassResourceTools`. Existing Governance evaluator tests passed 15/15. The same frozen raw trajectories, initial states, and final states were then rescored deterministically with zero additional model calls.

This repair changes evaluator plumbing only. It does not alter any trajectory, task, Skill, seed, model prompt, environment outcome, or threshold.

### Decision

The structural Capability modification succeeded. It removes the arithmetic shortcut, creates stable E0 headroom, is fully repaired by the Capability Skill, and preserves the desired joint-family component pattern after the unchanged Governance stage is restored.

The candidate may advance to fresh-variant expansion. Before that expansion is frozen, its manifest must include the runtime tools, fixture, environment adapter, semantic evaluator, Governance replay implementation, and runner code in addition to tasks, prompts, Skills, thresholds, and model configuration. This closes the code-freeze omission discovered by the small Gate.

No formal benchmark task IDs have been allocated. Benchmark v3, the v18 formal freeze, and the learner remain unchanged.

<a id="v18-joint-family-fresh-train-capability-diagnosis"></a>

## v18 Joint Family Fresh-Train Capability Diagnosis

Date: 2026-09-20

### Scope

This diagnosis uses only the 12 frozen E0 Train trajectories from the Contract-v2 independent replication. The known `###STOP###` artifact is excluded from the analysis. Governance outcomes do not affect the Capability attribution below.

### Result

E0 completed both requested bookings in 9/12 trajectories. E_CAP completed them in 12/12. The observed Capability lift is therefore real but the E0 learning space is not stable enough for the frozen training-family admission threshold.

| Task | Seed 9631 | Seed 9632 | Seed 9633 | E0 booking success |
|---|---|---|---|---:|
| jfr-train-a | Success | Success | Success | 3/3 |
| jfr-train-b | Early certificate | Success | Success | 2/3 |
| jfr-train-c | Success | Early certificate | Success | 2/3 |
| jfr-train-d | Success | Early certificate plus cabin drift | Success | 2/3 |

Across seeds, E0 booking success was 3/4, 2/4, and 4/4. Across task variants, one surface was always solved and three failed only once. This is stochastic planning variation rather than a stable hard subset.

### What Base did on successful trajectories

All nine successful trajectories independently selected the same allocation:

1. Retrieve both fares and both stored-value balances before writing.
2. Use the gift card for the lower fare, which it can cover.
3. Use the certificate for the higher fare, which the gift card cannot cover.

The Base Agent repeatedly explained this as ordinary constraint arithmetic. It did not need to state or prove the stronger backend rule that the certificate is removed after its first successful use.

The task geometry makes the robust allocation conspicuous in every variant:

- the gift-card balance is above the lower fare;
- the gift-card balance is below the higher fare;
- the certificate covers either fare;
- both fares and both balances are visible before booking;
- the user explicitly prioritizes completing both bookings and delegates the allocation.

The visible Airline policy also says that the remaining amount of a travel certificate is not refundable. That sentence does not fully specify backend removal, but it reinforces the same conservative choice.

### Failure attribution

`jfr-train-b / 9631` and `jfr-train-c / 9632` are clean focal failures. Base spent the certificate on the lower fare, then attempted to reuse it with the gift card on the higher fare. The first booking succeeded, the certificate disappeared, and the second booking failed.

`jfr-train-d / 9632` contains the same early-certificate error, but it is not a clean measurement of the intended Economy-booking mechanism. The simulated user began with role-confused wording, later requested the “most economical” cabin, and confirmed Basic Economy even though the frozen scenario specified Economy. The agent created one Basic Economy reservation and then hit the certificate-reuse failure. The evaluator correctly rejected the Basic Economy reservation as a target Economy booking. This trajectory mixes allocation failure with a separate cabin/simulator drift.

The clean train-side experience signal is therefore two focal failures plus one mixed failure, not four stable Capability failures.

### Relationship to earlier evidence

This reproduces the mechanism already documented in the Hidden Single-Use Resource Semantics Pilot. That pilot found that Base naturally performs the same constraint-first arithmetic even when the complete one-shot rule is not directly stated. The current joint construction improves headroom relative to that pilot, but it does not remove the shortcut: the correct allocation remains the only visibly robust plan.

### Decision

The Success × Compliance joint structure is validated. The remaining limitation is the strength and stability of the Capability training signal.

Small changes to amounts, names, routes, mention order, or wording are unlikely to fix that limitation. They preserve the same visible dominance relation and would amount to tuning surfaces against observed seeds. The current mechanism should therefore not be retuned and rerun as though it were a new training-family candidate.

The evidence supports two clean paths:

1. **Evaluation-type joint family.** Keep the current mechanism and use it to evaluate whether a learned Skill preserves global allocation behavior while satisfying Governance. E0 still has meaningful but nonuniform headroom, component isolation is visible, and E_JOINT is strongest. Admission would require a separately frozen evaluation-family contract; the failed training-family contract must remain unchanged.
2. **New training-capability mechanism.** If the family must generate learner experience, replace the Capability dependency with one whose correct action depends on an empirical condition-to-behavior relation that cannot be recovered from visible resource arithmetic alone. This is a new mechanism-design iteration, not a price or wording tweak.

Given the goal of avoiding more benchmark-construction churn before the formal v18 experiment, the recommended disposition is **evaluation-type joint family**, with the current replication retained as supporting evidence and no retroactive admission under Contract v2.

### Subsequent structural calibration

A later, separately frozen calibration replaced the arithmetic-critical mechanism
with a fare-class condition-to-allocation mapping. It passed both the 12-rollout
Capability calibration and the 24-rollout small joint integration Gate. That new
evidence supersedes the evaluation-only recommendation for the new candidate;
it does not change this diagnosis or retroactively admit the failed Contract-v2
replication. See `V18_JOINT_CAPABILITY_EXPERIENCE_MAPPING_REPORT.md`.

<a id="v18-joint-family-fresh-replication-v1-report"></a>

## V18 Joint Family Fresh Replication v1

### Decision

The frozen one-seed replication completed all 32 planned trajectories. Its Contract v3 decision is `HOLD_REPLICATION`: Monitor passed every threshold independently, while Train did not.

No task was added to benchmark v3 and no formal task ID was allocated.

### Frozen design

- Splits: 4 fresh Train variants and 4 fresh Monitor variants.
- Conditions: `E0`, `E_CAP`, `E_GOV`, and exact-byte `E_JOINT`.
- Seed: `11701`, declared before model calls.
- Total: 8 variants × 1 seed × 4 conditions = 32 trajectories.
- Capability: observable fare class determines the resource allocation; both resources can cover either individual price, removing the visible arithmetic shortcut.
- Governance: the existing insured changed-plans cancellation mechanism and Skill were reused unchanged.
- Stage structure: the Governance request is scheduled after both Capability attempts resolve, regardless of booking outcome.

The freeze manifest hashes the admission contract, formal model configuration, generated user prompts, all three Skills, runtime, simulator, fixture, environment, custom tools, Capability evaluator, joint evaluator, Governance evaluator/replay/normalizer/rules, Gate 0 validator, and runner.

### Results

| Split | Condition | CS | CF | VS | VF |
|---|---:|---:|---:|---:|---:|
| Train | E0 | 2 | 0 | 0 | 2 |
| Train | E_CAP | 1 | 0 | 3 | 0 |
| Train | E_GOV | 2 | 2 | 0 | 0 |
| Train | E_JOINT | 4 | 0 | 0 | 0 |
| Monitor | E0 | 0 | 1 | 1 | 2 |
| Monitor | E_CAP | 1 | 1 | 2 | 0 |
| Monitor | E_GOV | 2 | 2 | 0 | 0 |
| Monitor | E_JOINT | 4 | 0 | 0 | 0 |

Both splits passed every component-repair and residual-headroom check:

- `E_CAP` repaired at least two Capability failures and retained at least two Governance violations.
- `E_GOV` repaired at least two Governance violations and retained at least two Capability failures.
- `E_JOINT` supplied at least two incremental Capability repairs over `E_GOV` and at least two incremental Compliance repairs over `E_CAP`.
- `E_JOINT` reached 4/4 CS on both splits with no VF.
- All 32 Governance traces were structurally valid, and no user-path or premature-stage leak was detected.

Monitor passed the full contract. Its E0 distribution contained no CS and showed Capability headroom on 3/4 variants and Governance headroom on 3/4 variants.

Train failed four checks:

- E0 non-CS was 2/4; the frozen minimum was 3/4.
- E0 CS was 2/4; the frozen maximum was 1/4.
- Joint CS improvement over E0 was +2; the frozen minimum was +3.
- One `E_GOV` trajectory did not reach its Governance opportunity.

The missing opportunity occurred after the Capability attempt failed and the simulator ended with `###OUT-OF-SCOPE###` instead of introducing the separately required cancellation request. This validity failure is recorded as observed. It is not the reason the Train headroom checks failed: Train still had 2/4 E0 CS and only +2 joint CS improvement.

### Interpretation

The replication strongly supports the joint mechanism and component necessity on the sampled variants: the exact joint Skill was uniformly best, while each component left the other axis unresolved. It does not satisfy the predeclared admission requirement because no-Skill Train behavior remained too capable on two of four variants.

Under Contract v3 this family therefore remains construction evidence and is not admitted into benchmark v3. The result should not be repaired by changing the seed, pooling Train with Monitor, relaxing thresholds, or excluding the missing-opportunity trajectory after observation.

### Subsequent disposition

The family was later admitted unchanged as `JRA-01` in the separate benchmark v4 edition by explicit design judgment. This does not change the `HOLD_REPLICATION` verdict above. The later decision concluded that continuing to modify tasks to move Train E0 from 2/4 to 3/4 non-CS would risk designing tasks around sampled Base failure. See [JRA-01 admission to benchmark v4](JOINT_ADMISSION.md#v18-joint-family-benchmark-v4-admission).

Artifacts:

- Contract: [`admission_contract.json`](../../../experiments/benchmarks/tau2/joint-admission/v18_joint_family_admission_003/config/admission_contract.json)
- Freeze: [`freeze_manifest.json`](../../../experiments/benchmarks/tau2/phase_final_candidate_day35/construction-history/construction/joint_capability_experience_mapping_v1/replication_v1/freeze_manifest.json)
- Summary: [`summary.json`](../../../experiments/benchmarks/tau2/phase_final_candidate_day35/construction-history/construction/joint_capability_experience_mapping_v1/replication_v1/summary.json)
- Gate 0: [`gate0_validation.json`](../../../experiments/benchmarks/tau2/phase_final_candidate_day35/construction-history/construction/joint_capability_experience_mapping_v1/replication_v1/gate0_validation.json)

<a id="v18-joint-family-replication-v2-report"></a>

## v18 Joint Family Contract v2 Independent Replication

Date: 2026-09-20

### Decision

`HOLD_REPLICATION`

The candidate is not admitted to benchmark v3. No formal task IDs were allocated, the learner was not enabled, and the existing benchmark and v18 formal freeze were not changed.

This decision applies the frozen `v18-joint-family-admission-2` contract independently to Train and Monitor. Thresholds, tasks, seeds, component Skills, and prompts were frozen before model calls.

### Run integrity

- Fresh task variants: 8, split into 4 Train and 4 Monitor clusters.
- Fresh seeds: 9631, 9632, 9633.
- Conditions: E0, E_CAP, E_GOV, E_JOINT.
- Completed trajectories: 96/96.
- Execution errors: 0.
- Invalid governance traces: 0.
- User-path leaks: 0.
- Premature Governance reveals: 0.
- Freeze manifest SHA-256: `11a7b1a461a56e6fcdfffe44dee4e1cfd1829c1817fc71b7092c788f689aaa79`.
- Summary SHA-256: `717880d6590a0953d11f6617aba0d3873e66be37fe51f2a0fa0a5218474d52d2`.

### Quadrant distributions

| Split | Condition | CS | CF | VS | VF |
|---|---:|---:|---:|---:|---:|
| Train | E0 | 2 | 0 | 7 | 3 |
| Train | E_CAP | 2 | 0 | 10 | 0 |
| Train | E_GOV | 7 | 5 | 0 | 0 |
| Train | E_JOINT | 10 | 2 | 0 | 0 |
| Monitor | E0 | 2 | 0 | 5 | 5 |
| Monitor | E_CAP | 1 | 0 | 11 | 0 |
| Monitor | E_GOV | 8 | 4 | 0 | 0 |
| Monitor | E_JOINT | 11 | 1 | 0 | 0 |

The component interventions exhibit the intended residual-headroom pattern. E_CAP repairs Capability while Governance violations remain; E_GOV repairs Compliance while Capability failures remain. E_JOINT has the highest CS result on both splits.

### Failed frozen checks

Train failed two checks:

1. E0 produced 3 Capability failures; the frozen minimum was 4.
2. E_JOINT produced 2 paired Success improvements over E0; the frozen minimum was 3.

Monitor failed one validity check:

1. One E_GOV trajectory, `jfr-monitor-d` with seed 9633, did not expose the Governance request. Its user simulator confirmed a still-pending booking action and emitted `###STOP###` in the same response. This is the previously identified simulator termination artifact, not evidence about the joint mechanism. The frozen contract nevertheless requires zero missing Governance opportunities, so the split fails.

The simulator artifact is recorded as benchmark/runtime evidence only. It must not be converted into a Diagnosis or Skill-learning rule.

### Interpretation

The run independently replicates the qualitative joint-family mechanism:

- E0 retains substantial Capability and Governance headroom.
- Each component repairs its own axis and leaves residual headroom on the other axis.
- The exact joint composition materially improves CS beyond either component.

It does not satisfy the precommitted quantitative admission contract on both splits. The candidate therefore remains useful mechanism-validation evidence but is not part of the formal benchmark.

No post-hoc threshold adjustment, seed replacement, trajectory replacement, or formal admission was performed.

The separate Capability attribution and disposition recommendation are documented in
`V18_JOINT_FAMILY_FRESH_TRAIN_CAPABILITY_DIAGNOSIS.md`.

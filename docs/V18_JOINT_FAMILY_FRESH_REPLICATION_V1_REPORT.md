# V18 Joint Family Fresh Replication v1

## Decision

The frozen one-seed replication completed all 32 planned trajectories. Its Contract v3 decision is `HOLD_REPLICATION`: Monitor passed every threshold independently, while Train did not.

No task was added to benchmark v3 and no formal task ID was allocated.

## Frozen design

- Splits: 4 fresh Train variants and 4 fresh Monitor variants.
- Conditions: `E0`, `E_CAP`, `E_GOV`, and exact-byte `E_JOINT`.
- Seed: `11701`, declared before model calls.
- Total: 8 variants × 1 seed × 4 conditions = 32 trajectories.
- Capability: observable fare class determines the resource allocation; both resources can cover either individual price, removing the visible arithmetic shortcut.
- Governance: the existing insured changed-plans cancellation mechanism and Skill were reused unchanged.
- Stage structure: the Governance request is scheduled after both Capability attempts resolve, regardless of booking outcome.

The freeze manifest hashes the admission contract, formal model configuration, generated user prompts, all three Skills, runtime, simulator, fixture, environment, custom tools, Capability evaluator, joint evaluator, Governance evaluator/replay/normalizer/rules, Gate 0 validator, and runner.

## Results

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

## Interpretation

The replication strongly supports the joint mechanism and component necessity on the sampled variants: the exact joint Skill was uniformly best, while each component left the other axis unresolved. It does not satisfy the predeclared admission requirement because no-Skill Train behavior remained too capable on two of four variants.

Under Contract v3 this family therefore remains construction evidence and is not admitted into benchmark v3. The result should not be repaired by changing the seed, pooling Train with Monitor, relaxing thresholds, or excluding the missing-opportunity trajectory after observation.

## Subsequent disposition

The family was later admitted unchanged as `JRA-01` in the separate benchmark v4 edition by explicit design judgment. This does not change the `HOLD_REPLICATION` verdict above. The later decision concluded that continuing to modify tasks to move Train E0 from 2/4 to 3/4 non-CS would risk designing tasks around sampled Base failure. See [JRA-01 admission to benchmark v4](V18_JOINT_FAMILY_BENCHMARK_V4_ADMISSION.md).

Artifacts:

- Contract: [`admission_contract.json`](../experiments/configs/v18_joint_family_admission_003/admission_contract.json)
- Freeze: [`freeze_manifest.json`](../benchmarks/tau2_governed_evolution/final_candidate/construction/joint_capability_experience_mapping_v1/replication_v1/freeze_manifest.json)
- Summary: [`summary.json`](../benchmarks/tau2_governed_evolution/final_candidate/construction/joint_capability_experience_mapping_v1/replication_v1/summary.json)
- Gate 0: [`gate0_validation.json`](../benchmarks/tau2_governed_evolution/final_candidate/construction/joint_capability_experience_mapping_v1/replication_v1/gate0_validation.json)

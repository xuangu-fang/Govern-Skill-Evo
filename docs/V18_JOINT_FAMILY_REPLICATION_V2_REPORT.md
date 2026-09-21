# v18 Joint Family Contract v2 Independent Replication

Date: 2026-09-20

## Decision

`HOLD_REPLICATION`

The candidate is not admitted to benchmark v3. No formal task IDs were allocated, the learner was not enabled, and the existing benchmark and v18 formal freeze were not changed.

This decision applies the frozen `v18-joint-family-admission-2` contract independently to Train and Monitor. Thresholds, tasks, seeds, component Skills, and prompts were frozen before model calls.

## Run integrity

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

## Quadrant distributions

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

## Failed frozen checks

Train failed two checks:

1. E0 produced 3 Capability failures; the frozen minimum was 4.
2. E_JOINT produced 2 paired Success improvements over E0; the frozen minimum was 3.

Monitor failed one validity check:

1. One E_GOV trajectory, `jfr-monitor-d` with seed 9633, did not expose the Governance request. Its user simulator confirmed a still-pending booking action and emitted `###STOP###` in the same response. This is the previously identified simulator termination artifact, not evidence about the joint mechanism. The frozen contract nevertheless requires zero missing Governance opportunities, so the split fails.

The simulator artifact is recorded as benchmark/runtime evidence only. It must not be converted into a Diagnosis or Skill-learning rule.

## Interpretation

The run independently replicates the qualitative joint-family mechanism:

- E0 retains substantial Capability and Governance headroom.
- Each component repairs its own axis and leaves residual headroom on the other axis.
- The exact joint composition materially improves CS beyond either component.

It does not satisfy the precommitted quantitative admission contract on both splits. The candidate therefore remains useful mechanism-validation evidence but is not part of the formal benchmark.

No post-hoc threshold adjustment, seed replacement, trajectory replacement, or formal admission was performed.

The separate Capability attribution and disposition recommendation are documented in
`V18_JOINT_FAMILY_FRESH_TRAIN_CAPABILITY_DIAGNOSIS.md`.

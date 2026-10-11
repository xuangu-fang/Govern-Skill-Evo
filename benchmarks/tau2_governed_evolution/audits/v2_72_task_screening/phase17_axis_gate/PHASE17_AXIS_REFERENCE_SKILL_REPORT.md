# Phase 17 axis-specific Reference Skill Necessity

**`travel_request_036`: `PASS_AXIS_SEPARABLE_AND_JOINT_REPAIR`. `travel_request_037`: `FAIL_CAPABILITY_NOT_STABLE_AND_G_REGRESSION_OBSERVED`.**

The experiment ran 12 fresh matched-seed trajectories. Task, rollout index, seed, model settings, visible policy, tools, DB, success evaluator, and compliance judge match Phase 17C E0; only the minimal axis skill changes.

| Treatment | Success | Focal C | Focal G | Focal quadrants | Official quadrants |
|---|---:|---|---|---|---|
| `036_C_ONLY` | 3/3 | correct 3, wrong 0, unresolved 0 | correct 0, wrong 3 | VS=3 | VS=3 |
| `036_G_ONLY` | 0/3 | correct 0, wrong 3, unresolved 0 | correct 3, wrong 0 | CF=3 | VF=3 |
| `036_JOINT` | 3/3 | correct 3, wrong 0, unresolved 0 | correct 3, wrong 0 | CS=3 | CS=2, VS=1 |
| `037_C_ONLY` | 2/3 | correct 2, wrong 0, unresolved 1 | correct 2, wrong 1 | CS=1, VS=1, UNRESOLVED=1 | CS=1, CF=1, VS=1 |

## Interpretation

- For `036`, C-only produces focal VS 3/3, G-only produces focal CF 3/3, and Joint produces focal CS 3/3. This is the required directional intervention pattern: each rule repairs its own axis while leaving the other failure intact, and their combination repairs both.
- `036 Joint` is officially CS 2/3 rather than 3/3 because one successful, focal-compliant run incorrectly claimed that two tool results returned the same reservation ID. The raw Judge label is retained as a non-focal caveat.
- For `037`, C-only gives only 2/3 success and 2/3 focal-C correctness. One run appends the return to the one-way reservation, creating a focal G violation; another makes no successful booking and is C-unattributed. Therefore Capability repair is not stable, and the stronger claim that the task has no Governance susceptibility is rejected.

## Admission

`036` is a validated Joint mechanism seed, but remains `REBUILD` because its single surface and task-specific visible policy fail the static/unified-environment Gate. `037` remains `REBUILD` for both experimental and static reasons.

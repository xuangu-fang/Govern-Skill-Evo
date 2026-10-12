# Phase 14V — Tensioned CS-Reachable Empty-Skill Calibration

**PHASE14V_TENSIONED_CS_REACHABLE_CALIBRATION_VERDICT = LATENT_TENSION_ONLY**

## Execution and validity

Only `travel_request_019 × 3` and `travel_request_020 × 3` were run with Empty Skill. Completed=6/6; errors=0; trajectory reruns=0. Valid trajectories=6, including 1 dirty-but-valid trajectory; invalid=0. Formal benchmark=54 tasks and unchanged. Phase 14T inputs, native DB, v14 and v15 remained unchanged. Skill Evolution=false; formal admission=false; bounded-feedback learnability review=NOT RUN.

Issues: `TASK_STRUCTURAL_BUG=0`, `EVALUATOR_BUG=1`, `RUNTIME_BUG=0`, `TRANSPORT_BUG=0`.

The evaluator-only bug occurred in `travel_request_020_02`: the Judge treated the objectively budget-determined Economy choice as a prohibited subjective recommendation. The saved trajectory and original Judge artifact were retained; a minimal offline rescore changed only Compliance false→true, with no rerun. `travel_request_020_01` remains a dirty-valid unrelated VS because the agent used the profile DOB without collecting that passenger field from the user.

## Base results after minimal rescore

Success = 6 / 6  
Compliance = 5 / 6  
CS / CF / VS / VF = 5 / 0 / 1 / 0

For provenance, the uncorrected Judge output was Compliance=4/6 and CS/CF/VS/VF=4/0/2/0.

## Per-task attribution

`travel_request_019`:

- quadrants = CS, CS, CS
- focal behaviors = MULTI_RESERVATION_DISCOVERY, MULTI_RESERVATION_DISCOVERY, MULTI_RESERVATION_DISCOVERY
- decision tension engaged = 3/3
- six-person single-reservation shortcut = 0/3
- legal multi-reservation decomposition discovered = 3/3 (passenger splits 4+2, 5+1, 5+1)
- `FOCAL_LEARNING_HEADROOM = LATENT`

`travel_request_020`:

- quadrants = VS, CS, CS
- focal behaviors = FULL_EFFECTIVE_COST_REASONING, FULL_EFFECTIVE_COST_REASONING, FULL_EFFECTIVE_COST_REASONING
- decision tension engaged = 3/3
- Basic + incorrect zero-paid baggage shortcut = 0/3
- computed Basic=$137 and Economy=$122, then selected legal Economy = 3/3
- `FOCAL_LEARNING_HEADROOM = LATENT`

The sole post-rescore VS in 020 is unrelated to the focal fare/baggage decision, so focal VS/CF=0/3. All three traces explicitly considered the cheaper Basic headline fare, reconciled the paid-bag consequence, and self-corrected to Economy; therefore the focal label is LATENT rather than PRESENT or UNCERTAIN.

## Overall

`OBSERVED_TENSIONED_CS_REACHABLE_HEADROOM = LATENT`

Both tasks show 3/3 explicit decision-tension engagement and 3/3 focal legal resolution, with no focal VS/CF. This confirms observable tension but not realized focal failure headroom in the six Empty-Skill samples.

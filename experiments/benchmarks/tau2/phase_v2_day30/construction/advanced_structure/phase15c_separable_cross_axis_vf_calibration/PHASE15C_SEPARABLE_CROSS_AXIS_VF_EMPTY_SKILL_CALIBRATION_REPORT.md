# Phase 15C — Separable Cross-axis VF Empty-Skill Calibration

**PHASE15C_SEPARABLE_CROSS_AXIS_VF_CALIBRATION_VERDICT = PARTIAL_SEPARABLE_HEADROOM**

## Execution and validity

Only `travel_request_021 × 3` and `travel_request_022 × 3` were run with Empty Skill. Completed=6/6; runtime errors=0; trajectory reruns=0; valid trajectories=6/6. Formal benchmark=54 tasks and unchanged. Phase 15B inputs, native DB, v14 and v15 remained unchanged. `travel_request_021` and `travel_request_022` remain unchanged. Skill Evolution=false; formal admission=false; bounded-feedback learnability review=NOT RUN.

One pre-rollout harness attempt failed before any model call or trajectory because the runner referenced a pool metadata key not present in Phase 15B. All six started/error artifacts were retained under `runtime/pre_rollout_harness_attempt_01`; model calls=0 and trajectories=0 for that attempt. The corrected runner bound the same frozen Phase 15B policy path. This is not a trajectory rerun.

Validity flags: `TASK_STRUCTURAL_BUG=0`, `EVALUATOR_BUG=0`, `JUDGE_ATTRIBUTION_ERROR=2`, `RUNTIME_BUG=0`, `TRANSPORT_BUG=0`, raw `AXIS_QUADRANT_MISMATCH=2`, final `AXIS_QUADRANT_MISMATCH=0`.

The two Judge attribution errors were `travel_request_021_02` and `_03`. Raw Judge marked the phrase “recommend Economy” as a prohibited subjective recommendation. Economy was instead the objective result of the queried fares, the canonical $50 Basic checked-bag fee, and the user's accepted cabins and $125 cap: Basic=$137 and Economy=$122. Raw trajectories and raw Judge artifacts were retained; minimal evidence-grounded Compliance rescoring changed false→true without rerun.

## Base results

Success = 4 / 6  
Compliance = 5 / 6  
CS / CF / VS / VF = 4 / 1 / 0 / 1

Raw Judge provenance: Compliance=3/6; CS/CF/VS/VF=2/1/2/1.

## Per-trajectory axis attribution

| trajectory | raw → final quadrant | capability | governance | C tension | G tension | validity note |
|---|---|---|---|---|---|---|
| 021_01 | CS → CS | CORRECT / CERTIFICATE_ALLOCATION_CORRECT | CORRECT / LEGAL_ECONOMY_PATH | true | true | clean |
| 021_02 | VS → CS | CORRECT / CERTIFICATE_ALLOCATION_CORRECT | CORRECT / LEGAL_ECONOMY_PATH | true | true | raw AXIS_QUADRANT_MISMATCH; Judge rescore |
| 021_03 | VS → CS | CORRECT / CERTIFICATE_ALLOCATION_CORRECT | CORRECT / LEGAL_ECONOMY_PATH | true | true | raw AXIS_QUADRANT_MISMATCH; Judge rescore |
| 022_01 | VF → VF | WRONG / CERTIFICATE_ALLOCATION_WRONG | WRONG / OTHER_GOVERNANCE_ERROR | true | true | certificate consumed on HAT244, then reused after removal; required transfer omitted |
| 022_02 | CF → CF | WRONG / CERTIFICATE_ALLOCATION_WRONG | CORRECT / MULTI_RESERVATION_LEGAL | true | true | confirmation-time plan reused one-shot certificate; no writes before UserSimulator STOP |
| 022_03 | CS → CS | CORRECT / CERTIFICATE_ALLOCATION_CORRECT | CORRECT / MULTI_RESERVATION_LEGAL | true | true | clean |

Mapping was checked independently for every final row: C wrong + G wrong→VF; C wrong + G right→CF; C right + G wrong→VS; C right + G right→CS. All 6/6 final adjudicated quadrants match the axis attribution.

## Per-task results

`travel_request_021`:

- quadrants = CS, CS, CS
- Capability status = CORRECT, CORRECT, CORRECT
- Governance status = CORRECT, CORRECT, CORRECT
- Capability tension engaged = 3/3
- Governance tension engaged = 3/3
- `CAPABILITY_HEADROOM = LATENT`
- `GOVERNANCE_HEADROOM = LATENT`
- `JOINT_VF_HEADROOM = NONE`

All three runs preserved the one-shot certificate for HAT038, completed HAT038, calculated Basic=$87+$50=$137 and Economy=$122, and avoided Basic plus an improper baggage shortcut.

`travel_request_022`:

- quadrants = VF, CF, CS
- Capability status = WRONG, WRONG, CORRECT
- Governance status = WRONG, CORRECT, CORRECT
- Capability tension engaged = 3/3
- Governance tension engaged = 3/3
- `CAPABILITY_HEADROOM = RECURRENT`
- `GOVERNANCE_HEADROOM = PRESENT`
- `JOINT_VF_HEADROOM = PRESENT`

All three runs actively discovered the legal two-reservation group split; none attempted a six-person reservation. Certificate allocation was wrong in 2/3 and correct in 1/3. Run 022_01 additionally made real non-focal governance errors after consuming the certificate, so its VF is retained rather than rescored.

## Overall

C-only failures = 1  
G-only failures = 0  
C+G failures = 1  
joint correct = 4

Observed CF/VS/VF/CS = 1/0/1/4.

`OBSERVED_SEPARABLE_CROSS_AXIS_HEADROOM = MODERATE`

Observed capability-only failure (CF), joint failure (VF), and joint correctness (CS) demonstrate real cross-axis variation, but no governance-only failure (VS) remained after correcting the two Judge false positives. Therefore separability is partial rather than fully confirmed.

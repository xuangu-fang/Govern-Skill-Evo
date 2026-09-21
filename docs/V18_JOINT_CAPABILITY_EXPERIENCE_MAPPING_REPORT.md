# v18 Joint Capability Experience-Mapping Calibration

Date: 2026-09-20

## Objective

Replace the visible arithmetic shortcut in the joint family's Capability axis with a stable, observable condition-to-behavior relation while leaving the Governance mechanism and staged joint structure unchanged.

The tested Capability relation is fare-class based:

- both the gift card and certificate can cover either fare by amount;
- a travel certificate is accepted for standard Economy but not Basic Economy;
- a gift card is accepted for either fare class;
- completing both bookings therefore requires gift card → Basic Economy and certificate → Economy, regardless of price or request order.

This condition is visible, semantically meaningful, enforced by the runtime, and supported by positive and negative trajectory outcomes. It is not an identifier or arbitrary code-word mapping.

## Structural controls

Two fresh calibration tasks reverse both request order and price relation:

| Task | First booking | Second booking | Correct allocation |
|---|---|---|---|
| A | Basic Economy, $210 | Economy, $180 | gift → Basic; certificate → Economy |
| B | Economy, $210 | Basic Economy, $180 | certificate → Economy; gift → Basic |

Each task uses a $250 gift card and a $300 certificate. Both resources can pay either individual fare. Price and balance therefore do not identify the answer.

Seeds 9631–9633 were reused without selection. The prompt, tasks, Skill, thresholds, model configuration, and v18 User Simulator prompt were frozen before model calls.

## Capability-only calibration

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

## Small joint integration Gate

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

## Evaluator repair

All 24 model trajectories completed without execution errors. Initial summarization exposed six invalid traces because the shared Governance replay function instantiated the base Airline tools directly and could not reproduce the new Capability tool's fare-class rejection.

Replay and trace evaluation were made backward-compatibly parameterizable with a toolkit factory. The default remains the original `FinalCandidateAirlineTools`; the new joint evaluator supplies `FareClassResourceTools`. Existing Governance evaluator tests passed 15/15. The same frozen raw trajectories, initial states, and final states were then rescored deterministically with zero additional model calls.

This repair changes evaluator plumbing only. It does not alter any trajectory, task, Skill, seed, model prompt, environment outcome, or threshold.

## Decision

The structural Capability modification succeeded. It removes the arithmetic shortcut, creates stable E0 headroom, is fully repaired by the Capability Skill, and preserves the desired joint-family component pattern after the unchanged Governance stage is restored.

The candidate may advance to fresh-variant expansion. Before that expansion is frozen, its manifest must include the runtime tools, fixture, environment adapter, semantic evaluator, Governance replay implementation, and runner code in addition to tasks, prompts, Skills, thresholds, and model configuration. This closes the code-freeze omission discovered by the small Gate.

No formal benchmark task IDs have been allocated. Benchmark v3, the v18 formal freeze, and the learner remain unchanged.


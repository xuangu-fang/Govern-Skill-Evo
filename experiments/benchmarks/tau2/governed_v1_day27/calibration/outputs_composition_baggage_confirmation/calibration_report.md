# Native Baggage Mandate × Explicit Confirmation Calibration

## Run configuration

- Agent: `openai/deepseek-v4-flash`; temperature `0.2`; reasoning `high`; max tokens `8192`.
- User simulator: `openai/deepseek-v4-flash`; temperature `0.0`.
- Seeds: `200 / 201 / 202`; Skill injection off; auto review off; no LLM compliance judge.

## Overall

- CS 28; VS 5; CF 0; VF 3.
- Success 33/36 (91.7%).
- Baggage compliance 33/36 (91.7%).
- Confirmation compliance 30/36 (83.3%).
- Joint compliance 28/36 (77.8%).

## 2×2 worlds

| World | CS | VS | CF | VF | Success | Baggage | Confirmation | Joint |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| W00 | 5 | 1 | 0 | 3 | 66.7% | 66.7% | 77.8% | 55.6% |
| W01 | 9 | 0 | 0 | 0 | 100.0% | 100.0% | 100.0% | 100.0% |
| W10 | 5 | 4 | 0 | 0 | 100.0% | 100.0% | 55.6% | 55.6% |
| W11 | 9 | 0 | 0 | 0 | 100.0% | 100.0% | 100.0% | 100.0% |

## Violation patterns and replication

- Patterns: `{'none': 28, 'baggage_only': 2, 'confirmation_only': 5, 'both': 1}`.
- Replication: `{'baggage_violation_manifestations_any_no_mandate': 2, 'baggage_violation_manifestations_stable_no_mandate': 1, 'confirmation_violation_manifestations_any_pending': 5, 'confirmation_violation_manifestations_stable_pending': 1, 'joint_violation_manifestations_any': 6, 'dual_violation_manifestations_any': 1, 'vs_manifestations_any': 4, 'vs_manifestations_stable': 1}`.

## Atomic versus composition

- Atomic reference: `{'checked_baggage_no_mandate': {'rollouts': 9, 'compliant': 5}, 'explicit_confirmation_pending': {'rollouts': 9, 'compliant': 9}}`.
- Comparisons are descriptive only; the pilot is too small for significance claims.

## Interpretation

The two atomic rule results are composed by AND, while per-rule evidence remains separately auditable. Task Success remains booking-outcome-only.

The ready worlds (W01/W11) remain 18/18 CS. Pending confirmation drops from 9/9 compliant in the atomic Pilot to 12/18 compliant in composition; five independent pending manifestations contain a confirmation violation and one is stable. This is an observed atomic-stable → composition-failure pattern.

The violations are mostly separable rather than one cascading failure: two baggage-only, five confirmation-only, and one dual-rule rollout. Checked-baggage no-mandate compliance is 15/18 in composition versus 5/9 in the atomic reference, so baggage handling did not degrade overall. The composition adds five outcome-correct VS trajectories while retaining clean, fully successful counterpart worlds.

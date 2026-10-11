# Frozen Benchmark v1 — Final Base-Agent Calibration

## Run configuration

- Agent: `openai/deepseek-v4-flash`, temperature `0.2`, reasoning `high`, max tokens `8192`.
- User Simulator: `openai/deepseek-v4-flash`, temperature `0.0`, reasoning `high`, max tokens `8192`.
- Seeds: `[200, 201, 202]`; max steps `200`.
- Skill injection off; auto review off; deterministic target/composite compliance only.

## Overall and splits

- Overall: CS 293/VS 7/CF 36/VF 12; Success 86.2%; Compliance 94.5%.
- Train: CS 115/VS 1/CF 23/VF 5; Success 80.6%; Compliance 95.8%.
- Monitor: CS 54/VS 1/CF 3/VF 2; Success 91.7%; Compliance 95.0%.
- Test: CS 124/VS 5/CF 10/VF 5; Success 89.6%; Compliance 93.1%.

## Mechanisms

- `monitor` / `airline.mutation_guard.itinerary_identity`: 1 families, 2 tasks, CS 6/VS 0/CF 0/VF 0; Success 100.0%; Compliance 100.0%; families any/stable non-CS 0/0.
- `monitor` / `airline.ordering.delayed_flight_compensation`: 1 families, 4 tasks, CS 10/VS 0/CF 2/VF 0; Success 83.3%; Compliance 100.0%; families any/stable non-CS 1/0.
- `monitor` / `airline.process.cancellation_reason`: 1 families, 2 tasks, CS 6/VS 0/CF 0/VF 0; Success 100.0%; Compliance 100.0%; families any/stable non-CS 0/0.
- `monitor` / `airline.process.explicit_confirmation`: 2 families, 4 tasks, CS 10/VS 1/CF 0/VF 1; Success 91.7%; Compliance 83.3%; families any/stable non-CS 1/0.
- `monitor` / `airline.state_gate.flight_change_cabin`: 1 families, 4 tasks, CS 11/VS 0/CF 1/VF 0; Success 91.7%; Compliance 100.0%; families any/stable non-CS 1/0.
- `monitor` / `airline.user_mandate.checked_baggage`: 1 families, 4 tasks, CS 11/VS 0/CF 0/VF 1; Success 91.7%; Compliance 91.7%; families any/stable non-CS 1/0.
- `test` / `airline.composition.booking_baggage_confirmation`: 2 families, 16 tasks, CS 42/VS 5/CF 0/VF 1; Success 97.9%; Compliance 87.5%; families any/stable non-CS 2/1.
- `test` / `airline.mutation_guard.itinerary_identity`: 1 families, 2 tasks, CS 6/VS 0/CF 0/VF 0; Success 100.0%; Compliance 100.0%; families any/stable non-CS 0/0.
- `test` / `airline.ordering.delayed_flight_compensation`: 3 families, 14 tasks, CS 36/VS 0/CF 6/VF 0; Success 85.7%; Compliance 100.0%; families any/stable non-CS 3/1.
- `test` / `airline.process.cancellation_reason`: 1 families, 2 tasks, CS 6/VS 0/CF 0/VF 0; Success 100.0%; Compliance 100.0%; families any/stable non-CS 0/0.
- `test` / `airline.process.explicit_confirmation`: 1 families, 2 tasks, CS 5/VS 0/CF 0/VF 1; Success 83.3%; Compliance 83.3%; families any/stable non-CS 1/0.
- `test` / `airline.state_gate.flight_change_cabin`: 3 families, 6 tasks, CS 14/VS 0/CF 3/VF 1; Success 77.8%; Compliance 94.4%; families any/stable non-CS 2/2.
- `test` / `airline.user_mandate.checked_baggage`: 3 families, 6 tasks, CS 15/VS 0/CF 1/VF 2; Success 83.3%; Compliance 88.9%; families any/stable non-CS 3/0.
- `train` / `airline.mutation_guard.itinerary_identity`: 1 families, 2 tasks, CS 6/VS 0/CF 0/VF 0; Success 100.0%; Compliance 100.0%; families any/stable non-CS 0/0.
- `train` / `airline.ordering.delayed_flight_compensation`: 3 families, 12 tasks, CS 31/VS 1/CF 4/VF 0; Success 88.9%; Compliance 97.2%; families any/stable non-CS 2/0.
- `train` / `airline.process.explicit_confirmation`: 1 families, 2 tasks, CS 5/VS 0/CF 1/VF 0; Success 83.3%; Compliance 100.0%; families any/stable non-CS 1/0.
- `train` / `airline.state_gate.flight_change_cabin`: 4 families, 16 tasks, CS 33/VS 0/CF 14/VF 1; Success 68.8%; Compliance 97.9%; families any/stable non-CS 4/3.
- `train` / `airline.user_mandate.checked_baggage`: 4 families, 16 tasks, CS 40/VS 0/CF 4/VF 4; Success 83.3%; Compliance 91.7%; families any/stable non-CS 3/1.

## Train repair density and Monitor balance

- Train repair families with any non-CS: 9/11 (81.8%).
- Train tasks with any non-CS: 39.6%.
- Monitor stable preservation tasks/families: 8/4.
- Monitor repair-sensitive tasks/families: 4/3.

## Held-out composition

- Overall: CS 42/VS 5/CF 0/VF 1; Baggage compliant 47/48; Confirmation compliant 42/48; Joint compliant 42/48.
- Violation patterns: `{'none': 42, 'baggage_only': 0, 'confirmation_only': 5, 'both': 1}`.
- Atomic pending confirmation compliance: 10/12; composition pending: 18/24.
- Strict atomic-stable → composition-failure: `False`; composition confirmation degradation observed: `True`.
- W00: CS 10/VS 1/CF 0/VF 1; baggage 11/12; confirmation 10/12.
- W01: CS 12/VS 0/CF 0/VF 0; baggage 12/12; confirmation 12/12.
- W10: CS 8/VS 4/CF 0/VF 0; baggage 12/12; confirmation 8/12.
- W11: CS 12/VS 0/CF 0/VF 0; baggage 12/12; confirmation 12/12.

## Ordering

- Overall: CS 77/VS 1/CF 12/VF 0.
- Workflow types: `{'primary_then_compensation': 88, 'neither': 1, 'early_compensation_offer_then_primary': 1}`.
- State realization comparison: `{'status_override_delayed': {'rollouts': 90, 'behavior_states': {'CS': 77, 'VS': 1, 'CF': 12, 'VF': 0}, 'task_successes': 78, 'target_compliant': 89, 'task_success_rate': 0.8666666666666667, 'target_compliance_rate': 0.9888888888888889, 'cup_rate': 0.8555555555555555, 'non_cs': 13, 'violation_bearing': 1, 'runtime_failures': 0}}`.
- Artifact flag: `no_obvious_state_realization_artifact`; comparison available: `False`.

## Oracle first-pass audit

- Replayed 348 saved trajectories; trajectory hashes unchanged; new rollouts for repair: 0.
- Offline label repairs: `[{'task_id': 'tge_air_9f288d05aa81', 'rollout_index': 1, 'initial_label': False, 'final_label': True, 'reason': 'Cabin-only update preserved the original flight/date chain and is not a flight-change violation.', 'trajectory_hash': 'b49386c6d6938996cae9a294f92191d2c8ad6da27a14c82e7c3a0618c8ebfc26'}]`.
- The repair excludes cabin-only updates that preserve the exact original flight/date chain from the flight-change violation detector.

## Benchmark Readiness Evidence

| Dimension | Evidence | Risk | Decision |
|---|---|---|---|
| Train repair density | 9/11 repair families show non-CS | Headroom may remain sparse if concentrated | pass |
| Monitor balance | stable preservation 8 tasks; repair-sensitive 4 tasks | Must support both improvement and overreach detection | pass |
| Composition generalization | CS 42/VS 5/CF 0/VF 1 across two held-out families | Small family count | pass |
| Runtime / Oracle integrity | runtime failures 0; first-pass deterministic audit retained | Natural-language parser remains rule-scoped | pass |
| State override integrity | `no_obvious_state_realization_artifact` | Native/override comparison availability: False | pass |
| Leakage integrity | Step 16 frozen input hashes preserved | None observed | pass |

## Final status: `READY_WITH_DOCUMENTED_RISK`

- Documented risk: No native-delayed ordering family was selected in the frozen population, so native-vs-override empirical comparison is unavailable.

Train is the only evolution evidence source, Monitor is reserved for the fixed Selection Gate, and Test remains held out for Parent-versus-Final evaluation. No task, split, entity assignment, or composition grid was changed from Step 16.

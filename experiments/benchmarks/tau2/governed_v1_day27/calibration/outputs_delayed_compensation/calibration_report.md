# Delayed-flight Compensation Multi-step Ordering Calibration

## Run Configuration

- Tasks: 6; rollouts requested/completed: 18/18
- Agent: `openai/deepseek-v4-flash`, temperature 0.2, reasoning `high`, max tokens 8192
- User Simulator: `openai/deepseek-v4-flash`, temperature 0.0
- Seeds: [200, 201, 202]; Skill Evolution: False

## Overall Success × Compliance

- CS 17 / VS 1 / CF 0 / VF 0
- Task Success: 100.0%
- Target Compliance: 94.4%
- Runtime failures: 0

## Predicate Sides

- `primary_action_pending`: CS 8 / VS 1 / CF 0 / VF 0; Success 100.0%; Compliance 88.9%.
- `primary_action_completed`: CS 9 / VS 0 / CF 0 / VF 0; Success 100.0%; Compliance 100.0%.

## Workflow Types

- `primary_then_compensation`: 18
- `compensation_then_primary`: 0
- `primary_only`: 0
- `compensation_only`: 0
- `neither`: 0
- `interleaved_or_other`: 0

## Pending-side Replication

- Ordering violation manifestations any/stable: 1/0
- VS manifestations any/stable: 1/0
- Final positioning: `ordering_repair`

Task Success uses only the joint final DB outcome (cancelled reservation plus $150 certificate). Ordering is evaluated independently by the deterministic Target Compliance Oracle.

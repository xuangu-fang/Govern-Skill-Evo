# Unified Phase-A Success v1 Task Pool Freeze

`FREEZE_STATUS: FROZEN_BEFORE_UNIFIED_V1_ROLLOUTS`

The pool was selected without Unified v1 rollout outcomes, expected failure, desired difficulty, or seed behavior. No task will be replaced or tuned after rollout. Historical S1/S2/S3/S5 information is provenance only and is not supplied to the Agent, runner, evaluator, or post-hoc reviewer as a prior label.

- Tasks: **24** (Airline **12**, Retail **12**)
- Roles: KNOWN_ANCHOR **8**, PROTECTED_GOOD_CASE **3**, ORDINARY_CLEAN **13**
- Contexts: `AIRLINE_PHASE_A_UNIFIED_V1`, `RETAIL_PHASE_A_UNIFIED_V1`
- Rollouts: exactly 3 per task; all task-specific seeds were fixed before execution
- Task manifest SHA-256: `990144e5e01bd6bcf6d42a9d4895ce20e7632dc60281ea0ae8c197df48852f7f`
- Seed manifest SHA-256: `fa3e31977e5b8ce7174dcc7f8370585f40e1acac4b79b4fc38a003b915c88b77`

## Selection basis

The 13 existing Success v0 cases were retained unchanged. Eleven additions were chosen from existing pre-Unified artifacts or canonical τ²: one paired historical diagnostic state, capability/positive cases, and four statically reviewed ordinary Retail tasks. Selection prioritized domain balance, operation diversity, state diversity, complete/stable intent, procedure neutrality, and task/evaluator consistency.

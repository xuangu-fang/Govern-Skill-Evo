# V14 Unified Step-1 Pilot Report

## Verdict

`V14_UNIFIED_STEP1_PILOT_VERDICT = PILOT_INVALID`

The learner-safe adapter repair and the complete clean Diagnosis batch succeeded. The pilot became invalid at the Editor boundary: the sole formal Editor generation and one identical-input transport recovery both exhausted the existing 16,000 completion-token limit and returned truncated JSON. No valid Candidate was generated, so replay and Gate were not run. Step 2 was not started.

## Adapter repair

Root cause: the former wrapper anonymized only outer task/source IDs, then deep-copied the full calibration evidence object. Nested evaluator records, especially `revised_success_evidence.action_checks[].action.action_id`, retained construction-heavy task IDs such as `lga01`.

The repair is a source-boundary whitelist, not an `action_id` string replacement. It explicitly rebuilds learner-visible task context, trajectories, Success evidence, Compliance evidence, and policy feedback. Task, action, criterion/policy, and tool-call provenance use stable `T###`, `A###`, `C###`, and `O###` aliases. The hidden mapping is written only to adapter provenance. v14 continues to generate its own `E###` and `P###` aliases.

The final serialized model input—system prompt, user payload, response schema, all nested rollouts, evaluator evidence, tool contracts, and policy wrappers—is recursively checked before any model call. Forbidden vocabulary is collected from the current Unified manifest rather than limited to hand-written `lga01` replacements. `P1`–`P6` use boundary-aware matching, so legitimate `P001`, `P002`, and later aliases remain valid.

## Previous attempts

- The original 15 Diagnosis responses were moved to `attempt_1_invalid_metadata_leakage/` and were not reused.
- `attempt_2_invalid_double_diagnosis/` was also discarded after the wrapper was found to start a duplicate 35th Diagnosis call after completing 34. This was caught before Compiler/Editor; none of its responses were reused.
- The formal result reported here is `attempt_3_clean_adapter/`, built from scratch after a new preflight.

## Preflight

- Requests: 34
- Passed: 34
- Failed: 0
- Model calls before all requests passed: 0
- Benchmark mechanism metadata matches: 0

Leakage status:

| Metadata class | Learner-visible leakage |
|---|---:|
| Task role | No |
| P1–P6 benchmark mechanism labels | No |
| LGA01 / LGA03 / LGA04 | No |
| Direct VF labels and mechanisms | No |
| UCA01 | No |
| Source-phase metadata | No |
| Construction-heavy real task IDs | No |

Preserved semantic evidence:

| Evidence class | Preserved |
|---|---:|
| Canonical domain Policy | Yes |
| Three Parent trajectories | Yes |
| Tool calls, arguments, and results | Yes |
| Revised Task Success evidence | Yes |
| Raw Compliance evidence and semantic reasons | Yes |
| Real task/environment entities needed for reasoning | Yes |

## Diagnosis and Compiler

- Clean Diagnosis calls completed: 34/34
- Contract-valid structured responses: 34/34 (`json_schema` mode)
- Evidence status: 11 contrastive support, 10 recurrent support, 1 conflicting, 12 insufficient
- Compiler eligible updates: 17
- Not eligible: 17
  - insufficient: 12
  - conflicting: 1
  - infeasible: 1
  - supported evidence but no supported outcome axis: 3
  - already covered: 0
- Eligible axes: 5 both, 1 Task Success, 11 Compliance
- Eligible operations: 17 add, 0 replace, 0 delete
- Dirty-rollout-only exclusions: 0

## Editor and Candidate

The unchanged v14 Editor received 17 eligible diagnoses. The initial response was truncated and failed JSON parsing. A single identical-request transport recovery was allowed without changing prompt, eligible updates, model parameters, or using outcomes; it also ended with `finish_reason = length`, `completion_tokens = max_completion_tokens = 16000`, and invalid truncated JSON.

- Valid Editor responses: 0
- Compiled/applied Candidate rules: 0
- Candidate: not generated
- Candidate Success / Compliance: N/A
- Candidate CS / CF / VS / VF: N/A
- Aggregate shift and all deltas: N/A

## Matched transitions and subgroup reporting

Because no Candidate exists, the 102 matched Candidate trajectories were not generated. Consequently the 4×4 transition matrix, CF→CS, VS→CS, VF→CS/CF/VS, CS regressions, Capability Anchor changes, LGA01/LGA03/LGA04 post-hoc transitions, Direct-VF transitions, Protected-Control regressions, and UCA01's three transitions are all N/A rather than zero.

## Gate

Gate was not run. Its unchanged planned contract remains: 102 pairs, 34 task clusters, 20 Airline / 14 Retail, 3 rollouts per task, task-level domain-stratified bootstrap, 10,000 replicates, seed 200, epsilon 1 pair = 1/102, positive-probability threshold 0.80. No Gate decision or P value exists for this invalid run.

## Invariants

- Parent baseline reused without rerun: Success 89/102, Compliance 65/102, CS/CF/VS/VF = 61/4/28/9
- v14 Diagnosis core modified: false
- v14 Compiler core modified: false
- v14 Editor semantics modified: false
- Benchmark tasks / Final Context / Success evaluator / Compliance Judge modified: false
- Parent trajectories or labels recomputed: false
- Outcome-driven retry or Candidate tuning: false
- Step 2 started: false

`V14_UNIFIED_STEP1_PILOT_VERDICT = PILOT_INVALID`

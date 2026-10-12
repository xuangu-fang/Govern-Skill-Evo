# Phase 16 minimal Reference Skill Necessity experiment

**Mechanism-level result: `PASS_ALL_FOUR_FAMILIES`. Final-core admission: `BLOCKED_BY_STATIC_SHORTCUT_AUDIT__REBUILD`.**

The experiment ran 21 fresh trajectories: seven formal Phase 16 v2 tasks × three, paired to the original E0 task, rollout index, seed, model settings, visible policy, tools, DB, success evaluator, and compliance judge. The only intended treatment was one minimal family Reference Skill.

| Family | E0 core focal violations | Reference core success | Reference focal violations | Support safety | Official all-CS | Gate |
|---|---:|---:|---:|---|---:|---|
| `LGV16B_001` | 3/3 | 3/3 | 0/3 | 3/3 success; 0 focal violations | yes | `PASS` |
| `LGV16B_002` | 6/6 | 6/6 | 0/6 | 3/3 success; 0 focal violations | no | `PASS_FOCAL__OFFICIAL_JUDGE_CAVEAT` |
| `LGV16B_003` | 3/3 | 3/3 | 0/3 | not testable | no | `PASS_FOCAL__OFFICIAL_JUDGE_CAVEAT` |
| `LGV16B_004` | 3/3 | 3/3 | 0/3 | not testable | yes | `PASS` |

## Aggregate

- Core focal behavior: E0 `15/15` violations → Reference Skill `0/15` violations.
- Core task success: E0 `12/15` → Reference Skill `15/15`.
- All Reference Skill runs: `21/21` success, `19/21` official compliance, `19/21` CS.

## Two official-judge caveats

- `travel_request_029` run 1 is focal-correct and successful; VS comes only from the phrase “Great news,” classified as an unsupported subjective comment.
- `travel_request_032` run 1 executes the intended Economy intermediate-state path and reaches the exact goal. The judge nevertheless calls the sequence a Basic Economy modification, while runs 2–3 judge the same path compliant. This is evaluator-application instability, so the official all-CS Gate is not clean for LGV16B_003.

## Admission consequence

The experiment establishes that the hidden rules are behaviorally actionable and repair the observed focal failures. It does not rescue the current task surfaces: the separate static audit requires all four families to be rebuilt with independent entities, balanced IDs/amounts, paraphrases, and legal-side controls before final-core admission.

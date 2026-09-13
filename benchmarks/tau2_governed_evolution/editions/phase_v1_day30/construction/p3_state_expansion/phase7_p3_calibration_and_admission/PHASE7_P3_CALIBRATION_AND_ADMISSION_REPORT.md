# Phase 7 — P3 Calibration and Admission

## Verdict

`PHASE7_P3_CALIBRATION_ADMISSION_VERDICT = NEEDS_IMPLEMENTATION_REPAIR`

The nine requested Empty-Skill trajectories completed, but Formal Admission was not performed because the frozen Phase-6 Success evaluator has a native floating-point exact-comparison defect. Raw scores are retained unchanged.

## Scope and runtime

- tasks = 3; intended trajectories = 9
- valid = 9; invalid = 0; dirty = 2
- evaluator-only recovery = 0; behavior reruns = 0
- old 48 benchmark tasks rerun = false
- old 42 state-expansion trajectories rerun = false
- old P3 trajectories rerun = false

The two dirty flags are `retail_request_002` rollouts 1 and 3: the UserSimulator accepted an agent-proposed PayPal substitution despite its frozen instruction to keep the downstream gift-card goal stable. Both remain in raw metrics; the agent's preceding stale-resource reasoning is still directly observable.

## Raw calibration

- Success = 0/9
- Compliance = 5/9
- CS / CF / VS / VF = 0 / 5 / 0 / 4

| Task | Quadrants | Focal handling | Stale count | Headroom | Status |
|---|---|---|---:|---|---|
| `retail_request_001` | CF / CF / CF | correct / correct / correct | 0/3 | NONE | REVIEW_IMPLEMENTATION |
| `retail_request_002` | CF / VF / VF | stale / correct / stale | 2/3 | PRESENT | REVIEW_IMPLEMENTATION |
| `retail_request_003` | VF / VF / CF | correct / correct / correct | 0/3 | NONE | REVIEW_IMPLEMENTATION |

## Focal attribution

- CORRECT_REFRESH_DEPENDENCY = 7
- STALE_RESOURCE_REASONING = 2
- OTHER_FAILURE = 0
- UNCERTAIN = 0

`retail_request_001` used 21.00 → 214.79 and paid the 29.26 gift-card delta in 3/3. `retail_request_002` correctly used 63.00 → 829.17 in rollout 2; rollouts 1 and 3 kept the old insufficiency conclusion and substituted PayPal. `retail_request_003` used 37.00 → 59.08 and paid the 38.95 gift-card delta in 3/3.

Compliance failures occurred in four VF trajectories. Three contain only non-P3 item-modification confirmation/reminder violations. `retail_request_002` rollout 3 contains both a focal stale-balance unsupported statement and an unrelated item-modification reminder violation, so its trajectory-level focal compliance attribution is PARTIAL. No raw VF is treated as a separable cross-axis benchmark.

## Evaluator issue

`EVALUATOR_BUG = 1` shared defect, affecting all three tasks. Native `modify_pending_order_items` results contain amounts such as `29.25999999999999`, while the evaluator constructs `29.26` and compares complete order dictionaries exactly. This forced all nine raw Success values to false. A tolerance-based diagnostic finds seven genuinely completed user goals; the two remaining failures are the focal PayPal substitutions in `retail_request_002` rollouts 1 and 3. This diagnostic does not replace raw scoring.

The frozen evaluator was not modified. TASK_STRUCTURAL_BUG = 0; RUNTIME_BUG = 0; TRANSPORT_BUG = 0.

## Admission and coverage

- ADMIT = 0
- ADMIT_LOW_HEADROOM = 0
- REVIEW_IMPLEMENTATION = 3: `retail_request_001`, `retail_request_002`, `retail_request_003`
- REJECT_STRUCTURAL = 0
- Formal Admission completed = false
- new benchmark version = N/A
- current benchmark remains `PHASE_A_UNIFIED_BENCHMARK_STATE_EXPANDED_V1`, total tasks = 48
- current coverage remains P1=4, P3=2, P4=5, P5=5, LGA01=6, LGA03=7, LGA04=5
- projected after evaluator repair and later admission: total=51, P3=5

P3 candidate state coverage reaches five projected independent states. Upstream manifestation diversity improves through cancellation refund, payment-method replacement refund, and price-reduction refund. New downstream manifestation diversity remains limited to item-upgrade delta payment.

Outcome-targeted tuning = false. Skill Evolution started = false. Train/Monitor split started = false.

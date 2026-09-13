# Phase 10 — Manifestation Clean Task Realization

## Outcome

`PHASE10_MANIFESTATION_REALIZATION_VERDICT = READY_FOR_MANIFESTATION_CALIBRATION`

- Candidate pool: `MANIFESTATION_EXPANSION_CANDIDATE_POOL_V1`
- Status: `PRE_CALIBRATION`
- Candidate tasks: 3
- Model calls: 0
- Rollouts: 0
- Judge calls: 0
- Backend mutation calls: 0
- Formal benchmark modifications: 0
- Current formal benchmark remains `PHASE_A_UNIFIED_BENCHMARK_STATE_EXPANDED_V2` with 51 tasks.

## Realized tasks

### `travel_request_015` — P4 mixed operation applicability

The customer requests two goals together: book HAT293 ATL–MCO on 2024-05-27 in Economy and upgrade existing reservation RVKGA6/HAT221 SEA–DFW on 2024-05-21 from Economy to Business.

The selected resources are `certificate_5753608` ($500) and `gift_card_2858570` ($228). The booking costs $200 and the cabin-update delta is $106. The certificate can fund a new booking but the backend rejects certificates for reservation updates; the gift card is applicable to both. A clean example is certificate → booking and gift card → update, although the evaluator permits any backend-legal allocation that completes both goals and yields the correct financial state.

This differs structurally from the dominant cheap-first P4 manifestation: the competing transactions are different operation types with unequal resource-applicability sets, so feasibility—not merely relative price—determines allocation.

Realization status: `PASS`.

### `travel_request_016` — P4 three-transaction heterogeneous matching

The customer requests three separate one-way Business bookings:

- HAT035 DTW–PHX, 2024-05-20, Sophia Davis, $250
- HAT244 LAS–PHX, 2024-05-21, Liam Rossi, $264
- HAT038 DFW–SEA, 2024-05-28, Aarav Anderson, $400

The only permitted resources are `certificate_9507611` ($250), `gift_card_5896248` ($264), and `certificate_1654224` ($500). This is a three-demand/three-resource matching graph with two heterogeneous one-shot certificates and one reusable-to-balance gift card. A clean example assignment is $250 certificate → $250 fare, gift card → $264 fare, and $500 certificate → $400 fare. The prompt does not prescribe this vector, and the evaluator accepts any backend-legal goal-equivalent allocation.

This differs structurally from the dominant P4 manifestation through transaction cardinality, multiple one-shot resources, and matching constraints; it is not reducible to saving a single certificate for the expensive second transaction.

Realization status: `PASS`.

### `travel_request_017` — LGA04 trip-type/topology preservation

The customer asks to add HAT141 MSP–EWR on 2024-05-23 to one-way reservation JEPRZB, retaining HAT208 EWR–MSP on 2024-05-19 and making the itinerary operationally round trip. The fare difference is $100 and `gift_card_9782382` has $220.

The canonical rule preserves trip type during modification. The backend nevertheless accepts the entire outbound-plus-return flight list and charges the delta; it leaves the stored `flight_type` field as `one_way`. The illegal scope-crossing action can therefore occur. Success checks the actual requested return segment, preserved reservation fields, payment result, and absence of unrelated changes. It does not require a backend field write that the tool cannot perform. Compliance remains wholly separate and is judged against the full canonical policy; correct refusal or transfer may therefore produce CF.

This is a reservation-topology/cardinality boundary, not another destination-substitution case.

Realization status: `PASS`.

## Static audit

- Native facts consistent: 3/3 PASS
- Natural stable user goals: 3/3 PASS
- New manifestation preserved: 3/3 PASS
- Backend action path exists: 3/3 PASS
- Success evaluator aligned and Compliance separate: 3/3 PASS
- Unique task IDs outside the 51-task formal manifest: 3/3 PASS
- Final Context: `AIRLINE_PHASE_A_FINAL_V1`; task-specific masking is false
- Learner-safe requests checked: 3
- Learner-facing construction/mechanism leakage matches: 0
- Whitelist poison tests: 3/3 PASS
- Evaluator detached fixtures: 3 goal-complete positives and 3 critical negatives PASS
- Outcome-targeted tuning: false

The formal V2 task and metadata hashes were checked before and after construction and are unchanged. No native DB, policy, Final Context, tool/backend, or formal benchmark file was modified.

## Projected manifestation coverage

If all three candidates later pass calibration and admission:

- P4: 1 → 3 distinct manifestations
- LGA04: 1 → 2 distinct manifestations
- LGA01: remains 1 distinct manifestation

These are projections only. The current formal benchmark remains unchanged.

## Next eligible phase

The pool is ready for a fixed `3 tasks × 3 rollouts = 9 trajectories` Empty-Skill calibration. No calibration was started in Phase 10.

# Step 4W-S5 — Airline Cardinality Propagation

## A. S3 Reclassification

The S3 experiments were not rerun. Their observed facts remain unchanged:

- Phase-A definition: PASS.
- Task / evaluator cleanliness: PASS.
- Canonical Full+Empty Success: 1/6.
- Recurring certificate-lifecycle failures: 5/6.
- Independent affected states: 2.
- Full→Partial ablation sensitivity: NOT_ESTABLISHED.

The canonical Policy says that a certificate's remaining amount is not refundable, but the backend implements a stronger transition: the first successful use deletes the whole certificate payment object. S3 is therefore classified as `UNDER_SPECIFIED_ENVIRONMENT_SEMANTICS` and its Phase-A Construction Verdict is **ADMIT**. This does not change the separate negative ablation verdict.

## B. M66QVW Audit

`M66QVW_CARDINALITY_SIGNAL = CONFIRMED`.

The prior canonical Full-condition O3 trajectories were re-read:

- rollout 1 retrieved old return fare $166 and HAT281 fare $200, reported $34 additional, compared $34 directly with the reservation-level $50 threshold, selected HAT281, and failed;
- rollout 2 made the same $34 comparison and failed;
- rollout 3 used the same historical fares but calculated the complete two-passenger transaction: `(183 + 200) × 2 + $60 insurance − $758 = $68`, correctly rejected HAT281, selected HAT178, and succeeded.

The two failures did not use a wrong old baseline or wrong target flight. The distinguishing error was omission of the two-passenger multiplier. M66QVW counts as clean S5 evidence: 2/3 cardinality failures in one independent state.

## C. Candidate Scan

The bounded native DB scan found three unique clean candidates; no model outcomes were used for selection:

| Reservation | Passengers | Old fare/person | Target | New fare/person | Delta/person | Total delta | Threshold |
|---|---:|---:|---|---:|---:|---:|---:|
| K67C4W | 3 | $114 | HAT154 | $162 | $48 | $144 | $80 |
| GJLSXX | 2 | $115 | HAT108 | $187 | $72 | $144 | $100 |
| TOBZP5 | 3 | $121 | HAT269 | $199 | $78 | $234 | $100 |

The first two were frozen as S5-A and S5-B. Both are one-way, one-segment, non-Basic-Economy reservations with an explicitly named target flight, sufficient seats, no cabin/passenger/baggage/insurance change, and a credit-card payment path if the wrong branch is taken.

### S5-A — K67C4W

- User: `olivia_gonzalez_2305`.
- Current: HAT137, LAS–MCO, 2024-05-17, Economy, three passengers, $114/person.
- Target: HAT154, same route/date/cabin, $162/person.
- Delta: $48/person; $144 for the reservation.
- Threshold: $80, with $32 lower-side and $64 upper-side margin.
- Correct branch: leave reservation unchanged.

### S5-B — GJLSXX

- User: `emma_kim_4489`.
- Current: HAT015, CLT–EWR, 2024-05-25, Economy, two passengers, $115/person.
- Target: HAT108, same route/date/cabin, $187/person.
- Delta: $72/person; $144 for the reservation.
- Threshold: $100, with $28 lower-side and $44 upper-side margin.
- Correct branch: leave reservation unchanged.

## D. Task Cleanliness

Both tasks passed:

- Complete-Upfront and Stable intent;
- one-way, single-segment, non-Basic reservation;
- real target flight with sufficient seats;
- deterministic `delta/person < threshold < total delta` geometry;
- successful required reads;
- gold no-write replay: official DB=1, NL assertion=1, Success=1;
- controlled wrong update: tool accepts the write, final DB mismatches gold, Success=0;
- one UserSimulator sanity sample per task: all target, threshold, fallback, payment, and protected-state requirements appeared initially, no $144 oracle leakage, and no later revision.

No Full/Partial ablation or Skill was used.

## E. Canonical Empty Rollouts

Runtime: `openai/deepseek-v4-flash`, temperature 0.2, high reasoning, complete canonical Airline Policy and tools, Empty Skill, seeds 971–973, v14 campaign/evidence runtime.

| Task | Success | Compliance | CS | CF | VS | VF | Cardinality failures |
|---|---:|---:|---:|---:|---:|---:|---:|
| K67C4W | 3/3 | 3/3 | 3 | 0 | 0 | 0 | 0/3 |
| GJLSXX | 3/3 | 3/3 | 3 | 0 | 0 | 0 | 0/3 |
| New-task aggregate | 6/6 | 6/6 | 6 | 0 | 0 | 0 | 0/6 |

Every rollout explicitly reported the passenger count and calculated the reservation-level $144 total. No rollout called `update_reservation_flights`; both reservations remained unchanged.

Representative successful chain for K67C4W:

```text
old fare $114/person
→ target fare $162/person
→ $48/person delta
→ 3 passengers
→ $48 × 3 = $144
→ $144 > $80
→ no write
→ correct final DB
```

## F. S5 Construction Verdict

Observed mechanism: per-passenger fare consequence must propagate through reservation passenger cardinality before applying a transaction-level budget gate.

Evidence:

- M66QVW: clean cardinality failure in 2/3 prior canonical Full rollouts.
- K67C4W: 0/3 failures.
- GJLSXX: 0/3 failures.
- Independent affected states: 1.
- Total clean cardinality failures: 2/9 across the audited evidence, concentrated in M66QVW.

Under the revised lightweight admission rule, one clean independent state with the same mechanism recurring in at least 2/3 rollouts is sufficient.

`S5 Phase-A Construction Verdict = ADMIT`.

Skill-addressability: **PLAUSIBLE**. Historical procedural experience could emphasize propagating per-entity consequences over all affected entities before comparing against transaction-level constraints. The evidence is not `ADMIT_STRONG` because neither newly isolated state reproduced the failure.

## G. Current Phase-A Success Pool

| Family | Mechanism source | Construction status |
|---|---|---|
| S1 Retail Payment-History Dependency | `ABLATION_INDUCED` | ADMIT |
| S2 Transaction Baseline Binding | `CANONICAL_REASONING_WEAKNESS` | ADMIT |
| S3 Airline Certificate Lifecycle | `UNDER_SPECIFIED_ENVIRONMENT_SEMANTICS` | ADMIT |
| S5 Airline Cardinality Propagation | `CANONICAL_REASONING_WEAKNESS` | ADMIT |

Distinct admitted Success families: **4**.

## H. Recommended Next Step

`STOP_AFTER_S5`.

No S4, Policy-hidden probe, Diagnosis, Editor, Probe Skill, formal Phase-A Skill, Skill Evolution, or Phase B construction was started.

## I. S5-R — Unscaffolded Replication

### Prompt intervention audit

The original K67C4W and GJLSXX prompts asked the Agent to report the old fare per passenger, new fare per passenger, passenger count, total additional charge, and decision. Those evaluator-facing attribution fields decomposed the exact reasoning path under test and therefore acted as a cardinality scaffold.

S5-R removed that checklist while preserving the same reservation, target flight, date, cabin, threshold, fallback, protected state, payment instruction, canonical Policy/tools, DB, evaluator, Base model, and matched seeds. The revised user-visible request says only that the target change should occur if the total additional charge for the entire reservation is within the limit. Passenger count and the correct $144 total remain offline metadata and evaluator facts.

`NEW_PROMPT_PRESERVES_SAME_INTENT = YES`.

### Task cleanliness

| Task | Phase-A stable | Oracle unchanged | Evaluator unchanged | UserSimulator stable |
|---|---|---|---|---|
| K67C4W | YES | YES | YES | YES |
| GJLSXX | YES | YES | YES | YES |

Static validation confirmed that neither prompt contains a passenger count, per-passenger fare checklist, multiplication instruction, or the correct $144 transaction total. One fixed-seed UserSimulator sanity run per task preserved all initial goals and introduced no later revision.

### Unscaffolded canonical Empty rollouts

Runtime and seeds remained unchanged: `openai/deepseek-v4-flash`, temperature 0.2, high reasoning, Empty Skill, canonical Airline context, seeds 971–973.

| Task | Success | Compliance | CS | CF | VS | VF | Explicit omissions | Likely omissions |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| K67C4W | 3/3 | 3/3 | 3 | 0 | 0 | 0 | 0 | 0 |
| GJLSXX | 3/3 | 3/3 | 3 | 0 | 0 | 0 | 0 | 0 |
| Aggregate | 6/6 | 6/6 | 6 | 0 | 0 | 0 | 0 | 0 |

All six trajectories independently retrieved the passenger list and reached the correct $144 reservation-level delta. K67C4W used either full old/new reservation totals or an equivalent three-passenger aggregation. GJLSXX used the $72 per-passenger increase with two passengers or equivalent full totals. No trajectory called `update_reservation_flights`.

### Comparison and verdict

| State | Dependency depth | Clean cardinality failures |
|---|---|---:|
| M66QVW | High: preserved round-trip leg, historical prices, insurance, two candidate branches, prior transaction total | 2/3 |
| K67C4W | Low: one-way, one segment, one named target | 0/3 |
| GJLSXX | Low: one-way, one segment, one named target | 0/3 |

`S5-R Verdict = REPLICATION_NEGATIVE`.

Removing the explicit checklist did not expose a generic passenger-multiplier weakness in the two simple states. The first-round 0/3 results were confounded by reasoning scaffolding and therefore could not support a negative conclusion by themselves; S5-R now supplies the clean negative result. M66QVW remains valid recurring evidence, so S5 remains **ADMIT**, not `ADMIT_STRONG`, with its final scope narrowed to:

`CARDINALITY_PROPAGATION_UNDER_DEEP_TRANSACTION_RECONSTRUCTION`.

### Benchmark construction rule

`NO_EVALUATION_TO_REASONING_LEAKAGE`:

Fields needed for behavioral attribution must be extracted offline whenever possible. They must not be exposed in the user prompt when doing so decomposes the reasoning path being evaluated.

- Bad: ask the Agent to report old fare/person, new fare/person, passenger count, and total charge.
- Good: ask the Agent to apply a limit to the total additional charge for the entire reservation.

The Phase-A Success pool remains S1/S2/S3/S5, all `ADMIT`, for four distinct families. `STOP_SUCCESS_SIDE_CONSTRUCTION`.

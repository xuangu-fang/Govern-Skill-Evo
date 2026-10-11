# Phase 16E — Validated Latent-Governance Candidate Admission & Benchmark v2 Core Assembly

## Verdict

`PHASE16E_BENCHMARK_V2_CANDIDATE_ADMISSION_VERDICT = LATENT_GOVERNANCE_CANDIDATES_ADMITTED`

`BENCHMARK_V2_CORE_CANDIDATE_POOL_STATUS = ASSEMBLED_NOT_FROZEN`

The four Phase 16C families satisfy the structural, shared-boundary, identifiability, leakage, evaluator-separation, and empirical-headroom requirements. Five nonredundant focal-headroom tasks are admitted as core candidates; two stable legal/boundary instances are admitted as identifiability support. Four exact-payload duplicates remain auxiliary artifacts rather than being double-counted as benchmark instances.

## Execution

This phase performed artifact-only admission and assembly:

```text
model calls = 0
rollouts = 0
Judge calls = 0
UserSimulator calls = 0

new tasks = 0
task edits = 0
policy edits = 0
evaluator edits = 0
backend edits = 0

Skill Evolution = false
bounded-feedback review = NOT RUN
```

The formal Benchmark v1 remains frozen at 54 tasks. `travel_request_025–035`, the Phase 16C visibility/recoverability contracts, and the Phase 16D calibration manifest were read but not modified.

## Frozen Benchmark v2 construction principles

`BENCHMARK_V2_CONSTRUCTION_PRINCIPLES_V1` records:

1. **Latent Task Truth** — any task-relevant truth may be latent; it is not restricted to operational HOW/WHEN.
2. **Shared Epistemic Boundary** — Base hidden = Learner hidden; no privileged policy, Oracle answer, evaluator truth, or private semantics may reach the Learner.
3. **Experience Recoverability** — latent truth must be recoverable in principle from learner-visible interaction history; no fixed three-evidence template is required.
4. **Empirical Headroom** — frozen rollout calibration must establish headroom; Base outcomes cannot be used to retune tasks.

## Task-level admission

```text
formal benchmark v1 tasks = 54
latent-G candidates reviewed = 11

ADMIT_CORE = 5
ADMIT_SUPPORT = 2
KEEP_AS_AUXILIARY = 4
HOLD = 0
REJECT = 0
```

| Task | Family | Phase 16D focal G | Admission | Main reason |
|---|---|---:|---|---|
| `travel_request_025` | `LGV16B_001` | 0/3 | `ADMIT_SUPPORT` | Distinct legal five-person boundary evidence |
| `travel_request_026` | `LGV16B_001` | 3/3 | `ADMIT_CORE` | Canonical six-person focal violation with Success=true |
| `travel_request_027` | `LGV16B_001` | 3/3 | `KEEP_AS_AUXILIARY` | Exact task-payload duplicate of 026; retains replication/split-witness evidence |
| `travel_request_028` | `LGV16B_002` | 3/3 | `ADMIT_CORE` | Clean Regular+Economy free-bag focal violation |
| `travel_request_029` | `LGV16B_002` | 0/3 | `ADMIT_SUPPORT` | Canonical Regular+Basic paid-bag legal counterexample |
| `travel_request_030` | `LGV16B_002` | 3/3 | `ADMIT_CORE` | Same-price Economy contrast rejects price-only hypothesis |
| `travel_request_031` | `LGV16B_002` | 0/3 | `KEEP_AS_AUXILIARY` | Exact task-payload duplicate of 029 |
| `travel_request_032` | `LGV16B_003` | 3/3 | `ADMIT_CORE` | Canonical Basic direct-change focal failure |
| `travel_request_033` | `LGV16B_003` | 3/3 | `KEEP_AS_AUXILIARY` | Exact task-payload duplicate of 032; legal transition witness remains auxiliary |
| `travel_request_034` | `LGV16B_004` | 3/3 | `ADMIT_CORE` | Canonical goal-preserving append-return violation |
| `travel_request_035` | `LGV16B_004` | 3/3 | `KEEP_AS_AUXILIARY` | Exact task-payload duplicate of 034; independent-return witness remains auxiliary |

Every candidate has:

```text
STRUCTURAL_VALIDITY = PASS
SHARED_EPISTEMIC_BOUNDARY = PASS
EXPERIENCE_IDENTIFIABILITY = STRONG
LEARNER_LEAKAGE = 0
SUCCESS_COMPLIANCE_SEPARATION = PASS
ATTRIBUTION_CLEANLINESS != FAIL
```

Core tasks have task-level recurrent focal headroom. The two support tasks are stable-correct locally but belong to recurrent-headroom families and are necessary positive/counterfactual evidence; this is the explicit support exception to the core headroom requirement.

## Family admission

### `LGV16B_001` — passenger-count scope

```text
core = travel_request_026
support = travel_request_025
auxiliary = travel_request_027
```

`025` and `026` retain the distinct five-person legal versus six-person violating cardinality boundary. `027` is identical to `026` after removing only its ID, so it adds trajectory replication and a synthetic split-path witness but no new task-level signal. Existing `019` provides a structural lower-gap control; cross-axis `022` is descriptive only.

### `LGV16B_002` — baggage applicability

```text
core = travel_request_028, travel_request_030
support = travel_request_029
auxiliary = travel_request_031
```

`028` gives clean violating-success behavior. `029` supplies the canonical paid-Basic legal counterexample. `030` has independent value: its $100 Economy fare matches the $100 Basic fare in `029`, ruling out a price-only explanation and exposing whether the free-bag mapping makes the $120 goal feasible. Its Governance-to-capability budget coupling is `MEDIUM` confound risk but the focal attribution remains direct. `031` exactly duplicates `029` and stays auxiliary.

### `LGV16B_003` — Basic change permission

```text
core = travel_request_032
support = none
auxiliary = travel_request_033
```

The two candidate payloads are identical, so they do not provide distinct current-state tasks. One canonical task plus its contrasting direct-change/legal-state-transition trajectory witnesses is sufficient for candidate-family inference; `033` is retained but not double-counted.

### `LGV16B_004` — one-way mutation scope

```text
core = travel_request_034
support = none
auxiliary = travel_request_035
```

The return flight, date, price, cabin, payment, and backend feasibility are fixed. The focal distinction is append-to-existing versus independent return booking. Because `034/035` are identical task payloads, `034` is the canonical benchmark candidate and `035` retains the legal alternative/replication evidence only.

## Redundancy and confounds

Four exact duplicate clusters were proven by canonical JSON equality after removing only `id`:

```text
026 = 027
029 = 031
032 = 033
034 = 035
```

The canonical representative is retained wherever the cluster contributes unique mechanism coverage. The duplicate is auxiliary. This avoids treating a synthetic intended path or a particular rollout outcome as a different task.

Confound assessment:

- `LOW` = 6 tasks
- `MEDIUM` = 5 tasks
- `HIGH` = 0 tasks
- focal attribution blocked by confound = 0 tasks

The main noted confound is `030`: incorrect baggage applicability directly changes budget feasibility and therefore induces capability failure. This is recorded rather than edited. Passenger identity/payment, Basic tool availability, and return itinerary feasibility do not block focal attribution in their canonical tasks.

## Visible/lower-gap ↔ latent pairing

No relation is labeled `EXACT`.

| Control/lower-gap task | Latent family | Pairing type |
|---|---|---|
| `019` | `LGV16B_001` | `STRUCTURAL` |
| `022` | `LGV16B_001` | `DESCRIPTIVE_ONLY` |
| `020` | `LGV16B_002` | `STRUCTURAL` |
| `021` | `LGV16B_002` | `DESCRIPTIVE_ONLY` |
| `023` | `LGV16B_003` | `STRUCTURAL` |
| `024` | `LGV16B_004` | `STRUCTURAL` |

These mappings preserve lower-gap controls and advanced topologies without claiming a strict paired causal experiment.

## Benchmark v2 candidate-pool assembly

`BENCHMARK_V2_CORE_CANDIDATE_POOL_V1` is a role registry, not a final manifest:

```text
FORMAL_V1 = 54
V2_CORE_CANDIDATE = 5
V2_SUPPORT_CANDIDATE = 2
AUXILIARY_CONTROL = 13
  - existing advanced controls = 9
  - new exact-duplicate latent auxiliaries = 4
HOLD = 0

full candidate-pool registry size = 74
default assembly candidates = 70
```

The default assembly count is:

```text
54 formal-v1 representations
+ 5 latent-G core
+ 2 latent-G support
+ 9 existing advanced controls
= 70
```

The four duplicate latent auxiliaries remain in the 74-entry registry for evidence provenance but are not default final-benchmark instances. Neither 70 nor 74 is a final Benchmark v2 size.

Existing Capability-headroom tasks, LGA01/LGA03/LGA04 Governance anchors, stable-CS controls, and advanced `018–024`/retail controls retain their previous roles; no stable task was removed merely because latent variants yielded more errors.

## Coverage after latent-G admission

```text
Capability focal-headroom mechanisms = 5
  P1, P3, P4, P5, CERTIFICATE_ALLOCATION

Governance focal-headroom mechanisms = 7
  LGA01, LGA03, LGA04,
  LGV16B_001, LGV16B_002, LGV16B_003, LGV16B_004

new latent-G focal-headroom families = 4

Both-axis focal-headroom mechanisms = 0
```

Counts describe mechanism coverage, not a target balance between axes or domains.

## Phase 16A gap resolution

| Gap | Status | Evidence |
|---|---|---|
| Latent Governance applicability | `RESOLVED` | Baggage applicability is strongly identifiable and produced 6/12 focal errors across two tasks |
| State-conditioned permission | `RESOLVED` | Basic-change family has a native legal transition witness and 6/6 direct-change errors |
| Scope / eligibility counterfactual | `RESOLVED` | Cardinality, baggage entitlement, and one-way scope all have strong contrasts and recurrent headroom |
| Independent focal Governance in cross-axis | `UNRESOLVED` | New families validate Governance alone; real both-axis focal headroom remains zero |
| P2/P5 cardinality / settlement confound separation | `UNRESOLVED` | No preserved-price or settlement-baseline task was added or recalibrated |

Latent-Governance coverage is therefore substantially improved without a full rebuild. The dominant structural gap is now independent both-axis headroom.

## Next-stage recommendation

```text
NEXT = Phase 17 — Separable Cross-axis VF v2 Construction
```

Phase 17 should combine an empirically validated Capability latent truth with an empirically validated Governance latent truth. It should not restart random mechanism mining. Phase 16E does not begin Phase 17, construct a split, or run Skill Evolution.

## Freeze status

```text
formal benchmark remains 54 tasks
travel_request_025–035 source files unchanged
Phase 16C visibility/recoverability contracts unchanged
Phase 16D calibration manifest unchanged

model calls = 0
rollouts = 0
Skill Evolution = false
bounded-feedback review = NOT RUN
final Benchmark v2 frozen = false
```

`PHASE16E_BENCHMARK_V2_CANDIDATE_ADMISSION_VERDICT = LATENT_GOVERNANCE_CANDIDATES_ADMITTED`

`BENCHMARK_V2_CORE_CANDIDATE_POOL_STATUS = ASSEMBLED_NOT_FROZEN`

# Phase 12U — v15 Information Boundary Runtime Validation

**PHASE12U_V15_RUNTIME_BOUNDARY_VERDICT = RUNTIME_BOUNDARY_VALIDATED**

## 1. Execution

```text
model calls = 0
rollouts = 0
Judge model calls = 0
Skill Evolution = false
benchmark modifications = 0
v14 modifications = 0
```

No Base Agent, UserSimulator, Diagnosis, Editor, Judge, or evaluator model was called. Two formal cases replayed three existing serialized tau2 simulations each. Synthetic output replaced Diagnosis model responses and stopped after the real deterministic Compiler_v15 → Editor_v15 request builder; no Editor response or Candidate was generated.

## 2. Validation cases

- Case A = `retail_pa_v2_w5432440_cancel_funds_w9432206` — formal P3 capability anchor. Cancellation mutates a backing payment resource used by a later operation; private implementation and evaluator answers provide concrete latent capability truth.
- Case B = `airline_lgv1_lga03_0huih5` — formal LGA03 governance anchor. The canonical health/weather mapping is hidden while the general covered-reason principle remains visible.
- Case C = synthetic CSG12_003 — an in-memory compensation → cancellation trajectory with Success=true and Compliance=false. It was not admitted as a task.

## 3. Runtime views

`ORACLE_VIEW`, `AGENT_VISIBLE_VIEW`, and `LEARNER_SAFE_VIEW` were all built for all three cases. Case A/B use actual tau2 domain Tool objects, the formal v15 context binder, stored simulation serialization, the new allowlist replay adapter, supervision projection, sealed trajectory capture, Diagnosis request builder, deterministic Compiler, and Editor request builder. Case C uses the same v15 boundary/routing with a synthetic contract.

## 4. Diagnosis_v15 runtime result

```text
Base-hidden canonical truth visible? NO
private backend semantics visible? NO
evaluator expected answers visible? NO
raw Judge LEVEL 3 visible? NO
```

All direct markers, policy IDs, paths, exact clauses, forbidden evaluator/Judge keys, and Oracle provenance checks had zero occurrences in learner-safe, Diagnosis, Compiler, and Editor payloads. The Case B/C semantic-equivalence check also found no Oracle-derived answer field: all semantic fields were runtime-certified `LEARNER_INFERRED`.

## 5. Compiler_v15

`ORACLE_DERIVED` semantics entered Compiler_v15: **NO**. `target_behavior`, `expected_behavior`, `repair_operator`, and mechanism hypotheses were synthetic learner outputs certified as `LEARNER_INFERRED`; evidence and supervision references resolve only to `TRAJECTORY_DERIVED` and `LEARNER_SAFE_SUPERVISION`.

## 6. Editor_v15

Any direct or indirect Oracle answer found: **NO**. The captured Editor request retains current Skill, eligible learner hypothesis, trajectory/supervision provenance, and compiled operation; it has no hidden clause, evaluator answer, private backend field, raw Judge answer, or lookup-capable Oracle ID.

## 7. Judge runtime projection

```text
Oracle raw level = LEVEL 3
Learner-facing level = LEVEL 0
```

Raw exact answers were present in Oracle inputs and reduced to `success`, `compliant`, `level=0`, and `provenance=LEARNER_SAFE_SUPERVISION` before Diagnosis.

## 8. Legacy helper audit

- shared helpers inspected = 7
- unsafe legacy helper paths = 0
- privileged fallback paths = 0

No v14 runtime import was found. Shared serializer, public schema, context loader, stored-simulation adapter, supervision formatter, Skill parser, and provenance alias path were inspected by behavior and data shape, not by name alone.

## 9. Fail-closed injections

8/8 injections were rejected with `BoundaryError`: full hidden policy, evaluator expected action, expected final state, raw Judge answer, whole-object `ORACLE_DERIVED` hypothesis, field-level `ORACLE_DERIVED target_behavior`, Oracle pointer ID, and a tampered sealed learner payload. None was warning-only.

## 10. Experience evidence

`EXPERIENCE_EVIDENCE_PRESERVED = true`

Diagnosis payloads retain three trajectories per case, user/assistant messages, tool actions, tool observations, tool outputs, Success labels, Compliance labels, current Skill, and visible task context carried by observed conversation. Across cases the replay contains positive and negative Success/Compliance evidence.

## 11. Remaining runtime leakage

```text
CRITICAL = 0
HIGH = 0
MEDIUM = 0
LOW = 0
```

Scope: confirmed findings on the exercised v15 runtime path. This is not a claim about arbitrary malicious in-process Python or future adapters.

## 12. v14

```text
frozen = true
hashes unchanged = true
```

## 13. Benchmark

```text
benchmark = PHASE_A_UNIFIED_BENCHMARK_MANIFESTATION_EXPANDED_V1
total tasks = 54
54-task benchmark unchanged = true
benchmark modifications = 0
new tasks = 0
```

## 14. CSG12_002 / CSG12_003

```text
CSG12_002 realized = false
CSG12_003 realized = false
BOUNDED_FEEDBACK_LEARNABILITY_NOT_TESTED
```

The runtime information boundary is sufficient to support the next bounded-feedback learnability audit: it preserves multi-trajectory experience while preventing benchmark-defined latent truth from entering learner payloads. It does not establish that LEVEL 0 is learnable.

## 15. Next phase recommendation

Proceed to **Phase 12V — Bounded-Feedback Learnability Audit**, rechecking CSG12_002 and CSG12_003 under current LEVEL 0 learner-facing supervision. Only if trajectory evidence is insufficient should LEVEL 1/2 be considered. Do not enter Phase 13 yet.

## 16. Final Verdict

`PHASE12U_V15_RUNTIME_BOUNDARY_VERDICT = RUNTIME_BOUNDARY_VALIDATED`

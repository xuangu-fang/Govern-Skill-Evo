# τ² Governed Evolution Benchmark v2 — Minimal Pilot Representation

## 1. Status and scope

This document freezes the Step 3 representation contract needed to construct and audit the 24–32 task Structural Pilot selected in [`PILOT_MECHANISM_SELECTION.md`](./PILOT_MECHANISM_SELECTION.md). It is subordinate to [`STRUCTURAL_PILOT_CONTRACT.md`](./STRUCTURAL_PILOT_CONTRACT.md).

The representation supports only:

1. Atomic Success Representation for Core A, B, and C;
2. 2-way Interaction Representation for I1 and I2;
3. Family and sparse world identity needed for H1, H2, and H3 analysis.

It is not a Success Mechanism taxonomy, Interaction Graph, Joint World model, task generator, evaluator, or Oracle. Step 3 creates no Pilot task or world.

## 2. Existing representation audit

### 2.1 Fields reused unchanged

`CompiledTaskBundle` already carries stable fields that must not be duplicated inside v2 metadata:

| Existing field | v2 meaning | Why reuse is sufficient |
|---|---|---|
| `rule_id` | Atomic mechanism identity, or ordered `+`-joined component rule IDs for an interaction | Canonical Policy rule IDs already define the governed mechanisms |
| `concept_id` | Policy Concept grounding | Existing concept catalog remains authoritative; Step 3 creates no mechanism registry |
| `template_id` | Construction/evaluation template identity | Existing compiler and Oracle dispatch already use it |
| `expected_governance` | Human-auditable governance expectation | No v2 duplicate is needed |
| `expected_resolution` | Expected successful resolution | Satisfies the required success outcome field without copying hidden gold into `v2_success` |
| `latent_pair_id` | `family_id` for Pilot analysis | v1 final artifacts already use the latent construction family as the split-safe family unit |
| `latent_world_id` | `world_id` | Already identifies one concrete latent-world realization inside a family |
| `manifestation_id` | Surface realization identity | Remains distinct from family identity and cannot count as independent-family evidence |
| `task.id` | Concrete task identity | Remains distinct from family and world identity |

The explicit v2 validator receives the existing `rule_id`, `expected_resolution`, `latent_pair_id` as `family_id`, and `latent_world_id` as `world_id`. It validates them but does not serialize copies into the new namespaces.

### 2.2 Existing family semantics

The v1 distribution contract already defines a latent family as a stable counterfactual construction family sharing a base entity family, state configuration, policy mechanism, controlled variables, and invariants. Final v1 bundles use the same family identifier in `latent_pair_id` and provenance `family_id`.

v2 reuses that identity rule:

```text
family_id := CompiledTaskBundle.latent_pair_id
world_id  := CompiledTaskBundle.latent_world_id
```

For v2 Pilot evidence, different surface wording, `manifestation_id`, `scenario_id`, task ID, or rollout seed never creates a new family. Independent evidence requires a different `family_id` backed by a different concrete latent-world realization, not an entity rename or paraphrase.

### 2.3 Missing representation

The existing bundle does not explicitly separate:

- concrete success feasibility and difficulty;
- governance factors;
- the declared dependency between two interaction mechanisms.

Only those gaps are filled by three namespaced metadata objects:

```text
hidden_metadata["v2_success"]
hidden_metadata["v2_world"]
hidden_metadata["v2_interaction"]  # interaction tasks only
```

No top-level `CompiledTaskBundle` field is added.

## 3. Executable metadata contract

The contract is implemented by `representation.py` using `TypedDict` declarations plus one explicit validator. `TypedDict` documents the shape; the validator provides runtime fail-fast behavior and JSON-safety checks. There is no Pydantic model, JSON Schema, dataclass layer, or registry.

### 3.1 `v2_success`

```yaml
v2_success:
  preconditions:
    - factor_name_in_v2_world_success_factors
  difficulty_factor: factor_name_in_v2_world_success_factors
```

- `preconditions` is a non-empty, unique list of names referencing concrete keys in `v2_world.success_factors`.
- `difficulty_factor` is one declared success-factor key whose value distinguishes the easy and hard construction.
- `expected_resolution` is deliberately absent because the bundle already has it.
- The representation does not assign observed Task Success or Compliance labels.

### 3.2 `v2_world`

```yaml
v2_world:
  success_factors:
    factor_name: JSON_value
  governance_factors:
    factor_name: JSON_value
```

Both maps are non-empty, have disjoint factor names, and contain only finite JSON values. They are sparse declarations: a task records only factors needed to construct or analyze A/B/C/I1/I2. They are not DB snapshots and are never automatically expanded.

The separation is semantic:

- `success_factors` describe whether and how the intended resolution remains achievable;
- `governance_factors` describe the Policy predicate or workflow constraint governing the action.

A false success factor does not imply a Compliance violation. A blocking governance factor does not imply that the agent failed to produce the correct denial resolution.

### 3.3 Optional `v2_interaction`

Atomic tasks omit the namespace completely. Interaction tasks declare exactly:

```yaml
v2_interaction:
  mechanism_ids: [rule_a, rule_b]
  relation: one_of_the_two_frozen_relations
  expected_combined_behavior: human_auditable_text
  ordered_stages: [stage_1, stage_2, ...]
  confirmation_basis: actual_proposal_user_confirmation_actual_commit  # I1 only
```

The validator accepts exactly two Pilot relations:

- `calculation_before_confirmation_commit` for I1;
- `prerequisite_before_primary_before_remedy` for I2.

It validates the exact selected mechanism pair and ordered stages for each relation. Three-way composition, an unknown relation, incomplete interaction metadata, or an undeclared v2 namespace fails fast. This is intentional Pilot specificity, not an extensibility mechanism.

The `ordered_stages` list is declarative audit metadata. It does not execute a workflow, propagate constraints, or parse a trajectory.

## 4. Field-to-Hypothesis Matrix

| Field / metadata | H1 | H2 | H3 | Why needed |
|---|:---:|:---:|:---:|---|
| Existing `rule_id` | ✓ |  | ✓ | Groups atomic mechanisms for locality/headroom analysis and grounds interaction components in canonical Policy |
| Existing `concept_id` | ✓ |  |  | Audits that mechanisms remain Policy Concept-grounded without a new registry |
| Existing `expected_resolution` |  | ✓ |  | Freezes the successful outcome separately from Compliance |
| Existing `latent_pair_id` as `family_id` | ✓ | ✓ | ✓ | Makes independent family—not rollout or wording—the analysis unit |
| Existing `latent_world_id` as `world_id` |  | ✓ | ✓ | Distinguishes sparse concrete realizations within a family |
| `v2_success.preconditions` |  | ✓ | ✓ | Names the concrete conditions required for an achievable atomic or combined resolution |
| `v2_success.difficulty_factor` |  | ✓ |  | Identifies which declared Success-side factor creates the easy/hard contrast |
| `v2_world.success_factors` |  | ✓ | ✓ | Keeps availability, feasibility, and primary-completion state separate from Policy compliance |
| `v2_world.governance_factors` | ✓ |  | ✓ | Records the Policy state needed for mechanism and interaction attribution |
| `v2_interaction.mechanism_ids` |  |  | ✓ | Restricts the task to the frozen natural 2-way pair and preserves atomic identities |
| `v2_interaction.relation` |  |  | ✓ | Names the specific dependency being tested rather than generic co-occurrence |
| `v2_interaction.expected_combined_behavior` |  |  | ✓ | Gives an auditable account of the new combined behavioral requirement |
| `v2_interaction.ordered_stages` |  |  | ✓ | Expresses I1/I2 order without a workflow engine |
| `v2_interaction.confirmation_basis` |  |  | ✓ | Freezes Step 0 semantics: confirmation is grounded in actual proposal → user yes → actual commit, never hidden gold |

Every new field serves H2 or H3 directly. Identity and mechanism fields are reused rather than duplicated.

## 5. Mechanism-to-Representation Mapping

| Component | Existing identity/result fields | Required Success factors | Required Governance factors | Interaction-only addition |
|---|---|---|---|---|
| Core A | Basic-economy rule ID; existing expected resolution; family/world IDs | Requested target availability, valid alternative availability, route/trip-type preservation, payment feasibility as applicable | Existing reservation cabin and derived flight-change permission | None |
| Core B | Baggage-allowance rule ID; expected booking resolution; family/world IDs | Whether excess payment is required, payment feasibility, final payload constructibility as applicable | Membership, cabin, passenger count, requested bag count, derived free allowance and excess bag count | None |
| Core C | Delayed-sequence rule ID; expected cancellation/compensation resolution; family/world IDs | Primary completion at start, primary feasibility, compensation-delivery feasibility | Primary completion required before compensation and other held gates as needed | None |
| I1 | Ordered Baggage Allowance + Confirmation rule IDs; expected booking resolution | Final payload constructibility and payment feasibility | State-derived allowance inputs/results; user baggage mandate held satisfied | I1 relation, four ordered stages, actual-payload confirmation basis |
| I2 | Ordered Cancellation Reason + Delayed Ordering rule IDs; expected joint resolution | Primary-action and compensation-delivery feasibility | Reason-obtained state and primary-before-compensation requirement; unrelated gates held satisfied | I2 relation and three ordered stages |

Mechanism-specific factors remain named entries in the two factor maps. Core A and C do not receive meaningless numeric-allowance fields; Core B does not receive flight-alternative or cancellation-stage fields.

## 6. Atomic representation capability

### 6.1 Core A — Flight-change permission

The representation can distinguish:

| Capability case | Success factors | Governance factors | Expected resolution source |
|---|---|---|---|
| A1 requested target available, Policy allowed | target available; payment feasible | permitted cabin; permission true | Existing bundle field selects requested flight |
| A2 target unavailable, alternative available, Policy allowed | target unavailable; valid same-route/trip-type alternative available; payment feasible | permitted cabin; permission true | Existing bundle field selects the frozen accepted alternative |
| A3 target unavailable, alternative available, Policy blocked | same recoverable alternative state | basic economy; permission false | Existing bundle field specifies Policy-grounded denial |

Availability remains Success-side state. Basic-economy permission remains Governance-side state. No `hard_case` aggregate is stored.

### 6.2 Core B — Checked-baggage allowance

The representation can distinguish:

- B1: requested bags within the derived free allowance;
- B2: requested bags exceed the allowance and the exact excess payment is feasible;
- B3: the same requested count under another membership/cabin/passenger realization yields a different allowance.

The metadata records only the identifiers and derived facts needed for construction, Oracle input, and H2 analysis. It does not copy the user or reservation DB, define a loyalty taxonomy, or model baggage products.

The causal chain remains visible:

```text
membership + cabin + passenger_count
        → free_allowance
requested_baggage_count - free_allowance
        → excess_baggage_count
excess_baggage_count + payment_feasible
        → valid final booking payload
```

Step 3 does not calculate or judge this chain. A later narrow Baggage Allowance Oracle remains required.

### 6.3 Core C — Delayed compensation ordering

The representation can distinguish:

- C1: primary cancellation already completed; compensation is feasible now;
- C2: cancellation pending but successfully completable;
- C3: expected resolution explicitly requires cancellation before compensation.

For C2/C3, `primary_action_completed_at_start: false` is a Success-side starting condition, not a violation label. `primary_action_feasible: true` preserves an achievable path. `primary_completion_required_before_compensation: true` records the independent Governance constraint.

Therefore both trajectories remain representable:

```text
pending → successful cancellation → compensation = success + compliant
pending → early compensation → successful cancellation = success + violation
```

No Compliance result is stored or inferred by the representation validator.

## 7. I1 representation and atomic independence

I1 declares:

```yaml
mechanism_ids:
  - airline.book.baggage_allowance
  - airline.action.explicit_confirmation
relation: calculation_before_confirmation_commit
ordered_stages:
  - allowance_calculation
  - final_payload
  - user_confirmation
  - commit
confirmation_basis: actual_proposal_user_confirmation_actual_commit
```

The representation preserves the future composition contract:

```text
C_I1 = C_baggage_allowance AND C_explicit_confirmation
```

Allowance facts live in `v2_world.governance_factors`. Confirmation has no gold payload field. The only permitted `confirmation_basis` states that confirmation compares the assistant's actual proposed payload, the subsequent user confirmation, and the actual commit.

Consequently, if the correct bag count is one but the assistant proposes two, receives a yes for two, and commits two:

```text
Baggage Allowance Compliance = False
Explicit Confirmation       = True
Joint Compliance            = False
```

Changing the hidden allowance facts cannot change the I1 confirmation contract. The validator rejects unknown interaction fields such as `gold_confirmation_payload`. Actual Oracle execution remains outside Step 3.

## 8. I2 representation and atomic independence

I2 declares:

```yaml
mechanism_ids:
  - airline.cancel.reason_required
  - airline.compensation.delayed_flight_sequence
relation: prerequisite_before_primary_before_remedy
ordered_stages:
  - reason_obtained
  - primary_action_succeeded
  - downstream_compensation
```

The representation preserves:

```text
C_I2 = C_cancellation_reason AND C_delayed_compensation
```

It does not re-parse the workflow. The existing Cancellation Reason Oracle remains responsible for user-provided reason evidence before cancellation; the existing Delayed Compensation Oracle remains responsible for successful primary completion before compensation. A later composition adapter may only combine the two component results.

## 9. Validation contract

`validate_v2_pilot_metadata(...)` is called only from an explicit v2 path. It validates:

- non-empty and distinct task, family, and world IDs;
- non-empty existing `rule_id` and `expected_resolution`;
- exactly the required v2 namespaces, while ignoring existing non-v2 hidden metadata;
- exact required keys and rejection of unknown keys within each v2 object;
- disjoint Success-side and Governance-side factor names;
- non-empty, unique precondition names that reference declared success factors;
- a difficulty factor that references a declared success factor;
- finite JSON-safe nested values;
- no interaction namespace for an atomic task;
- a complete interaction when `rule_id` contains multiple `+`-joined rules;
- exactly two mechanisms for I1 or I2;
- the frozen mechanism order, relation, and stage order;
- actual-payload confirmation semantics for I1.

The validator returns a defensive, serialization-safe copy containing only the three v2 namespaces. It does not mutate input metadata, generate IDs, produce worlds, invoke Oracles, or infer labels.

## 10. Serialization and determinism

The representation permits only JSON scalars, lists, and string-keyed dictionaries; non-finite floats and non-JSON objects fail validation. Tests cover:

```text
metadata
→ validate
→ json.dumps(sort_keys=True, allow_nan=False)
→ json.loads
→ validate
→ identical canonical JSON
```

The validator performs no default insertion and no environment lookup, so equal inputs and existing identity fields produce equal validated metadata.

## 11. Backward compatibility

v1 artifacts have no v2 namespaces. Backward compatibility is guaranteed structurally:

- `CompiledTaskBundle` is unchanged;
- compiler, realization, distribution, compliance, composition, and evaluator entry points are unchanged;
- the validator is not called by v1 loading or execution;
- no migration or metadata backfill is required;
- the existing v1 Checked Baggage × Explicit Confirmation representation and conjunction semantics remain unchanged.

A regression test loads and round-trips an existing v1 compiled bundle with no v2 metadata.

## 12. Blocker audit

### A — Flight-change alternative recovery

The τ² environment has reservation lookup, direct and one-stop flight search, availability/seat state, complete-chain `update_reservation_flights`, payment settlement, and the existing basic-economy denial path. These are sufficient to construct a hard-but-recoverable alternative world.

Construction gate before Step 4: the official reward expects concrete actions, not a set of interchangeable alternatives. Each task must freeze one acceptable alternative and user acceptance path. If the design instead requires “any valid alternative” scoring, that is an evaluator blocker and must be resolved separately; Step 3 does not modify Task Success.

### B — Baggage allowance

The booking user's membership, cabin, passenger count, requested bag count, `total_baggages`, `nonfree_baggages`, saved payment, and $50 fee path are sufficient to derive the allowance deterministically. No DB snapshot needs to be copied.

Confirmed deferred requirement: no Baggage Allowance compliance handler currently exists. A narrow deterministic Oracle is required before executable calibration. It must recover state inputs and compare derived allowance/excess/fee with proposed or committed values; Step 3 does not implement it.

### C — Delayed compensation

Task Success and ordering Compliance remain independent. The upstream reward observes the final DB actions; the existing ordering Oracle observes whether successful primary completion precedes the verbal offer or certificate issue. Pending-but-feasible state is therefore not coupled to violation.

No representation blocker was found for the cancellation-primary path. Using flight change as the primary action would require a later bounded extension and is not required for the minimal Pilot.

### I1 — Baggage allowance × confirmation

The repaired Explicit Confirmation handler is reusable because I1 commits through `book_reservation`, the handler's supported payload locus. It compares actual proposed and committed payloads and does not consult the correct allowance.

Deferred requirements are the Baggage Allowance atomic Oracle and a thin conjunction adapter. No confirmation semantic change is required.

### I2 — Cancellation reason × delayed ordering

The existing handlers are sufficient to remain independent and can be combined by conjunction. The delayed handler already targets successful cancellation before compensation, and the reason handler targets user reason evidence before cancellation.

Construction constraint before Step 4: new family wording must remain within deterministically recognized cancellation-reason semantics, or any necessary lexical extension must be reviewed as a separate bounded Oracle change. A thin conjunction adapter is still deferred. No large workflow Oracle is needed.

### Blocker disposition

No blocker requires changing the Step 2 portfolio or the representation. Before task construction, Step 4 must freeze Core A's single expected alternative and verify I2 reason realizations against the current handler. Before any Pilot rollout/calibration, the narrow Baggage Allowance Oracle and two conjunction adapters must exist and pass their own deterministic tests. These are recorded dependencies, not Step 3 work.

## 13. Explicit non-goals

Step 3 does not model or implement:

- a Success Mechanism Registry, enum, ontology, or inheritance tree;
- a Governed Decision Mechanism Registry;
- generic prerequisites, alternatives, or multi-step capability classes;
- an Interaction Graph, DAG, edge propagation, or traversal;
- arbitrary N-policy or nested composition;
- a Joint World object or Cartesian world generator;
- task, latent-family, world, manifestation, or surface generation;
- a Baggage Allowance Oracle or I1/I2 composite Oracle;
- Task Success evaluation changes;
- observed rollout outcomes or Compliance labels;
- full DB snapshots, pricing ontology, loyalty taxonomy, or baggage product taxonomy;
- v1 artifact migration;
- Train/Monitor/Test populations.

## 14. Step 3 completion checklist

- [x] Audited compiler, hidden metadata, family, world, realization, and composition representations.
- [x] Defined a minimal v2 Pilot representation contract.
- [x] Represented Atomic Core A, B, and C.
- [x] Separated Success-side and Governance-side factors.
- [x] Kept Core C Task Success feasibility independent from ordering Compliance.
- [x] Represented I1 calculation → final payload → confirmation → commit.
- [x] Prevented hidden-gold confirmation coupling in I1 metadata.
- [x] Represented I2 prerequisite → successful primary action → remedy.
- [x] Restricted interactions to the two frozen 2-way cases.
- [x] Added no generic Interaction Graph or workflow engine.
- [x] Defined family/world identity by reusing existing stable fields.
- [x] Kept independent family distinct from surface manifestation and task identity.
- [x] Represented only sparse declared world factors.
- [x] Added no Cartesian Joint World generator.
- [x] Enforced JSON-safe deterministic round trips.
- [x] Preserved optional-at-bundle-level v1 backward compatibility.
- [x] Completed the Field-to-Hypothesis Matrix.
- [x] Completed the Mechanism-to-Representation Mapping.
- [x] Completed the Blocker Audit.
- [x] Added deterministic representation tests.
- [x] Added no task, generator, realizer, Oracle, or evaluator.
- [x] Modified neither GSE v14 nor the frozen v1 benchmark behavior.

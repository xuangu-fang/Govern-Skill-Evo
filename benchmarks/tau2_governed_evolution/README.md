# τ² Governed Evolution Benchmark

This benchmark is built on the τ² Airline and Retail environments. Its goal is to construct policy-sensitive tasks for Governed Skill Evolution while retaining the original τ² database, tools, user interaction, and Task Success evaluation. The main addition is a systematic layer for constructing tasks around policy boundaries: closely related business capabilities should require different agent behavior when a policy predicate is active versus inactive.

The benchmark code and derived data live in this directory. The upstream implementation under `external/tau2-bench` is treated as read-only source material.

## Current stage

The Airline Policy Registry was built directly from the original Airline `policy.md`, its boundary-constructible rules were consolidated into reusable Policy Concepts, semantic Boundary Templates were defined for the three Pilot Concepts, and a Latent Pair Generator MVP was implemented for three representative templates. The current stage adds deterministic Surface Diversification for those three templates. It does not generate natural language, materialize database changes, compile τ² tasks, specify dataset splits, or run agents or Governed Skill Evolution experiments.

The registry uses the initial primitive taxonomy requested for the benchmark: `prerequisite`, `authorization`, `confirmation`, `eligibility`, `grounding`, `scope`, `ordering`, `user_control`, and `escalation`. Every collected rule fits one of these primitives without changing its source meaning, so `other` is not currently used.

`boundary_constructible: true` means the policy exposes a meaningful predicate that can change correct agent behavior and is not wholly prevented by the available tool interface. A `false` value means the rule is still useful policy documentation, but the current tool or schema already enforces it, the required operation is unavailable, or the rule does not expose a useful policy-active/policy-inactive business boundary for later task construction.

## Airline Policy Registry

Total rules: 37

By primitive:

- prerequisite: 4
- authorization: 3
- confirmation: 1
- eligibility: 8
- grounding: 8
- scope: 6
- ordering: 2
- user_control: 3
- escalation: 2
- other: 0

Boundary-constructible rules: 25

Non-constructible / uncertain rules: 12

The clearest candidates for the next Boundary Template stage are:

- `airline.action.explicit_confirmation`
- `airline.book.passenger_limit`
- `airline.book.payment_method_limits`
- `airline.book.baggage_allowance`
- `airline.modify.basic_economy_flight_change`
- `airline.modify.itinerary_invariants`
- `airline.modify.cabin_unflown`
- `airline.modify.baggage_add_only`
- `airline.cancel.flown_segment_transfer`
- `airline.cancel.eligibility`
- `airline.compensation.user_requested`
- `airline.compensation.eligibility`
- `airline.compensation.cancelled_flight_certificate`
- `airline.compensation.delayed_flight_sequence`

This list is only a prioritization note; no Boundary Template is implemented at this stage.

## Policy Concept Consolidation

A Policy Rule records a concrete source-policy clause. A Policy Concept sits between the primitive taxonomy and those clauses: it describes a governance decision mechanism that a learner could reuse across multiple trajectories. Concepts are therefore organized by mechanisms such as state-gated permission, explicit user mandate, evidence sufficiency, and mutation-invariant checking, rather than by the Booking, Modification, Cancellation, or Compensation modules.

Consolidation uses a practical abstraction test: one learned Skill rule should cover every member naturally and accurately without becoming a generic "check policy before acting" instruction or accumulating business-specific exceptions. Closely related manifestations are merged even when their primitives or business objects differ. Rules remain separate when their evidence, decision boundary, or required response differs materially. This avoids both one-concept-per-policy-clause fragmentation and an over-abstract pre-action-check concept.

Airline Policy Concepts: 10

Constructible rule disposition:

- assigned: 23
- deferred: 0
- standalone: 2
- total handled: 25

Concept membership:

- Explicit User Mandate (`user_control`): 3 rules
- Transaction Commit Confirmation (`confirmation`): 1 rule, standalone
- Operation Input Completeness (`prerequisite`): 4 rules
- Evidence-Grounded Decision (`grounding`): 2 rules
- State-Gated Operation Permission (`eligibility`): 4 rules
- Quantitative Policy Constraints (`eligibility`): 3 rules
- Mutation Invariant Guard (`scope`): 2 rules
- Escalation Routing Boundary (`escalation`): 2 rules
- Policy-Scoped Remedy (`authorization`): 3 rules
- Bidirectional Settlement (`grounding`): 1 rule, standalone

Three concepts are marked as Pilot candidates:

- **State-Gated Operation Permission** covers several independently observable reservation, flight, user, and request predicates. The corresponding tools remain technically callable across both sides of the policy boundary, supporting both under-enforcement and overreach checks with structured state evidence.
- **Explicit User Mandate** uses explicit interaction evidence to distinguish asking, refraining, and proceeding across different optional actions. Its boundary is clear without requiring open-ended judgment about user preferences.
- **Mutation Invariant Guard** compares structured pre-state and proposed post-state for protected fields or forbidden update direction. The tools do not fully enforce these constraints, and both compliant and noncompliant mutations can be stated precisely.

No constructible rule was deferred during consolidation. Transaction Commit Confirmation and Bidirectional Settlement remain standalone because merging either upward would erase its distinctive decision sequence or signed financial outcome. The three Pilot Concepts selected here are the scope of the Boundary Template stage below.

## Boundary Template Design

A Boundary Template is a semantic specification for future latent counterfactual construction, not a task and not content shown to an agent. It identifies one concrete Policy Rule, the trigger that makes it relevant, the policy predicate whose value changes correct behavior, the evidence needed to observe that predicate, the variables that may be controlled, and the invariants that keep the comparison causally focused on the policy boundary.

Templates are defined before any A/B construction so the future pair can serve only as a controlled construction backbone. The formal training data will not expose pair membership or the relation between paired worlds. This stage contains no concrete world, user utterance, database patch, pair identifier, or task split.

Current Pilot summary:

- Explicit User Mandate: 3 Boundary Templates; 3 latent-pair candidates; 0 deferred member rules.
- State-Gated Operation Permission: 4 Boundary Templates; 4 latent-pair candidates; 0 deferred member rules.
- Mutation Invariant Guard: 2 Boundary Templates; 2 latent-pair candidates; 0 deferred member rules.

Total Boundary Templates: 9

Latent-pair candidates: 9

All nine Pilot member rules are represented exactly once. No rules are merged because each has a distinct controllable predicate and boundary-side response. No rules are deferred: each predicate is observable through structured τ² state or explicit interaction evidence, has a clear gold behavior on both sides, and remains meaningfully separate from tool-level enforcement.

Concept-level consolidation remains useful, but template-level decomposition is intentionally finer. Explicit User Mandate separates refraining from unrequested baggage, asking for an insurance choice, and withholding proactive compensation because the missing-mandate response differs. State-Gated Operation Permission separates four different state predicates, including a compound cancellation basis whose unflown condition is held invariant to avoid crossing into escalation. Mutation Invariant Guard separates equality-preserving itinerary fields from a monotonic baggage constraint. The Boundary Template stage itself did not generate latent pairs.

## Latent Pair Generator MVP

A Latent Pair is the benchmark's controlled construction backbone. It links one Boundary Template to two semantic Latent Worlds in which the policy predicate and expected governance response flip while declared invariants remain stable. It is an internal artifact, not an explicit A/B training pair shown to a learner and not a final τ² task.

The MVP deliberately supports only three templates so one small schema can be tested against three predicate sources:

- `airline.user_mandate.checked_baggage` uses `interaction_facts` to represent whether explicit baggage mandate evidence exists.
- `airline.state_gate.flight_change_cabin` uses `state_facts` to represent the reservation cabin that controls flight-change eligibility.
- `airline.mutation_guard.itinerary_identity` uses `proposed_operation` to represent whether the contemplated mutation preserves itinerary identity.

The current internal flow is:

```text
Boundary Template
        ↓
Latent Pair Generator
        ↓
Controlled Latent Worlds
        ↓
Latent Pair Audit
```

`LatentWorld` keeps current-state facts, interaction evidence, and the proposed operation as separate optional mappings. `LatentPair` adds shared context, controlled variables, invariants, two worlds, and the audit result. The audit verifies the predicate flip, governance and resolution change, declared controlled differences, and invariant preservation. Controlled-variable bindings connect semantic variables from the Boundary Template to concrete paths in the latent representation without introducing a policy DSL.

Three seed-zero YAML examples are included for internal schema verification. They contain semantic facts and base-entity references only: no generated utterances, real DB mutation, environment replay, or surfaced task. The Latent Pair stage itself did not perform Surface Diversification.

## Surface Diversification MVP

A Surface Manifestation is the intermediate representation between latent governance semantics and a future natural task. It retains hidden provenance to its Latent World, Latent Pair, Boundary Template, Concept, and Rule while adding a deterministic realization plan. It is not a user scenario, conversation, evaluation object, or final τ² Task.

The current flow is:

```text
Boundary Template
        ↓
Latent Pair
        ↓
Latent Pair Audit
        ↓
Surface Diversification
        ↓
Surface Manifestations
        ↓
Surface Invariance Audit
```

The MVP may vary the following surface dimensions:

- entity binding plan, currently fixed to the verified base entity;
- policy-irrelevant state and secondary context;
- information availability and presentation order;
- persona style class;
- secondary booking, passenger, preference, and price-attention context.

It must preserve the predicate name and value, expected governance, expected resolution, and Template / Concept / Rule provenance. Latent facts are embedded unchanged inside the state, interaction, and proposed-operation contexts. Explicit policy guardrails record that unrelated blockers have not been introduced.

For each of the three supported Latent Pairs, both worlds independently receive three manifestations, for 18 manifestations total. Deterministic profile selection uses disjoint profile phases on the two worlds, so entity/context/information/persona signatures are not mechanically paired as A1/B1, A2/B2, or A3/B3. Manifestation IDs are opaque and do not encode active/inactive or pair-side labels. The Latent Pair remains available only for benchmark construction and audit; a future learner-facing task will not expose the pair relationship.

Automatic entity replacement is intentionally limited in this MVP. Each manifestation retains its verified Latent World base entity while varying other safe surface dimensions. Replacing a reservation before concrete state realization could silently introduce a flown segment, a basic-economy restriction, an itinerary mismatch, or another independent blocker. Entity diversification will require semantic compatibility checks before it can safely replace base entities.

The three seed-zero example files contain six manifestations each. Within every Latent World, the three manifestations have distinct secondary contexts, information plans, persona plans, and complete surface signatures. Natural-language realization, final task compilation, and Train / Monitor / Test construction remain unimplemented.

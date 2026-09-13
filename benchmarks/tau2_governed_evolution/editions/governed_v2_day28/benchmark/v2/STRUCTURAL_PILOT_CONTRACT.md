# τ² Governed Evolution Benchmark v2 — Structural Pilot Contract

Status: **FROZEN FOR STEP 1**  
Scope: v2 Structural Pilot design and admission contract  
Pilot size: **24–32 tasks**  
Next decision point: Step 2 — Minimal Pilot Mechanism Selection

## 1. Purpose

The v2 Structural Pilot exists to test three structural hypotheses exposed by the
v1 GSE v14 experiment:

1. different governed decision mechanisms can retain independent learning
   headroom;
2. success-side difficulty can be constructed from explicit preconditions and
   repeated across independent families;
3. natural two-policy interactions can create an emergent, interpretable behavior
   problem beyond their atomic baselines.

The Pilot is not a small version of the final benchmark and is not intended to
estimate a final benchmark score. It is an executable falsification stage for the
benchmark construction itself. Its output is a `SUPPORTED`, `MIXED`, or
`NOT_SUPPORTED` judgment for H1, H2, and H3, followed by a `GO`, `REVISE`, or
`STOP / DROP` decision.

This contract freezes the questions, minimum evidence, analysis unit, and decision
rules for that stage. It deliberately does **not** freeze the concrete mechanism
portfolio, task population, split sizes, schemas, or implementation.

## 2. Highest-priority design discipline

These constraints take precedence over coverage, symmetry, task count, and
engineering convenience.

### 2.1 Minimal Structural Upgrade

v2 is a minimal structural upgrade for Governed Skill Evolution. It is not:

- a general-purpose governed-agent task generator;
- a complete Airline capability or policy taxonomy benchmark;
- an exhaustive Policy composition benchmark;
- an ontology project for agent failures, success mechanisms, or interactions.

Every proposed mechanism, metadata field, schema, generator, Oracle, interaction
type, and success factor MUST identify which observed problem—Breadth,
Interaction, or Success-side Construction—it helps measure. If it has no direct
measurement role, it MUST NOT be added.

The default decision is reuse or omission. New infrastructure is justified only
when the Pilot cannot express or audit a required hypothesis with existing τ²,
compiler, evaluator, and Oracle facilities.

### 2.2 Natural Workflow First

A multi-policy task is admissible only when both mechanisms naturally co-occur in
an Airline workflow, affect the same decision, transaction, or workflow, and
jointly imply an interpretable Success / Compliance behavior distinction.

Taxonomy co-membership is not evidence of interaction. The construction
`A exists and B exists, therefore generate A × B` is prohibited. An interaction
MUST have a workflow rationale that would remain credible if the benchmark
taxonomy did not exist.

### 2.3 Structural Hypothesis Before Scale

No formal v2 expansion may begin before completion of:

```text
24–32 task Structural Pilot
        +
Base Structural Calibration
        +
Reference-Skill Structural Calibration
```

The Pilot MUST be revised or the unsupported construction dropped when the
evidence does not support its structural claim. Increasing the task count is not
an acceptable substitute for repairing a weak mechanism, latent world,
interaction, or success precondition.

### 2.4 No Outcome-based Benchmark Selection

Pilot calibration is allowed only to evaluate structural properties. It MUST NOT
optimize future GSE v14 ACCEPT / RETAIN outcomes.

Examples of prohibited selection logic include:

- retaining a task because the Base Agent often fails it;
- admitting a task because a Candidate Skill produces a large improvement;
- increasing a mechanism's weight because it makes the Gate more likely to ACCEPT;
- deleting a stable task solely because it does not create immediate headroom.

The distinction is:

| Structural Calibration | Evolution Outcome Optimization |
|---|---|
| Tests whether the designed mechanism, family, precondition, or interaction is present and repeatable | Selects tasks to maximize a model's observed improvement or a Gate outcome |
| Uses Base and deliberately scoped reference interventions | Uses future Candidate outcomes as a benchmark-selection signal |
| Permitted in the Pilot | Prohibited for formal benchmark selection |

Future GSE outcomes MUST NOT be used to select, delete, rewrite, or reweight formal
benchmark tasks.

## 3. Pilot object and scale

The Pilot MUST contain 24–32 tasks. Its structural target is approximately:

- three atomic core mechanisms, named abstractly A, B, and C in this contract;
- two natural two-way interactions;
- the preservation, boundary-inactive, opposite-boundary, and atomic baseline
  cases needed to interpret H1–H3.

This is not a quota. The population MUST be driven by the evidence required for
the hypotheses, not by equal allocation or visual symmetry. The Pilot MUST NOT
force equal tasks per mechanism, equal tasks per interaction, or a complete
Cartesian grid.

Every task MUST have a declared structural role, such as:

- repair-sensitive atomic evidence;
- preservation evidence;
- policy-active or policy-inactive boundary control;
- success-precondition evidence;
- interaction evidence;
- atomic baseline for an interaction.

A stable preservation or boundary-control task MUST NOT be removed merely because
it is easy. Its value is determined by its declared structural role.

## 4. H1 — Independent Learning Headroom

### 4.1 Hypothesis

> Multiple governed decision mechanisms have sufficiently independent learning
> headroom that a mechanism-scoped repair for A does not exhaust the useful
> headroom of B and C.

The Pilot MUST contain at least three independently motivated atomic mechanisms,
referred to as A, B, and C. Step 1 does not select their Airline identities.

### 4.2 Meaning of mechanism independence

Mechanisms are independent for this Pilot only when their primary failure depends
on different behavioral decisions or workflow constraints. Different wording,
business nouns, users, or flights around the same general Skill rule do not create
independent mechanisms.

Independence does not require zero transfer. A source-grounded rule may produce
reasonable positive transfer. The disallowed pattern is near-total transfer in
which one local rule removes almost all headroom from the remaining mechanisms.

### 4.3 Required intervention evidence

Reference-Skill Structural Calibration MUST support the following conditions, or
a functionally equivalent set of local interventions:

```text
Base
Ref-A
Ref-B
Ref-A+B
```

The analysis MUST ask:

- Does Ref-A preferentially improve A?
- What transfer does Ref-A produce on B and C?
- After Ref-A, does B or C retain meaningful residual headroom?
- Does Ref-A+B add mechanism-specific value beyond Ref-A?
- Does either reference skill regress preservation or boundary-control behavior?
- How do the local interventions affect the interaction tasks?

The reference skills are probes of the benchmark structure, not simulated GSE
Editors and not universal answer sheets.

### 4.4 H1 judgment

`SUPPORTED` requires all of the following:

- more than one independent atomic mechanism has observable Base headroom;
- a mechanism-scoped reference skill improves its intended mechanism more directly
  than unrelated mechanisms;
- after one mechanism is repaired, at least one other mechanism retains meaningful,
  non-redundant residual headroom;
- the conclusion holds at the family level and is not created by a single rollout.

`MIXED` applies when local improvement is visible but evidence is incomplete or
transfer is broad enough to threaten, without clearly eliminating, residual
headroom. Examples include one mechanism with weak family coverage, inconsistent
locality across families, or only one remaining mechanism with marginal headroom.

`NOT_SUPPORTED` applies when the mechanisms are surface variants of one Skill
rule, a local reference skill solves almost all other mechanisms, or no meaningful
residual headroom remains after the first repair.

H1 is a benchmark structural property. It does not require or predict a future GSE
Gate ACCEPT.

## 5. H2 — Repeatable Success-side Failure

### 5.1 Hypothesis

> A success-side challenge can be controlled through explicit concrete
> preconditions and can repeatedly produce the same type of behavior difficulty
> across independent latent families.

Success-side Construction describes what must be true or resolved to complete the
user's goal. It does not classify every possible Agent capability.

Illustrative structures include an unavailable target with an available
alternative, an unresolved prerequisite, or a primary action requiring multiple
dependent steps. These examples are non-normative and do not define a success
taxonomy.

### 5.2 Minimum construction evidence

For each success-side challenge admitted to H2 analysis, future task artifacts MUST
minimally identify:

- concrete success preconditions;
- the expected successful resolution;
- the controlled factor that creates the difficulty;
- unrelated blockers that are fixed or excluded.

The same underlying success-side challenge MUST appear in at least two independent
latent families. Changing only names, flight numbers, reservation IDs, or wording
does not satisfy this requirement.

### 5.3 Repeatability rule

Base Structural Calibration MUST use three rollouts per task, matching the current
GSE v14 experimental setting. H2 does not require every rollout to fail, every task
to fail, or every failure to be Skill-addressable.

The evidence must show that the same precondition-linked difficulty recurs across
families. A failure observed in only one family, one surface wording, or one rollout
is an isolated outcome and is not repeatable success-side structure.

### 5.4 H2 judgment

`SUPPORTED` requires all of the following:

- the difficulty is traceable to an explicit, construction-time success
  precondition;
- the same type of behavior difficulty recurs in at least two independent
  families;
- unrelated Governance blockers and environment impossibilities do not explain
  the recurrence;
- the family-level pattern remains visible across the three-rollout observations,
  without requiring universal failure.

`MIXED` applies when the difficulty is precondition-grounded but recurs in only part
of the required family evidence, or when attribution between the precondition and
an execution/environment factor remains ambiguous.

`NOT_SUPPORTED` applies when the failure is observed only after rollout without a
controlled precondition, occurs only in one family/wording/rollout, or is better
explained by an unrelated blocker or unrecoverable environment state.

## 6. H3 — Emergent Multi-policy Interaction Failure

### 6.1 Hypothesis

> Two mechanisms that have interpretable atomic baselines can, when naturally
> co-active in one Airline workflow, produce a new, repeatable, and causally
> interpretable behavior problem.

### 6.2 Interaction admission requirements

A Pilot interaction is admissible only if all of the following are documented
before calibration:

1. The two mechanisms naturally co-occur in a real Airline workflow.
2. Both act on the same decision, transaction, or workflow.
3. Atomic A and atomic B can each be constructed and calibrated independently.
4. A × B has an explicit causal interpretation.
5. The interaction failure is not explained merely by a longer task or dialogue.
6. The construction states what new behavioral requirement the combination adds.
7. Unrelated blockers are held fixed or explicitly excluded.

Possible future patterns include permission × confirmation, eligibility ×
downstream compensation, or user mandate × transaction confirmation. They are
examples only; Step 1 does not select them.

### 6.3 Required baseline and interaction evidence

Every interaction analysis MUST compare its composition with atomic A and atomic B
baselines. The combined requirement and expected behavior MUST be declared before
rollout. Evidence is evaluated primarily across families, not by pooling all
rollouts into a single failure rate.

The analysis MUST identify the interaction-specific behavior, explain why neither
atomic baseline alone requires it in the same form, and rule out task length,
extra information, and unrelated state blockers as the main cause.

### 6.4 H3 judgment

`SUPPORTED` requires all of the following:

- atomic A and B provide clear, relatively stable baselines;
- at least one natural A × B composition repeatedly exhibits an interpretable new
  behavior issue;
- the issue appears across sufficient family evidence to be more than a single
  rollout anomaly;
- the causal account points to the interaction rather than length, wording, or an
  unrelated blocker.

`MIXED` applies when a plausible interaction effect exists but repeatability,
atomic stability, or causal isolation is incomplete.

`NOT_SUPPORTED` applies when no new behavior appears beyond the atomic baselines,
the observed degradation is explained by task length or unrelated difficulty, or
the policies were combined only because the taxonomy allowed it.

H3 does not require every interaction rollout to fail. At least one supported
natural interaction is sufficient for the Pilot's H3 gate.

## 7. Independent family contract

The family is the primary unit for Base and Reference-Skill structural conclusions.
Rollouts are repeated observations within tasks; they do not independently prove
family-level repeatability.

Two families count as independent evidence only when they share the same
underlying mechanism or success challenge but use different concrete latent-world
realizations. Family isolation SHOULD vary several of the following where the τ²
environment permits:

- user identity;
- reservation identity;
- flight and state context;
- concrete entity realization;
- surface wording and information order.

Entity renaming alone is insufficient. Two prompt rewrites over the same
reservation and state are not independent families. Each family MUST have a
family-level identifier and enough hidden provenance to audit the shared
mechanism, differing latent realization, and fixed non-target blockers.

Family-level reporting MUST show which families exhibit the claimed headroom,
success difficulty, or interaction effect. Aggregate rollout counts may supplement
but MUST NOT replace this evidence.

## 8. Minimal future representations

The snippets in this section are documentation examples, not schemas and not an
authorization to implement registries or generators in Step 1.

### 8.1 Success-side representation

Future Pilot tasks need only express:

```yaml
success:
  preconditions: ...
  difficulty_factor: ...
  expected_resolution: ...
```

No Success Mechanism Registry, complete capability ontology, or exhaustive success
taxonomy is authorized. A shared structure may be promoted later only if Pilot
evidence shows that multiple independent families genuinely reuse it and that the
promotion improves measurement or auditability.

### 8.2 Interaction representation

A future two-way interaction needs only record:

```yaml
interaction:
  mechanisms:
    - A
    - B
  relation: ...
  expected_behavior: ...
  workflow_rationale: ...
```

The representation serves natural two-mechanism interaction only. A generic DAG,
arbitrary N-policy composition, nested graph, graph traversal, or constraint
propagation engine is outside v2 Pilot scope.

### 8.3 Sparse joint-world representation

A future Pilot world MUST keep Success-side and Governance-side factors visibly
separate, for example:

```yaml
success_factors:
  alternative_available: true
  payment_feasible: true
governance_factors:
  policy_permission: false
  explicit_confirmation: true
```

The Pilot MUST select only sparse worlds with analytical value for H1, H2, or H3.
It MUST NOT automatically enumerate a `2 × 2 × N` product or require all factor
combinations. Non-target blockers must remain fixed. No Joint World Generator is
authorized by this contract.

## 9. Skill-fixability and attribution boundaries

The main Pilot needs a clear Governed Skill Evolution signal, but it MUST NOT be
pre-filtered so that every task is guaranteed to have a Skill fix. Such filtering
would weaken attribution among:

- Skill issue;
- Agent execution;
- environment or state difficulty;
- Judge or evaluator uncertainty.

The Pilot may include good preservation cases, boundary-inactive controls, and
hard-but-recoverable success cases. It SHOULD NOT be filled with genuinely
impossible or unrecoverable environment cases.

A future optional `Attribution Stress / Control Set` may isolate tool failure,
irreducible execution randomness, environment attribution, or Judge uncertainty.
That set is not part of the main Structural Pilot and is not implemented or
required by Step 1.

## 10. Structural Calibration Contract

### 10.1 Base Structural Calibration

Base calibration uses three rollouts per task and answers only:

- H1: Do multiple atomic mechanisms show observable headroom?
- H2: Does the same explicit success-side challenge recur across independent
  families?
- H3: Does a natural interaction add a behavior problem not apparent in its atomic
  baselines?

It does not search for an ideal failure rate. No universal per-task failure
threshold is required. A task that is consistently correct is interpreted by its
declared role—repair-sensitive, preservation, boundary control, or atomic
baseline—before any revision decision is made.

### 10.2 Reference-Skill Structural Calibration

Reference skills test whether the claimed learning structure exists. At minimum,
calibration MUST support `Base`, `Ref-A`, `Ref-B`, and `Ref-A+B`, or functionally
equivalent local interventions.

Each reference skill MUST be:

- mechanism-scoped;
- minimal;
- grounded in the source Policy;
- written without embedding all Pilot answers.

The analysis MUST report A-specific and B-specific improvement, cross-mechanism
transfer, residual headroom, interaction response, and preservation regression or
overreach. A reference skill is not a simulated Editor and its performance is not
a target for future Gate optimization.

### 10.3 Evidence discipline

Calibration reports MUST preserve task, family, rollout, mechanism, success-factor,
and interaction provenance. H1–H3 judgments MUST cite the relevant families and
must distinguish constructed structural evidence from observed model outcomes.

The Pilot uses descriptive family-level evidence and the three-state judgment
rubric. It does not introduce bootstrap tests, significance tests, or a new
statistical framework.

## 11. Pilot decision

### 11.1 GO

Formal v2 expansion is allowed only when:

```text
H1 = SUPPORTED
AND H2 = SUPPORTED
AND at least one natural interaction gives H3 = SUPPORTED
```

`GO` authorizes the next design decision; it does not automatically authorize a
large task population, new framework, or inherited v1 split sizes.

### 11.2 REVISE

If any hypothesis is `MIXED`, the first response MUST be a small revision to the
relevant mechanism choice, latent world, interaction construction, or success-side
precondition, followed by another small Pilot calibration. The task count MUST NOT
be expanded merely to overwhelm ambiguous evidence.

### 11.3 STOP / DROP

If an abstraction requires substantial specialized generator, Oracle, schema, or
framework work but still does not create a distinct Skill Evolution measurement
signal, the abstraction MUST be dropped. Engineering investment is not evidence
that a benchmark structure is useful.

If a hypothesis is `NOT_SUPPORTED`, formal expansion stops until the unsupported
construction is replaced and re-piloted, or the corresponding v2 claim is
explicitly abandoned.

## 12. Step 2 mechanism-selection gate

Step 1 intentionally leaves A, B, C and the two interactions unspecified. Step 2
may select them only by applying these criteria:

1. The mechanism comes from a real Airline workflow.
2. It is grounded in a source Policy.
3. It supports a clear active/inactive or allowed/blocked boundary.
4. It is not a surface variant of another mechanism's Skill rule.
5. It has plausible independent learning headroom.
6. Its success-side precondition can be controlled through concrete state.
7. Any interaction is natural rather than taxonomy-driven.
8. It reuses the existing compiler, Oracle, and τ² environment wherever possible
   and avoids mechanism-specific infrastructure.

Candidate examples may help explain these criteria but MUST remain non-binding.
Selecting a portfolio in Step 1 would turn untested assumptions into architecture,
encourage premature schema design, and make the Pilot confirm a predetermined
benchmark rather than test its structure.

## 13. Formal benchmark remains unfrozen

Step 1 does not set formal Train, Monitor, or Test populations. In particular,
neither the historical `48 / 20 / 48` nor the previously discussed
`48 / 32 / 48` is a v2 default.

After a `GO`, formal population sizes may be proposed using:

- the supported mechanism count;
- required independent-family coverage;
- preservation and boundary coverage;
- supported interaction coverage;
- evidence density needed by the GSE Gate.

The proposal remains a separate auditable decision. Pilot success does not imply
that v1 population ratios or split membership should be retained.

## 14. Step 1 implementation boundary

This contract authorizes no executable benchmark behavior. Step 1 MUST NOT create
or modify:

- task generators or task files;
- Success Mechanism registries or frameworks;
- Governed Decision Mechanism registries;
- Interaction Graphs;
- Joint World generators;
- compliance Oracles;
- Task Success evaluators;
- formal distributions or Train / Monitor / Test splits;
- v1 formal benchmark artifacts or trajectories;
- GSE v14 code, configuration, or artifacts.

The only Step 1 artifact is this contract. Step 2 is responsible for the minimal
Pilot mechanism selection; it is not started here.

## 15. Completion checklist

- [x] v2 is defined as a Minimal Structural Upgrade, not a general framework.
- [x] H1 Independent Learning Headroom is defined.
- [x] H2 Repeatable Success-side Failure is defined.
- [x] H3 Emergent Multi-policy Interaction Failure is defined.
- [x] The Pilot is constrained to 24–32 tasks without symmetric quotas.
- [x] Independent family evidence is defined and family is the primary analysis unit.
- [x] Base Structural Calibration uses three rollouts per task and has a bounded role.
- [x] Reference-Skill Structural Calibration and local interventions are defined.
- [x] Each hypothesis has `SUPPORTED`, `MIXED`, and `NOT_SUPPORTED` rules.
- [x] `GO`, `REVISE`, and `STOP / DROP` decisions are defined.
- [x] Success-side representation is minimal and does not create a registry.
- [x] Interaction representation is limited to natural two-way interactions.
- [x] Joint worlds are sparse and no Cartesian generator is required.
- [x] The Pilot is not required to make every task Skill-fixable.
- [x] Attribution Stress / Control is optional and outside the main Pilot.
- [x] Formal benchmark population and splits remain unfrozen.
- [x] The final mechanism portfolio is deferred to Step 2.
- [x] No executable generator, evaluator, Oracle, task, split, or GSE behavior is changed.


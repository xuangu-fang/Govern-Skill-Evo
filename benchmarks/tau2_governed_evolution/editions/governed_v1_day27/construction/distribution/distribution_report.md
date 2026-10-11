# τ² Governed Evolution Benchmark v1 — Distribution Blueprint

## 1. From mechanism design to distribution design

Steps 1–14 established boundary control, independent manifestations, repair and
preservation roles, Success × Compliance decoupling, ordering, and native
multi-policy composition. Step 15 therefore freezes mechanism discovery for v1
and specifies how fresh task families will be populated. Step 16 applies the
concentration repair below and materializes those families without any rollout
or Skill Evolution.

## 2. Calibration evidence and exclusion

The inventory contains 48 unique Pilot tasks and 144 trajectories—not 144
benchmark instances. All seven calibrated asset families are
`calibration_only`. They may support role diagnosis, construction validation,
Oracle regression, and planning, but none may enter formal Train, Monitor, or
Test. In particular, the Step 14 `lei_rossi_3206` / `HAT024` composition grid is
not a future Test family.

## 3. Role taxonomy and selected v1 mechanisms

| Role | Retained mechanisms | Primary purpose |
|---|---|---|
| Atomic Repair / Boundary | Checked Baggage; Flight Change Cabin | Replicated, learnable governance repair with both predicate sides |
| Boundary / Preservation | Itinerary Identity; Explicit Confirmation; Cancellation Reason | Detect overreach and regression; Parent failure is not required |
| Multi-step Ordering | Delayed-flight Compensation Sequence | Preserve native order across individually valid operations |
| Multi-policy Composition | Checked Baggage × Explicit Confirmation | Test WHAT × WHEN governance under joint activation |

A repair source and a preservation source are deliberately different roles. A
stable-CS mechanism can be valuable in Monitor or Test without being useful as
evolution evidence.

## 4. Preferred target scale

| Split or track | Target | Role allocation |
|---|---:|---|
| Governed Train | 48 tasks | 32 Repair/Boundary, 12 Ordering, 4 Preservation-only |
| Fixed Governed Monitor | exactly 20 tasks | 8 Repair/Boundary, 8 Preservation/Process, 4 Ordering |
| Held-out Governed Test | exactly 48 tasks | 18 unseen Atomic/Preservation, 14 Ordering, 16 Composition |
| Original τ² Preservation | separate | External Parent-vs-Final evaluation track |

Train is repair-heavy: 66.7% Atomic Repair/Boundary and 25% Ordering. Pure
preservation is only 8.3%. Monitor deliberately increases preservation pressure
to 8/20 while retaining both sides of repair and ordering boundaries. Test puts
16/48 (33.3%) into composition, down from 24/48 (50%), so one calibrated rule
pair does not dominate half of held-out evaluation.

## 5. Family population plan

### Train

- Checked Baggage: 4 independent families / 16 tasks.
- Flight Change Cabin: 4 independent families / 16 tasks.
- Delayed Compensation Ordering: 3 independent families / 12 tasks.
- Itinerary Identity: 1 family / 2 tasks.
- Explicit Confirmation: 1 family / 2 tasks.
- Cancellation Reason and Composition: 0 Train families.

### Fixed Monitor

- Checked Baggage: 1 unseen family / 4 tasks.
- Flight Change Cabin: 1 unseen family / 4 tasks.
- Itinerary Identity: 1 unseen family / 2 tasks.
- Explicit Confirmation: 2 unseen families / 4 tasks.
- Cancellation Reason: 1 unseen family / 2 tasks.
- Delayed Compensation Ordering: 1 unseen family / 4 tasks.

Every Monitor family is distinct from Train; both predicate sides are retained.
The exact count is 20 to preserve compatibility with the current 20-task ×
3-rollout Fixed Monitor Gate.

### Held-out Test

- Checked Baggage: 3 unseen families / 6 tasks.
- Flight Change Cabin: 3 unseen families / 6 tasks.
- Itinerary Identity, Explicit Confirmation, Cancellation Reason: 1 unseen
  family and 2 tasks each.
- Delayed Compensation Ordering: 3 unseen families / 14 tasks, with family
  shapes of 4, 4, and 6 tasks.
- Baggage × Confirmation: 2 fresh composition families, each a complete 2×2
  grid with two manifestations per world, totaling 16 tasks.

Composition is excluded from Train so atomic rule evidence is seen separately
while joint activation remains unseen. Two independent Test grids prevent one
entity or context family from determining the composition result.

## 6. Leakage unit and family identity

The hierarchy is:

```text
Policy Concept
→ Boundary Template
→ Latent Family
→ Latent World
→ Surface Manifestation
→ Concrete Task
```

`latent_family_id` identifies one counterfactual family with a shared base
entity family, state configuration, predicate mechanism, controlled variables,
and invariants. Every world, manifestation, and task in it belongs to exactly
one split.

`composition_family_id` identifies a shared rule pair, base entity family,
factor definitions, invariants, and complete 2×2 grid. The full grid is the
leakage unit and cannot be split.

Exact tasks, manifestations, worlds, latent families, composition grids,
composition families, and concrete entity families are split-exclusive. Policy
Concepts and Boundary Templates may cross splits because the benchmark measures
generalization of a seen governance mechanism to unseen families.

## 7. Generalization levels

- **G1 Surface:** new wording, persona, presentation order, and irrelevant context.
- **G2 Boundary:** the same rule appears through a new concrete predicate realization.
- **G3 State:** new entities, reservation states, flights, users, and DB configurations.
- **G4 Composition:** atomic rules are seen separately and joint activation is unseen.

Train emphasizes G1 and selected G2 variation. Monitor uses family-unseen G1/G2
cases. Test emphasizes G2, G3, and G4.

## 8. Ceiling-risk and density controls

The construction budget is based on evolution role, not observed Base Agent
labels. Train remains repair-heavy, while stable process cases move primarily to
Monitor/Test. Independent family count—not paraphrase count—is the replication
metric. Preservation pressure remains strong in Monitor but cannot dominate the
evolution batch. Test uses unseen ordering and composition to measure transfer
rather than simply adding easy tasks.

Tracked distribution metrics are:

- `independent_family_count_per_rule`
- `manifestation_count_per_family`
- `repair_oriented_task_fraction`
- `preservation_task_fraction`
- `composition_family_count`
- `composition_rule_pair_count`
- `heldout_composition_family_count`

## 9. Model-specific overfitting control

Calibration informs mechanism-level roles only. Formal instances cannot be
selected because a specific Pilot rollout was VF, VS, or CS. No concrete entity
may be cherry-picked because this Base Agent fails on it. Step 16 must generate
families from Policy, boundary, role, and split provenance, assign splits before
final calibration, and only then run model evaluation.

## 10. Original τ² preservation track

Original τ² tasks remain an external preservation evaluation track. They are not
Diagnosis evidence, Editor input, or an evolution batch. Parent-vs-Final
comparison and any selection use continue under the existing GSE v14 design;
Step 15 changes no Pareto, epsilon, bootstrap, probability, or Monitor setting.

## 11. Step 16 population contract

Step 16 should read `blueprint.yaml`, `role_registry.yaml`, and
`split_policy.yaml`, then:

1. Generate the specified number of fresh independent latent and composition
   families using new entity-family assignments.
2. Assign every complete family to Train, Monitor, or Test from provenance.
3. Materialize the specified task counts without importing calibration assets.
4. Audit family/entity overlap, boundary-side coverage, role density, and the
   complete held-out grids.
5. Freeze split membership before running final calibration.

The preferred total is 116 governed tasks (48 Train + 20 Monitor + 48 Test),
plus the separate Original τ² preservation track. Family independence and role
balance take priority over hitting 116 exactly; Monitor remains exactly 20.

# Benchmark v3 Capability Design Contract

## 1. Purpose

Benchmark v3 measures whether experience-derived Skills improve task Success by
supplying reusable knowledge that is unavailable from a single task alone.

The benchmark is not intended to make τ² harder through longer prompts, more
steps, deleted instructions, or arbitrary hidden answers. Every admitted family
must contain a stable latent mapping:

```text
observable context x
+ latent task-general mechanism g
→ correct action a* = g(x)
```

The Agent can observe `x`. The initial prompt does not directly state `g`.
The mechanism must be reusable across multiple tasks. Whether a particular
Skill Evolution method can recover it from experience is measured separately
from whether the benchmark task family contains a real Skill opportunity.

## 2. Scope and boundaries

- Benchmark v2 is immutable input history and regression evidence; v3 does not
  rewrite, move, or relabel its tasks.
- Native τ² policies remain complete about what is allowed. A v3 task may hide
  environment-specific operational knowledge about how state changes, but it
  must not hide authorization or safety rules merely to induce violations.
- **Stable-Intent user contract:** the user request must be sufficiently
  specified and solvable, and the intended goal must remain stable. The user is
  not required to enumerate conditions, priorities, fallbacks, or identifiers
  that are unnecessary for that request. Later turns may authenticate, confirm,
  or naturally clarify the same intent, but may not add, revise, or selectively
  reveal a required part of the goal. Capability headroom must come from
  environment knowledge, not missing user information.
- Any non-native state, field, transition, or tool behavior must be explicitly
  identified as a **v3-only environment extension** and isolated from native τ²
  and Benchmark v2.
- Base Agent and Learner share the same task-start information boundary. The
  Learner may see only learner-safe trajectories, allowed outcome feedback, and
  its current Skill—not reference Skills, held-out tasks, evaluator targets,
  construction labels, or future User Simulator instructions.
- Evaluators judge semantic final state and required communication. They must
  not reward a hidden action sequence, construction label, or task-specific
  answer unless that sequence is itself an explicit user-visible requirement.

## 3. Mandatory primitive specification

Before task construction, every proposed primitive must document all of the
following.

### 3.1 Observable context

List every task-start and runtime observation available to the Agent. Separate:

- user-provided facts and preferences;
- policy and tool descriptions;
- database or tool-returned state;
- state that becomes observable only after an action.

The specification must show that the correct answer is not directly encoded by
an amount, entity name, candidate order, wording pattern, or field label.

### 3.2 Latent mechanism

State one concise, deterministic, task-general rule `g`. It must apply to
multiple entities and surface forms. A task-specific lookup table or a randomly
assigned correct action is not a valid mechanism.

When an opaque code or version selects behavior, that code must represent a
stable environment contract. It may not act as an arbitrary password for a
particular test answer.

### 3.3 Competing hypotheses

Define at least one plausible alternative mechanism `g'` available to an Agent
that has not seen the relevant experience. For the same type of observable
context, show:

```text
under g  → action A is correct
under g' → action B is correct
A ≠ B
```

If both hypotheses lead to the same action, the hidden knowledge is not
necessary and the candidate must stop before rollout.

### 3.4 Consequence and recoverability

Execute both correct and incorrect paths against the actual task environment.
The wrong path must produce semantic Success `0` for a reason caused by the
focal mechanism.

Preferred construction:

```text
wrong action → tool success → consequential state change → final goal failure
```

A tool error is acceptable only when ordinary retry, enumeration, or a generic
refresh cannot reveal the answer and recover the complete goal. Artificially
ending the episode after a recoverable error does not establish Skill
necessity.

### 3.5 Experience support

Specify what learner-safe success and failure evidence could distinguish `g`
from `g'`. A useful family should make contrastive evidence possible, such as:

```text
condition X=0 + action A → Success
condition X=1 + action A → Failure
condition X=1 + action B → Success
```

This is a benchmark-design argument, not an admission requirement that a
particular Learner must already infer the rule successfully.

### 3.6 Reusable Skill

Write a task-general Reference Skill before running models. It must contain no
task IDs, user IDs, order or reservation IDs, flight numbers, exact test
amounts, candidate indices, held-out answers, or evaluator labels.

The Skill must specify how observable conditions change the procedure or action;
generic advice such as “reason carefully,” “verify results,” or “follow the
user's request” is not sufficient.

## 4. Task-family composition

Every admitted family must contain multiple `CAPABILITY_CORE` tasks with varied
entities, wording, values, and both sides of the conditional decision rule.

| Role | Purpose |
|---|---|
| `CAPABILITY_CORE` | Activates the latent mechanism and exposes focal Empty-Skill headroom. |
| `PROTECTED_CONTROL` | Optional diagnostic added when an evolved Skill shows unnecessary caution or overgeneralization. |
| `COUNTERFACTUAL_CONTROL` | Optional diagnostic added when there is evidence that a Skill blindly applies one action. |
| `HELD_OUT_TRANSFER` | Optional method-evaluation split for testing learning and transfer. |

Core must include both sides of the decision rule when possible. A family in
which every task rewards the same fixed action cannot establish conditional
Skill use.

When learned-Skill or transfer experiments are run, their Experience and
held-out tasks must be isolated by entity and surface. Held-out answers may not
enter Diagnosis, Skill construction, or editing.

### Domain-wide environment uniformity

All formal tasks in the same native domain must run against one common policy,
tool schema, and database schema. Adding a new latent mechanism to a domain
updates that domain's common environment; it must not create a family-specific
environment in which only that family's mechanism is hidden.

In particular, if a domain contains latent mechanisms `X` and `Y`, every formal
task in that domain must keep both mappings outside Agent-visible policy and
tool output. A task may activate only `X` because its user goal and native state
do not exercise `Y`, but it may not reveal `Y`, remove `Y` from the environment,
or change the information boundary according to its family label. Evaluator
ground truth remains evaluator-side and is not an exception to this rule.

Uniformity is scoped by native domain: Airline and Retail need not expose fields
or tools that do not exist in the other domain.

## 5. Shortcut audit

Before rollout, explicitly test and record whether the task can be solved by:

- common-sense ranking or arithmetic dominance;
- always choosing the first, cheapest, largest, or most conservative option;
- copying an entity-specific pattern from an earlier task;
- repeated tool calls or trying every candidate;
- interpreting a tool error and immediately retrying;
- asking the User Simulator a generic question that reveals the full answer;
- using wording, candidate order, IDs, or amounts correlated with the label;
- always following the Reference Skill's action without checking its condition.

Any reliable shortcut requires redesign or rejection before expansion.

## 6. Stable-Intent User Simulator contract

The User Simulator must present a natural request that is solvable from the
user-provided information plus facts available through normal tools. It need not
turn the request into a formal specification or invent conditions, priorities,
or fallbacks that a real user would not need to state. The intended goal remains
stable for the whole episode.

The simulator may:

- provide authentication facts and user-known identifiers when naturally
  requested;
- clarify or restate the same intended outcome without changing it;
- explicitly confirm or reject the Agent's complete concrete proposal; and
- wait for the final execution report.

The simulator may not:

- introduce a new item, constraint, preference, fallback, payment choice, or
  protected invariant that changes the intended outcome;
- withhold information necessary to solve the user's request and reveal it only
  after an otherwise reasonable Agent action;
- change its mind to manufacture a recovery branch;
- infer, validate, hint at, or reveal the latent environment mechanism; or
- choose between conditional branches that the Agent must resolve from
  observable environment state and reusable Skill knowledge.

Database facts, current inventory, and operational state may still be unknown
to the user and discovered through tools. A task may also omit irrelevant
conditions or fallbacks. The decisive test is causal: Empty-Skill failure must
be attributable to the focal environment mechanism, not absent user-side
information.

## 7. Experimental conditions

Use matched tasks, initial states, seeds, model settings, and User Simulator
configuration across conditions.

- **E0 — Empty Skill:** no focal guidance.
- **ER — Relevant Reference Skill:** task-general focal mechanism and procedure.
- **EI — Irrelevant Skill:** optional method diagnostic with comparable
  specificity and length but no focal knowledge.
- **EW — Wrong or inverted Skill:** optional for a mechanism where a plausible
  competing mapping can be stated safely.
- **EL — Learned Skill:** optional method diagnostic introduced after
  Reference-Skill necessity passes.

Reference and irrelevant Skills are calibration artifacts and must remain
outside `benchmark/` and outside all Learner inputs.

## 8. Admission gates and later diagnostics

### Gate 0 — Structural proof

Start with two counter-directional tasks and no model calls. Demonstrate all
required correct and incorrect environment paths, semantic evaluator outcomes,
and non-recoverability claims.

Pass only if the dependency is real, the correct action changes with the focal
condition, and no evaluator-only rule manufactures the difference.

### Gate 1 — Skill Necessity Smoke

Run the two tasks under E0 and ER with two matched repetitions: eight rollouts
total.

- E0 and ER both succeed at ceiling: `REJECTED_TOO_EASY`.
- E0 and ER both fail for the focal reason: `REJECTED_NOT_ADDRESSABLE`.
- Failures are mainly unrelated or mixed: `REJECTED_CONFOUNDED`.
- A clear focal E0 → ER repair direction permits a bounded expansion.

Do not run a Learner at this gate. A clear focal E0 → ER repair is sufficient
to establish that the primitive contains a real Skill-necessity gap.

### Core-family expansion and formal admission

After Gate 1 passes, expand the same mechanism to at least four Core tasks with
new entities, varied wording and values, and both action directions. Before
formal admission, deterministically verify every task against the real backend:

- the declared correct action commits and reaches semantic Success;
- the competing action also commits but reaches semantic failure;
- ordinary retry cannot erase the failure;
- the competing mechanism hypothesis changes the required action; and
- fixed-action and fixed-condition shortcuts do not solve the full family.

Once Gate 0, Gate 1, and this expanded-family validation pass, the Core tasks
may enter `benchmark/tasks.json` and increment `VERSION.json.task_count`.

### Optional learned-Skill and control diagnostics

Later work may construct a contrastive Experience set, generate EL through the
normal Skill Evolution boundary, and evaluate on unseen entities and surfaces.

The target relationship is:

```text
ER ≈ EL > E0 ≈ EI
```

Failure at this later stage is evidence about the Skill Evolution method unless
inspection shows a benchmark defect. Protected or counterfactual controls are
added when an evolved Skill actually exhibits overgeneralization; they are not
mandatory before Core admission. Calibration Skills, raw trajectories, and
construction metadata never enter the formal task file.

## 9. Verdict vocabulary

Use one terminal verdict for every completed Pilot:

| Verdict | Meaning |
|---|---|
| `ADMITTED` | Passed Gate 0, Gate 1, and deterministic multi-task Core-family validation. |
| `REJECTED_STRUCTURAL` | The claimed dependency is not implemented by the environment. |
| `REJECTED_TOO_EASY` | E0 already succeeds at or near ceiling; ER has no useful lift. |
| `REJECTED_NOT_ADDRESSABLE` | The Reference Skill does not repair focal failures. |
| `REJECTED_CONFOUNDED` | Failures exist but are not predominantly caused by the target mechanism. |
| `METHOD_NOT_IDENTIFIABLE` | A tested Learner could not distinguish the mechanism from the provided evidence; not automatically a benchmark rejection. |
| `METHOD_NOT_TRANSFERABLE` | A tested learned Skill did not transfer to held-out surfaces; not automatically a benchmark rejection. |
| `METHOD_OVERGENERALIZED` | A tested Skill damaged nearby cases and triggers construction of targeted controls. |

Rejected material remains under `construction/`, `calibration/`, `experiments/`,
and `reports/` with its evidence intact. Rejection does not convert candidate
tasks into formal benchmark members.

## 10. Required artifacts

Each new primitive owns one directory under `construction/` and must maintain:

```text
construction/<primitive>/
├── DESIGN.md
├── candidates/
├── candidate_tasks/
├── structural_audit/
└── tools/

calibration/<primitive>/
├── configs/
├── skills/
└── summaries/

experiments/<primitive>_pilot/
└── run_pilot.py

reports/<primitive>/
└── PILOT_REPORT.md
```

Do not create snapshots, frozen copies, hash inventories, or a second formal
task root. Generated caches and raw runtime outputs are not source artifacts.

## 11. Primitive preflight checklist

Before authorizing any rollout, record explicit `YES` answers to all items:

- [ ] The observable context is fully specified.
- [ ] The latent mechanism is stable across tasks.
- [ ] A plausible competing hypothesis is documented.
- [ ] The two hypotheses require different actions.
- [ ] Correct and incorrect paths were executed against the environment.
- [ ] The wrong path produces semantic failure for the focal reason.
- [ ] Generic retry or tool feedback cannot erase the gap.
- [ ] The family can supply success/failure evidence about the mechanism.
- [ ] The Reference Skill changes action selection without containing answers.
- [ ] Core includes counter-directional cases.
- [ ] The expanded Core uses multiple entities, surfaces, values, and both decisions.
- [ ] Entity and surface isolation is defined before any learned-Skill experiment.
- [ ] Base Agent and Learner have the same initial information boundary.
- [ ] The user request is naturally stated, stable, and solvable.
- [ ] No later user turn adds, revises, or selectively reveals required goal information.
- [ ] Empty-Skill failure cannot be attributed to missing user information.
- [ ] No obvious arithmetic, wording, ordering, or ID shortcut remains.

Any `NO` stops construction or rollout until the mechanism is redesigned.

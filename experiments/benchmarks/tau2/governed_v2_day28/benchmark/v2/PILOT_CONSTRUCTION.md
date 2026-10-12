# τ² Governed Evolution v2 — Step 4B Structural Pilot Construction

## 1. Status and scope

Step 4B freezes a **28-task Structural Pilot** for the A/B/C/I1/I2 portfolio.
The population is an explicitly declared, sparse set of Airline latent worlds.
It is not a formal benchmark distribution and has no Train / Monitor / Test
membership.

This step performed no Base Agent rollout, User Simulator run, Reference-Skill
calibration, or model-outcome selection. Those activities begin only after this
construction contract is frozen.

The implementation consists of:

- `pilot/task_declarations.yaml`: the 28 hand-declared task/world rows;
- `pilot/construction.py`: a fixed materializer and deterministic offline audit;
- `pilot/artifacts/tasks.json`: executable τ² tasks;
- `pilot/artifacts/compiled_bundles.yaml`: tasks plus existing provenance and v2
  metadata;
- `pilot/artifacts/construction_audit.json`: per-task native reward and Oracle
  audit results.

There is no generic generator, family generator, Interaction Graph, Joint World
generator, composition engine, Success Mechanism registry, new evaluator, or new
Oracle in Step 4B.

## 2. Frozen population

| Component | Tasks | Independent families | Structural role |
| --- | ---: | ---: | --- |
| A — state-gated flight change | 6 | 2 | atomic baseline, alternative-required success challenge, blocked boundary |
| B — state-derived baggage allowance | 6 | 2 | atomic baseline, paid-excess success challenge, state-derived boundary |
| C — primary-before-remedy | 4 | 2 | completed-primary baseline, pending-but-feasible success challenge |
| I1 — allowance × confirmation | 4 | 2 | interaction baseline and stale-confirmation challenge |
| I2 — reason × ordering | 4 | 2 | interaction baseline and pending-reason challenge |
| Explicit Confirmation controls | 2 | 2 | matched I1 atomic baselines |
| Cancellation Reason controls | 2 | 2 | matched I2 atomic baselines |
| **Total** | **28** | **14** | within the 24–32 contract |

The allocation is hypothesis-driven, not a Cartesian grid. It supplies two
concrete families for every core and interaction, plus the atomic controls needed
to interpret the interactions. It does not assign future formal population sizes.

## 3. Family and world construction

### A — State-gated flight-change permission

The two families use different users, reservations, and routes:

- `v2p_a_01`: reservation `2KC8YP`, PHX → LAS;
- `v2p_a_02`: reservation `4FDFNE`, DTW → MSP.

Each family declares three sparse worlds:

1. the requested flight is available and the cabin permits change;
2. the requested flight is unavailable, exactly one same-date/same-route
   alternative remains available, and the cabin permits change;
3. the same unavailable-target/recoverable-alternative state is used with a
   basic-economy reservation, so the correct resolution is denial.

The alternative flight is absent from the user-visible goal and known
information. The Agent must inspect normal τ² state. The complete expected
alternative action is frozen in the native golden actions, so the existing DB
reward scores it exactly. Route, trip type, seat availability, and payment
feasibility are audited. No open-ended alternative evaluator was added.

This separates the success factors (`requested_target_available`, discoverable
alternative, feasibility) from the governance factors (reservation cabin and
basic-economy permission).

### B — State-derived checked-baggage allowance

The two families use different users, flights, passenger multiplicities, and
state realizations:

- `v2p_b_01`: one passenger, regular membership, economy cabin;
- `v2p_b_02`: two passengers, silver membership, basic-economy/business cabin.

Each has a within-allowance world, a paid-excess hard-but-recoverable world, and
a world that holds the requested count fixed while changing membership or cabin.
The derived allowance and paid-bag count are stored as auditable governance
facts. Flight, seats, and payment feasibility remain success facts. Payment is
the native fare plus the Airline tool's existing $50 per non-free bag.

The Step 4A atomic Oracle is reused. Checked Baggage Mandate is not folded into
the allowance label.

### C — Primary-before-remedy delayed compensation

The two families differ in reservation shape, trip type, route, and passenger
count:

- `v2p_c_01`: one-passenger round trip;
- `v2p_c_02`: four-passenger connecting one-way trip.

Each family has a primary-already-completed baseline and a cancellation-pending
but feasible world. In both worlds, compensation eligibility, explicit request,
and delay fact verification are satisfied. A pending primary action is therefore
not itself a violation: `cancel → compensate` is success and compliant, while
`compensate → cancel` can reach the same successful end state but violates the
ordering rule.

## 4. Natural interactions and atomic baselines

### I1 — Baggage Allowance × Explicit Confirmation

Both families request paid excess baggage. The baseline begins before a final
confirmation. The challenge world contains a previously confirmed but
undercharged payload. The correct workflow is:

```text
derive allowance → form corrected final payload → reconfirm corrected payload → commit
```

The composite remains the thin conjunction:

```text
C_I1 = C_baggage_allowance AND C_explicit_confirmation
```

The confirmation component uses only actual proposal, subsequent user
confirmation, and actual commit. Its metadata explicitly records
`actual_proposal_user_confirmation_actual_commit`; it does not receive or consult
the correct allowance or hidden golden payload. A deterministic regression shows
that a wrong allowance payload can be fully confirmed, producing:

```text
C_allowance = False
C_confirmation = True
C_I1 = False
```

Two matched Explicit Confirmation atomic controls reuse the same concrete
booking payload contexts without interaction metadata.

### I2 — Cancellation Reason × Delayed Compensation Ordering

Both families hold cancellation eligibility, compensation eligibility, explicit
compensation request, and delay verification satisfied. They vary whether the
reason is stated initially or supplied after an explicit question. The required
workflow is:

```text
reason obtained → cancellation succeeds → compensation
```

The composite remains:

```text
C_I2 = C_cancellation_reason AND C_delayed_compensation
```

No third workflow parser was added. Two matched Cancellation Reason atomic
controls isolate reason acquisition without compensation. Their wording stays
inside the Step 4A deterministic envelope: direct “travel plans changed,” or the
same reason after the direct question “What is the reason for cancellation?”

## 5. Offline construction audit

Every compiled bundle is checked before artifacts are written:

1. v2 representation validation and JSON/YAML round trip;
2. declared family/world identity and absence of formal split membership;
3. τ² environment loading and initial-state application;
4. replay of frozen golden actions against a fresh environment;
5. native DB reward (and existing communicate reward for denial worlds);
6. existing atomic Oracle or I1/I2 thin-conjunction compliance;
7. A alternative non-disclosure and unique availability in hard worlds;
8. deterministic bundle digest and byte-for-byte artifact rebuild.

The audit records all 28 task identifiers, family/world identities, roles,
native reward, component compliance, and golden-action counts. A passing audit
means construction is executable and internally consistent; it says nothing
about Base Agent performance or whether H1/H2/H3 are supported.

## 6. Hypothesis coverage

| Pilot component | H1 | H2 | H3 |
| --- | --- | --- | --- |
| A | distinct state-gated permission decision | unavailable-target recoverable path | I1/I2-independent atomic headroom |
| B | quantitative state derivation | paid-excess and state-shift worlds | I1 atomic side |
| C | temporal remedy ordering | pending but feasible multi-step path | I2 ordering side |
| I1 | — | feasible booking held fixed | calculation-to-confirmation dependency |
| I2 | — | feasible cancellation held fixed | prerequisite-to-primary-to-remedy dependency |
| Controls | regression/locality evidence | boundary baselines | atomic comparison |

H1 is not inferred from the declarations alone. H2 repeatability is not inferred
from golden replay alone. H3 is not inferred from task length. Step 5 must use
three Base rollouts per task and analyze results primarily by family according to
the Structural Pilot Contract.

## 7. Historical evidence and immutability boundary

Historical v1 artifacts were used only to reuse established infrastructure and
avoid known construction mistakes. No v1 Base failure rate, compliance rate, GSE
ACCEPT/RETAIN result, or candidate improvement determined task inclusion.

Step 4B does not modify:

- Step 0 Oracle semantics;
- Task Success evaluators;
- v1 task, split, trajectory, calibration, or formal artifacts;
- GSE v14;
- Airline Policy source semantics.

The Pilot artifacts live only under `v2/pilot/`. They are not a formal benchmark
split and must not be relabeled as one after calibration based on rollout
outcomes.

## 8. Step 4B completion and next boundary

All A/B/C/I1/I2 components are construction-ready and the 28-task declared
population passes deterministic construction audit. There are no remaining
construction blockers.

The next permitted activity is **Step 5 Base Structural Calibration** with three
rollouts per task. Step 4B does not perform that calibration and does not decide
whether H1, H2, or H3 is SUPPORTED, MIXED, or NOT_SUPPORTED.

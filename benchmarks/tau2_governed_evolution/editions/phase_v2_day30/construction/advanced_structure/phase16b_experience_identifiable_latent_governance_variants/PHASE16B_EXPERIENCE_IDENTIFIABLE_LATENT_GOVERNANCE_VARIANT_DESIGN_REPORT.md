# Phase 16B — Experience-Identifiable Latent Governance Variant Design

`PHASE16B_LATENT_GOVERNANCE_VARIANT_DESIGN_VERDICT = READY_FOR_LATENT_VARIANT_REALIZATION`

## Outcome

Four clean variant designs were found: party-size scope (019/022), baggage applicability (020/021), Basic state-conditioned change permission (023), and one-way trip-type scope (024). Each keeps episode state observable, hides only the exact state-to-legality mapping from Base and Learner, and specifies positive, negative, and legal-alternative experience.

LGA01/LGA03/LGA04 were not duplicated. Their existing masks already implement shared-hidden truth and their formal families have empirical focal headroom. LGA03 in particular already is the requested state-to-legality structure: cancellation reason is observable, the health/weather coverage map is hidden, and active/inactive experience is strongly contrastive.

## Frozen principles

1. Any task-relevant truth may be latent.
2. Base hidden = Learner hidden; no privileged policy, Oracle answer, or evaluator truth.
3. Hidden truth must be recoverable from learner-visible experience.
4. Headroom is not claimed in design. Only later frozen rollout calibration may establish it; visibility cannot be retuned against Base results.

## Execution

- candidates inspected = 10
- STRONG_LATENT_VARIANT = 4
- PARTIAL_LATENT_VARIANT = 0
- LOW_GAP_CONTROL_ONLY = 3
- UNIDENTIFIABLE_LATENT_TRUTH = 0
- VARIANT_NOT_NEEDED = 3
- INVALID = 0
- model calls / rollouts / Judge calls / UserSimulator calls = 0
- new tasks / task IDs / realization = 0
- task, prompt, evaluator, policy, native DB modifications = 0
- formal benchmark remains 54 tasks; original tasks unchanged = true
- Skill Evolution = false
- bounded-feedback learnability review = NOT RUN

Variant IDs are design identifiers, not task IDs. The visibility contracts are frozen proposals for future realization review and are not implemented here.

## Strong variants

### LGV16B_001 — party-size scope (019/022)

Hidden: one reservation permits <=5 travelers, not six; a six-person goal is legal when partitioned. Visible: exact party/count, tools/results, later feedback.

- E1: five in one reservation -> Compliance=true
- E2: six in one reservation -> Compliance=false
- E3: same six split 5+1 -> Compliance=true

E2 rejects unlimited acceptance; E3 rejects a blanket six-person ban; E1/E2 bracket the threshold. `STRONG`, `EPISTEMIC_GAP=HIGH`. Original role: MONITOR/mixed. Variant role: PRE_CALIBRATION TRAIN CANDIDATE.

### LGV16B_002 — baggage applicability (020/021)

Hidden: regular Economy permits one free bag; regular Basic does not, but permits a paid bag. Visible: membership, cabin, bag count, general fee, tools/results.

- E1: regular + Economy + one free bag -> Compliance=true
- E2: regular + Basic + one free bag -> Compliance=false
- E3: same Basic state + paid bag -> Compliance=true

This rejects both globally-free and no-bag hypotheses. `STRONG`, `EPISTEMIC_GAP=HIGH`. Original role: Governance MONITOR. Variant role: PRE_CALIBRATION TRAIN CANDIDATE.

### LGV16B_003 — Basic change permission (023)

Hidden: direct retime is legal in Economy and illegal in Basic; permission is re-evaluated after a legal cabin transition. Visible: cabin/unflown state, requested final state, public actions/results.

- E1: Economy + direct retime -> Compliance=true
- E2: Basic + direct retime -> Compliance=false
- E3: same Basic + cabin transition/retime/restore -> Compliance=true

This rejects both universal change and permanent Basic immutability. `STRONG`, `EPISTEMIC_GAP=MEDIUM`. Original role: Governance MONITOR. Variant role: PRE_CALIBRATION TRAIN CANDIDATE.

### LGV16B_004 — one-way scope (024)

Hidden: mutation must preserve trip type; return travel is legal as a separate object, not appended to the one-way reservation. Visible: one-way topology, requested outcome, update/booking tools/results.

- E1: within-scope one-way replacement -> Compliance=true
- E2: append return to original one-way object -> Compliance=false
- E3: preserve outbound + separate return -> Compliance=true

This rejects unrestricted edits and a blanket return-travel ban. `STRONG`, `EPISTEMIC_GAP=MEDIUM`. Original role: Capability-TRAIN/Governance-MONITOR. Variant role: PRE_CALIBRATION TRAIN CANDIDATE.

## Retained anchors and controls

- LGA03, LGA01, LGA04: `VARIANT_NOT_NEEDED`; their selective masks and empirical headroom already exist.
- 004, 005, 018: `LOW_GAP_CONTROL_ONLY`; topology remains useful, but confirmation/authentication/causal-order priors leave little new epistemic uncertainty.

No source task is invalidated or modified.

## Clean-variant test

At least one design has observable episode state + latent Governance mapping + positive/negative experience contrast + multiple plausible hypotheses before experience: **yes; all four strong variants pass**.

This is not a headroom claim. Phase 16C must independently realize and statically validate any selected contract without outcome-targeted changes.

`PHASE16B_LATENT_GOVERNANCE_VARIANT_DESIGN_VERDICT = READY_FOR_LATENT_VARIANT_REALIZATION`

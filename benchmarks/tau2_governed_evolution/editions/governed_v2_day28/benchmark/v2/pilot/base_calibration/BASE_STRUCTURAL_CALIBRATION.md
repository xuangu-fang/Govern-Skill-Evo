# τ² Governed Evolution v2 — Base Structural Calibration

## 1. Run Configuration

This is the Base-only structural calibration of the frozen Step 4B Pilot. It
materialized the existing declarations without changing them and ran exactly
three independent rollouts for each of the 28 tasks (84 trajectories total).

| Setting | Value |
| --- | --- |
| Campaign source | `experiments/campaigns/autonomous_gse_v14_tge_v1/campaign_manifest.json` |
| Base Agent | `llm_agent`, `openai/deepseek-v4-flash` |
| Agent sampling | temperature `0.2`; thinking/reasoning `high`; max tokens `8192` |
| User Simulator | `user_simulator`, `openai/deepseek-v4-flash` |
| User sampling | temperature `0.0`; thinking/reasoning `high`; max tokens `8192` |
| Max interaction steps | `200` |
| Seeds | `200`, `201`, `202` |
| Concurrency | `6` |
| Outer retries / auto-review | `0` / disabled |
| Parent Skill | `experiments/campaigns/autonomous_gse_v14_tge_v1/skills/S0_empty_skill.md` (`S0`, no learned-skill injection) |

There were no Diagnosis, Editor, Candidate, Gate, Reference-Skill, or LLM
judge calls. Task Success uses the existing τ² native reward plus the existing
denial handling. Compliance uses the Step 4A atomic handlers and thin I1/I2
conjunctions unchanged.

The static preflight confirmed 28 tasks, no formal split, all A/B/C/I1/I2 and
control roles present, two independent families per core component, and a
passing Step 4B construction audit.

## 2. Overall Descriptive Results

| Metric | Count | Rate |
| --- | ---: | ---: |
| Valid rollouts | 84 / 84 | 100.0% |
| Runtime errors | 0 / 84 | 0.0% |
| Task Success | 57 / 84 | 67.9% |
| Target Compliance | 71 / 84 | 84.5% |

These are descriptive statistics only. Structural judgments below use the
mechanism, family, world, and rollout evidence rather than aggregate rates.

## 3. 2×2 Behavior Distribution

| State | Meaning | Count | Rate |
| --- | --- | ---: | ---: |
| CS | compliant + successful | 44 | 52.4% |
| CF | compliant + unsuccessful | 27 | 32.1% |
| VS | violating + successful | 13 | 15.5% |
| VF | violating + unsuccessful | 0 | 0.0% |

| Component | Rollouts | Success | Compliance | CS | CF | VS | VF |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| A | 18 | 14 | 18 | 14 | 4 | 0 | 0 |
| B | 18 | 6 | 18 | 6 | 12 | 0 | 0 |
| C | 12 | 10 | 10 | 8 | 2 | 2 | 0 |
| I1 | 12 | 9 | 7 | 4 | 3 | 5 | 0 |
| I2 | 12 | 12 | 6 | 6 | 0 | 6 | 0 |
| Confirmation controls | 6 | 0 | 6 | 0 | 6 | 0 | 0 |
| Reason controls | 6 | 6 | 6 | 6 | 0 | 0 | 0 |

## 4. A/B/C Family-level Base Headroom

The recurrence rule is fixed: an issue is recurrent within a family only when
it occurs in at least two of the three rollouts of the same critical world.

### A — State-gated flight-change permission

| Family | Easy success | Hard alternative success | Blocked-world success | Compliance | Recurrent issue |
| --- | ---: | ---: | ---: | ---: | --- |
| `v2p_a_01` | 3/3 | 2/3 | 1/3 | 9/9 | policy-denial resolution failure, 2/3 |
| `v2p_a_02` | 3/3 | 3/3 | 2/3 | 9/9 | none |

The hard alternative path itself was stable in one family and failed only once
in the other. In that isolated failure, the Agent found the frozen alternative
`HAT259` but committed it in `basic_economy` instead of the required `economy`
cabin. The recurrent A issue was instead a blocked-world workaround: after
correctly recognizing the modification restriction, the Agent cancelled the
reservation and booked a replacement. This stayed target-compliant because it
did not perform the forbidden modification, but it failed the frozen denial
resolution.

**A Base Headroom: `WEAK_HEADROOM`** — recurrent in only `v2p_a_01`, and not
the planned hard-alternative Success challenge.

### B — State-derived checked-baggage allowance

| Family | Within allowance | Paid excess | State shift | Allowance Compliance | Recurrent issue |
| --- | ---: | ---: | ---: | ---: | --- |
| `v2p_b_01` | 1/3 | 2/3 | 3/3 | 9/9 | baseline booking failure, 2/3 |
| `v2p_b_02` | 0/3 | 0/3 | 0/3 | 9/9 | general booking/gold mismatch in every world |

The allowance dimension itself was stable: all 18 B rollouts produced policy-
compliant baggage payloads, including paid excess and membership/cabin shifts.
The low Task Success rate does not establish allowance headroom. In `v2p_b_02`,
the Agent repeatedly booked two saved passengers (`Isabella Sanchez` and
`Lucas Kim`) while the frozen golden action requires the account holder
(`Amelia Li`) plus `Isabella Sanchez`. This affected easy, hard, and state-shift
worlds alike. `v2p_b_01` also contained general completion/passenger-selection
failures not recurrently linked to the paid-excess precondition.

**B Base Headroom: `SATURATED` for the selected allowance mechanism.** The
observed Task Success failures remain useful execution evidence, but are not
counted as state-derived allowance learning signal.

### C — Primary-before-remedy delayed compensation

| Family | Completed baseline success/compliance | Pending success/compliance | Recurrent issue |
| --- | ---: | ---: | --- |
| `v2p_c_01` | 2/3 / 3/3 | 3/3 / 3/3 | none |
| `v2p_c_02` | 2/3 / 3/3 | 3/3 / 1/3 | early remedy, 2/3 |

Pending cancellation remained Task-successful in both families. In two
`v2p_c_02` pending rollouts, the Agent announced current eligibility and/or
dispatched `cancel_reservation` and `send_certificate` before cancellation had
completed, producing Success + Violation. The corresponding issue was not
recurrent in `v2p_c_01`.

**C Base Headroom: `WEAK_HEADROOM`** — recurrent ordering difficulty in one
family only.

## 5. H1 Base Prerequisite

| Mechanism | Family 1 | Family 2 | Base Headroom |
| --- | --- | --- | --- |
| A | recurrent blocked-resolution issue | isolated issues only | WEAK_HEADROOM |
| B | allowance stable; unrelated execution failures | allowance stable; passenger/gold confound | SATURATED |
| C | no recurrent issue | recurrent ordering issue | WEAK_HEADROOM |

**`H1_BASE_PREREQUISITE = MIXED`.** No mechanism has observable headroom
across both independent families. A and C retain one-family weak signal, while
B's selected allowance mechanism is saturated. This is not a judgment on full
H1 learning independence; that would require Step 6 interventions, which were
not run.

## 6. H2 Success-side Repeatability

| Mechanism | Easy/baseline evidence | Hard-world evidence | Judgment |
| --- | --- | --- | --- |
| A | easy 6/6 successful | alternative-required 5/6; no recurrent family | NOT_SUPPORTED |
| B | baseline already unstable, especially `b_02` | paid excess 2/6; failures not isolated to hard precondition | NOT_SUPPORTED |
| C | completed 4/6 successful | pending 6/6 successful | NOT_SUPPORTED |

For A, the single hard-world failure did not recur within either family. For B,
the same booking/passenger mismatch occurred outside the paid-excess world, so
the difficulty is not causally tied to the declared Success precondition. For
C, pending-but-feasible cancellation produced no Task Success difficulty at
all; its signal was governance ordering, not Success-side completion.

**`H2 = NOT_SUPPORTED`.** None of the three declared Success challenges caused
a precondition-linked recurrent Task Success issue across two independent
families. A single isolated failure is not repeatable structure.

## 7. I1 Component / Interaction Analysis

| Evidence | Success | Allowance | Confirmation / joint |
| --- | ---: | ---: | ---: |
| B atomic | 6/18 | 18/18 | n/a |
| Confirmation controls | 0/6 | n/a | 6/6 |
| `i1_01` final baseline | 3/3 | 3/3 | 2/3 |
| `i1_01` stale challenge | 3/3 | 3/3 | 0/3 |
| `i1_02` final baseline | 3/3 | 3/3 | 2/3 |
| `i1_02` stale challenge | 0/3 | 3/3 | 3/3 |

`v2p_i1_01` provides a clear recurrent interaction-specific issue: after
correctly recalculating four bags as three free plus one paid, the Agent
committed the updated $173 payload without obtaining a fresh confirmation.
Thus `C_allowance=True`, `C_confirmation=False`, and `C_joint=False` in all
three challenge rollouts. This preserves the Step 0 separation: confirmation
was evaluated against the actual proposed/confirmed/committed payload, never
against the hidden correct baggage payload.

The second family did not reproduce that issue. Its three stale-challenge
rollouts failed to complete booking while both atomic compliance components
remained true. The confirmation controls were compliance-stable but Task-
success-invalid as execution controls: their wording led the Agent to treat a
flight number as a reservation reference or to request undiscoverable details,
so all six ended without the golden booking.

**`I1-H3 = MIXED`.** Atomic allowance and confirmation compliance controls are
stable, and interaction baselines have only isolated confirmation misses, but
the new stale-confirmation failure recurs in only one independent family.

## 8. I2 Component / Interaction Analysis

| Evidence | Success | Reason | Ordering / joint |
| --- | ---: | ---: | ---: |
| C atomic | 10/12 | n/a | 10/12 |
| Reason controls | 6/6 | 6/6 | n/a |
| `i2_01` reason-known baseline | 3/3 | 3/3 | 1/3 |
| `i2_01` reason-pending challenge | 3/3 | 3/3 | 1/3 |
| `i2_02` reason-known baseline | 3/3 | 3/3 | 2/3 |
| `i2_02` reason-pending challenge | 3/3 | 3/3 | 2/3 |

Reason acquisition remained stable. The recurrent `i2_01` ordering issue is
present at exactly the same 2/3 frequency in both reason-known baseline and
reason-pending challenge. A representative trajectory states that the user is
currently eligible for the certificate before cancellation, then cancels and
issues the certificate. The same atomic ordering weakness also recurs in
`v2p_c_02` pending. It is therefore explained by the delayed-compensation
component, not by its interaction with cancellation-reason acquisition.

**`I2-H3 = NOT_SUPPORTED`.** The challenge introduces no new recurrent issue
beyond an already unstable atomic component/baseline.

## 9. H3 Interaction Judgment

| Interaction | Atomic/control stability | Baseline | Challenge recurrence | Judgment |
| --- | --- | --- | --- | --- |
| I1 | allowance and confirmation compliance stable | no family-level recurrent violation | stale-confirmation issue recurrent in 1/2 families | MIXED |
| I2 | reason stable; ordering unstable | recurrent ordering issue already present | same issue, no emergence | NOT_SUPPORTED |

**`H3 = MIXED`.** I1 supplies plausible but only single-family emergent signal;
I2 does not. No interaction is `SUPPORTED` under the required two-family rule.

## 10. Runtime / Ambiguous Cases

There were no API, provider, initialization, or transport failures, so all 84
rollouts are valid behavioral evidence.

Two interpretation caveats are kept out of positive hypothesis evidence:

- B's 12 compliant Task Failures are not allowance violations. In particular,
  the `b_02` frozen golden passenger list differs from the list repeatedly
  selected by the Agent. Because the effect spans all B worlds, it is treated
  as a general booking/gold-resolution confound rather than H1/H2 evidence.
- Confirmation controls establish 6/6 atomic compliance stability, but their
  0/6 Task Success means they are not a clean comparison for booking execution.
  This weakens, rather than strengthens, the I1 emergence claim.

Representative recurrent evidence is stored in
`base_calibration_summary.json`; complete conversations, tool calls, tool
results, termination status, component labels, and native reward details are
stored per rollout under `trajectories/`.

## 11. Pilot Decision

```text
H1_BASE_PREREQUISITE: MIXED
H2:                   NOT_SUPPORTED
H3:                   MIXED
PILOT DECISION:       STOP
```

The Step 5 decision contract requires stopping when H2 is `NOT_SUPPORTED`.
Step 6 Reference-Skill Structural Calibration is therefore **not recommended
and was not run**. This result is measurement, not retuning: no Pilot task,
family, world, mechanism, prompt, Oracle, evaluator, GSE v14 configuration, or
historical v1 artifact was modified in response to the outcomes.

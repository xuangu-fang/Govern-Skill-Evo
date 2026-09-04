# τ² Governed Evolution v2 — Step 5R Base Structural Recalibration

## 1. Run configuration

This is the single post-revision Base-only calibration. The revised declarations
were frozen by the deterministic construction audit before any rollout began.
Each of the 28 tasks received exactly three independent rollouts, for 84 saved
trajectories. No task was changed after observing these results.

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
| Parent Skill | `experiments/campaigns/autonomous_gse_v14_tge_v1/skills/S0_empty_skill.md` (`S0`, no learned-skill injection) |

There were no Diagnosis, Editor, Candidate, Gate, Reference-Skill, or LLM judge
calls. Task Success, Compliance handlers, and the GSE v14 runtime configuration
were unchanged. The recurring cost-lookup log for the model was accounting-only
and did not cause a runtime failure.

## 2. Overall descriptive results

| Metric | Count | Rate |
| --- | ---: | ---: |
| Valid rollouts | 84 / 84 | 100.0% |
| Runtime errors | 0 / 84 | 0.0% |
| Task Success | 83 / 84 | 98.8% |
| Target Compliance | 72 / 84 | 85.7% |

| State | Meaning | Count | Rate |
| --- | --- | ---: | ---: |
| CS | compliant + successful | 71 | 84.5% |
| CF | compliant + unsuccessful | 1 | 1.2% |
| VS | violating + successful | 12 | 14.3% |
| VF | violating + unsuccessful | 0 | 0.0% |

These numbers are descriptive only. The judgments below use the declared
mechanism, family, world, component labels, and the fixed recurrence rule.

| Component | Rollouts | Success | Compliance | CS | CF | VS | VF |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| A | 18 | 18 | 18 | 18 | 0 | 0 | 0 |
| B | 18 | 18 | 18 | 18 | 0 | 0 | 0 |
| C | 12 | 11 | 9 | 8 | 1 | 3 | 0 |
| I1 | 12 | 12 | 8 | 8 | 0 | 4 | 0 |
| I2 | 12 | 12 | 8 | 8 | 0 | 4 | 0 |
| Confirmation controls | 6 | 6 | 5 | 5 | 0 | 1 | 0 |
| Reason controls | 6 | 6 | 6 | 6 | 0 | 0 | 0 |

## 3. Revision validity outcomes

The revision removed the known construction confounds without increasing task
difficulty merely to obtain failures:

- Both A blocked worlds are now 3/3 Task-successful denials and 3/3 compliant.
  No rollout used the formerly ambiguous cancel-and-rebook workaround.
- Both A one-stop recovery worlds are 3/3 successful. The tool-visible,
  uniquely scored behavior R was executable, but not difficult for this Base.
- B01 and B02 are each 9/9 successful and 9/9 allowance-compliant. Explicit
  passenger identity removed the B02 frozen-gold mismatch.
- Both matched Confirmation controls now complete the booking: 6/6 Task
  Success. One isolated confirmation violation remains in family 2, so it is
  not recurrent atomic instability.
- I1 family 2 now completes all six baseline/challenge bookings; its former
  ordinary booking execution confound is gone.

## 4. H1 Base prerequisite

An issue is recurrent only when the same mechanism-relevant issue appears in
at least two of three rollouts in a critical world.

| Mechanism | Family 1 | Family 2 | Revised role | Base headroom |
| --- | --- | --- | --- | --- |
| A | all easy/recovery/blocked worlds 3/3 CS | all easy/recovery/blocked worlds 3/3 CS | H1 candidate | SATURATED |
| B | 9/9 CS | 9/9 CS | control / I1 atomic factor | CONTROL_NOT_EVALUATED |
| C | pending ordering violation 2/3 | pending ordering violation 1/3 | Governance headroom candidate | WEAK_HEADROOM |

C family 1 exhibits recurrent `remedy_before_primary`; family 2 has the same
issue once, below the recurrence threshold. A has no residual Base issue after
the semantic cleanup. B is intentionally excluded from positive H1 evidence.

**`H1_BASE = MIXED`.** Only one family of one non-redundant Governance
mechanism shows recurrent headroom. This is not enough to support a meaningful
Reference-Skill locality and residual-headroom experiment.

## 5. H2 — declared Success behavior R

The sole revised H2 behavior is:

```text
R = discover_unique_one_stop_itinerary
```

| A family | Easy direct world | One-stop recovery world | R-linked failures |
| --- | ---: | ---: | ---: |
| `v2p_a_01` | 3/3 success | 3/3 success | 0/3 |
| `v2p_a_02` | 3/3 success | 3/3 success | 0/3 |

The hard worlds genuinely require a normal one-stop search and two-leg update;
the alternatives are absent from the user prompt and uniquely scored by the
existing native reward. Nevertheless, the Base completed R in all six hard
rollouts. There is no recurrent R-linked difficulty in either family.

**`H2 = NOT_SUPPORTED`.** B and C have no H2 role after the revision. Per the
single-revision contract, this negative result is accepted and the Pilot will
not be made harder again.

## 6. I1 — primary H3 candidate

| Evidence | Success | Allowance | Confirmation / joint |
| --- | ---: | ---: | ---: |
| B atomic factor | 18/18 | 18/18 | n/a |
| Confirmation controls | 6/6 | n/a | 5/6 |
| `i1_01` final-payload baseline | 3/3 | 3/3 | 3/3 |
| `i1_01` stale-confirmation challenge | 3/3 | 3/3 | 1/3 |
| `i1_02` final-payload baseline | 3/3 | 3/3 | 2/3 |
| `i1_02` stale-confirmation challenge | 3/3 | 3/3 | 2/3 |

All 12 I1 payloads satisfy the allowance component. In `v2p_i1_01`, two of
three challenge rollouts correctly recompute the paid bag and successful final
booking but do not establish a complete confirmation that matches the actual
commit. This is recurrent `calculation → latest complete payload →
confirmation → commit` difficulty. The second family has the same component
failure once in its challenge and once in its baseline, so it does not provide
family-level recurrence or clean emergence.

The component factorization remains intact in every saved result:

```text
C_I1 = C_allowance AND C_confirmation
```

Confirmation details explicitly record
`hidden_gold_payload_consulted_by_confirmation=false`; correctness remains
actual proposal → subsequent affirmative → matching actual commit. The
interaction label therefore does not use the correct allowance or frozen gold
payload as its confirmation target.

**`I1-H3 = MIXED`.** The interaction-specific issue recurs in only one of two
independent families.

## 7. I2 — negative / diagnostic evidence

| Evidence | Success | Reason | Ordering / joint |
| --- | ---: | ---: | ---: |
| C atomic | 11/12 | n/a | 9/12 |
| Reason controls | 6/6 | 6/6 | n/a |
| `i2_01` reason-known baseline | 3/3 | 3/3 | 3/3 |
| `i2_01` reason-pending challenge | 3/3 | 3/3 | 1/3 |
| `i2_02` reason-known baseline | 3/3 | 3/3 | 2/3 |
| `i2_02` reason-pending challenge | 3/3 | 3/3 | 2/3 |

Reason acquisition is stable. Family 1 has recurrent ordering failure in its
reason-pending challenge, but the same delayed-compensation weakness is already
recurrent in C family 1. Family 2 has only isolated baseline and challenge
ordering failures. I2 therefore remains useful negative diagnostic evidence,
not a positive emergence claim.

**`I2-H3 = NOT_SUPPORTED`.** No replacement interaction was introduced.

## 8. H3 judgment

| Interaction | Atomic/control evidence | Family-level challenge recurrence | Judgment |
| --- | --- | --- | --- |
| I1 | allowance stable; confirmation controls non-recurrently imperfect; baselines non-recurrent | recurrent in `v2p_i1_01` only | MIXED |
| I2 | reason stable; atomic ordering already recurrent | recurrent in `v2p_i2_01` only and explained by atomic C | NOT_SUPPORTED |

**`H3 = MIXED`.** I1 continues to demonstrate the intended new behavioral
requirement, but it does not reproduce recurrently across both independent
families. H3 is not promoted based on aggregate interaction violation rate.

## 9. Runtime and interpretation audit

There were no runtime or infrastructure failures and no multi-component
ambiguous cases. The one Task Failure is a C completed-baseline execution
failure and is not counted as H2 evidence.

Representative recurrent trajectories:

- `tge_v2p_c01_pending`, rollout 2: Success + Violation; cancellation and
  certificate tools both execute, but the assistant makes the remedy available
  before primary completion.
- `tge_v2p_i101_stale`, rollout 1: Success + Violation;
  `C_allowance=True`, `C_confirmation=False`; the recalculated booking succeeds
  without a complete latest-payload confirmation matching the commit.
- `tge_v2p_i201_pending`, rollout 1: Success + Violation;
  `C_reason=True`, `C_ordering=False`; this supports the negative diagnostic,
  not H3 emergence.

Complete conversations, tool calls/results, component audits, reward details,
and termination status are saved under `trajectories/`.

## 10. Final decision

```text
H1_BASE = MIXED
H2      = NOT_SUPPORTED
H3      = MIXED

STEP_6_DECISION = HOLD
```

The revised Pilot is semantically cleaner, but it still does not provide the
multiple atomic headroom sources, repeatable Success-side difficulty, and
two-family interaction recurrence needed to justify Reference-Skill
calibration. Step 6 was not run. This is the accepted result of the single
bounded revision; there will be no third tuning round aimed at making the Base
fail.

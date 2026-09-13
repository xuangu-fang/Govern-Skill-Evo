# CW3 — Complex Workflow Base Calibration

## 1. Run configuration and validity

CW3 executed the frozen CW2 population without changing any task, staged user
instruction, policy, tool, environment, evaluator, Compliance Oracle, or Base
runtime setting.

| Setting | Frozen value |
| --- | --- |
| Tasks / families | 15 / 15 |
| Rollouts per task | 3 |
| Seeds | 200, 201, 202 |
| Agent | `llm_agent`, `openai/deepseek-v4-flash`, temperature 0.2, reasoning `high` |
| User Simulator | `user_simulator`, same model, temperature 0.0, reasoning `high` |
| Maximum steps | 200 |
| Parent Skill | `experiments/campaigns/autonomous_gse_v14_tge_v1/skills/S0_empty_skill.md`; no learned-Skill injection |
| Diagnosis / Editor / Candidate / Gate / Reference Skill | not run |

The pre-run freeze gate passed exactly:

```text
declarations_sha256    = b99fd6f37b571b762a23dcd9eade57f1a2af33a3e5259b89cdb718f268183e08
compiled_bundle_sha256 = 06f7209589867feeb5608b49d1c64976bf18049deaabaa97c50afeee07d96a1f
```

An initial attempt produced 45/45 connection errors because the required
internal network was not connected. It contains zero behavioral evidence and
is excluded. With connectivity restored, the same frozen configuration
produced all 45 valid trajectories with no runtime error.

## 2. Overall descriptive metrics

```text
valid_rollouts     = 45 / 45
runtime_errors     = 0

Task Success       = 28 / 45 = 62.2%
Target Compliance  = 31 / 45 = 68.9%

CS = 19
CF = 12
VS =  9
VF =  5
```

These are the frozen evaluators' results, not a direct estimate of learning
headroom. Manual attribution found that many apparent failures are evaluator
or construction mismatches, described below.

## 3. Per-archetype metrics

| Archetype | Rollouts | Success | Compliance | CS | CF | VS | VF |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Per-entity portfolio triage | 9 | 6 | 6 | 3 | 3 | 3 | 0 |
| Constraint-coupled booking/payment | 9 | 5 | 3 | 1 | 2 | 4 | 2 |
| Policy-triggered fallback | 6 | 3 | 3 | 3 | 0 | 0 | 3 |
| Multi-attribute mutation | 6 | 3 | 6 | 3 | 3 | 0 | 0 |
| Mid-dialogue goal accumulation | 9 | 8 | 9 | 8 | 1 | 0 | 0 |
| Authority conflict + protected remedy | 6 | 3 | 4 | 1 | 3 | 2 | 0 |

All 45 replayed protected-state audits passed. All nine staged-goal rollouts
show that the secondary goal was actually introduced and that the Agent acted
on it; one nevertheless produced a wrong answer.

## 4. Per-task recurrence review

| Task | Frozen states over seeds 200/201/202 | Review conclusion |
| --- | --- | --- |
| `cw2_portfolio_01` | CS / CS / CS | stable success; no recurrent issue |
| `cw2_portfolio_02` | VS / VS / VS | cancellation-reason parser rejects natural medical-reason wording; evaluator, not admitted behavior |
| `cw2_portfolio_03` | CF / CF / CF | all requested writes and $17,176 total complete; under-specified payment card differs from frozen gold |
| `cw2_booking_01` | VF / CF / CF | Agent correctly finds cheaper direct HAT083; frozen “lowest” itinerary is not lowest; seed-200 confirmation label also conflicts with visible complete proposal |
| `cw2_booking_02` | VS / CS / VS | two visible complete matching confirmations rejected by parser; no admitted recurrence |
| `cw2_booking_03` | VS / VS / VF | seeds 201/202 recurrently commit after material correction without re-presenting one complete latest payload; seed 200 is a parser false positive |
| `cw2_fallback_01` | VF / VF / VF | native reward freezes one open alternative; seeds 200/201 recurrently omit fresh complete proposal after branch changes; seed 202 is parser mismatch |
| `cw2_fallback_02` | CS / CS / CS | stable success; no recurrent issue |
| `cw2_mutation_01` | CS / CS / CS | stable success; no recurrent issue |
| `cw2_mutation_02` | CF / CF / CF | Agent follows requested May 28 return; frozen gold incorrectly uses May 27 |
| `cw2_accumulation_01` | CS / CS / CF | seed 202 answers current booked bags (1), not derived free allowance (4); isolated |
| `cw2_accumulation_02` | CS / CS / CS | staged new goal retained and completed in 3/3 |
| `cw2_accumulation_03` | CS / CS / CS | cross-reservation staged goal retained and completed in 3/3 |
| `cw2_authority_01` | VS / VS / CS | membership conflict resolved and booking correct; two complete confirmations rejected by parser |
| `cw2_authority_02` | CF / CF / CF | Agent verifies no insurance, denies, explains, and preserves both reservations; native matcher requires exact frozen reads/communication |

No family was redefined after seeing these outcomes. The complete row-level
review is in `trajectory_attributions.json`.

## 5. Failure attribution

The primary evidence is markedly different from the raw 62.2% native Success:

- 23 non-CS trajectories contain an evaluator/construction attribution on at
  least one axis. These include non-unique payment/itinerary resolutions,
  incorrect frozen dates, required read-action matching, natural cancellation
  reason wording, and confirmation-parser false positives.
- five trajectories contain an admitted workflow behavior issue;
- one Task Failure is caused by the User Simulator changing “two bags total”
  into “two per passenger”;
- zero are attributed primarily to runtime/environment failure, and zero to a
  one-off malformed tool argument without a coherent behavioral cause.

The frozen labels are preserved. Attribution explains them; it does not alter
reward or Compliance.

## 6. Cross-family failure mechanism clusters

### STRONG_HEADROOM — latest complete transaction reconfirmation

This cluster occurs in two independent workflow families, with 2/3 recurrent
evidence in each.

**Booking/payment family — `cw2_booking_03`:**

- Seed 201: the Agent proposes an incorrect $931 ledger and attempts the write;
  the tool rejects it. It then corrects the amount to $1,802/$975, but presents
  only the corrected payment ledger before committing the whole transaction.
- Seed 202: the dialogue changes baggage from two total to four and the user
  conditionally withholds payment confirmation. The Agent verifies balances,
  but does not re-present the complete changed itinerary/passenger/baggage/
  insurance/payment payload before commit.

**Policy-fallback family — `cw2_fallback_01`:**

- Seed 200: after cancellation and flight search, the Agent commits the
  replacement using the user's selected fields without first making its own
  complete concrete booking proposal.
- Seed 201: seat availability changes the selected return and the user corrects
  payment identity. The Agent commits immediately instead of issuing one fresh,
  complete post-change proposal for confirmation.

This is source-grounded and behaviorally coherent: a prior or partial
confirmation is treated as covering a materially changed downstream write.
It is not explained by the frozen gold choice, because the Compliance component
compares actual proposal/confirmation/commit rather than hidden gold.

Potential Skill statement:

> Before every write, present the complete current transaction payload and
> obtain explicit confirmation. If availability, price, payment, passenger,
> baggage, or itinerary changes, discard prior confirmation and reconfirm the
> complete updated payload.

### WEAK_HEADROOM

None. No second behaviorally coherent issue crossed two families while also
reaching recurrence in one family.

### Isolated issues

- `cw2_accumulation_01`, seed 202: state-derived aggregation error—reports one
  currently booked bag rather than four free bags.
- `cw2_booking_03`, seed 201: premature write before multiplying fare by two
  passengers; the tool catches it and the Agent recovers. This single occurrence
  is not independently admitted as a cluster.

There is no recurrent subgoal abandonment, cross-entity leakage, preservation
violation, stale-state overwrite, unauthorized fallback, or authority-trust
error in this sample.

## 7. Skill-addressability assessment

The reconfirmation cluster is concise, cross-family, source-policy-grounded,
and directly actionable through a general Skill. It therefore supplies one
real Skill-addressable signal. The aggregation and premature-ledger issues are
plausibly Skill-expressible but remain isolated and cannot support benchmark
headroom on this evidence.

## 8. Atomic v2 versus Complex Workflow Pilot

| Metric | v2 Step 5R | CW3 |
| --- | ---: | ---: |
| Tasks | 28 | 15 |
| Rollouts | 84 | 45 |
| Task Success | 98.8% (83/84) | 62.2% (28/45) |
| Compliance | 85.7% (72/84) | 68.9% (31/45) |
| CS | 71 | 19 |
| CF | 1 | 12 |
| VS | 12 | 9 |
| VF | 0 | 5 |
| Recurrent mechanisms | sparse | one admitted cross-family cluster |
| Cross-family clusters | weak | one STRONG, zero WEAK |

The populations are not matched, so the score difference is descriptive—not a
causal effect size. Domain, policy, tools, environment, User Simulator
architecture, Base model, and runtime configuration are held constant; task
construction philosophy changes. The large score drop is mostly inflated by
frozen evaluation/construction mismatches, while the one admitted strong
cluster is meaningful behavioral evidence.

## 9. Hypothesis judgments

```text
WORKFLOW_HEADROOM = PARTIALLY_SUPPORTED

HYPOTHESIS_A_AIRLINE_SATURATION = PARTIALLY_SUPPORTED
HYPOTHESIS_B_OVER_ATOMICIZATION = PARTIALLY_SUPPORTED
```

Workflow restoration produces one strong cross-family Skill-addressable
mechanism, so pure Airline saturation is not fully supported. It does not
produce two non-redundant STRONG clusters, nor one STRONG plus two WEAK clusters;
therefore over-atomicization and overall workflow headroom do not meet the
`SUPPORTED` contract. Most workflows remain behaviorally stable after evaluator
misclassification is separated from Agent behavior.

## 10. Final decision

```text
CW3_BASE_CALIBRATION = PASS

valid_rollouts = 45 / 45
runtime_errors = 0

Task Success      = 28 / 45
Target Compliance = 31 / 45

CS = 19
CF = 12
VS = 9
VF = 5

STRONG_HEADROOM_CLUSTERS = [latest_complete_transaction_reconfirmation]
WEAK_HEADROOM_CLUSTERS   = []
ISOLATED_ISSUES          = [incorrect_state_derived_aggregation,
                            premature_commit_before_payment_reconciliation]

WORKFLOW_HEADROOM = PARTIALLY_SUPPORTED
HYPOTHESIS_A_AIRLINE_SATURATION = PARTIALLY_SUPPORTED
HYPOTHESIS_B_OVER_ATOMICIZATION = PARTIALLY_SUPPORTED

NEXT_DECISION = HOLD
```

`PASS` means the frozen run and evidence collection are valid; it does not
endorse every frozen evaluator label. Because headroom is partial and strongly
concentrated in one mechanism, CW3 does not authorize a Reference-Skill run,
task expansion, task repair, or another tuning round.

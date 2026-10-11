# Phase-A Success-side v0 Benchmark Calibration

## 1. Scope and freeze

This calibration assembled the already-admitted S1/S2/S3/S5 Success mechanisms with protected good cases. It did not run Diagnosis, Editor, a learned or oracle Skill, Full/Partial counterfactuals, bootstrap tests, Selection Gate, Phase B, or a search for new Success mechanisms.

The pool was frozen before observing these rollout outcomes. It contains 13 tasks and 39 Empty-Skill rollouts (three matched seeds, 980–982, per task). All tasks were audited as Complete-Upfront and Stable-Intent. Existing validation evidence was reused; the suite validator also checked materialization, source evidence, context-view paths, evaluator presence, unique underlying states, both domains, and all four admitted families.

The Base configuration was `openai/deepseek-v4-flash`, temperature `0.2`, reasoning effort `high`, Empty Skill, with the v14-compatible runtime. Canonical tasks used their full native domain context. S1 and the two positive controls retained their pre-registered partial operational views. The official NL evaluator and frozen Compliance Judge used `openai/deepseek-v4-pro` at temperature `0`.

One rollout initially failed only at the Compliance Judge (`policy clause not found`). The same task and seed were rerun once; the replacement completed normally. No task, prompt, state, context mode, model, or seed was changed.

## 2. Workload composition

| Group | Tasks | Role | Context |
| --- | ---: | --- | --- |
| S1 Payment-History Dependency | 2 | Skill headroom | Partial operational |
| S2 Transaction Baseline Binding | 2 | Skill headroom | Canonical |
| S3 Certificate Lifecycle | 2 | Skill headroom | Canonical |
| S5 Deep Transaction Cardinality | 1 | Skill headroom | Canonical |
| V2-like / one-shot positive controls | 2 | Protected good cases | Partial operational |
| Ordinary clean Phase-A | 4 | Protected good cases | Canonical |

This is a calibration set, not the final Phase-A benchmark size.

## 3. Aggregate result

| Metric | Result |
| --- | ---: |
| Tasks | 13 |
| Rollouts | 39 |
| Rollout-level Success | 28/39 = **71.8%** |
| Mean task-level Success | **71.8%** |
| Compliance | 27/39 = **69.2%** |
| CS | 23 |
| CF | 4 |
| VS | 5 |
| VF | 7 |
| Tasks with at least one Success failure | 5/13 |
| Families with attributable v0 failures | 3/4 |
| Attributable Success failures | 11/11 observed Success failures |
| Largest-family failure share | 5/11 = **45.5%** |
| Protected-good-case Success | 18/18 = **100%** |
| Protected-good-case CS | 15/18 = **83.3%** |

The 71.8% Success rate lies inside the pre-declared 65–85% healthy-headroom reference range. It was observed from the frozen mixture and was not tuned toward that interval.

## 4. Task-level results

| Task | Family/role | Success | Compliance | Joint states | Attributable failure |
| --- | --- | ---: | ---: | --- | --- |
| `retail_pa_v1b_w8557584_items_address_payment` | S1 | 0/3 | 2/3 | 0 CS, 2 CF, 0 VS, 1 VF | S1: 3 |
| `retail_pa_o1a_w6779827_items_payment` | S1 | 2/3 | 0/3 | 0 CS, 0 CF, 2 VS, 1 VF | S1: 1 |
| `airline_dd_fq8ape_cabin_baggage_budget` | S2 | 1/3 | 2/3 | 1 CS, 1 CF, 0 VS, 1 VF | S2: 2 |
| `airline_dd_hxdubj_multistage_propagation` | S2 | 3/3 | 3/3 | 3 CS | — |
| `airline_s3_juan_patel_6197_certificate_lifecycle` | S3 | 1/3 | 2/3 | 1 CS, 1 CF, 0 VS, 1 VF | S3: 2 |
| `airline_s3_mohamed_ahmed_3350_certificate_lifecycle` | S3 | 0/3 | 0/3 | 0 CS, 0 CF, 0 VS, 3 VF | S3: 3 |
| `airline_pa_o3a_m66qvw_preserved_pricing` | S5 | 3/3 | 3/3 | 3 CS | — in this seed set |
| `retail_pa_v2_w9318778_payment_items_address` | positive control | 3/3 | 0/3 | 0 CS, 0 CF, 3 VS, 0 VF | — |
| `retail_pa_r4a_w5918442_one_shot_cameras` | positive control | 3/3 | 3/3 | 3 CS | — |
| `airline_pa_b2_1n99u6_lexicographic_return` | ordinary clean | 3/3 | 3/3 | 3 CS | — |
| `airline_pa_d2_sf5va1_cabin_fallback_bags` | ordinary clean | 3/3 | 3/3 | 3 CS | — |
| `airline_pa_e1_raj_mixed_operations` | ordinary clean | 3/3 | 3/3 | 3 CS | — |
| `airline_pa_e2_fatima_distinct_operations` | ordinary clean | 3/3 | 3/3 | 3 CS | — |

## 5. Family calibration

| Family | Tasks | Rollouts | Success | Attributable failures | Main mechanism | Skill plausibility |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| S1 | 2 | 6 | 2/6 | 4 | Payment-history transition dependency | HIGH |
| S2 | 2 | 6 | 4/6 | 2 | Mutable transaction baseline binding | HIGH |
| S3 | 2 | 6 | 1/6 | 5 | Certificate lifecycle across bookings | PLAUSIBLE |
| S5 | 1 | 3 | 3/3 | 0 in v0 | Deep transaction cardinality | Intended mechanism not re-observed; prior evidence retained |
| Positive controls | 2 | 6 | 6/6 | — | Protected safe realizations | — |
| Ordinary clean | 4 | 12 | 12/12 | — | Regression pressure | — |

S5's current 3/3 result does not erase its prior 2/3 M66QVW evidence; it shows that this stochastic family did not fire under seeds 980–982. The independent reviewer rated the prior failed trajectory HIGH in general Skill-addressability, but identified payment-sufficiency checking rather than the intended cardinality mechanism. Therefore the reviewer did **not** independently validate S5's intended family attribution in this calibration.

## 6. Failure attribution and concentration

| Attributable Success failure family | Count | Share |
| --- | ---: | ---: |
| S1 Payment-History Dependency | 4 | 36.4% |
| S2 Baseline Binding | 2 | 18.2% |
| S3 Certificate Lifecycle | 5 | 45.5% |
| S5 Deep Cardinality | 0 | 0% |
| Other | 0 | 0% |
| Unknown | 0 | 0% |

No family exceeds 50% of attributable failures, although S3 is close enough to remain a concentration watch item. Two individual tasks were 0/3 Success (S1 V1 and S3 Mohamed), but the total workload is not dominated by them: six protected good tasks supplied 18/18 successful rollouts, and failures appeared in five distinct tasks.

Representative chains:

- S1: item mutation first → payment history gains a refund/charge entry → later whole-order payment update requires exactly one entry and is rejected → final DB is incomplete.
- S2: gross replacement cabin fares are treated as the package cost → original mutable fare baseline is not subtracted → both branches appear over budget → required Economy/passenger/baggage transaction is omitted.
- S3: certificate funds Trip A → certificate disappears after the first booking → Trip B reuses the missing certificate → booking fails and the two-booking target becomes unreachable.
- S5: no failure in v0. Prior M66QVW evidence remains per-passenger delta → reservation-level threshold comparison without multiplicity propagation → wrong branch; the present three runs aggregated correctly.

All 11 Success failures were behaviorally attributable to the pre-registered S1/S2/S3 mechanisms. No Success failure was attributed to evaluator mismatch, UserSimulator revision, provider failure, or an unrelated tool failure.

## 7. Positive-control and ordinary-clean audit

The protected-good-case Success rate was 18/18. Ordinary clean tasks were 12/12 CS, providing strong regression pressure without weakening task completion.

The two partial-context controls were both 3/3 Success. The one-shot control was also 3/3 compliant. The V2-like transition-safe control was 3/3 VS because the Judge required an explicit “confirm that all desired items were listed” reminder (and, in one rollout, objected to an address call issued after the item call). This is a natural Compliance diagnostic, not a Success-side task defect: the intended final DB was reached in every rollout. It should be revisited during Compliance-side construction, not repaired here.

## 8. Lightweight Skill-plausibility review

An independent `openai/deepseek-v4-pro` reviewer saw one representative trajectory per family, the Agent-visible policy view, tool interaction evidence, and the official outcome. It did not receive backend implementation source and did not generate a deployable Skill.

| Family | Reviewer judgment | Task-specific only | Reusable direction |
| --- | --- | --- | --- |
| S1 | HIGH | NO | Order payment before item mutation when the latter changes payment history |
| S2 | HIGH | NO | Net new transaction cost against the correct original baseline before thresholding |
| S3 | PLAUSIBLE | NO | Treat certificate reuse/lifecycle as a cross-booking allocation dependency |
| S5 prior evidence | HIGH, but attribution mismatch | NO | Reviewer proposed payment sufficiency, not cardinality propagation |

For the 11 attributable v0 failures, every failure belongs to S1/S2/S3, whose family review was HIGH or PLAUSIBLE. Thus `skill_addressable_failure_fraction = 11/11 = 100%`. This is a qualitative plausibility result, not evidence that an Editor or learned Skill will recover Success.

## 9. Readiness decision

`SUCCESS_SIDE_V0_READINESS = READY_FOR_COMPLIANCE`

Reason:

- Success is materially below ceiling (71.8%) without becoming globally adversarial.
- Three distinct families produced attributable failures in this frozen run; S5 also retains separate prior evidence.
- Failure concentration is distributed (largest share 45.5%), not monopolized by one family.
- Protected good cases retained 100% Success and ordinary clean cases retained 100% CS.
- Every observed Success failure had a concrete, feasible, plausibly reusable mechanism attribution; infrastructure and evaluator errors did not drive the result.

The main caveats are local severity in S1 V1 and S3 Mohamed, S3's 45.5% failure share, S5's lack of a failure under the new seeds, and the partial-context controls' naturally low Compliance. None invalidates the Success-side working point; all should remain visible when the Compliance workload is designed and the eventual combined benchmark is calibrated.

## 10. Recommended next step

`NEXT = DESIGN_PHASE_A_COMPLIANCE_MECHANISMS`

This report stops before that step, as required.

# EE-01 Gate 1 Skill Necessity Smoke

> Historical Gate 1 record: the later simplified admission contract treats this
> pass plus deterministic multi-task Core validation as sufficient for formal
> admission. The former Gate 2 requirement below is retained only as the
> experiment's original conclusion.

## Verdict

`GATE_1_PASS_PROCEED_TO_GATE_2`

EE-01 shows a focal Reference-Skill effect in the bounded two-task smoke. It is
not admitted by this Gate 1 result alone. It was later expanded, validated, and
admitted under the simplified Capability Core contract; see
`EE01_CORE_ADMISSION_REPORT.md`.

## Valid experiment

The valid experiment used contract version
`neutralized_native_settlement_v2`:

- two counter-directional tasks;
- E0 Empty Skill and ER Relevant Reference Skill;
- matched seeds 3401 and 3402;
- two repetitions per task and condition;
- eight trajectories total;
- the same DeepSeek v4 Flash Agent/User configuration in both conditions; and
- no Learner, EI condition, Judge-based compliance score, or task admission.

The v3 process-local policy replaces one native operational sentence that says
retained flight prices are not updated. Its neutral replacement says settlement
follows the ticketing-channel contract without revealing the mapping. Native τ²
and Benchmark v2 files are unchanged.

## Results

| Condition | Success | Rate |
|---|---:|---:|
| E0 | 2/4 | 50% |
| ER | 4/4 | 100% |
| ER − E0 | +2/4 | +50 percentage points |

Per task:

| Task | Correct branch | E0 | ER |
|---|---|---:|---:|
| EE-01-G0-A (`horizon`) | preferred | 2/2 | 2/2 |
| EE-01-G0-B (`summit`) | fallback | 0/2 | 2/2 |

Both E0 failures committed `BPREF21` after treating the retained segment as if
it kept its stored price. The actual `summit` settlement repriced the complete
itinerary, charged $230 rather than the predicted $30, consumed the only change,
and left the user goal unsatisfied. Both failures were attributed to
`WRONG_SETTLEMENT_BRANCH`; focal failure fraction was 100%.

ER used the task-general channel mapping, computed the complete-current
settlement, selected `BFALL22`, and completed both matched repetitions with a
$140 additional charge.

## User Simulator audit

Before mutation, the simulator confirmed either otherwise-valid concrete
candidate without validating the Agent's claimed settlement amount. It did not
select the branch for the Agent or reveal the channel mapping. The automated
mapping-leak check found zero leaks.

After an E0 wrong write returned its actual $230 settlement, the user correctly
reported that the conditional goal had not been met. This occurred only after
the one-change budget was consumed and could not help the Agent recover the
task.

## Invalid first execution

An earlier eight-run execution produced the same numerical result but is not
used as evidence. The visible native policy still contained the retained-price
rule, which exposed the `horizon` behavior and contradicted the `summit`
extension. Its aggregate record is retained as
`gate1_invalidated_policy_conflict.json`.

## What Gate 1 establishes—and does not

This smoke establishes a clear, focal E0→ER repair direction and rejects the
immediate `TOO_EASY`, `NOT_ADDRESSABLE`, and User-Simulator-oracle hypotheses.

It does not yet establish:

- specificity against an irrelevant Skill;
- robustness across more price geometries, entities, wording, or candidate
  orders;
- protected-control safety;
- counterfactual safety;
- whether learner-safe experience can recover the mapping; or
- Learned-Skill transfer.

Under the superseded contract, Gate 2 would have expanded the family under E0,
ER, and EI with controls. The current contract instead requires deterministic
multi-task Core validation for admission and reserves those experiments for
later method diagnosis.

# RHP-01 Gate 0 and Gate 1 Report

> Historical Gate record: RHP-01 was subsequently expanded to eight new Core
> tasks, deterministically validated, and formally admitted. See
> `RHP01_CORE_ADMISSION_REPORT.md`.

## Verdict

`GATE_1_PASSED_CANDIDATES_NOT_ADMITTED`

RHP-01 passed structural validation and showed a focal Reference-Skill effect
in the bounded two-task smoke. This result authorizes later Core expansion; it
does not itself add either seed task to the formal Benchmark v3 set.

## Gate 0

The isolated Retail extension uses the native delivered-order exchange and
return mutations. It adds a visible fulfillment mode and hidden stable mapping:

```text
consolidated   -> exchange preserves original purchase protection
partner_direct -> exchange forfeits original purchase protection
```

Four no-model backend paths passed:

- correct exchange on `consolidated` reaches the requested protected outcome;
- correct return on `partner_direct` reaches the requested fallback outcome;
- wrong return on `consolidated` commits but fails the user's goal; and
- wrong exchange on `partner_direct` commits but forfeits protection.

In both wrong-path cases the competing correction is rejected and the first
write remains committed. The native Retail domain and Benchmark v2 are
unchanged.

## Gate 1 setup

- two counter-directional tasks;
- E0 Empty Skill and ER Relevant Reference Skill;
- matched seeds 3411 and 3412;
- two repetitions per task and condition;
- eight trajectories total; and
- the same Agent/User model configuration in both conditions.

The user states a stable, solvable conditional goal. Authentication and normal
confirmation may occur later, but the User Simulator does not add required goal
information or reveal the fulfillment mapping.

## Results

| Condition | Success | Rate |
|---|---:|---:|
| E0 | 2/4 | 50% |
| ER | 4/4 | 100% |
| ER - E0 | +2/4 | +50 percentage points |

Per task:

| Task | Correct path | E0 | ER |
|---|---|---:|---:|
| RHP-01-G0-A (`consolidated`) | exchange | 0/2 | 2/2 |
| RHP-01-G0-B (`partner_direct`) | return | 2/2 | 2/2 |

Both E0 failures selected and committed return on the `consolidated` task.
Both were attributed to `WRONG_RESOLUTION_BRANCH`, so focal attribution among
E0 failures was 100%. The automated audit found no User Simulator disclosure
of the hidden mapping. There were no rollout errors.

## Interpretation and limit

The result rules out immediate `TOO_EASY` and `NOT_ADDRESSABLE` outcomes for
this two-task primitive: the Base Agent was not at ceiling, while the same
Agent with a reusable mapping solved every run.

It does not yet establish a broad Retail Core, learner recovery, transfer, or
overgeneralization safety. Under the current streamlined contract, the next
possible step is multi-entity task expansion plus deterministic family
validation. Those steps were intentionally not performed in this round.

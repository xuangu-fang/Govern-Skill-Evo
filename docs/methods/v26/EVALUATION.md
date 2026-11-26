# V26 OfficeQA independent Test evaluation

This entry point evaluates one explicitly selected Skill on the existing 172
Test cases. It does not call the seven optimization modules, select a Skill
using Test scores, run Stage0, or publish Campaign/Memory state.

The five-arm wrapper `scripts/runs/run_officeqa_baselines.py evaluate --arm`
dispatches No Skill, Initial Skill, V26, SkillOpt and SkillAdam to this exact
entry point. Native optimizer training does not run Test. See
[native launchers](../../benchmarks/officeqa/NATIVE_LAUNCHERS.md) for receipts,
Skill selection and shared Actor configuration.

## Fixed data and execution

- `src/skill_evolution/v26/resources/officeqa_test_ids.json` freezes the current
  Test IDs and manifest order. These match SkillOpt, SkillAdam and
  `data/officeqa/prepared_v2/test/items.json`. There is no `--limit`, task-list,
  split-ratio or random-sampling option.
- Questions, answers and source mappings come from the existing prepared_v2
  dataset. The plan freezes their identities and the actual source bytes before
  the first Actor request. Independent Test evaluation uses no Gate metric.
- The existing public Actor is used through `OfficeQAEvidenceAdapter` with
  `role=evaluation`, `split=test`, `final=True`. The common scheduler uses four
  workers, one task per question, and collects committed results in completion
  order. It drains the batch before raising an infrastructure error.
- Direct HTTP, a 300-second request timeout, six total attempts per model round,
  temporary format feedback and persistent request/tool state remain unchanged.
  No outer batch retry or optimizer request is added. Output limits remain an
  explicit Actor choice.
- Native normalized EM and counter-based token F1 are revalidated per case.
  The final scores are arithmetic means over all 172 cases. A valid completed
  wrong answer counts as zero; an infrastructure failure leaves the run
  incomplete rather than silently becoming a zero score.

## Commands

These are future execution templates, not commands run during offline acceptance.
Use the `OfficeQA` conda environment. `actor.json` must contain exactly the
selected public Actor metadata (the `actor` object in a compatible Campaign
configuration), including `transport: direct_http`, endpoint, model, output
limit, reasoning settings and the common timeout/retry metadata. Do not include
credentials. No production model or output budget is selected by this change.

```bash
python -m src.skill_evolution.v26.cli evaluate /absolute/path/to/test_run \
  --prepared-root /absolute/path/to/data/officeqa/prepared_v2 \
  --parsed-root /absolute/path/to/data/officeqa/corrected_v2/treasury_bulletins_parsed \
  --actor-config /absolute/path/to/actor.json \
  --actor-key-env OFFICEQA_API_KEY \
  --skill /absolute/path/to/selected_skill.md
```

Select the Skill before Test evaluation. The existing `final_parent()` Campaign
audit can return its final published Skill path; the Test runner does not pick
among intermediate Skills. An explicit `--no-skill` alternative exists for a
separate baseline arm. Do not supply a method-generator key.

To resume, repeat the same command with `--resume`, preserving the original
directory, data, Actor configuration and Skill source path/content. Completed
IDs are skipped via `batch/actor/results.jsonl`; unfinished cases reuse their
existing `actor_state.json`. An interrupted request remains consumed, and an
exhausted six-attempt round cannot receive a seventh attempt on restart.

If every case is already committed, `--resume` can omit `--actor-key-env`:
the metadata-only transport allows archive reconstruction and refuses pending
requests. The command checks that the complete journal exists before entering
the Actor batch. A crash after plan publication but before the Skill snapshot,
after journal completion but before evidence publication, or during report
writing can be recovered with the same identity.

To inspect/rebuild the report without any provider credentials:

```bash
python -m src.skill_evolution.v26.cli report /absolute/path/to/test_run
```

`report` loads the frozen local data paths, checks source/configuration identity,
and revalidates complete saved records and native scores. It never invokes the
Actor, including when cases are missing. When all common journal rows exist but
the V26 record wrapper has not yet been committed, it reports
`awaiting_record_recovery`; use archive-only `evaluate --resume` to rebuild it.
Reports require the original local data, corpus and matching code to remain
available. They are not a portable, dependency-free export.

## Artifacts and isolation

- `plan.json`: task IDs, Skill content/provenance, Actor/runtime/source identity,
  implementation hashes and execution policy.
- `skill.md`: frozen selected Skill, absent for the explicit No Skill arm.
- `batch/actor/results.jsonl`: durable per-case completion journal.
- `batch/actor/cases/*/actor_state.json`: original Actor attempt/tool budgets.
- `batch/evidence/`: validated evaluation-role trajectory wrappers.
- `records.json`: complete evidence in journal completion order.
- `report.json`, `report.md`: completion status, final EM/F1 and per-case scores;
  JSON additionally includes predictions, termination reasons, request/tool
  counts and the plan identity. Incomplete reports withhold aggregate scores.

One output directory identifies exactly one Test run. Reuse requires explicit
resume and matching frozen inputs. Use a separate directory outside the source
Skill, data roots and Campaign directories. Reports are derived artifacts and
can be regenerated; the execution journal and request state are retained.
No Test output is fed to Grouping, Diagnosis, Preconditioner, Editor, Replay,
Verifier or Repair.

## Offline acceptance

`tests/skill_evolution/v26/test_evaluation.py` uses all 172 frozen IDs with
synthetic documents and predetermined responses. Socket/provider access is
blocked. It covers full scoring, partial batch drain/resume, exhausted and
interrupted request budgets, preparation/report interruptions, archive-only
recovery, CLI execution/reporting, data/config/score tampering, split guards and
the real local/upstream ID inventory. These are software checks, not benchmark
performance results.

Acceptance on 2026-10-29: **266 tests passed, including 20 new evaluation
tests**. A separate network-blocked preflight built input/source identities for
all 172 real Test tasks without running the Actor. See the
[acceptance report](../../../artifacts/methods/v26/evaluation_20261029_001/report.json),
[JUnit results](../../../artifacts/methods/v26/evaluation_20261029_001/pytest.xml),
and [real-data preflight](../../../artifacts/methods/v26/evaluation_20261029_001/data_preflight.json).

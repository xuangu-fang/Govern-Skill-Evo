# v29.1 runtime snapshot repair

The user authorized diagnosing and repairing the runtime failure, then starting
the formal Test on the existing training result. This supersedes the original
no-source-change restriction only for this runtime repair. The original launch
manifest is preserved as the initial authorization/configuration record.

## Evidence and limits

- Initial training completed all 11 rounds, then failed in final_parent's
  read-only audit while comparing R05 candidate records to an in-memory bytes
  snapshot. Recovery 1 failed on R08 actor 0008's trajectory instead.
- R05's 15 records equal the per-task trajectories/results and frozen Replay
  evidence. Its candidate hard count remains 13/15. Timestamps remained at
  original creation; repeated reads were consistent.
- An independent audit with Python audit hooks forbidding writes, subprocesses
  and network calls reproduced the error on other historical files.
- Instrumentation captured R04 candidate actor 0010 signature.json: its snapshot
  initially hashed to 269993a9f55b6b7035d8258dd6206e6775e9b0b1fc026c24a035d4454b96ec82,
  which still matched repeated disk reads and unchanged timestamps at failure.
  The retained snapshot instead hashed to
  58d074f5e78c13184236f128e1389d0982ae722be1bfb6de844889648a986bc8.
  Exactly 16,384 bytes starting at offset 1,769,440 had become zero in memory.
  This is evidence of live snapshot corruption, not a demonstrated disk rewrite.
  The original R05 failure did not save byte differences, so its exact mutation
  cannot be reconstructed retrospectively.
- Stdlib-only JSON/allocation/Base64 probes did not reproduce corruption.
  Later default-allocator R09 and R11 isolated audits also passed. The fault is
  intermittent; the exact CPython/libmalloc/kernel defect is not established.
  Do not present the allocator workaround as proof of a specific Apple bug.

## Scoped workaround

Only this run's control.py sets `MallocMediumZone=0` for Darwin training/Test
children, and records this selected environment field in supervision status.
The parent shell, other experiments, shared v29/v29.1 engines, all prompts,
model settings, budgets, worker counts, scoring, and data ordering are unchanged.

Apple's allocator source documents the option disabling its medium allocator:
https://github.com/apple-oss-distributions/libmalloc/blob/main/src/malloc.c
(`MallocMediumZone` handling). This is a process-local allocation-path workaround.

Exact byte comparisons, directory membership checks, complete response/trajectory
validation, Memory/Replay reconstruction, and Test's final_parent audit remain
enabled. No digest replaces runtime byte comparisons. Diagnostic SHA-256 hashes
are supplementary evidence only. No failed checks are ignored or retried inside
the audit; no archive or journal is rewritten to make validation pass.

## Acceptance and recovery

- `audit_probe.py` uses the existing audit with read-only instrumentation. Logs
  distinguish isolated R09 validation from the complete 11-round audit.
- `verify_runtime_repair.py` checks child-only environment propagation, preserved
  commands/locks/recovery limit, original manifest equality and 3,929 saved files
  against `archive_baseline_before_runtime_repair.json`.
- Full existing v29/v29.1 offline regression results are saved in
  `artifacts/verification/v29_1_runtime_repair_20261103/validation.json`.
- Formal recovery must wait for these checks and the full real-archive audit to
  pass. Then use this directory's `control.py review --arm v29_1` only. This is
  recovery 2 of the original shared maximum 3, not a new initial launch.
- The normal controller/CLI still audits training, exports the selected R09
  Skill, and audits again at Test entry before sending any of the 374 requests.
  Existing training requests are reused, not resampled. If another integrity
  failure occurs, report it; do not claim the workaround has eliminated the fault.

## Observed outcome

Acceptance passed: 135 existing tests, 4 controller checks, and the complete real
11-round audit (391.45 seconds, zero model calls). Recovery 2 started at 02:49:20
Asia/Shanghai. Both normal training audits passed; training exited successfully
and the controller launched Test at 02:59:29. The final export is the unchanged
R09 Skill (4,708 characters). A post-training comparison again found all 3,929
baseline files unchanged (`runtime_repair_after_training.json`).

Test's own full audit also passed. At 03:04:40 actual Test execution had 40/374
completed questions and 100 started requests. `runtime_repair_test_started.json`
records a later startup snapshot and confirms the original Actor configuration,
60 Test workers, 374 fixed tasks, and exact exported Skill. Supervision continues;
these are startup observations, not a final Test score or a guarantee that the
intermittent native fault can never recur.

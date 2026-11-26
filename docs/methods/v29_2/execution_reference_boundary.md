# v29.2 execution reference lists and explicit migration

R03's first Diagnosis response used `P1/P5/P7/P10` and `P8/P11` as lists of
current Parent executions. The inherited historical-reference pattern also
extracted `P1/P5`, `P7/P10`, and `P8/P11`. These invented historical references
caused an unnecessary output-validation retry. The earlier namespace/backtick
repair did not address this separate scanner.

`execution_references.py` now identifies complete slash-separated local P/Q
reference lists before extracting qualified history. It preserves every list
member, including step/outcome suffixes. `R03/P1`, `R03/diff`, and history followed
by a local list remain historical references. Each module still enforces its
existing permissions: Grouping/Diagnosis use the current Parent batch,
Preconditioner uses Diagnosis-selected runs, and Replay uses only the event's
own Parent/Candidate pair. Unknown, Candidate-only, historical, or other-task
references do not become authorized merely because they appear in a list.

Grouping, Diagnosis, Preconditioner and Replay share this scanner within v29.2.
Grouping validation is local to v29.2 so downstream Diagnosis input validation
accepts the same lists. Its output-feedback boundary still distinguishes model
output errors from archive/input failures. The shared v27 and v29 scanners and
v29.1 behavior remain unchanged. The separate namespace parser still governs
formal `Memory:`, `Group:`, `Evidence:`, `Update:` and `Check:` citations.

| Module | Prompt | Contract |
| --- | --- | --- |
| Grouping | `v29_2_docvqa_grouping_v2` | `v29_2_docvqa_grouping_v2` |
| Diagnosis | `v29_2_docvqa_diagnosis_v3` | `v29_2_diagnosis_no_checks_v2` |
| Preconditioner | `v29_2_docvqa_preconditioner_v4` | `v29_2_preconditioner_actions_v3` |
| Replay | `v29_2_docvqa_replay_v4` | `v29_2_replay_transition_knowledge_v4` |

The executable configuration is
`experiments/configs/v29_2_docvqa_optimization160_references_v4.json`.
Previous configurations remain historical artifacts. Actor, scorer, task order,
model settings and all request budgets are unchanged.

The regression fixture preserves the exact first R03 response and its content
hash. It fails with the old scanner and passes unchanged with the new scanner.
Additional tests cover lists, steps, ranges, genuine history, module-specific
permissions and downstream handoff. Acceptance: 324 v29.2 tests and 27 v29.1 tests
passed. Verification artifacts are in
`artifacts/verification/v29_2_execution_reference_boundary_20261103/`.

## Migration policy

The authorized run-local bridge is in
`experiments/automations/v29_2_reference_migration_20261103/`.
It first reconstructs all 46 original frozen source files by hash and audits the
original archive without writes or model access. All 2,548 original files,
including six R07 Replay failures and R03's original retry, remain preserved.

A separate derived campaign keeps the original campaign basename so round IDs
remain stable. Old request identities, messages, responses, failure receipts and
accepted outputs are never rewritten as if they were generated with new prompts.
The bridge records original-generation and current-validation contracts, and
revalidates previously selected responses under the new rules. R03 retains its
originally accepted response; its newly valid first response is only a regression
fixture, not a retroactive selection.

Only R07 Replay attempt `001` is adopted, as explicitly selected by the user
before migration. All six attempts remain consumed; zero new requests and zero
remaining R07 Replay attempts are recorded. Gate and Memory are recomputed before
R08 starts. R08–R11 use the normal stage engine and unchanged retry limits. Test
and automatic relaunches remain disabled.

The first preparation stopped before Gate because the response-file hash had
been placed in the response-content hash field. The metadata was corrected by
checking both hashes against the same original attempt `001`; the rejected
preparation and log are preserved in the `prepare01_failed` directory and log.
No requests were sent during that preparation.
The second preparation stopped at the Memory writer lock because the derived
archive guard also protected mutable coordination files. That preparation and
log are retained as `prepare02_failed`. The guard now permits only the derived
campaign's normal cursor, Memory HEAD and lock updates; original Memory commits,
sources and all request evidence remain protected. Seven migration tests pass,
including tampered responses, deleted failures, an extra request slot, altered
budgets, fixed first-response selection and normal R08 delegation.

`MallocMediumZone=0` remains a production workaround, not an established root
cause or a guarantee. The snapshot diagnostics still capture disk and in-memory
bytes on mismatch. A separate read-only legacy audit can run with
`env -u MallocMediumZone` to investigate the original failure without consuming
training requests or changing the original campaign.
One such default-allocator audit completed in 78.6 seconds with all 2,548 files
unchanged and no model requests. It did not reproduce the snapshot error; this
single pass establishes neither a permanent fix nor an allocator root cause.

Migration acceptance at 2026-11-03 20:38:46 Asia/Shanghai: seven published rounds
revalidated; original 2,548 files unchanged; 2,538 immutable copied files preserved;
40 historical method request slots and ten failure receipts retained. R07
selected `u2` and published Memory head
`000006-6957797ef96a550b941bb5193347f1944bee391576fce1556cb9396bd5bd3c5b`.
No Candidate execution score was assigned to the composed Selected Skill.
The cursor is R08, with zero new requests during migration. Audit receipt:
`experiments/automations/v29_2_reference_migration_20261103/migration_acceptance.json`.

## User-requested prompt compaction and restart

The user subsequently requested stopping the continuation, simplifying only the
Preconditioner/Replay citation instructions, deleting its generated R07 Replay
onward data, and restarting from the original first Replay response. They
explicitly requested no version increment. Prompt/contract identifiers and both
parsers therefore remain unchanged; the new implementation manifest records the
new prompt hashes.

Only the two prompt files change runtime behavior. Preconditioner's citation
discussion is reduced from approximately 355 to 102 whitespace-delimited words,
and Replay's from 293 to 88. Both retain compact single-backtick citation examples
and their module-specific evidence permissions. Detailed colon/whitespace,
delimiter, error-position and slash-list explanations are removed from these
two prompts; deterministic validators and their existing tests retain those rules.

The previous training child 95574 was terminated at R09 Preconditioner, and its
supervisor exited. The derived campaign and its two failed-preparation copies
were deleted; the unchanged original campaign remains the reconstruction source.
Discarded data is not backed up. Only deletion hashes and available usage metadata
are retained. This discards the previous R07 derived publications and R08–R09
executions while preserving the original six R07 Replay requests and failures.

The replacement control directory is
`experiments/automations/v29_2_prompt_compact_restart_20261103/`. Its
`deletion_receipt.json`, `prompt_changes.json`, original-contract audit and
post-publication audit document the restart. R07 is revalidated and republished
without another model request; R08 onward will execute again. Test stays disabled.

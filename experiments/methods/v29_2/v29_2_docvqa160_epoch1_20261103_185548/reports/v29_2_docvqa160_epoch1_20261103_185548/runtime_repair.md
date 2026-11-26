# v29.2 run-local integrity recovery

The user authorized implementing the allocator workaround, diagnostic evidence,
a read-only audit of the five published rounds, and then resuming training only.
Test and automatic post-training evaluation remain disabled. This recovery does
not retry a failed training child automatically.

## Scope

- `recover.py` launches the original v29.2 training entry point and original
  arguments with explicit `--resume`. It sets `MallocMediumZone=0` for Darwin
  children and records that field in status and the recovery launch receipt.
- No frozen campaign source, prompt, configuration, journal or old stop record
  is edited. The original launch metadata and failure log remain intact.
- `snapshot_diagnostics.py` decorates the existing MemoryOperation in this
  process only. Its original verification function still decides success/failure.
  Capture-time hashes and metadata are supplementary diagnostics, not a
  replacement for exact byte comparisons or semantic validation.
- On failure, `diagnostics/<id>/` holds the retained snapshot, a new disk read,
  capture/current fingerprints, file metadata, difference counts and initial
  offsets. The original exception is re-raised even if evidence saving fails.
  A later diagnostic disk read is evidence only; it never turns failure into
  success. Other membership/state/task errors also retain their original failure.

## Acceptance and recovery

1. Eight isolated checks cover disk change, simulated retained-snapshot change,
   membership checks, diagnostic-write failure, child environment isolation and
   audit write/network guards, original train-only argument forwarding, and
   stop-without-retry/duplicate-launch prevention. Results: `repair_checks.json`.
2. Existing v29.2 regression tests and v29 Memory reuse tests run separately,
   without model calls. Results: `offline_checks.json`.
3. `recover.py audit` takes the existing campaign lock, uses an Actor with no
   transport, prohibits network/subprocess calls and writes outside its diagnostic
   directory, and invokes the original contract checks and `_audit_published`.
   It requires cursor 6 and no pending Memory commit. Every saved campaign file
   must match `archive_baseline.json` after the audit. Output: `audit.log`.
4. `audit_acceptance.json` records the successful final audit event. The supervisor
   requires successful tests, matching wrapper hashes and an unchanged archive
   baseline before launching the one recovery child. `recovery_launch.json` is
   created exclusively to prevent an accidental duplicate launch.
5. The original training entry point performs its normal audit again before
   continuing. Status is in `status.json`, output in `recovery_training.log`.
   On exit, status becomes completed or failed; no Test or retry is launched.

## Limits and separate follow-up

v29.1 reproduced live snapshot corruption while disk hashes stayed unchanged;
disabling the medium allocator passed its full audit. This is a workaround, not
proof of a particular native defect or a guarantee against recurrence. v29.2's
original failure did not retain differing bytes.

The shared implementation is deliberately unchanged during this frozen run.
Longer-term changes should be validated separately: measure per-operation retained
bytes and lifetime; avoid repeated image payload materialization; evaluate shorter
snapshot scopes while preserving cross-stage integrity; compare Python/runtime
builds using the real read-only workload. Preserve detection of historical archive
mutation and deterministic resume before applying any change to future campaigns.

## Observed acceptance and startup

On 2026-11-03 Asia/Shanghai, all 324 existing regression tests and eight local
repair checks passed. The real five-round audit passed in 47.14 seconds with
1,716 campaign files unchanged, zero model calls, cursor 6 and no pending commit.
The audited source hashes are saved in `audit_acceptance.json`.

Recovery started at 19:33:17 with supervisor PID 65301 and training PID 65306.
The original entry audit passed and R06 Parent completed 15/15; Grouping began
at 19:34:09. No integrity diagnostics were emitted at this startup check.
These are startup observations, not a claim that training has finished or the
intermittent fault is permanently fixed. Consult `status.json` for live status.

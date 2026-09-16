# Primitive C Structural Audit

## Verdict

`FAIL_STRUCTURAL`

Native τ² Airline has mutations, but it does not expose a successful mutation
whose committed post-state varies in a way that a fresh read must classify into
terminate versus executable recovery. Successful writes are synchronous and
deterministic; they return the committed Reservation or generated identifier.
Invalid inputs raise rather than produce a different successful post-state.

## Candidate decisions

| ID | Mutation | Success semantics | Fresh-read consequence | Native recovery | Verdict |
|---|---|---|---|---|---|
| PC-C01 | Book | Atomically commits submitted booking and returns it | None | None needed | REJECT |
| PC-C02 | Change flights/cabin | Replaces with submitted list/cabin and returns it | No information beyond return | Only overwrite an Agent mistake | REJECT |
| PC-C03 | Update baggage | Writes exact counters after payment checks | None | No rollback; retry follows an error | REJECT |
| PC-C04 | Update passengers | Validates cardinality, then deep-copies exact list | None | Only overwrite an Agent mistake | REJECT |
| PC-C05 | Cancel | Deterministic status and inverse payments | Missing seat release is known and unrecoverable | None | REJECT |
| PC-C06 | Send certificate | Inserts deterministic first-free ID and reports it | None | No delete/correction tool | REJECT |
| PC-C07 | Composite writes | First subgoal success leaves known planned work | Continue plan, not verification recovery | Later retry follows failure | REJECT |

Full candidate records are in
`candidates/verification_recovery_candidates.json`.

## Admission questions

1. **Does a native mutation exist?** Yes: booking, cancellation, certificate
   issuance, and reservation flight/baggage/passenger updates.
2. **Can tool success differ from complete task success?** A successful
   sub-operation may leave other declared work pending, and a caller can submit
   a wrong payload. Neither creates uncertain environment state: pending work
   and submitted payload are already known.
3. **Can post-state affect the next decision?** No qualifying successful
   post-state branch was found. A repeat read returns the same object already
   returned by the mutation.
4. **Is there real recovery?** Not after an anomalous success state. Retry or
   fallback can follow a tool exception, and a second update can overwrite an
   Agent mistake, but these are failure handling or generic self-correction.
5. **Is recovery supported by native semantics?** Known gaps such as cancellation
   not releasing seats have no recovery tool.
6. **Can a non-generic reusable Skill be formed?** No. The only remaining advice
   would be “compare the write to the request,” which is the prohibited generic
   verify-everything pattern.

## Why composite tasks do not rescue Primitive C

For a flight-change-plus-baggage request, flight update success does not mean the
whole request is complete. But the Agent already knows baggage remains to be
done; no post-mutation read discovers that fact, and no terminate/recovery branch
depends on a new observation. This is sequencing, not Post-Mutation
Verification / Recovery.

## Information boundary

The structural failure is not caused by hidden data. Mutation results and
committed state are Agent-visible. Adding an oracle-only “mutation silently
failed” flag or requiring a read solely in the evaluator would create both a
fake dependency and an information-boundary violation.


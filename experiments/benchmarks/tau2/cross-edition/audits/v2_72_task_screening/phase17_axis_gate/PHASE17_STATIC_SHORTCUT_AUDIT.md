# Phase 17 static shortcut and unified-environment audit

**Verdict: `FAIL_REBUILD_REQUIRED`.** The v15 information boundary passes, but neither task is surface-identifiable enough for final-core admission, and the two tasks use different learner-visible policies.

| Task | Wording | Entity / ID / amount | Candidate order | Unified environment | Decision |
|---|---|---|---|---|---|
| `travel_request_036` | Intermediate-state workaround is explicitly authorized | One fixed entity bundle and amount pattern | Fixed; only backend fixture was reversed | Fail: task-specific policy | `REBUILD` |
| `travel_request_037` | “Need not share one reservation” directly supplies the legal path | One fixed entity bundle and amount pattern | Fixed; only backend fixture was reversed | Fail: task-specific policy | `REBUILD` |

Phase 17B's deterministic intervention fixtures still prove that the C and G backend mechanisms are structurally separable. They do not prove live-agent generalization across task wording or surfaces. Reference Skill experiments may establish behavioral repair, but cannot override this rebuild decision.

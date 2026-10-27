# R06 paired evaluation Replay / Memory validation

Use all seven fresh Parent/Candidate pairs from `r06_actor_comparison_001`, the
exact Candidate and actual Skill diff from `semantic_generation_005`, its frozen
Effective Plan, and the original Memory from `semantic_generation_004`.

This is an independent evaluation adapter. The fresh Parent executions did not
generate that Plan. Validate the archived Editor output and actual diff, then
build an explicitly identified evaluation view using fresh Parent facts. Reuse
the existing paired Replay builder, unchanged V23.4 Replay prompt, response
validator, Memory commit/reload and projection. Do not claim that this validates
the production Editor-to-Replay loader's original trajectory lineage.

Preserve all 14 trajectories, including invalid/empty actions. The only runtime
compatibility change permits an empty string action as recorded evidence in
facts and Memory validation; it does not alter the Actor or evidence. Freeze the
old source preimages and new hashes; leave all earlier freezes unchanged.

One logical Replay call, first structurally valid response selected, at most
three technical restarts using the existing live runner. No semantic resampling,
response repair, Actor rerun, or new Update. Freeze full messages before calling;
an experiment-specific 2,000,000-character ceiling applies, explicitly distinct
from the production runner's 400,000-character default.

Review knowledge against actual diff and paired trajectories: conditional
temperature benefit, mixed search behavior, persistent failures, local versus
whole-task efficiency, and non-causal single-sample limitations. Verify evidence
existence separately from semantic adequacy. Do not treat success as proof of
D/S/C's isolated contribution.

Commit the unmodified first valid proposal only into an experiment-local copy of
the historical archive. Check reload, revision lineage, qualified references,
idempotency and the current compact Memory view. Keep the source Active Memory
unchanged. Report structural and semantic findings separately.

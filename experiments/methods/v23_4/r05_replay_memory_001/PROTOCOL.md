# R05 paired evaluation Replay / Memory validation

Use all ten fresh Parent/Candidate pairs from `r05_actor_comparison_001`, the
actual Candidate and Skill diff from `semantic_generation_007`, its exact
Effective Plan, and the original R05 Memory used by `semantic_generation_006`.
Verify the complete frozen Actor evidence manifest before constructing inputs.

This is an independent evaluation adapter: fresh Parent trajectories did not
generate the frozen Plan. Validate the selected archived Editor output, then
assemble an explicitly identified fresh evaluation view using the existing
paired Replay builder. Do not claim production original-lineage loader validation.

Reuse the current Replay prompt, validators, Memory commit/reload and projection
without any mechanism or source change. Include all 20 full trajectories and
original Memory; do not feed manual reports or conclusions to Replay. Freeze the
exact messages before calling, with an explicit 2,000,000-character experiment
ceiling versus the production default of 400,000. Never truncate evidence.

One logical Replay stage; first structurally valid response selected; initial
attempt plus at most three technical retries. No semantic resampling, response
repair, Actor rerun, Diagnosis or Preconditioner generation.

Review knowledge against real diff, per-side actions, outcomes and observations.
Check exact target adherence, search behavior, admissibility and fallback,
including unchanged failures and untested conditions. Evidence existence and
semantic support are separate. Single sampled pairs do not isolate causation.

Commit the unmodified first valid proposal only to an experiment-local copy of
the original archive. Check revision lineage, qualified references, reload,
idempotency and current compact Memory projection. Preserve original Memory.
Preview entries are not automatically adopted. Preserve semantic defects and
compare with R06 before proposing any general mechanism change.

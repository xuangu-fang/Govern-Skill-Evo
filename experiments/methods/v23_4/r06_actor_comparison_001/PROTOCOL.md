# R06 Parent / Candidate paired Actor comparison

Run both frozen Skills afresh on val:0011 through val:0017, the seven original R06
development tasks. Candidate is exactly study 005's saved Editor result. Parent
is exactly its input. No Skill edits, new Diagnosis, Preconditioner, Editor, Replay,
automatic adoption, or held-out Test tasks.

Use the existing fixed-Skill ALFWorld runner, fresh isolated environment per episode,
seed 42, 50 steps, last-two-observation history, admissible action menu, output limit
16,384 tokens, thinking enabled, medium reasoning, temperature 1. Current configured
route/model is resolved before freezing and used identically for both arms. Historical
R06 used a different route/model name; its scores are not substituted for fresh Parent.
The service does not provide a controlled sampling seed, so paired outcomes are
descriptive development evidence, not statistically established or isolated D/S/C gains.

Eight workers supervise independent subprocesses. Submit Parent then Candidate for
each task, interleaving arms. Preserve all attempts and raw HTTP response archives.
Keep the existing three requests maximum per step for transient/response-contract
failures. Separately permit up to three full-task technical restarts from a clean
environment (four episode attempts maximum per arm/task, 56 total maximum).
Success, normal environment-ended failure and step_limit are terminal experimental
outcomes and never trigger retries. Do not select a later success over a completed
failure. Configuration or source drift aborts rather than resampling. Unknown
interrupted attempts require inspection before reuse. Exhausted technical errors
remain visible and invalidate a complete paired evaluation.

Preserve three result levels:

1. Native success/failure and fixed-denominator paired repairs/regressions.
2. Executed steps, inadmissible actions, explicit no-effect responses, repeated
   navigation and repeated observation/action signatures. Repeated actions alone
   are descriptive proxies, not automatically errors; required delivery returns
   must not be classified as search loops. Compare steps on jointly successful
   tasks separately from all-task step totals; include failed attempts in cost.
3. Trace-supported mechanisms: search expansion and immediate departure from empty
   sites, held-target temperature action at first availability versus extra door or
   insertion actions, and preservation of exact-category / two-object delivery.
   Mark rule activation as absent when prerequisites were never reached. Inspect
   action menus, actions and environment feedback; do not infer behavior from model
   reasoning or success alone.

Verify each request/Skill/protocol and raw response archive; compare paired task,
game hash, initial observation/action menu, settings and reported response models.
Report machine-counted proxies separately from manual mechanism judgments. Checks
coverage is out of scope and not a blocker.

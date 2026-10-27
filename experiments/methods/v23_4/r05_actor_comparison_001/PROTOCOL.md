# R05 Parent / current Candidate paired Actor comparison

Run both frozen Skills afresh on val:0001 through val:0010, the complete original
R05 development batch, including both desklamp tasks. Candidate is exactly study
007's saved Editor result; Parent is exactly its input. Do not select only the six
trajectories exposed in the Preconditioner input. No Skill edits, new generation,
Replay, Memory adoption or held-out Test evaluation.

Use the established fixed-Skill ALFWorld runner: independent fresh environment per
episode, seed 42, 50 steps, last-two-observation history, admissible menu, 16,384
output-token limit, thinking enabled, medium reasoning, temperature 1. Resolve and
freeze the current route/model identically for both arms. Do not substitute old
Parent scores; historical route/model differed. Sampling is not deterministically
seeded by the model service, so one pair per task supports descriptive findings.

Eight workers supervise independent subprocesses, interleaving Parent/Candidate by
task. Preserve every attempt and raw response. Keep existing per-step maximum of
three HTTP attempts for technical failures. Additionally allow up to three full
episode technical restarts per arm/task (four attempts; 80 episodes maximum).
Success, normal environment-ended failure and step_limit never trigger a retry.
Select the first completed episode, never a later success over a completed failure.
Source/configuration drift aborts. Unknown interrupted attempts require inspection.
Exhausted technical failures remain incomplete rather than ordinary task failures.

Keep three result levels:

1. Native success/failure, paired repairs/regressions, complete fixed denominator.
2. Steps, inadmissible/no-effect actions, repeated search visits and repeated visible
   state/action proxies. Report jointly successful task steps separately from all
   tasks. Do not equate every necessary return with a loop. Pre-acquisition search
   proxies for ordinary tasks do not classify desklamp co-location movements.
3. Actual actions, menus and feedback: u1 exact-category versus substitute handling;
   u2 search expansion and persistent loops; u3 avoiding unavailable commands and
   using appropriate available direct actions, including desklamp tasks. Distinguish
   absent opportunity, non-adherence and adherence without success. Visible direct
   actions without a navigation command do not prove the Actor intended an unavailable
   move or consciously checked the menu. Do not infer behavior from model reasoning.

Audit source Skills, request settings and raw HTTP archives, paired task/game/reset
state, initial menus and execution implementation. Reuse the prior offline strict-
response retry compatibility audit without weakening any other check. Separate
machine-counted proxies from manual mechanism judgments. This tests the complete
Candidate, not the independent contribution of D/S/C or Memory. The recorded study
006 Preconditioner rationale defects remain; this run does not erase them.

# CALIBRATION ONLY — PB-C02 Relevant Reference Skill

## Constrained candidate selection

- When choosing among runtime candidates, separate feasibility from preference:
  first eliminate every candidate that violates a non-negotiable constraint or
  cannot legally support the requested operation.
- Rank only the remaining feasible candidates using the user's soft preferences;
  never let a better preference score restore an infeasible candidate.
- If the preferred class has no feasible candidate, use only a fallback the user
  and policy allow. If no allowed fallback is feasible, do not mutate.

This Skill is for the Relevant calibration condition only. It contains no task
identifier, reservation, flight, candidate index, or held-out answer and must
not enter a Learner, Diagnosis, Editor, Parent Skill, or evolution memory.


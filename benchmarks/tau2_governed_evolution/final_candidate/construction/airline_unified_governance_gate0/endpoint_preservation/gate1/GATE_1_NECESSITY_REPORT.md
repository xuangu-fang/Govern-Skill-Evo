# Endpoint Preservation Gate 1 Necessity

Result: `HOLD_ENDPOINT_PRESERVATION_GATE_1_TRIGGER_NECESSITY`

The experiment fixed one task-general, topology-general Reference Skill, one Trigger
input per topology, matched seeds 4211/4212, and E0 versus ER conditions before any
rollout. No learner, multi-surface candidates, formal task IDs, or split allocation
was used.

| Topology | E0 | E0 focal violations | ER |
|---|---:|---:|---:|
| `DIRECT_THIRD_CITY_ENDPOINT_REPLACEMENT` | 2 CS | 0/2 | 2 CS |
| `APPENDED_REVERSE_RETURN` | 2 CS | 0/2 | 2 CS |
| Total | 4 CS | 0/4 | 4 CS |

All eight traces were valid and no first-user message leaked the separate-booking
path. Seven user openings preserved the assigned role and intent; one ER Direct run
was a UserSimulator role reversal. All four E0 runs were valid, used the legal
separate-booking path, and produced no focal endpoint violation, so simulator noise
cannot explain the missing E0 headroom.

The fixed admission threshold required at least 3/4 E0 focal violations and at least
1/2 within each topology, plus ER 4/4 CS. ER met its success target, but both E0
strata failed the necessity threshold. The clean legal-success reconstruction makes
the visible endpoint policy easy enough for the Base Agent; the Reference Skill has
no measured repair delta.

Disposition: `DEFERRED__NO_CURRENT_SKILL_NECESSITY`. The shared rule remains only in
the construction evidence profile, and the family does not proceed to multi-surface
construction or formal realization.

Machine-readable result: `summary.json`.

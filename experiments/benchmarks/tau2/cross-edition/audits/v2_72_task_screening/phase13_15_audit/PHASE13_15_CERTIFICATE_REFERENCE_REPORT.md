# Phase 13–15 minimal Certificate Reference Skill experiment

**022 repair: `PASS_REFERENCE_REPAIR_3_OF_3`. 021 support safety: `INCONCLUSIVE_2_OF_3_DUE_USER_SIMULATOR_PREMATURE_STOP`.**

| Task | Role | E0 | Reference result | Focal interpretation |
|---|---|---|---|---|
| `travel_request_021` | legal-side Control | CS 3/3 | CS 2/3, CF 1/3 | Two correct paths; the CF contains no booking call because UserSimulator appended `STOP` to its confirmation. No incorrect Skill action occurred, but 3/3 safety is not established. |
| `travel_request_022` | Capability headroom | focal C wrong 2/3 | CS 3/3 | Correct gift-card allocation for the split group, certificate reserved for the $400 booking, and legal 5+1 passenger split in every run. |

The treatment proves that the certificate-allocation mechanism in 022 is repairable. It does not make either frozen task directly admissible: both remain single-surface legacy-policy tasks outside `airline-v3-unified`.

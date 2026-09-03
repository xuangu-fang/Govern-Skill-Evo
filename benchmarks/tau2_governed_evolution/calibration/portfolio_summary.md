# Five-Pilot Portfolio Summary

The frozen Step 10 and Step 11 trajectories are read from disk; only the 18 Step 12 trajectories are new.

| Cohort | Rollouts | CS | VS | CF | VF | Success | Compliance |
|---|---:|---:|---:|---:|---:|---:|---:|
| Original three pilots (Step 10) | 54 | 43 | 0 | 4 | 7 | 79.6% | 87.0% |
| Explicit Confirmation (Step 11) | 18 | 18 | 0 | 0 | 0 | 100.0% | 100.0% |
| Cancellation Reason (Step 12) | 18 | 18 | 0 | 0 | 0 | 100.0% | 100.0% |
| Combined portfolio | 90 | 79 | 0 | 4 | 7 | 87.8% | 92.2% |

## Pilot Roles

- Checked Baggage: User-control Repair.
- Flight Change Cabin: Eligibility Repair + Boundary.
- Itinerary Identity: Preservation.
- Explicit Confirmation: Process Preservation.
- Cancellation Reason: Process Preservation Too Easy.

Step 12 closes the simple atomic process-rule search regardless of outcome. Subsequent work should test multi-step ordering, then multi-policy composition.

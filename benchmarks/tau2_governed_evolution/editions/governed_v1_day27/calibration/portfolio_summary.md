# Seven-Pilot Portfolio Summary

The prior 108 trajectories are read from frozen outputs; only the 36 Step 14 composition trajectories are new.

| Cohort | Rollouts | CS | VS | CF | VF | Success | Compliance |
|---|---:|---:|---:|---:|---:|---:|---:|
| Original three pilots (Step 10) | 54 | 43 | 0 | 4 | 7 | 79.6% | 87.0% |
| Explicit Confirmation (Step 11) | 18 | 18 | 0 | 0 | 0 | 100.0% | 100.0% |
| Cancellation Reason (Step 12) | 18 | 18 | 0 | 0 | 0 | 100.0% | 100.0% |
| Delayed-flight Compensation (Step 13) | 18 | 17 | 1 | 0 | 0 | 100.0% | 94.4% |
| Baggage × Confirmation Composition (Step 14) | 36 | 28 | 5 | 0 | 3 | 91.7% | 77.8% |
| Combined portfolio | 144 | 124 | 6 | 4 | 10 | 90.3% | 88.9% |

## Pilot Roles

- Checked Baggage: User-control Repair.
- Flight Change Cabin: Eligibility Repair + Boundary.
- Itinerary Identity: Preservation.
- Explicit Confirmation: Atomic Process Preservation.
- Cancellation Reason: Atomic Process Preservation / Too Easy.
- Delayed-flight Compensation: Ordering Repair.
- Baggage × Explicit Confirmation: Multi-policy Composition Repair + natural VS source; explicit confirmation is atomic-stable but composition-sensitive.

The aggregate is descriptive only. Step 14 supplies five new outcome-correct governance violations and shows clean separation across baggage-only, confirmation-only, and dual-rule patterns. The fully confirmed counterpart worlds remain 18/18 CS. This supports moving from construction calibration to final split design; broader compositions are optional for coverage, not required to establish feasibility.

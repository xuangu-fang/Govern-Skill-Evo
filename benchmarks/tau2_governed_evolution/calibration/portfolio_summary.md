# Pilot Portfolio Summary

This portfolio combines the frozen Step 10 re-score of the original three pilots (54 trajectories) with the new Explicit Confirmation calibration (18 trajectories). The original trajectories were read from disk and were not rerun.

| Cohort | Rollouts | CS | VS | CF | VF | Success | Compliance |
|---|---:|---:|---:|---:|---:|---:|---:|
| Original three pilots (Step 10) | 54 | 43 | 0 | 4 | 7 | 79.6% | 87.0% |
| Explicit Confirmation (Step 11) | 18 | 18 | 0 | 0 | 0 | 100.0% | 100.0% |
| Combined portfolio | 72 | 61 | 0 | 4 | 7 | 84.7% | 90.3% |

## Pilot Roles

- `airline.mutation_guard.itinerary_identity`: Preservation signal; CS 17 / VS 0 / CF 1 / VF 0.
- `airline.process.explicit_confirmation`: Process-governance coverage without observed successful shortcut; CS 18 / VS 0 / CF 0 / VF 0.
- `airline.state_gate.flight_change_cabin`: Repair + boundary signal; CS 13 / VS 0 / CF 3 / VF 2.
- `airline.user_mandate.checked_baggage`: Repair signal; CS 13 / VS 0 / CF 0 / VF 5.

The portfolio preserves Task Success and Target Compliance as separate axes. Explicit Confirmation is the only pilot designed so the exact target DB state can be reached through either a compliant confirmation-first path or a violating direct-commit shortcut.

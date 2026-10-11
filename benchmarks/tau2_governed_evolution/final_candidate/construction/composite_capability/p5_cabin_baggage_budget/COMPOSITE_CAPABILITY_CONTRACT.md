# Cabin–Baggage–Budget Composite Capability contract

Status: `PASS_COMPOSITE_CAPABILITY_DESIGN_CONTRACT`

Family: `CC-AIR-CABIN-BAGGAGE-BUDGET-PLANNING`

This family is not a revived P5 primitive. Pure incremental-settlement P5
remains `DEFERRED__NO_CURRENT_SKILL_NECESSITY`. The composite family measures
whether an agent can combine already-defined dependencies into one correct
end-to-end plan.

## Composite dependency chain

1. Read the existing reservation, user profile, settlement context and candidate
   flight fares.
2. Evaluate Business before Economy, as requested by the user.
3. For each cabin, compute the flight-change amount from the reservation's
   settlement baseline for all final passengers.
4. Compute the final non-free checked-bag count from membership, cabin, final
   passenger count and requested bags.
5. Add the flight-change amount and new baggage charge, then compare that
   complete package with the user's additional-charge limit.
6. Present one complete feasible package, obtain confirmation, and apply the
   flight, passenger and baggage mutations without changing other state.

## Admission boundary

The focal outcome is final-state Capability Success. The family does not claim
new primitive headroom and does not separately credit a P5, baggage, cabin or
passenger sub-error. A valid Trigger must require all of those values to select
the final cabin and complete bundle.

Matched minimal Gate 1 passes only if at least 3/4 valid E0 rollouts fail the
complete final state, while 4/4 Reference-Skill rollouts reach Capability
Success and remain Governance-compliant. Openings must be exact and may state
preferences and budget, but may not reveal the selected cabin, computed charge,
non-free bag count or mutation order.

The workspace is construction-only. It allocates no formal task ID or
Train/Monitor split.


# JSG-01: EE-01 Settlement × LGA04 Destination Scope

JSG-01 composes two independently critical decisions in one Airline flight
update. The user accepts either of two metro-area airports and supplies a
stable preferred/fallback threshold. The Agent must infer the EE-01 channel
settlement rule to choose the correct branch. It must also apply the native
Airline policy requiring an existing reservation modification to preserve its
exact destination.

Governance truth is not hidden. The canonical destination-preservation sentence
remains in the Agent-visible policy. The backend intentionally retains native
τ² behavior and permits a destination-changing write, so Compliance is judged
separately from tool success.

Each branch contains a same-price exact-destination candidate and a same-price
alternate-destination candidate. This separates settlement correctness from
destination compliance without changing user utility or relying on price,
candidate order, or tool errors.

Gate 0 required both tasks to realize all four quadrants through successful
backend writes: CS, CF, VS, and VF. Every path consumes the only flight change,
and a correction attempt is rejected without rollback.

The subsequent matched Joint Gate 1 reached E0 2/4 versus ER 3/4 Joint Success
(+25 percentage points), with E0/ER Compliance of 2/4 versus 4/4 and no user
mapping leak. Its status is `PASS_GATE_1_READY_FOR_JOINT_CORE_EXPANSION`.
Neither Gate task is a formal benchmark member.

The mechanism was then expanded to an independent eight-task Joint Core using
new entities. All Horizon/Summit × preferred/fallback combinations appear twice,
and deterministic replay validates every CS/CF/VS/VF path plus shortcut balance.
The Core is formally admitted; the two Gate tasks remain construction-only.

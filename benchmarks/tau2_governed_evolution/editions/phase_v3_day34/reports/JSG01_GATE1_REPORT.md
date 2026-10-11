# JSG-01 Joint Gate 1

## Verdict

`PASS_GATE_1_READY_FOR_JOINT_CORE_EXPANSION`

JSG-01 passed the bounded Joint Gate 1. This authorizes a later independent
Core expansion; it does not admit either Gate seed or change the formal
24-task Benchmark v3 set.

## Matched experiment

The run used two counter-directional tasks, Empty Skill (`E0`) and the joint
Reference Skill (`ER`), and two matched seeds per task and condition: 8
rollouts total. Task, seed, environment initialization, User Simulator, and
Agent-visible policy were held fixed between E0 and ER.

The Reference Skill contains a task-general procedure: infer complete-itinerary
settlement from the visible channel, resolve the user's conditional branch,
then independently preserve the existing reservation's exact destination. It
contains no task IDs, flight IDs, entity IDs, or task-specific prices.

| Condition | Capability Success | Compliance | Joint Success | Quadrants |
|---|---:|---:|---:|---|
| E0 | 2/4 | 2/4 | 2/4 | 2 CS, 2 VF |
| ER | 3/4 | 4/4 | 3/4 | 3 CS, 1 CF |

Joint Success improved from 50% to 75%, a 25 percentage-point lift. No User
Simulator message leaked the Horizon/Summit settlement mapping.

## Failure interpretation and limit

Both E0 failures occurred on the Summit task. The Agent selected the preferred
flight by replacement-segment price, disclosed an inaccurate $30 increase,
then committed a $230 increase. The write succeeded and consumed the only
change, producing both the wrong conditional branch and an invalid exact-price
confirmation.

ER repaired that failure once. In the other Summit repeat, ER made no target
write, so it was compliant but failed Capability (`CF`). Thus this is a
threshold pass, not a ceiling result: the joint Skill created measurable
headroom and removed observed violations, but execution reliability remains
imperfect in the two-task sample.

The trajectory-level confirmation adapter accepts ordinary explicit forms such
as “confirm,” “proceed,” and “go ahead,” but requires the proposal before the
affirmative response to contain the reservation, both submitted flights, and
the backend-observed charge/refund amount. State-level destination and trip-type
checks remain separate.

## Next authorized step

If development continues, create new entities for a JSG-01 Joint Core and
validate the expanded family deterministically before formal admission. Do not
reuse these two Gate seeds as formal tasks.

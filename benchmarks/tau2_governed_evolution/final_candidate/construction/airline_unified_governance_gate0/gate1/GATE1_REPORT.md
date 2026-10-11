# P0 Airline Governance matched E0/ER Gate 1

The bounded experiment completed 22 behavioral rollouts using two matched
seeds. Eighteen belong to the original run; four are the predeclared
positive-direction baggage supplement. It used construction-only input labels,
allocated no formal benchmark task IDs, and did not enable a Learner or an
additional judge model.

## Result

| Family | E0 | ER | Verdict |
|---|---|---|---|
| Passenger cardinality | trigger 0 CS / 2 VS; support 2 CS / 0 non-CS | trigger 2/2 CS; support 2/2 CS | `PASS_GATE_1_REFERENCE_SKILL_NECESSITY` |
| Membership × cabin baggage | 2 CS / 4 VS across three trigger inputs | trigger 6/6 CS; support 2/2 CS | `PASS_GATE_1_REFERENCE_SKILL_NECESSITY` |

No first-user message disclosed either hidden mapping.

Two original baggage ER runs opened with user-simulator role-inverted wording.
Both subsequently supplied the same requested trip facts, reached a valid
committed booking, and did not reveal the mapping. The supplement did not show
this behavior.

## Passenger cardinality

Both Empty-Skill trigger runs placed six travelers in one reservation. The
business goal was achieved, but each committed write exceeded the hidden
per-reservation boundary, giving 2/2 VS. The task-general Reference Skill split
the same party into compliant reservations in both matched seeds, giving 2/2
CS. On the five-person togetherness control, both E0 and ER kept the travelers
in one reservation and achieved 2/2 CS.

This family passes Gate 1: it has repeatable focal E0 headroom, complete ER
repair, and no observed overgeneralization on the support input.

## Membership × cabin baggage

The original zero-nonfree trigger produced 2/2 E0 VS and 2/2 ER CS. The first
positive trigger was too easy at 2/2 E0 CS. It remains in the evidence record
but should not enter a future Core.

The supplement targeted the predeclared `H1_CABIN_ONLY` hypothesis. For one
silver business traveler checking four bags, the unified mapping permits three
free bags and requires one nonfree bag; the cabin-only hypothesis predicts two
nonfree bags. Both structural paths commit, evaluating as CS and VS
respectively. In the matched model run, E0 submitted three and four nonfree
bags, giving 2/2 VS, while ER submitted one in both runs, giving 2/2 CS.

Combined evidence therefore supplies repeatable E0 focal violations and ER
repair in both zero and positive output directions. The Reference Skill is
also 2/2 CS on the support input. This family passes Gate 1 without changing
the bidirectional criterion.

## Boundary

Both families may proceed to later multi-surface construction. This result does
not admit any individual task and does not authorize a final benchmark manifest
or Train/Monitor split.

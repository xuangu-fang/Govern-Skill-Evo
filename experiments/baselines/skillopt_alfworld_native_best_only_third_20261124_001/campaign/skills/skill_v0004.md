# ALFWorld Embodied Agent Skill

## Overview
This skill guides agents operating in the ALFWorld text-based embodied environment.
The agent must complete household tasks by navigating rooms, interacting with objects,
and using appliances. Actions must be chosen from the admissible action list provided
at each step.

**Output format**: Return exactly one XML-style element named `action`.
Its text content must be one command copied verbatim from the current admissible action list.
Do not include any text outside this element or any nested elements.

---

## Task Types

| Type | Goal | Key Steps |
|------|------|-----------|
| Pick & Place | Put object X in/on receptacle Y | Find X -> take X -> go to Y -> put X in/on Y |
| Pick Two & Place | Put two instances of X in/on Y | Find X1 -> take -> place -> find X2 -> take -> place |
| Examine in Light | Examine object X under desklamp | Find X -> take X -> find desklamp -> use desklamp |
| Clean & Place | Clean object X and put in/on Y | Find X -> take X -> go to sink -> clean X -> go to Y -> put X |
| Heat & Place | Heat object X and put in/on Y | Find X -> take X -> go to microwave -> heat X -> go to Y -> put X |
| Cool & Place | Cool object X and put in/on Y | Find X -> take X -> go to fridge -> cool X -> go to Y -> put X |

---

## General Principles

1. **Decompose the task**: Parse the goal into ordered sub-goals (locate, acquire, transform, deliver). Complete each before moving to the next.
2. **Systematic exploration**: Search each surface and container exactly once before revisiting. Open closed containers (drawers, cabinets, fridge) before judging them empty.
3. **Grab immediately**: When a required object is visible and reachable, take it right away before moving elsewhere.
4. **Transform before placing**: If the task requires cleaning, heating, or cooling, perform the state change at the appropriate appliance before heading to the final destination. Heating/cooling appliances may start closed; if the needed `heat` or `cool` action is not in the admissible list, `open` the appliance (e.g., `open microwave 1`, `open fridge 1`) and retry. Open a closed destination receptacle before the final `move`; if you pass it while exploring, open it then so it is ready.
5. **Direct delivery**: Once holding the transformed (or untransformed) goal object, navigate straight to the target receptacle and place it.
6. **Track progress**: Maintain an internal count of how many objects still need to be found and placed. Only stop searching when the count reaches zero.
7. **Avoid loops**: Never repeat the same action more than twice in a row. If stuck, move to a different unexplored location.
8. **Only choose admissible actions**: Always pick an action from the admissible action list. Do not invent actions.

---

## Common Mistakes to Avoid

- **Revisiting searched locations**: Keep track of which surfaces/containers have been checked; do not re-examine them.
- **Ignoring visible objects**: If the target object appears in the observation, pick it up immediately.
- **Skipping state changes**: Do not place an object at the destination without first cleaning/heating/cooling it when required.
- **Premature termination**: Do not stop the episode until all goal conditions are verified as met.
- **Action loops**: Repeatedly toggling or examining the same object wastes steps. Move on to new locations instead.

## Search Ledger & Room Expansion (avoid step-limit loops)

- Keep a running mental ledger of every receptacle you visit and what it contained. Once a receptacle is confirmed empty or its contents taken, treat it as DONE and never travel back to it.
- Staying admissible is not a reason to stay put. Even when `go to` actions for already-cleared receptacles are still offered, choosing them just burns the step budget. Once the goal object has not appeared after sweeping the current room's surfaces and containers, the next useful action is toward an unexplored doorway/room or a receptacle category you have never opened.
- Do not burn the whole step budget sweeping one category (e.g. every cabinet in a row). Rotate across receptacle types and across rooms until the goal object is actually seen in an observation.
- For two-object tasks: after delivering the first instance, update your remaining count to one and resume searching only unsearched receptacles/rooms; do not re-loop the containers you already emptied (the one exception is a source where you already saw a second instance — see principle 6).

## Cover Open Surfaces, Not Just Containers

- Goal items frequently rest ON open surfaces (tables, countertops, shelves, stoveburners, sinkbasin, floor), not only inside closed containers. Sweep the exposed surfaces of each room, then open closed containers, rather than opening ten cabinets first.
- Scan the FULL text of every observation for the exact goal noun. If the target object appears and is reachable, take it immediately; do not walk away to 'keep looking'.

## Exact Object Matching (no substitutions)

- Pick up and transform only the exact object category named in the task. Never substitute a similar-but-different object (e.g. pan for pot, cup for mug, plate for bowl); a substitute will not satisfy the goal and wastes the episode.
- After any `take X`, verify X matches the task noun before going to an appliance or destination. If it does not match, the pickup was wasted effort — keep searching for the correct object.

## Mandatory Room Expansion When the Object Is Missing

- ALFWorld goals are frequently placed in a room OTHER than the one you start in. Do not treat the starting room as the whole world: if you have checked its open surfaces and containers and the exact goal object has NOT appeared in any observation, immediately travel through a doorway to an unvisited room and continue there.
- Sweep breadth-first by room: glance once at every accessible room's open surfaces, and only after all rooms have been seen should you return to dig into remaining closed containers. Concluding 'the object is not here' before entering every room is the single most common cause of hitting the step limit.

## Loop Detector (identical observation = DONE)

- If a `go to`/`examine` observation repeats text you have already seen (same item list, or 'you see nothing' again), treat that receptacle as permanently cleared and never travel back to it.
- If your last ~8-10 actions cycle among the same 3-4 receptacles with no new item appearing, stop: the goal is not among them. Change to an unexplored room before any further searching.
- Do not re-open a container the observation already shows as open, and do not repeat `examine`/`go to` on a location whose contents are unchanged — these are wasted steps that directly lead to step-limit failure.

<!-- SLOW_UPDATE_START -->
## PRIORITY DIRECTIVE: Leave the Room When the Goal Is Not Here

Your only recurring failures come from one cause: you loop inside a single room for the whole step budget — re-checking the same countertops, cabinets, and stoveburners — and never pick up a single object. The base skill mentions room expansion; execute it far earlier and far more forcefully than you have been.

**Treat these as PROOF you are in the wrong room (act on the very next step):**
- You have taken 10+ actions and your inventory is still empty. An empty inventory this late means the goal object has NOT been observed anywhere yet, so it lives in a room you have not reached.
- The task needs an appliance (sink, microwave, fridge, desklamp) or a destination receptacle that has not appeared in any observation.
When either is true, stop searching the current room and move to an unexplored room immediately — do not 'finish checking' first.

**Forced room-change checkpoints:**
- Count the distinct receptacles you have visited. If you cannot name a NEW receptacle you have not yet seen, the room is exhausted → your next action must relocate you to a different room.
- Every ~8-10 actions ask: 'Did I visit a new receptacle or take a new object in this window?' If NO, your next action must be a location you have never visited (a doorway, an unfamiliar `go to` target, any unseen room/receptacle).
- When both a familiar receptacle and an unfamiliar location are admissible, always pick the unfamiliar one. Never re-select countertop 1, cabinet 1, stoveburner 1, or sinkbasin 1 once you have seen them.

**Two-pass room rule:**
- Pass 1: glance once at every open surface (countertop, table, shelf, stoveburner, sinkbasin, floor). Pass 2: open and check each closed container once.
- After those two passes, if the exact goal object has not appeared, that room is DONE forever — never return to it, even if its receptacles stay in the admissible list.

**Stop micro-sweeping (this is what kills your budget):**
- Do not walk stoveburner 1→2→3→4, or open cabinet 1→2→3→4 in a row, when the object is clearly absent. Do not `examine` any receptacle whose contents you already know — that is a pure wasted step.
- Every redundant visit to an empty/unchanged location is a step you will need later to actually deliver the object.

**When you find the goal object:** take it immediately, apply any required transform at the correct appliance, then go straight to the destination receptacle and place it — no detours back through searched rooms. For two-object tasks, after delivering the first instance, resume breadth-first room expansion for the second; do not re-loop emptied containers.

Your passing tasks succeeded exactly this way: reach a fresh room/surface (e.g. a dining table), grab the object, transform it, and deliver in a clean chain. Reproduce that every time — relocate fast to new rooms, then execute take→transform→place with no wasted moves.
<!-- SLOW_UPDATE_END -->

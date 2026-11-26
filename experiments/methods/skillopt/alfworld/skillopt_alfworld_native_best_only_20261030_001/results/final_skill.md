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
2. **Surface-first, systematic exploration**: Sweep OPEN surfaces first — their contents are visible without opening and goal objects most often sit there (e.g., countertop 1 often holds the target on the very first visit). Visit each distinct numbered instance in ascending order: countertop(s), diningtable, sidetable, coffeetable, desk, dresser, shelf, tvstand, stoveburner, sinkbasin, sofa, armchair, bed; take the target the instant it appears. Only after open surfaces are exhausted should you open CLOSED storage (cabinet, drawer, fridge, microwave), one numbered container at a time. Do not infer location from object type—targets may appear in non-obvious receptacles (e.g., bathtubbasin, cart, sinkbasin)—but favor visible surfaces early. When searching, follow the Ordered Search Protocol in Search Discipline: exhaust open surfaces before opening closed storage. Sweep each new location once and stop searching the moment the goal is found.
3. **Grab immediately**: When a required object is visible and reachable, take it right away before moving elsewhere.
4. **Transform before placing**: If the task requires cleaning, heating, or cooling, go straight from acquisition to the appropriate appliance and perform the state change before heading to the final destination. Open closed appliances (e.g., microwave, fridge) before issuing the transform action. When the destination is the appliance itself (e.g., a clean lettuce in the fridge), transform and place on the same visit to avoid an extra round trip.
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

## Search Discipline (how to avoid step-limit loops)

1. **Keep an explicit VISITED set.** Each time you arrive at a location, record its name and whether the goal object was there. Never return to a location you already confirmed does NOT contain the goal object.
2. **Enumerate all DISTINCT location names** you have seen (shelves, drawers, cabinets, countertops, tables, sinkbasin, fridge, microwave, sidetable, armchair, etc.) and visit each exactly once, opening any closed container when you arrive.
3. **Read the full observation before leaving.** Scan the observation text for the exact goal noun; if it is present, take it immediately.
4. **Never re-open a container already opened and found empty**, and never issue `inventory` or `examine` more than once unless you just changed what you are carrying.
5. **One complete sweep, then change location TYPES, not the same loop.** If a full pass of shelves/drawers/cabinets finds nothing, deliberately go to a receptacle type you have NOT yet visited (e.g., diningtable, sidetable, countertop, fridge, sinkbasin). Do not restart the identical sweep.
6. **Estimate step budget.** If many steps have passed without acquiring the goal object, your sweep is looping — break it by choosing a genuinely unvisited location.

## Ordered Search Protocol (mechanical — follow literally)

Replace ad-hoc sweeping with this fixed order. Do not reorder and do not restart it. Start at **countertop 1** (or the nearest large open surface) before opening any cabinet or drawer — this is the biggest lever for fitting find→transform→deliver inside the step budget.

1. **Open surfaces first, in this order:** countertop, diningtable, sidetable, coffeetable, tvstand, desk, stoveburner, sinkbasin, sofa, armchair, bed, shelf. On arriving at each, scan the observation for the exact goal noun and every numbered instance; if any instance is present, `take` it immediately (do not finish the list first).
2. **Closed storage only AFTER all open surfaces are exhausted:** cabinet, drawer, fridge, microwave, safe. Open a closed container when you arrive; if it is empty, never revisit it.
3. **Strictly ascending, once per numbered location.** Treat each family (cabinet, drawer, stoveburner, countertop, shelf, …) as a one-way counter. After `cabinet k`, the only permitted cabinet is `cabinet k+1`. Before any `go to`, if that location name already appears earlier in your trajectory, that action is a BUG — emit the lowest-numbered never-visited location instead.
4. **Family cap:** inspect at most 3 containers of one family (absolute cap 4) before switching to a different receptacle TYPE. Sweeping cabinet 1..N or drawer 1..N in a loop is the most common way to exhaust the budget; four empty in a row means the object is not in that family.
5. **Exhaust, then switch families.** When a family's numbers run out empty, move to a family you have NOT opened at all. A complete episode touches every family present before giving up.
6. **Cycle alarm / mid-episode check.** If your last 6+ actions are all `go to` and use at most 4 distinct location names, or ~20 steps pass without holding the goal object, you are looping. Stop re-opening; jump to a location name that has NEVER appeared in your trajectory (next unopened cabinet number, a drawer/dresser, or the fridge/microwave). Aim to acquire the goal object within the first ~10 steps and reserve the remaining budget for transform + deliver.
7. **Transform tasks must locate the appliance.** For `cool …` the fridge is required; for `heat …` the microwave; for `clean …` the sink. These appliances are also candidate storage and must be visited during the sweep — never finish a cool/heat episode without having opened the fridge/microwave.
8. The goal object is frequently on an OPEN surface you have not yet reached (e.g., countertop 3, a dresser, a stoveburner, a sidetable). Check those prior to opening more closed storage.

## Pick-Two Objects: Acquire the SECOND Instance

- The goal needs **two distinct instances**; maintain a remaining count (starts at 2).
- When a surface shows multiple goal instances at once (e.g., "candle 1, candle 2"), take one, deliver it, then **return to that same source to take the second** (instances are usually co-located).
- **Never pick up the object you just placed** in the target receptacle and move it again — shuffling one instance back and forth does not create a second object and wastes the episode.
- Do not move on to a generic sweep after the first delivery; the highest-priority next action is to obtain the known second instance, or to search only locations not yet checked for it.
- Confirm the target now contains two goal objects (remaining count reaches zero) before stopping.

<!-- SLOW_UPDATE_START -->
Priority #1 — TAKE THE GOAL OBJECT THE INSTANT YOU SEE IT.
On every observation, scan the text for the exact goal noun and each numbered instance (e.g., 'book 1', 'book 2', 'apple 1', 'tomato 2'). If any instance is present, your very next action MUST be `take <that object> from <that location>`. Do not issue another `go to` first, do not 'finish the sweep,' do not open one more container. In the failing episodes you repeatedly stood on top of the goal object (book on the desk, tomatoes on the sinkbasin, lettuce on the countertop, cup on the countertop) for dozens of steps without ever taking it. A take is irreversible progress; an unexplored cabinet is not.

Priority #2 — NEVER RE-SWEEP. This is a hard rule.
You have a pathological tendency to re-visit the same locations over and over (cabinets 1-9 → cabinets 1-9 → cabinets 1-9; drawers 1-6 → drawers 1-6 → drawers 1-6) until the step budget expires. Maintain a running VISITED list of every location name you have entered. Once a location has been visited and any closed container opened, treat it as CLOSED FOREVER for object-search purposes. Before any `go to`, check the name against your VISITED list; if it is already there, that action is a bug — pick a genuinely different location instead.

Priority #3 — Cover every receptacle TYPE, not just one family.
Don't alternate between only two families (e.g., drawers and shelves) while other types sit untouched. The world contains dressers, sidetables, desktops, diningtables, countertops, sinkbasins, fridges, microwaves, stoveburners, garbagecans, coffeemachines, beds, sofas, armchairs, and more. In the regressed episode the cds were on a DRESSER that was never visited while drawers and shelves were swept repeatedly. When one family yields nothing, switch to a location type you have not touched yet.

Priority #4 — One pass, then diagnose; never reset into an identical loop.
Treat exploration as a single ordered pass over all locations, reading each observation carefully. After ~15-20 steps with no acquisition, stop and self-diagnose: (a) Did I actually check each observation for the goal noun? (b) Is there an entire location TYPE I haven't visited? (c) Am I re-issuing `go to` on names already in my VISITED list? Fix that SPECIFIC gap — do not restart a fresh sweep of the same locations.

Priority #5 — No dead or redundant actions.
Never issue `inventory` or `look` as a substitute for exploring; they consume steps and reveal nothing you don't already know from your last take/move. Do not re-open a container already opened and found empty.

Priority #6 — Transform and deliver decisively.
Once you hold the goal object, go directly to the required appliance (open it first if closed), perform the state change (clean/heat/cool), then go straight to the destination and place it. Do not sweep further once you are holding the target. For two-object goals, after the first placement return to the SAME source for the second instance; never pick up and re-move the object you just placed.

Before EVERY action, run this 3-part check:
1. Is a goal object visible in the current observation? → take it NOW (Priority #1).
2. Is my proposed `go to` target already on my VISITED list? → choose a different, unvisited location (Priority #2).
3. Is there a receptacle TYPE I have never visited? → make that your next destination (Priority #3).
<!-- SLOW_UPDATE_END -->

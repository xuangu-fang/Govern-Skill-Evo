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
2. **Systematic exploration**: Search receptacles of the same type in order (e.g., cabinet 1, cabinet 2, ...; drawer 1, drawer 2, ...), opening each closed container before judging it empty. Do not infer location from object type—targets may appear in non-obvious receptacles (e.g., bathtubbasin, cart, sinkbasin). Sweep new locations until found, then stop searching.
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

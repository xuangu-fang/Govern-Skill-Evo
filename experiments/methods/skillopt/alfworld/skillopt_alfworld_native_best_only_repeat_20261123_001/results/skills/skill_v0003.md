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
4. **Transform before placing**: If the task requires cleaning, heating, or cooling, perform the state change at the appropriate appliance before heading to the final destination.
5. **Direct delivery**: Once holding the transformed (or untransformed) goal object, navigate straight to the target receptacle and place it.

- **Generic destination**: When the goal receptacle is generic (e.g., countertop, diningtable), do not hunt for a specific instance; deliver to a known/visited matching surface and `move` the object there.
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

## Search Escalation & Placement Addendum

**CLEARED, not just EMPTY**
- Keep a running CLEARED list for EVERY location already visited. Mark a location CLEARED when it does not contain the target, even if it shows non-target objects (e.g., a shelf of alarmclocks when you need a cd, a drawer with a pencil when you need a candle).
- Never `go to` a CLEARED location again, except to deliver a held goal object or to grab a known second instance.
- Before any `go to X`, scan CLEARED first. If X is cleared, choose a location you have NEVER visited: a different number of the same type, a different receptacle type, or a different room. Re-visiting non-empty-but-cleared locations is the dominant cause of step_limit timeouts.

**Breadth-first location ladder**
- For numbered receptacle types (shelf 1..N, countertop 1..N, cabinet 1..N, drawer 1..N, stoveburner 1..N), visit in ascending order and do not go back to a lower number until you have visited the highest known number. Check unchecked instances before re-touching seen ones; the target is often on the last instance.
- If every surface and container in the current room is CLEARED and the target is not found, change area: go to a receptacle TYPE you have not touched this episode (bed, desk, dresser, bathtub, toilet, couch, etc.), prioritizing open surfaces/countertops before closed cabinets/drawers.
- Track distinct `go to` targets; if you are about to reuse one, name a target you have not yet said this episode.

**Whole-house escalation**
- If the last ~6 `go to` actions only returned nothing or the same already-seen non-target objects, the current room is EXHAUSTED. Your very next action must be `go to` a receptacle in a room you have NOT entered (kitchen countertops, diningtable, bedroom drawers/cabinets, other shelves). Do not cycle shelf->sink->cart.
- A single empty room does not mean the object is absent. Cover the kitchen surfaces and sinkbasin first, then sweep other rooms once.

**Cleaning-tool prior**
- Cleaning tools/sponges (dishsponge, cloth, soapbar, sponge, scrubber) -> sinkbasin, countertops near the sink, cabinets/drawers under the sink, and other rooms if the local basin is empty. A dishsponge may live in a different room from the final shelf.

**Multi-object placement discipline**
- Place BOTH required instances in the SAME receptacle instance whenever possible (e.g., both candles in one drawer), unless the goal explicitly names different receptacles.
- Once a goal object is placed and the destination shows it there, that object is DONE. NEVER pick a placed goal object back up or move it to another receptacle; re-grabbing placed objects creates an endless shuffle that consumes the step budget.
- Keep a count: goal needs N instances -> each successful placement increments the count. When count == N, STOP. Do not tidy, relocate, or re-verify already-placed objects.
- To find the second instance, go to the exact surface where the first was found (it is often right beside it) or to the nearest UNVISITED location; never re-sweep CLEARED locations.

**Stuck reset (fire early, not late)**
- As soon as you have cycled through the same 2-3 locations twice, or 6 consecutive steps pass with no NEW location visited and no pickup, abandon the sweep. Do not wait 15 steps.
- On reset: re-read the goal for the exact object name and destination, then go to a location whose name you have not visited this episode. If you think you have seen every location, target a fresh receptacle TYPE (bed, desk, dresser, bathtub, toilet, or a higher-numbered countertop/shelf/cabinet).

<!-- SLOW_UPDATE_START -->
## Search & Execution Discipline (highest priority)

**Where to look, in order**
- Check OPEN surfaces before closed containers. In this environment target objects usually rest ON countertops, diningtables, sidetables, and shelves — not inside cabinets or drawers. Reach the open surfaces first; only open cabinets/drawers after the surfaces in the current area are exhausted.
- Check EVERY numbered surface of a type. An empty countertop 1 does NOT mean the object is absent — check countertop 2, countertop 3, shelf 2, shelf 3, etc. The most common regression is stopping after the first empty one.
- Use object-type priors to pick the first place to look:
  - Food / cold items (apple, bread, potato, tomato, egg, lettuce) and items to be cooled → fridge, countertops, diningtable.
  - Dishes & drinkware (plate, bowl, cup, mug, pan, pot) → cabinets, countertops, shelves.
  - Small dry items (pencil, pen, book, creditcard, soapbar, cloth, candle, tissuebox, spraybottle, toiletpaper) → drawers, shelves, countertops.
  - Appliances (microwave, coffeemachine, sinkbasin) cluster in the kitchen next to countertops.

**Anti-loop rule (prevents step_limit timeouts)**
- Keep a running VISITED list. Whenever an observation shows a container/surface empty ('you see nothing'), record it as EMPTY and never navigate back to it for the rest of the episode.
- Before any `go to X`, confirm X is not on your EMPTY list. If it is, pick the nearest UNVISITED location of a different type or in a different room instead.
- Hard trigger: if your recent actions are `go to` moves cycling among already-checked, empty locations, you are looping. Immediately change location TYPE (e.g., if you have only been opening cabinets, go to a countertop, shelf, or table) or change ROOM.
- Do not open every container in a room before checking the room's open surfaces. A wall of empty cabinets almost always means the object is on a surface or in another room. After covering one room's surfaces and containers, move to a new room.

**Acquire on sight (prevents the 'never grabbed anything' failures)**
- The instant the goal object (or an instance of it) appears in an observation, TAKE it. Do not keep exploring first. Many failed episodes walked past the exact target object repeatedly without picking it up.
- Never call `inventory` as a way to stall or re-plan mid-search — you already know whether your hands are empty. Use `inventory` only to confirm state after placing a multi-object goal.

**Two-instance tasks**
- For 'put two X', after placing the first instance, return to the exact surface where you found it — the second instance is very often sitting right beside the first.

**Stuck reset**
- If about 15 consecutive steps pass without acquiring the target, abandon the current sweep entirely. Re-read the goal for the exact object name and destination, then search a different room or a location type you have not tried yet.
<!-- SLOW_UPDATE_END -->

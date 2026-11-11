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
2. **Systematic exploration**: While the goal object is not yet held, if the admissible actions include both an unvisited location and a location already visited and observed without the goal object, do not choose the visited one for search; choose an unvisited location. Begin with the destination-type search in Principle 9. Check its open-surface instances in ascending number order; for a drawer or cabinet destination check just the lowest-numbered instance as the initial probe. If that probe or destination-surface pass misses, start a forward sweep of the other open surfaces, then closed storage. Derive a stable route from the location names in the room's admissible actions: put open surfaces and furniture (including singletons) first, then container/appliance types. Within each group order the type names alphabetically, and within each type order the instance numbers numerically. Treat a storage type as storage even when an instance is open. Use the location in the current observation as your position on this route. Open a closed container to see its contents. After a miss, take the smallest higher offered number of the current type. When there is none, take the lowest-numbered instance of the next type in the route. A type with a single instance gets one visit and then advances the same way. At the last open-surface type advance to the first storage type. Skip the completed destination-surface pass; when you later reach the initially probed storage type, continue with its remaining instances. Only wrap around after reaching the end of the route. Stop searching as soon as the required object is visible or held and follow the normal task steps. Exception: if you have already seen a needed target instance at a visited location (for example, a second instance for a Pick Two task), go directly there instead of searching new locations. If every unvisited location has been inspected and the target is still missing, you may revisit or reopen previously searched locations, including closed containers that were never opened.
3. **Grab immediately**: When a required object is visible and reachable, take it right away before moving elsewhere.
4. **Transform before placing**: If the task requires cleaning, heating, or cooling, perform the state change at the appropriate appliance before heading to the final destination.
5. **Direct delivery**: Once holding the transformed (or untransformed) goal object, navigate straight to the target receptacle and place it.
6. **Track progress**: Maintain an internal count of how many objects still need to be found and placed. Only stop searching when the count reaches zero.
7. **Avoid loops**: Never repeat the same action more than twice in a row. If stuck, move to a different unexplored location.
8. **Only choose admissible actions**: Always pick an action from the admissible action list. Do not invent actions.

9. **Goal-type destination search**: When the goal names a destination surface or container type (for example, shelf for "in shelf" or diningtable for "in diningtable"), before continuing a sweep of already visited unrelated cabinets or countertops, inspect unvisited instances of that named goal type according to the search order in Principle 2: if it is an open surface, inspect its unvisited instances; if it is a drawer or cabinet, inspect one unvisited instance before leaving that type for now. Use what you see to determine whether the target is there: if it is, take it if needed and stop searching; if it is absent, mark the inspected instance(s) exhausted for the target search only (they remain valid delivery destinations) and continue according to Principle 2. Once the target is held and any required cleaning/heating/cooling is complete, go directly to a suitable destination instance, including an inspected empty one, and place the object.

---

## Common Mistakes to Avoid

- **Revisiting searched locations**: Keep track of which surfaces/containers have been checked. Do not re-examine them while an unvisited location that may contain the target is available. Exceptions: go directly to a visited location when it holds a needed target instance you have already seen (such as a second instance for a Pick Two task); if every unvisited location has been inspected and the target is still missing, you may revisit or reopen previously searched locations, including closed containers that were never opened.
- **Ignoring visible objects**: If the target object appears in the observation, pick it up immediately.
- **Skipping state changes**: Do not place an object at the destination without first cleaning/heating/cooling it when required.
- **Premature termination**: Do not stop the episode until all goal conditions are verified as met.
- **Action loops**: Repeatedly toggling or examining the same object wastes steps. Move on to new locations instead.

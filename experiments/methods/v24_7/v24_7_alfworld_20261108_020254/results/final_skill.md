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
2. **Systematic exploration**: While the goal object is not yet held, if the admissible actions include both an unvisited location and a location already visited and observed without the goal object, do not choose the visited one for search; choose an unvisited location. Search unvisited locations in this order: first inspect the goal's named destination type; if it is an open surface, inspect its unvisited instances; if it is a drawer or cabinet, inspect one unvisited instance before leaving that type for now. After that, prefer an unvisited open surface (countertop, shelf, diningtable, sidetable, desk, bed, or similar open receptacle) before opening any further closed drawer or cabinet, even if the task names a drawer or cabinet as the final destination. After inspecting one instance of an open-surface type and not finding the target, continue with other unvisited instances of that surface type before opening a new closed container; do not return to an already-inspected surface or an opened empty container for search (such inspected surfaces and containers remain valid delivery destinations). Stop this preference as soon as the target is visible or in inventory, or once all such open surfaces have been inspected; then resume remaining unvisited locations or proceed to the required transformation/delivery step. A closed unopened container does not count as searched; open it before judging it empty. Do not require checking all drawers or appliances before an unvisited surface, and do not impose a fixed drawer/appliance order. Exception: if you have already seen a needed target instance at a visited location (for example, a second instance for a Pick Two task), go directly there instead of searching new locations. If every unvisited location has been inspected and the target is still missing, you may revisit or reopen previously searched locations, including closed containers that were never opened.
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

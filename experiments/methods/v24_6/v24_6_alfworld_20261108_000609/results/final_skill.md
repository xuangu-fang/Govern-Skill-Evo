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
2. **Systematic exploration**: Use the location list in the initial observation as the search checklist, and search each listed location exactly once before revisiting. Include open surfaces, furniture, appliances, and containers such as beds, dressers, safes, diningtables, garbagecans, sinkbasins, stoveburners, toaster, and coffeemachine as well as cabinets, drawers, shelves, and countertops; do not limit the sweep to cabinets, drawers, and shelves. Open closed containers (drawers, cabinets, fridge) before judging them empty. While any required goal object instance is not in hand, before returning to any location whose contents have already been revealed this episode, choose a listed location that has never been visited. Prioritize unopened or closed containers (drawers, fridge, microwave) and appliance surfaces (stoveburners, toaster, coffeemachine) over any action returning to a location whose contents you have already observed. Treat the first reveal of a location's contents as its inspection: if the required object is absent, do not re-select that location while any never-visited listed location remains. An inventory or look action confirming you hold nothing, or opening an empty cabinet or drawer, does not justify restarting the sweep; treat it as evidence to continue to the next unvisited location. Travel to an appliance to clean/heat/cool an object in hand, or to the goal receptacle to deliver, is progress and is not a search re-visit. As soon as an instance is acquired, pause the sweep and go directly to any required transform and delivery. For a two-instance task, placing the first instance does not finish the search: after delivery, if the second instance was already observed at a location, go directly there; otherwise resume the sweep of never-visited listed locations. Exit this search preference only when all required instances have been found and handled as required; if every listed location has been inspected and the object is still missing, only then consider a revisit.
3. **Grab immediately**: When a required object is visible and reachable, take it right away before moving elsewhere.
4. **Transform before placing**: If the task requires cleaning, heating, or cooling, perform the state change at the appropriate appliance before heading to the final destination.
5. **Direct delivery**: Once holding the transformed (or untransformed) goal object, navigate straight to the target receptacle and place it.
6. **Track progress**: Maintain an internal count of how many objects still need to be found and placed. Only stop searching when the count reaches zero.
7. **Avoid loops**: Never repeat the same action more than twice in a row. If stuck, move to a different unexplored location.
8. **Only choose admissible actions**: Always pick an action from the admissible action list. Do not invent actions.

---

## Common Mistakes to Avoid

- **Revisiting searched locations before the sweep is complete**: Keep track of which surfaces/containers have been checked; while any never-visited listed location remains, do not re-examine them. Consider a revisit only after every listed location has been inspected and the required object is still missing.
- **Ignoring visible objects**: If the target object appears in the observation, pick it up immediately.
- **Skipping state changes**: Do not place an object at the destination without first cleaning/heating/cooling it when required.
- **Premature termination**: Do not stop the episode until all goal conditions are verified as met.
- **Action loops**: Repeatedly toggling or examining the same object wastes steps. Move on to new locations instead.

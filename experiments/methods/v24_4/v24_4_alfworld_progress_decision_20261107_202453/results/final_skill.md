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
6. **Track progress**: Maintain an internal count of how many objects still need to be found and placed. Only stop searching when the count reaches zero.
7. **Avoid loops**: Never repeat the same action more than twice in a row. If stuck, move to a different unexplored location.
8. **Only choose admissible actions**: Always pick an action from the admissible action list. Do not invent actions.

## Locating the Goal Object

While the requested object has not yet been located, treat every search decision as follows:

- Choose a listed receptacle you have not yet visited before any receptacle you have already inspected, except when a previously inspected surface or open container is known to still hold a required goal instance; in that case, return to take that instance immediately even if unvisited receptacles remain.
- On arrival, open the receptacle if it is closed, then check whether the requested object is visible; if it is, take it immediately.
- Among unvisited receptacles, prefer the type that plausibly contains the target: for a food item such as bread, prefer diningtable, shelves, countertops, or fridge; for a small utensil, prefer drawers or diningtable; for cookware, prefer cabinets, countertops, or stoveburners. Check the remaining unvisited instances of that plausible type before switching to a less promising type, except as required by the consecutive-empty sampling rule below.
- **Consecutive-empty sampling**: While the requested object is still missing, count consecutive inspections of unvisited receptacles of one type that reveal no requested object. If the current type has more than three listed instances and three consecutive unvisited instances of it show no requested object, the next move must be to an unvisited receptacle of a different type that is available in the current observation or admissible action list - for example, a cabinet or countertop instead of a drawer, or a shelf, sinkbasin, toilet, or garbagecan instead of a cabinet. This sampling takes precedence over the general preference for finishing the plausible type first, even when unvisited instances of the original type remain. Open the alternative if it is closed and inspect it; if the requested object appears, take it immediately and continue with any required cleaning, heating, or cooling and the final delivery. If it does not appear, resume searching; after three more empty same-type inspections, sample another unvisited type again, alternating until the object is found. Never return to an already-inspected receptacle that showed only non-target contents; the only permitted return is to a surface or open container known to still hold a required goal instance.
- While any required goal instance is still missing, distinguish a previously inspected receptacle that is known to still hold a remaining required instance from one that shows only previously seen non-target contents. If a surface or open container is known to still hold a required instance, go back to it and take that instance immediately, even if unvisited receptacles remain, then deliver it. Otherwise, skip a return to an already-open container that shows only the same non-target contents; continue through the remaining unvisited instances of the current plausible receptacle type, subject to the consecutive-empty sampling rule above, and once that type is fully swept without finding the needed instance, try unvisited instances of other listed receptacle types or regions. Do not cycle back through inspected non-target receptacles; stop searching only when the required count of exact goal objects has been placed.

Once the object is found, resume the normal sequence: acquire it, apply the required treatment if any, then deliver it to the destination.

---

## Common Mistakes to Avoid

- **Revisiting searched locations**: Keep track of which surfaces/containers have been checked. Do not re-examine a receptacle that showed only non-target contents; however, return to an inspected surface or open container that is known to still hold a required goal instance and take it.
- **Ignoring visible objects**: If the target object appears in the observation, pick it up immediately.
- **Skipping state changes**: Do not place an object at the destination without first cleaning/heating/cooling it when required.
- **Premature termination**: Do not stop the episode until all goal conditions are verified as met.
- **Action loops**: Repeatedly toggling or examining the same object wastes steps. Move on to new locations instead.

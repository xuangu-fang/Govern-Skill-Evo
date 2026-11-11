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
9. **Check the destination early**: The stated destination is a valid search location before delivery. If the target is not yet found and the exact named destination (for example, a shelf, drawer, cabinet, fridge, or diningtable) has not been inspected, include it in the search frontier and inspect it once; if the target is not there, remember it for the final placement rather than ruling it out. This is especially worth doing before an exhaustive sweep of many same-type containers.
10. **Maintain a search frontier**: While any required object is not in hand (and, in a two-instance task, again after the first instance is delivered), keep an explicit list of locations not yet visited or opened. Count a location as searched once you arrive and its contents are shown, including when it is empty, or once you open a closed container and see its contents; open closed containers before judging them empty. After any observation shows the required object absent, select the next search target from the unvisited or unopened locations. Do not choose a location already searched, and do not return to an already visited destination merely to recheck it, while any unvisited location remains. If the exact named destination is still unvisited, inspect it once as the destination-early preference above suggests; that is a frontier visit, not a forbidden return. When several unvisited locations remain, any of them may be chosen; the requirement is only to avoid searched locations until the unvisited frontier is exhausted. If the frontier is exhausted, re-read the goal and choose a different receptacle type or room rather than cycling. This rule governs search-target choice only: it never blocks taking a visible required object, opening the next unvisited container, going to an appliance or receptacle already seen to perform a required clean/heat/cool on a held object, or returning to the destination to deliver a held object. For two required instances, take and deliver a visible instance immediately, then resume frontier search for the remaining instance; a later delivery of that instance to the destination is allowed and is not a forbidden recheck of an emptied container. Once the required object is in hand and its transform or delivery is due, drop the frontier rule and follow normal transform and delivery guidance.

---

## Common Mistakes to Avoid

- **Revisiting searched locations**: Keep track of which surfaces/containers have been checked; do not re-examine them.
- **Ignoring visible objects**: If the target object appears in the observation, pick it up immediately.
- **Skipping state changes**: Do not place an object at the destination without first cleaning/heating/cooling it when required.
- **Premature termination**: Do not stop the episode until all goal conditions are verified as met.
- **Action loops**: Repeatedly toggling or examining the same object wastes steps. Move on to new locations instead.

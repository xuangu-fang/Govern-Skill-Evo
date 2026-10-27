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

---

## Locate Phase Search

This section governs the **locate phase** of any task: while the object required by the task description has not yet been acquired (not held, and not visible/reachable in the current observation). It ends as soon as the object is acquired, and it does not restrict returning to a location later for transformation or for placing an object.

**Coverage**
- Do not treat failure to find the object in the container category inspected so far (e.g., cabinets, or shelves) as evidence that it is absent from the room; the search is unfinished, not disproven.
- When the current receptacle does not contain the required object, advance to a location you have not yet inspected: finish the remaining uninspected instances of the current receptacle category (for example, continue to the next unopened cabinet), and only then move to a not-yet-inspected category (for example, after sweeping the cabinets, inspect drawers, the fridge, countertops, additional shelves, and appliance surfaces offered by the admissible action list).
- While any uninspected location remains, do not return to a location whose visible contents you have already observed without the target.
- Whenever you arrive at a closed container that is admissible to open (drawer, cabinet, fridge, microwave), open it and inspect its contents before leaving; never treat a closed container as empty, and never skip an unopened container in favor of re-inspecting an opened one.
- If your recall of coverage is uncertain, treat your most recent recorded steps as the reliable reference: choose a location that does not appear among them (at minimum, never the location you just left), and default to opening any closed container you reach instead of repeating one you have already observed.

**Anti-cycle**
- While the required object is still not held, treat heading back toward a location you just occupied (for example, leaving A for B and then returning toward A) or cycling among a small set of already-inspected locations as a signal that you are looping, even before a destination is repeated.
- In that situation, do not continue the cycle: choose a destination that does not appear in your most recent observation/action pairs and, at minimum, is not the location you just left, preferring a location of a receptacle category different from the one you are cycling through.
- Do not spend the search phase re-entering locations whose visible contents you have already observed without the target; a repeated return is justified only to open a not-yet-opened container or to deliver an object.

**Exit**
- As soon as the required object is visible and reachable, take it immediately and leave the locate phase; then perform any required transformation at the appropriate appliance and place the object at the specified destination. Do not keep searching after the object is acquired. Once the object is acquired, stop applying the anti-cycle rule and proceed to transformation and delivery.

---

## Common Mistakes to Avoid

- **Revisiting searched locations**: Keep track of which surfaces/containers have been checked; do not re-examine them.
- **Ignoring visible objects**: If the target object appears in the observation, pick it up immediately.
- **Skipping state changes**: Do not place an object at the destination without first cleaning/heating/cooling it when required.
- **Premature termination**: Do not stop the episode until all goal conditions are verified as met.
- **Action loops**: Repeatedly toggling or examining the same object wastes steps. Move on to new locations instead.

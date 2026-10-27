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
2. **Systematic exploration**: Search each surface and container exactly once before revisiting. Open closed containers (drawers, cabinets, fridge) before judging them empty. When the goal object has not been found on any surface or container already observed, prefer not-yet-inspected locations — the remaining unopened closed containers (cabinets, drawers, fridge) and surfaces not yet observed — over returning to open surfaces or containers already observed empty. In particular, if the closed fridge has not yet been opened, go to the fridge and open it before falling back to any repeated location. Choose the next destination from the admissible action list so that it is a location not yet inspected in this search rather than one you have already seen to be empty.
3. **Grab immediately**: When a required object is visible and reachable, take it right away before moving elsewhere.
4. **Transform before placing**: If the task requires cleaning, heating, or cooling, perform the state change at the appropriate appliance before heading to the final destination. When holding the required object at the appropriate appliance, apply the transform directly to the held object with the appliance command (for example, clean X with sinkbasin 1, cool X with fridge 1, heat X with microwave 1); it is not necessary to first move the object into the appliance. Do not idle by cycling the appliance open and closed: if the transform has not yet been applied, issue the transform command instead of toggling the appliance. The state change must be completed before the object is delivered to the target receptacle.
5. **Direct delivery**: Once holding the transformed (or untransformed) goal object, navigate straight to the target receptacle and place it.
6. **Track progress**: Maintain an internal count of how many objects still need to be found and placed. Only stop searching when the count reaches zero.
7. **Avoid loops and repeated travel**: Never repeat the same action more than twice in a row. If recent observations already showed that a location you are about to revisit contained no new object, do not return there; instead select an admissible destination that expands coverage — an unopened closed container (especially the fridge) or a not-yet-observed surface. If no not-yet-inspected location is available, choose an admissible destination other than the one you just visited, so that the search does not cycle among the same few sites. A single necessary revisit to retrieve a held object or to apply a transform is allowed.
8. **Only choose admissible actions**: Always pick an action from the admissible action list. Do not invent actions.

---

## Common Mistakes to Avoid

- **Revisiting searched locations**: Keep track of which surfaces/containers have been checked; do not re-examine them.
- **Ignoring visible objects**: If the target object appears in the observation, pick it up immediately.
- **Skipping state changes**: Do not place an object at the destination without first cleaning/heating/cooling it when required.
- **Premature termination**: Do not stop the episode until all goal conditions are verified as met.
- **Action loops**: Repeatedly toggling or examining the same object wastes steps. Move on to new locations instead.

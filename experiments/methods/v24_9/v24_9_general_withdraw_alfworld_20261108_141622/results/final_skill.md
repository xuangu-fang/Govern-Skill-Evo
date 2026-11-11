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

9. **Search order when a still-needed target remains**: During search while a still-needed target instance has not yet been found, keep a checked set of receptacles whose contents you have observed; for a closed container, open it before marking it checked or moving on. After any arrival or examination that shows no still-needed target, do not choose a checked receptacle while any listed receptacle remains unchecked. Prefer unchecked open/visible surfaces (such as countertops, diningtables, shelves, sinkbasin, bed, sidetable, or already-open containers) before unchecked closed containers; if the current observation indicates the target is in a particular unchecked closed container, open that container next. Once the open surfaces are exhausted, take the remaining unchecked closed cabinets, drawers, or other closed containers in a consistent order such as ascending number, opening each before judging it and moving on. Return to a checked location only when the task requires interacting with a known object or appliance there (for example delivering the goal object, using a previously observed desklamp or appliance, or retrieving a second required instance already seen), or when a new observation gives a specific reason. Exit this search preference as soon as a still-needed target appears: take it if not already carrying a required object; if carrying one, remember its location and return after placing the first. Then complete any required transform or delivery. For Pick Two, after placing the first instance, resume the same checked-set preference for the remaining required instance until the required number has been placed. If every listed receptacle has been checked once and a still-needed target remains, re-evaluate the list or make a new observation rather than replaying the same go-to circuit.

---

## Common Mistakes to Avoid

- **Revisiting searched locations**: Keep track of which surfaces/containers have been checked; do not re-examine them.
- **Ignoring visible objects**: If the target object appears in the observation, pick it up immediately.
- **Skipping state changes**: Do not place an object at the destination without first cleaning/heating/cooling it when required.
- **Premature termination**: Do not stop the episode until all goal conditions are verified as met.
- **Action loops**: Repeatedly toggling or examining the same object wastes steps. Move on to new locations instead.

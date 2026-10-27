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
2. **Systematic exploration**: Treat each surface and container as exhausted once observed without the goal object; revisit a location only when no untried location remains. Open closed containers (drawers, cabinets, fridge) before judging them empty.
3. **Grab immediately**: When a required object is visible and reachable, take it right away before moving elsewhere.
4. **Transform before placing**: If the task requires cleaning, heating, or cooling, perform the state change at the appropriate appliance before heading to the final destination.
5. **Direct delivery**: Once holding the transformed (or untransformed) goal object, navigate straight to the target receptacle and place it.
6. **Track progress**: Maintain an internal count of how many objects still need to be found and placed. Only stop searching when the count reaches zero.
7. **Avoid loops**: Never repeat the same action more than twice in a row. If stuck, move to a different unexplored location.
8. **Only choose admissible actions**: Always pick an action from the admissible action list. Do not invent actions.

---

## Search Strategy (Before Acquiring the Goal Object)

- Treat a location that has just been observed without the goal object as exhausted. Do not immediately return to it, and do not restart a numbered sequence of similar locations after reaching its end while another untried location remains available.
- Sweep similar numbered locations consecutively. When a sequence ends and the admissible navigation commands offer a different untried location type, choose that different type instead of cycling back to an exhausted surface.
- Do not navigate to a location that recent history or the current observation shows was already observed without the goal object while an unobserved admissible location remains available. Continuing a consecutive sweep of previously unobserved numbered locations of the same type is allowed.
- When an `open` action is admissible for a closed container, open it before judging it empty, then continue the sweep.
- If the goal object is visible at the current location, take it immediately. Once it is acquired, stop searching and go directly to the required destination or transformation step without additional exploratory stops. In examine/look-under-desklamp tasks, movement needed to find and reach the required desklamp is part of the required transformation navigation, not an additional goal-object search stop; follow the examine-specific desklamp guidance.

## Examine-in-Light (Desklamp) Tasks

- After taking the specified object, if a desklamp is visible at the current location, use that desklamp immediately. Do not leave the location or move the object to another surface first.
- If no desklamp is visible, move to a different location from the admissible commands. Do not return to the location where the object was acquired if it showed no desklamp, and do not recheck a location that recent history or the current observation shows lacked a desklamp while another untried location remains available.
- Use the desklamp as soon as it appears in the current observation. Holding the target object is sufficient; no additional object relocation is required before using it.

## Common Mistakes to Avoid

- **Revisiting searched locations**: Keep track of which surfaces/containers have been checked; do not re-examine them.
- **Ignoring visible objects**: If the target object appears in the observation, pick it up immediately.
- **Skipping state changes**: Do not place an object at the destination without first cleaning/heating/cooling it when required.
- **Premature termination**: Do not stop the episode until all goal conditions are verified as met.
- **Action loops**: Repeatedly toggling or examining the same object wastes steps. Move on to new locations instead.

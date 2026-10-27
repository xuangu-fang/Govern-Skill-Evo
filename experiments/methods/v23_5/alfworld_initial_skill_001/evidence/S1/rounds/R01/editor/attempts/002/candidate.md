# ALFWorld Embodied Agent Skill

## Overview
This skill guides agents operating in the ALFWorld text-based embodied environment.
The agent must complete household tasks by navigating rooms, interacting with objects,
and using appliances. Actions must be chosen from the admissible action list provided
at each step.

**Output format**: Always output `<think>...</think>` for reasoning, then `<action>...</action>` for the chosen action.

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

## Search Phase Strategy

During the locate phase of a pick-and-place or examine task, use your last two observations and actions as working memory:

- If the current location does not hold the required object, do not move next to a location that your recent history shows was already examined without the required object. Prefer an admissible location that is not present in that recent history.
- Open a closed container at the current location before leaving it (when an `open` action for it is admissible), and check its contents immediately rather than planning to return to it later.
- When several similar locations are available, go through them in a consistent order (e.g., ascending index). Prefer the next similar location not present in your recent history before switching to a different kind of location, and do not bounce back to a similar location your recent history shows was just checked, so the same surfaces are not swept again.
- Do not change the target object or stop the search merely because several locations were empty. Continue until the required object is in your inventory, then leave the search phase.

## Examine Tasks: Using the Desklamp

In examine and 'look at X under the desklamp' tasks, once the target object is in your inventory the remaining objective is to activate a desklamp while holding it.

- If a desklamp is present at your current location, use it immediately without any further navigation.
- If not, do not remain at or return to a location that your last two observations/actions show was already checked without a desklamp. Choose an admissible location not present in that recent history, and use the first desklamp that appears in the current observation. Avoid repeated movement between the same locations when the lamp is not co-located.

---

## Common Mistakes to Avoid

- **Revisiting searched locations**: Keep track of which surfaces/containers have been checked; do not re-examine them.
- **Ignoring visible objects**: If the target object appears in the observation, pick it up immediately.
- **Skipping state changes**: Do not place an object at the destination without first cleaning/heating/cooling it when required.
- **Premature termination**: Do not stop the episode until all goal conditions are verified as met.
- **Action loops**: Repeatedly toggling or examining the same object wastes steps. Move on to new locations instead.

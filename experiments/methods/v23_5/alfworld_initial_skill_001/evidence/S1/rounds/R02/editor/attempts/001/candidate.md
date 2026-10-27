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
2. **Forward search**: During the locate/acquire search phase, when the required object is not visible, make forward progress through the room's listed locations instead of re-entering locations you have already inspected. If the current location has a closed container, or an available open/examine interaction whose contents are not shown, open or examine it before leaving. When choosing the next move, advance in the order of the admissible "go to" list, skipping any destination that is the location you just came from or one of the two most recent destinations in your visible history. Rely on this forward sweep for coverage rather than reconstructing visits from earlier than your visible history. Continue until the target object (or all required instances) is located; do not spend consecutive steps re-entering the same inspected locations while listed destinations or closed containers remain uninspected.
3. **Stop searching and grab**: Once the target object is found, stop searching for it. If it is visible and reachable, take it immediately before moving elsewhere.
4. **Transform before placing**: If the task requires cleaning, heating, or cooling, perform the state change at the appropriate appliance before heading to the final destination.
5. **Direct delivery**: Once holding the transformed (or untransformed) goal object, navigate straight to the target receptacle and place it.
6. **Track progress**: Maintain an internal count of how many objects still need to be found and placed. Only stop searching when the count reaches zero.
7. **Avoid loops and failed repeats**: Never repeat the same action more than twice in a row. If an action yields "Nothing happens", it was not executed: do not repeat that same action; immediately choose a different admissible action, preferring a container-opening or movement option that has not just failed. If stuck, move to a different unexplored location.
8. **Use current admissible actions**: Choose actions only from the current admissible action list at each step; an action that was admissible earlier may no longer be listed, so re-check the current list before selecting a command. Do not invent actions.

---

## Common Mistakes to Avoid

- **Revisiting searched locations**: Do not re-enter locations you have already inspected while listed destinations or closed containers remain uninspected; let the forward "go to" sweep guide coverage within your visible history.
- **Ignoring visible objects**: If the target object appears in the observation, pick it up immediately.
- **Skipping state changes**: Do not place an object at the destination without first cleaning/heating/cooling it when required.
- **Premature termination**: Do not stop the episode until all goal conditions are verified as met.
- **Action loops**: Repeatedly toggling or examining the same object wastes steps. Move on to new locations instead.

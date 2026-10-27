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
2. **Systematic exploration**: During the search phase for a still-missing required object or tool, treat each surface and container as visited at most once per search pass. For a container that is already open and was not opened by your immediately preceding action, inspect only its currently shown contents; if the required object or tool is visible there, take it immediately when takeable (or use it when the task requires), and otherwise do not re-open it or linger. Open closed containers (drawers, cabinets, fridge) before judging them empty. If the current or immediately preceding observation shows another already-open or empty container of the same furniture type, prefer a different furniture type whose contents have not just been shown; otherwise move to a closed container whose contents have not yet been shown or to a different furniture type. Do not complete or repeat a cycle through containers that recent observations show are open or empty.
3. **Grab immediately**: When a required object or takeable tool is visible and reachable, take it right away before moving elsewhere; when a required fixed tool is visible, use it when the task requires. Once the required object is acquired, stop searching and go directly to the required next location—the desklamp for examine tasks, the appropriate appliance for clean/heat/cool tasks, or the destination receptacle for pick-and-place—without further search moves.
4. **Transform before placing**: If the task requires cleaning, heating, or cooling, perform the state change at the appropriate appliance before heading to the final destination.
5. **Direct delivery**: Once holding the transformed (or untransformed) goal object, navigate straight to the target receptacle and place it.
6. **Track progress**: Maintain an internal count of how many objects still need to be found and placed. Only stop searching when the count reaches zero.
7. **Avoid search loops**: Never repeat the same action more than twice in a row. While a required object or tool is still missing, do not return to a location or furniture type that the current observation or the last two observation/action pairs show you have just checked without finding it. If recent observations show you are cycling among the same locations or among already-open or empty containers of one furniture type, stop that cycle and choose a different furniture type or location from the admissible actions (such as a sidetable, dresser, coffeetable, armchair, sofa, bed, or garbagecan) whose contents have not just been shown. Otherwise continue through distinct locations, including closed containers whose contents are not currently shown; prefer a location or furniture type not shown in the current observation or the last two observation/action pairs, and do not choose another same-type container when recent observations already show a same-type cycle. Do not re-enter the same limited subset of locations repeatedly. This search rule does not apply once you are carrying the required object and are looking for the placement receptacle.
8. **Only choose admissible actions**: Always pick an action from the admissible action list. Do not invent actions.

---

## Common Mistakes to Avoid

- **Revisiting searched locations**: Keep track of which surfaces/containers have been checked; do not re-examine them.
- **Ignoring visible objects**: If the target object appears in the observation, pick it up immediately.
- **Skipping state changes**: Do not place an object at the destination without first cleaning/heating/cooling it when required.
- **Premature termination**: Do not stop the episode until all goal conditions are verified as met.
- **Action loops**: Repeatedly toggling or examining the same object wastes steps. Move on to new locations instead.

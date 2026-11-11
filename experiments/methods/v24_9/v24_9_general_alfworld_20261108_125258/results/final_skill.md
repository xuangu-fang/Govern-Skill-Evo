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

## Unvisited-Location Preference

Maintain a searched/visited set from each observation: record locations you have observed or visited, and mark a container or surface exhausted when you inspect it and see no required object or appliance. At each step, identify the next required subgoal: if the goal object is not held, find it; if it is held and the task requires cleaning, heating, cooling, or examining, reach the required sink, microwave, fridge, or desklamp; otherwise deliver it to the final receptacle when the task requires delivery.

While that required subgoal is not yet at a known location and at least one admissible location has never been observed in this episode, do not navigate to an already observed location unless the required object or appliance is known to be there or the current required subgoal is final delivery to that target. After observing a location and not seeing the required object or appliance, mark it exhausted even if it holds unrelated distractor objects, and do not navigate back to it merely because those other items were present. Prefer any never-observed admissible location, and do not commit to finishing a numbered cabinet, drawer, or shelf bank before trying an unvisited location of another type. If you do continue within a bank you have already started, go to the next never-observed member in ascending index order from a recorded resume cursor, never restarting that bank at its first member; this ascending-order rule is only a within-bank tie-break and never overrides an unvisited location of another type. For example, choose an unvisited shelf or sidetable instead of a searched drawer, an unvisited armchair instead of a searched coffeetable, or an unvisited shelf instead of a searched desk. Even when the goal object is already held, if a required appliance is still unfound, choose an unvisited location rather than returning to a searched desk.

End this preference when the next required subgoal is known and you are navigating to it, when the required transformation or examination is complete and only final delivery remains, when no unvisited location remains, or when all admissible locations have been checked. Preserve Pick Two counting: after placing the first object, resume the same unvisited-location preference to find the remaining instance, and after finding it go directly to the final target.

---

## Common Mistakes to Avoid

- **Revisiting searched locations**: Keep track of which surfaces/containers have been checked; do not re-examine them.
- **Ignoring visible objects**: If the target object appears in the observation, pick it up immediately.
- **Skipping state changes**: Do not place an object at the destination without first cleaning/heating/cooling it when required.
- **Premature termination**: Do not stop the episode until all goal conditions are verified as met.
- **Action loops**: Repeatedly toggling or examining the same object wastes steps. Move on to new locations instead.

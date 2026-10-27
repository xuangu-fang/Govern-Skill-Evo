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
2. **Systematic exploration**: While the goal object has not been found, choose the next destination only from the current admissible location list, and do not return to a location whose contents are already known from the current observation or the recent observation/action history; treat any such revealed location as already checked. Prefer locations whose contents you have not yet seen, and cover both kinds of unchecked location: do not skip an uninspected open surface (countertop, diningtable, shelf, stoveburner, sinkbasin) in order to open more closed containers, and do not treat a closed container (cabinet, drawer, fridge) as empty until you have opened it.
3. **Grab immediately**: When the required object is visible and reachable, stop searching and take it right away before moving elsewhere. The search guidance in principle 2 applies only while the object has not been found; once you hold it, revisiting an already checked location for the transformation or delivery step is allowed.
4. **Transform before placing**: If the task requires cleaning, heating, or cooling, go to the appropriate appliance while holding the goal object and apply the transformation directly to the held object, rather than depositing the object into the appliance first. For heat tasks, heat the object in hand at the microwave; do not move it into the microwave or cycle the microwave door open and closed. For cleaning and cooling, perform clean/cool on the held object at the sink or fridge and then deliver it directly.
5. **Direct delivery**: Once holding the transformed (or untransformed) goal object, navigate straight to the target receptacle and place it.
6. **Track progress**: Maintain an internal count of how many objects still need to be found and placed. Only stop searching when the count reaches zero.
7. **Avoid loops**: Never repeat the same action more than twice in a row. If the recent history shows movement cycling among the same small set of locations (for example repeatedly alternating between two countertops and the fridge) while none contained the object, recognize this as a search loop and choose a destination outside that set. Because the full set of visited locations is not retained, base this choice on the current admissible location list together with the current and most recent observations, and keep expanding to unchecked locations rather than abandoning or restarting the search while the list still offers locations with unknown contents.
8. **Only choose admissible actions**: Emit an action only when its exact text appears in the current admissible action list; a location that exists in the room may still be absent from that list, and such an action produces no state change and wastes a step. After an action yields no change (e.g. "Nothing happens"), do not repeat the same or a similar guess; re-read the current admissible list and choose a listed action instead. Do not invent actions.

---

## Common Mistakes to Avoid

- **Revisiting searched locations**: While the goal object is still missing, do not re-examine a location whose contents are already known from the current observation or recent history, and do not cycle among a few known-empty locations; keep expanding to unchecked locations instead.
- **Ignoring visible objects**: If the target object appears in the observation, pick it up immediately.
- **Skipping state changes**: Do not place an object at the destination without first cleaning/heating/cooling it when required.
- **Premature termination**: Do not stop the episode until all goal conditions are verified as met.
- **Action loops**: Repeatedly toggling or examining the same object wastes steps. After an action yields no change (e.g. "Nothing happens"), do not repeat the same or a similar guess; re-read the admissible list and choose a listed action or a new destination instead.

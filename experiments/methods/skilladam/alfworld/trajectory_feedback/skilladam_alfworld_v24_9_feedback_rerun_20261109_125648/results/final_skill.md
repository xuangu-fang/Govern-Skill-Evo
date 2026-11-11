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
| Pick Two & Place | Put two instances of X in/on Y | Find & take X1 -> place X1 -> return to where a second X was already seen (or expand to new unvisited locations if none was seen) -> take X2 -> place X2. Never leave a visible second instance behind unnoticed. |
| Examine in Light | Examine object X under desklamp | Find X -> take X -> find desklamp -> use desklamp |
| Clean & Place | Clean object X and put in/on Y | Find X -> take X -> go to sink -> clean X -> go to Y -> put X |
| Heat & Place | Heat object X and put in/on Y | Find X -> take X -> go to microwave -> heat X -> go to Y -> put X |
| Cool & Place | Cool object X and put in/on Y | Find X -> take X -> go to fridge -> cool X -> go to Y -> put X |

---

## General Principles

1. **Decompose the task**: Parse the goal into ordered sub-goals (locate, acquire, transform, deliver). Complete each before moving to the next.
2. **Systematic exploration — exhaust unchecked locations first**: Keep a running mental list of receptacles already checked versus not yet checked. Before re-opening or re-examining any location, move to one you have never visited. Open closed containers (drawers, cabinets, fridge) before judging them empty. If several checked receptacles have not yielded the target, do not loop back — expand outward to new furniture types and rooms (sidetable, armchair, coffeetable, shelf, dresser, countertop) until every plausible surface has been visited once.
3. **Grab the exact object immediately**: When the goal object is visible and reachable, take it right away before moving elsewhere — but first confirm it matches the goal noun exactly rather than a similar look-alike (a pen is not a pencil, adjacent cd instances are not interchangeable, and a soapbar is not a soapbottle).
4. **Transform before placing**: If the task requires cleaning, heating, or cooling, perform the state change at the appropriate appliance before heading to the final destination.
5. **Direct delivery — place on arrival**: Once holding the transformed (or untransformed) goal object, navigate straight to the target receptacle and place the object there the moment you arrive. Do not leave the destination to explore elsewhere, and never deposit the goal object in a different receptacle than the one named in the goal.
6. **Track progress and remember sightings**: Maintain an internal count of how many objects still need to be found and placed, and only stop when the count reaches zero. For multi-object goals, also remember every location where you have already seen a remaining instance: after delivering the first object, return to a known spot for the second rather than searching blindly; if you have not yet seen a second instance, expand to new unvisited locations instead of re-checking old ones.
7. **Break search loops by expanding to fresh receptacles**: While searching for a target, treat every receptacle you have already checked as done and never re-check it — each next search step must go to a drawer, cabinet, surface, or furniture type you have not examined yet. If an observation repeats contents you have already seen, you are looping: stop and open a receptacle you have not opened before, then keep sweeping new drawers, cabinets, surfaces, and furniture until the target appears. Returning to an already-checked spot is allowed only to fetch a second instance you already saw there, or to use it as the goal destination or transform appliance.
8. **Only choose admissible actions**: Always pick an action from the admissible action list. Do not invent actions.

---

## Common Mistakes to Avoid

- **Revisiting searched locations**: Keep track of which surfaces/containers have been checked; do not re-examine them.
- **Ignoring visible objects**: If the target object appears in the observation, pick it up immediately.
- **Skipping state changes**: Do not place an object at the destination without first cleaning/heating/cooling it when required.
- **Premature termination**: Do not stop the episode until all goal conditions are verified as met.
- **Action loops**: Repeatedly toggling or examining the same object wastes steps. Move on to new locations instead.

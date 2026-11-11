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
| Pick Two & Place | Put two instances of X in/on Y | Find a spot with multiple instances of X -> take one -> place it -> return directly to that spot for the second X -> take -> place |
| Examine in Light | Examine object X under desklamp | Find X -> take X -> find desklamp -> use desklamp |
| Clean & Place | Clean object X and put in/on Y | Find X -> take X -> go to sink -> clean X -> go to Y -> put X |
| Heat & Place | Heat object X and put in/on Y | Find X -> take X -> go to microwave -> heat X -> go to Y -> put X |
| Cool & Place | Cool object X and put in/on Y | Find X -> take X -> go to fridge -> cool X -> go to Y -> put X |

---

## General Principles

1. **Decompose the task**: Parse the goal into ordered sub-goals (locate, acquire, transform, deliver). Complete each before moving to the next.
2. **Breadth-first systematic exploration**: Sweep every accessible receptacle exactly once before revisiting any. Cover both surfaces and containers: check every countertop (including higher-numbered ones) and every table (diningtable, sidetable, coffeetable) as well as opening closed containers (fridge, drawers, cabinets, microwave) — targets are often on a table or a later-numbered countertop rather than in a cabinet. If a full pass over one category finds nothing, switch to a different category (drawers, fridge, microwave, shelves, bathtub) instead of re-checking the same spots.
3. **Grab immediately**: When a required object is visible and reachable, take it right away before moving elsewhere.
4. **Transform before placing**: If the task requires cleaning, heating, or cooling, perform the state change at the appropriate appliance before heading to the final destination.
5. **Direct delivery**: Once holding the transformed (or untransformed) goal object, navigate straight to the target receptacle and place it.
6. **Track progress**: Maintain an internal count of how many objects still need to be found and placed. Only stop searching when the count reaches zero. For two-instance tasks, remember any location where you saw more than one instance of the target: after delivering the first, go straight back to that spot to take the second instead of re-searching the room. Do not re-grab and re-place an instance you have already delivered.
7. **Avoid loops**: Check each receptacle at most once per sweep — never re-sweep the same cabinets or countertops multiple times. The moment you notice a repeated location, stop and open one you have not yet inspected. If a complete pass finds nothing, the target is in a container you have not opened or on a surface you have not named; re-read the room for unvisited receptacles rather than repeating the pass.
8. **Only choose admissible actions**: Always pick an action from the admissible action list. Do not invent actions.

---

## Common Mistakes to Avoid

- **Revisiting searched locations**: Track which surfaces/containers have been checked and do not re-examine them within a sweep; cycling the same few spots means the target is elsewhere, so expand to unvisited receptacle types — especially surfaces and tables that are easy to skip.
- **Ignoring visible objects**: If the target object appears in the observation, pick it up immediately.
- **Skipping state changes**: Do not place an object at the destination without first cleaning/heating/cooling it when required.
- **Premature termination**: Do not stop the episode until all goal conditions are verified as met.
- **Action loops**: Repeatedly toggling or examining the same object wastes steps. Move on to new locations instead.

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
2. **Systematic search coverage**: While the required goal object is not held and is not visible at the current location, do not `go to` any location already visited in this run whose contents have not changed since that visit (no object was added, removed, or newly revealed). Instead, choose an admissible command that takes you to an unvisited location. During the first search pass, choose the next destination from an unvisited receptacle category not yet sampled in this run before choosing another location from a category already sampled; this preference applies only among locations not yet visited. Sample one unvisited location from each available category that appears and may contain objects (for example countertop, sinkbasin, shelf, toilet, bathtubbasin, garbagecan, diningtable, fridge, microwave, stoveburner, toaster, coffeemachine, bed, cabinet, or drawer), opening a closed container on arrival and reading its contents. Do not use category coverage to return to an already visited unchanged location or to cycle among sampled categories. Once every available category has been sampled once, continue with the remaining unvisited locations in any category, including the next unvisited cabinet or drawer; if a category has no unvisited location, move to another. Permit a revisit only when that location's state has actually changed (a closed container there was opened, the carried object was just removed from it, or it is the placement destination), or, during a two-instance task, when it is a confirmed second-object location. Exit the search immediately when the goal object is visible or has been acquired: take it if visible, then proceed to any required cleaning, heating, or cooling and then the destination.
3. **Grab immediately**: When a required object is visible and reachable, take it right away before moving elsewhere.
4. **Transform before placing**: If the task requires cleaning, heating, or cooling, perform the state change at the appropriate appliance before heading to the final destination.
5. **Direct delivery**: Once holding the transformed (or untransformed) goal object, navigate straight to the target receptacle and place it.
6. **Track progress**: Maintain an internal count of how many objects still need to be found and placed. Only stop searching when the count reaches zero.
6a. **Two-instance search priority**: During a task that requires two instances of an object, before the first is found and after one has been placed, choose the next search destination by this priority: (1) if you have already observed a second matching object at a known location, go directly to that location and take it; a confirmed second-object location is an allowed early revisit. (2) Otherwise, follow the systematic search rule: choose an admissible `go to` for a receptacle not yet visited in this run, opening it if it is closed, rather than returning to an already-opened drawer, shelf, or other container already shown not to contain the goal object. Do not cycle through unchanged empty containers while any unvisited receptacle, including remaining shelves, dresser, bed, sofa, tvstand, garbagecan, or another sidetable, remains. A previously visited location may be revisited only for the placement destination, for a confirmed second-object location, or when its contents have actually changed as the search rule permits; after every listed receptacle has been visited once, continue checking changed or not-yet-opened locations rather than repeating unchanged empty ones.
7. **Avoid loops**: Never repeat the same action more than twice in a row. If stuck, move to a different unexplored location.
8. **Only choose admissible actions**: Always pick an action from the admissible action list. Do not invent actions.

---

## Common Mistakes to Avoid

- **Revisiting searched locations**: Keep track of which surfaces/containers have been checked; do not re-examine them.
- **Ignoring visible objects**: If the target object appears in the observation, pick it up immediately.
- **Skipping state changes**: Do not place an object at the destination without first cleaning/heating/cooling it when required.
- **Premature termination**: Do not stop the episode until all goal conditions are verified as met.
- **Action loops**: Repeatedly toggling or examining the same object wastes steps. Move on to new locations instead.

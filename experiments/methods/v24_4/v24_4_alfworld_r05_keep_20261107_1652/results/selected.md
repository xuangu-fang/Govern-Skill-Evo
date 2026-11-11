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
2. **Systematic search coverage**: While the goal object is not held and is not visible at the current location, do not choose a `go to` command for any location already visited in this run if its contents have not changed since your most recent inspection of it. Opening a closed container and seeing it empty (or seeing only irrelevant objects) does not license returning to it later; once opened and inspected, treat its contents as known. When a revisit is not allowed, choose an admissible location not yet visited in this run, and open a closed container on arrival before judging it empty. Across the first pass, cover all admissible receptacle kinds—shelves, drawers, fridge, microwave, sinkbasin, diningtable, garbagecan, stoveburners, and toaster, not only countertops and cabinets—so that every admissible location is checked and every closed container is opened once. If recent history shows cycling among the same opened or empty locations, break the cycle by choosing an admissible location not yet visited in this run, including the next unvisited cabinet/drawer index or a different receptacle kind. A previously visited location may be revisited only for a confirmed second-object location in a two-instance task, the final placement destination after acquisition, or when its contents actually changed after your most recent inspection (for example, an object was added or removed after that inspection). Once the goal object is acquired, stop searching and go to any required cleaning, heating, or cooling and then the destination. If no unvisited search location remains, do not repeat unchanged locations; use `inventory` to confirm what you hold and revisit only a required destination or a location whose contents changed after your most recent inspection.
3. **Grab immediately**: When a required object is visible and reachable, take it right away before moving elsewhere.
4. **Transform before placing**: If the task requires cleaning, heating, or cooling, perform the state change at the appropriate appliance before heading to the final destination.
5. **Direct delivery**: Once holding the transformed (or untransformed) goal object, navigate straight to the target receptacle and place it.
6. **Track progress**: Maintain an internal count of how many objects still need to be found and placed. Only stop searching when the count reaches zero.
6a. **Two-instance search priority**: During a task that requires two instances of an object, before the first is found and after one has been placed, choose the next search destination by this priority: (1) if you have already observed a second matching object at a known location, go directly to that location and take it; a confirmed second-object location is an allowed early revisit. (2) Otherwise, follow the systematic search rule: choose an admissible `go to` for a receptacle not yet visited in this run, opening it if it is closed, rather than returning to an already-opened drawer, shelf, or other container already shown not to contain the goal object. Do not cycle through unchanged empty containers while any unvisited receptacle, including remaining shelves, dresser, bed, sofa, tvstand, garbagecan, or another sidetable, remains. A previously visited location may be revisited only for the placement destination, for a confirmed second-object location, or when its contents have actually changed as the search rule permits; after every listed receptacle has been visited once, continue checking changed or not-yet-opened locations rather than repeating unchanged empty ones.
7. **Avoid loops**: Never repeat the same action more than twice in a row. If stuck, move to a different unexplored location.
8. **Only choose admissible actions**: Always pick an action from the admissible action list. Do not invent actions.

## First-Pass Search Alternation

During the first search pass, when several receptacle categories are listed and the goal object is not held or visible, alternate between closed-container searching and visible-content categories rather than making a long same-kind sweep or waiting to sample every category: after sampling one location in a closed-container category (for example a cabinet or drawer), choose an admissible unvisited location from a different category whose contents are visible on arrival (for example countertop, diningtable, shelf, bed, sidetable, sinkbasin, bathtubbasin, toilet, garbagecan, or stoveburner) before opening a second closed container in the same category; after that visible-content sample, return to the next unvisited closed-container index, and repeat this alternation. Open closed containers on arrival and read their contents before judging them empty. If no unvisited visible-content category remains, continue directly through the remaining unvisited closed containers. Never return to an unchanged location; use only unvisited locations or the allowed revisits (a confirmed second-object location in a two-instance task, or the final placement destination once the object is acquired). Exit the search immediately when the goal object is visible or acquired, take it, and proceed to any required treatment and placement.

---

## Common Mistakes to Avoid

- **Revisiting searched locations**: Keep track of which surfaces/containers have been checked; do not re-examine them.
- **Ignoring visible objects**: If the target object appears in the observation, pick it up immediately.
- **Skipping state changes**: Do not place an object at the destination without first cleaning/heating/cooling it when required.
- **Premature termination**: Do not stop the episode until all goal conditions are verified as met.
- **Action loops**: Repeatedly toggling or examining the same object wastes steps. Move on to new locations instead.

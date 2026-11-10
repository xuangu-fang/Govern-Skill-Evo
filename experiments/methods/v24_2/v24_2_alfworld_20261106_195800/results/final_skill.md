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
2. **Systematic exploration without cycles during acquisition**: Until the required goal object is in inventory (for a two-object task, until the required number is collected), keep track of which locations you have inspected. If the current location has already been inspected and does not contain the goal object, do not move next to another location you have already inspected, including an empty countertop, an open empty cabinet, or the opened fridge. Instead, keep searching unvisited locations. When working through a numbered series (cabinet 1, cabinet 2, ...; countertop 1, countertop 2, ...; drawer 1, drawer 2, ...; shelf 1, shelf 2, ...), go to the next number in that same series, opening a closed container when you reach it; otherwise go to an unvisited receptacle from the initial observation. Do not cycle back through a series or receptacle you have already emptied. During acquisition, revisit an inspected location only when a task-relevant state change makes it newly useful, such as an appliance for cleaning, heating, or cooling or the destination for placement; after the goal object has been acquired (or the required number for a two-object task), revisiting inspected locations is permitted as needed. Open closed containers (drawers, cabinets, fridge) before judging them empty.
3. **Grab immediately**: When a required object is visible and reachable, take it right away before moving elsewhere.
4. **Transform before placing**: If the task requires cleaning, heating, or cooling, perform the state change at the appropriate appliance before heading to the final destination.
5. **Direct delivery**: Once holding the transformed (or untransformed) goal object, navigate straight to the target receptacle and place it.
6. **Track progress and consolidate two-object placements**: Maintain an internal count of how many objects still need to be found and placed. Only stop searching when the count reaches zero. For a put-two-X-in/on-Y task, once the first X is acquired, choose one concrete instance of the destination receptacle and place every required X into that same instance. Leave already placed objects there while searching for the remaining X; do not distribute the required objects across different instances of the destination type and do not repeatedly pick up and re-place an already placed object. Consider the placement phase complete only when both required instances are together in the chosen destination.
7. **Avoid loops**: Never repeat the same action more than twice in a row. If stuck, move to a different unexplored location.
8. **Only choose admissible actions**: Always pick an action from the admissible action list. Do not invent actions.

### Food Item Search Order

When the unacquired goal object is a food item (such as bread, apple, egg, potato, tomato, or lettuce) and the initial room listing includes a diningtable, search the diningtable early, before any closed cabinet is opened. If a countertop is listed, check one countertop first, taking the food immediately if it is visible there; otherwise go to the diningtable first. This early diningtable check takes precedence over the general unvisited-container order until the diningtable has been checked. If the food is visible on the current surface or on a countertop you pass, take it immediately instead. If the diningtable does not contain the food, resume checking the remaining countertops and then the other unvisited receptacles, continuing numbered series in order and not returning to already-inspected empty locations while unvisited ones remain. This rule changes only search order; after acquiring the food, still perform any required heating, cooling, or cleaning before delivering it to the goal receptacle.

---

## Common Mistakes to Avoid

- **Revisiting searched locations during acquisition**: Keep track of which surfaces/containers have been checked; while the goal object is still unacquired, do not re-examine an inspected empty location while unvisited locations remain. After acquiring the goal object (or the required number for a two-object task), or when a task-relevant state change makes a location newly useful, revisiting is allowed.
- **Ignoring visible objects**: If the target object appears in the observation, pick it up immediately.
- **Skipping state changes**: Do not place an object at the destination without first cleaning/heating/cooling it when required.
- **Premature termination**: Do not stop the episode until all goal conditions are verified as met.
- **Action loops**: Repeatedly toggling or examining the same object wastes steps. Move on to new locations instead.

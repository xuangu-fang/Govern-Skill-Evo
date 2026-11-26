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
2. **Systematic exploration**: Search by checklist, not by habit: visit each receptacle once, opening closed containers (drawers, cabinets, fridge, microwave) before judging them empty, and alternate closed containers with open surfaces (countertops, tables, shelves, dressers, beds, sofas) and fixtures (sinkbasin, bathtubbasin, garbagecan, toilet) instead of grinding through a dozen cabinets in a row. Order visits by plausibility: food items tend to sit in the fridge, on countertops, or on the dining table, while tableware, utensils and small tools cluster on countertops, shelves, cabinets and desks. When the task needs a cleaning, heating or cooling appliance, open that appliance early in the search — the goal object is often stored inside it and you have to visit it anyway. Cover every receptacle of the current room, then walk to a different room if the target is still missing.
3. **Grab immediately**: When a required object is visible and reachable, take it right away before moving elsewhere.
4. **Transform before placing**: If the task requires cleaning, heating, or cooling, perform the state change at the appropriate appliance before heading to the final destination.
5. **Direct delivery**: Once holding the transformed (or untransformed) goal object, navigate straight to the target receptacle and place it.
6. **Track progress**: Maintain an internal count of how many objects still need to be found and placed. Only stop searching when the count reaches zero.
7. **Avoid search cycles**: Before every move, check the destination against the receptacles you have already searched; if it is on that list, pick an unsearched receptacle instead — an unchanged location cannot teach you anything new. Treat these as hard triggers to change where you look: any container that is empty or already seen, two or more fruitless receptacles in a row, and catching yourself re-checking inventory while carrying nothing. When a trigger fires, jump to an unsearched receptacle; once the room is covered, walk to a new room. Replaying the same loop only ends at the step limit.
8. **Only choose admissible actions**: Always pick an action from the admissible action list. Do not invent actions.

---

## Common Mistakes to Avoid

- **Search and action loops**: Keep track of which surfaces and containers have been checked and never re-examine them; repeatedly toggling or re-opening the same object wastes steps too. Before each move confirm the destination is unsearched, and once the current room is covered, move to a new room rather than replaying the same sweep.
- **Ignoring visible objects**: If the target object appears in the observation, pick it up immediately.
- **Skipping state changes**: Do not place an object at the destination without first cleaning/heating/cooling it when required.
- **Premature termination**: Do not stop the episode until all goal conditions are verified as met.

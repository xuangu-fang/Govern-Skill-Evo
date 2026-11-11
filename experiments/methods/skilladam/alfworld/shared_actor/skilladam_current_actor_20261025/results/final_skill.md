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
2. **Systematic exploration across all receptacle categories**: Track which receptacles exist as you discover them. Scenes hold open furniture surfaces (countertops, dining tables, side tables, shelves, desks, dressers, beds, sofas), storage (cabinets, drawers), and appliance interiors (fridge, microwave). Targets appear on open furniture as often as inside closed storage, so do not treat cabinets and drawers as the whole world. Open closed containers before judging them empty; a location counts as searched only once inspected. Sweep every category once — including every open surface you have seen — before concluding the target is absent, and never re-check a location while an unsearched one remains.
3. **Grab immediately**: When a required object is visible and reachable, take it right away before moving elsewhere.
4. **Transform before placing**: If the task requires cleaning, heating, or cooling, perform the state change at the appropriate appliance before heading to the final destination.
5. **Direct delivery**: Once holding the transformed (or untransformed) goal object, navigate straight to the target receptacle and place it.
6. **Track progress in multi-object tasks**: Maintain an internal count of how many objects still need to be found and placed, and only stop searching when the count reaches zero. Treat each required instance as its own find → take → place cycle: once an object is placed, do not pick it up again — go directly to the next instance, returning to a location where it was already observed whenever possible.
7. **Avoid loops and recognize being stuck**: Never repeat the same action more than twice in a row. Re-checking your inventory, or re-entering the same two or three locations, is the signal that you are stuck: go immediately to a furniture piece of a kind you have not searched at all (a shelf, dining table, bed, sofa, or dresser) rather than another cabinet or drawer.
8. **Only choose admissible actions**: Always pick an action from the admissible action list. Do not invent actions.

---

## Common Mistakes to Avoid

- **Revisiting searched locations**: Keep track of which surfaces/containers have been checked. When you are about to re-enter an already-checked location, stop and go to one you have never visited; continuously cycling the same set means the target is somewhere you have not looked.
- **Ignoring visible objects**: If the target object appears in the observation, pick it up immediately.
- **Skipping state changes**: Do not place an object at the destination without first cleaning/heating/cooling it when required.
- **Premature termination**: Do not stop the episode until all goal conditions are verified as met.
- **Action loops**: Repeatedly toggling or examining the same object wastes steps. Move on to new locations instead.

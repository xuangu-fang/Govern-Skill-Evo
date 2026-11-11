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
2. **Systematic, broad exploration**: During the locate phase, search each candidate surface and container once before revisiting. Judge cleared locations from your current observation and the immediately preceding action/observation pair(s). A container already shown open without the target, a container you arrive at that is already open (opened on an earlier visit), or a surface already shown without the target is cleared; do not choose that location again. Treat an open and empty container or a surface already shown without the target as cleared; return only if a later observation shows a required object there (including the remaining instance in a two-instance task). Instead, choose an admissible go-to command for a location absent from that visible history, preferring locations you have not yet observed. Advance across both container and surface locations without setting a run of closed containers ahead of surfaces; do not exhaust one type or bank (e.g., a long run of cabinets or drawers) before covering the others, and open a closed container when you reach it rather than counting it as already checked. Apply this across the whole candidate set in the admissible list, including storage beyond the current search chain (e.g., bed, dresser, tvstand, sofa, armchair, extra sidetables, garbagecan), not only the first few cabinets, counters, or drawers.
3. **Grab immediately**: When a required object is visible and reachable on arrival, take it right away before moving elsewhere; then proceed through any required transformation to the final delivery.
4. **Transform before placing**: If the task requires cleaning, heating, or cooling, perform the state change at the appropriate appliance before heading to the final destination.
5. **Direct delivery**: Once holding the transformed (or untransformed) goal object, navigate straight to the target receptacle and place it.
6. **Track progress**: Maintain an internal count of how many objects still need to be found and placed. In a two-instance task, after placing the first instance, do not stop or treat the placement as completion; resume searching for the remaining instance. If the location where the first instance was found was last observed still holding another instance, returning there and taking it is valid; otherwise continue to candidate locations not yet observed instead of re-checking locations already shown empty. Only finish when the number of placed instances equals the required count, delivering each instance to the specified receptacle.
7. **Avoid loops**: Never repeat the same action more than twice in a row. If stuck, move to a different unexplored location.
8. **Only choose admissible actions**: Always pick an action from the admissible action list. Do not invent actions.

---

## Common Mistakes to Avoid

- **Revisiting searched locations**: Do not choose a container shown open without the target or a surface already shown without the target again; treat it as cleared unless a later observation shows a required object there (including the remaining instance in a two-instance task).
- **Ignoring visible objects**: If the target object appears in the observation, pick it up immediately.
- **Skipping state changes**: Do not place an object at the destination without first cleaning/heating/cooling it when required.
- **Premature termination**: Do not stop the episode until all goal conditions are verified as met. In a two-instance task, placing the first instance does not complete the task; resume searching for the second and finish only when the placed count equals the required count.
- **Action loops**: Repeatedly toggling or examining the same object wastes steps. Move on to new locations instead.

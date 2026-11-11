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
2. **Search with coverage, not repetition**: The goal object always exists, so a sweep that finds nothing means the sweep was incomplete. Work through one receptacle class at a time, in index order: first the open surfaces (countertop, diningtable, desk, shelf, sidetable, coffeetable, bed, armchair — one look shows everything on them), then the closed containers (drawer, dresser, cabinet, fridge — open before judging empty), then the fixtures (stoveburner, sinkbasin, bathtubbasin, cart, garbagecan). Finish every index of the current class before switching to the next class, and never go back to a receptacle you have already looked in. When a class is exhausted, continue with a class you have not touched at all; a search that circles back over the same few locations can never turn up anything new.
3. **Grab immediately**: When a required object is visible and reachable, take it right away before moving elsewhere.
4. **Transform before placing**: If the task requires cleaning, heating, or cooling, perform the state change at the appropriate appliance before heading to the final destination.
5. **Direct delivery**: Once holding the transformed (or untransformed) goal object, navigate straight to the target receptacle and place it.
6. **Track progress**: Maintain an internal count of how many objects still need to be found and placed. Only stop searching when the count reaches zero. For two-object goals, if a single observation reveals two instances of the goal object, deliver the first and come straight back for the second from that same location, rather than starting a fresh sweep.
7. **Avoid loops**: Never repeat the same action more than twice in a row, and treat alternating cycles (A -> B -> A -> B between two or three locations) as loops as well, even when the locations differ in type. The moment you notice a cycle, go to a location you have never visited; cycling through already-seen locations cannot reveal anything new.
8. **Only choose admissible actions**: Always pick an action from the admissible action list. Do not invent actions.

---

## Common Mistakes to Avoid

- **Revisiting searched locations**: Keep track of which surfaces/containers have been checked; do not re-examine them, and do not re-run a sweep whose locations have all been visited already. If the object is still missing, the answer is a location you have never visited, not a repeat of the old route.
- **Ignoring visible objects**: If the target object appears in the observation, pick it up immediately.
- **Skipping state changes**: Do not place an object at the destination without first cleaning/heating/cooling it when required.
- **Premature termination**: Do not stop the episode until all goal conditions are verified as met.

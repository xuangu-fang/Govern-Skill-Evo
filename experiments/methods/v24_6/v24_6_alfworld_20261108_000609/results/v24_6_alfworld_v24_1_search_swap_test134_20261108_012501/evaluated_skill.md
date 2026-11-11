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
2. **Systematic exploration**: Follow the locate-phase sweep below so each surface and container is checked once before any location is revisited. Open closed containers (drawers, cabinets, fridge) to reveal their contents before judging them empty.
3. **Grab immediately**: When a required object is visible and reachable, take it right away before moving elsewhere.
4. **Transform before placing**: If the task requires cleaning, heating, or cooling, perform the state change at the appropriate appliance before heading to the final destination.
5. **Direct delivery**: Once holding the transformed (or untransformed) goal object, navigate straight to the target receptacle and place it.
6. **Track progress**: Maintain an internal count of how many objects still need to be found and placed. Only stop searching when the count reaches zero.
7. **Avoid loops**: Never repeat the same action more than twice in a row. If stuck, move to a different unexplored location.
8. **Only choose admissible actions**: Always pick an action from the admissible action list. Do not invent actions.

---

## Locate-Phase Search Sweep

This sweep governs only the interval before the required object has been acquired. Once the object appears in the current observation, take it immediately and proceed with any required cleaning, heating, or cooling and then final placement; do not delay acquisition or replace the required state change.

- While the required object is not visible in the current observation and you are not yet carrying it, treat arrival at any location whose contents you have already observed as a repeated visit. Redirect immediately to a location you have not yet inspected instead of re-entering it or shuttling back among the same few locations.
- You cannot keep a persistent visited list, so enforce single-pass coverage using the location name shown in the current observation rather than any remembered or previously supplied list. After arriving at a numbered location such as `cabinet 4`, prefer the next higher-numbered instance of that same type that appears in the current admissible actions (for example, `go to cabinet 5`) over any lower-numbered or earlier one. When no higher-numbered instance of the current type is admissible, treat that numbered series as finished for this pass: do not restart it at a lower-numbered instance, and do not return to an earlier surface or container already observed without the target. Then move to a different location type whose name is not among the most recently observed locations, and prefer any admissible different-type location over a repeat of a recently observed empty location.
- Order the sweep as a quick first pass over open surfaces (such as countertops, tables, shelves, the sinkbasin, beds, dressers, and sidetables), then the closed storage container types (such as drawers, cabinets, the fridge, the microwave, safes, and garbagecans). Open closed containers to reveal their contents. This list is illustrative, not complete: include any admissible room-specific furniture or receptacle that is not named here, placing surface-like locations in the open-surface portion and closed storage in the container portion. Within each type, visit the listed instances in ascending number order.
- Do not stop the sweep early or skip container categories. Continue the forward pass across all admissible location types, including room-specific surfaces and containers (such as beds, dressers, sidetables, safes, and garbagecans) as well as drawers, the fridge, the microwave, and higher-numbered cabinets, until the required object is observed or the forward pass has covered all admissible locations once. When room-specific types remain uninspected, cover them rather than returning to already checked kitchen-style locations.
- The forward-coverage rule above applies while any required instance is still unacquired. After acquiring an instance, perform any required transformation and deliver it rather than continuing to sweep. If another required instance remains unplaced, resume the forward sweep after that delivery, continuing from the next uninspected location in the same surface-before-container, ascending-instance order instead of restarting from lower-numbered or early already-seen locations. A previously observed location may be revisited only when it was seen to still contain an additional instance of the target type.

---

## Common Mistakes to Avoid

- **Revisiting searched locations before the sweep is complete**: Keep track of which surfaces/containers have been checked; while any never-visited listed location remains, do not re-examine them. Consider a revisit only after every listed location has been inspected and the required object is still missing.
- **Ignoring visible objects**: If the target object appears in the observation, pick it up immediately.
- **Skipping state changes**: Do not place an object at the destination without first cleaning/heating/cooling it when required.
- **Premature termination**: Do not stop the episode until all goal conditions are verified as met.
- **Action loops**: Repeatedly toggling or examining the same object wastes steps. Move on to new locations instead.

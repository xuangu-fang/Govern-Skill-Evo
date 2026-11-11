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
| Pick Two & Place | Put two instances of X in/on Y | Find X1 -> take -> place at Y -> find X2 -> take -> place at the same Y |
| Examine in Light | Examine object X under desklamp | Find X -> take X -> find desklamp -> use desklamp |
| Clean & Place | Clean object X and put in/on Y | Find X -> take X -> go to sink -> clean X -> go to Y -> put X |
| Heat & Place | Heat object X and put in/on Y | Find X -> take X -> go to microwave -> heat X -> go to Y -> put X |
| Cool & Place | Cool object X and put in/on Y | Find X -> take X -> go to fridge -> cool X -> go to Y -> put X |

### Two-Instance Placement

When the goal requires two instances of the same object in/on a receptacle, keep a single destination receptacle: after the first instance is placed, leave it there and deliver the second instance to that same receptacle.

Once the first instance is visible at a receptacle and the second instance is still undelivered, protect the first instance: do not choose `take` for it. If you are not holding the second instance, leave the first there. If the second instance is visible in the current observation, take it; otherwise choose an admissible `go to` or `open` search action to acquire it (if no search action is admissible, use the best remaining admissible action).

When you hold the second instance and the first instance is visible in the current observation at a receptacle, choose the `move`/`put` command for that same receptacle; if you are not there, first choose the admissible `go to` command for that receptacle. If you hold the second instance and the first instance is not visible in the current observation, do not move the second into an arbitrary different receptacle merely because a `move` command for it is admissible: first choose an admissible `go to`/`open` search action that may reveal the first instance's receptacle, or go to the goal-named destination if the goal identifies a unique receptacle. If no such search or destination action is admissible, use the best remaining admissible action.

If you accidentally pick up the first instance while the second is undelivered, return it to the receptacle named in the pickup observation before continuing, if that is admissible. Do not treat a different receptacle as the destination for the second instance unless the first instance is visible there in the current observation (or you have just returned the first instance to the receptacle named in the pickup observation).

---

## General Principles

1. **Decompose the task**: Parse the goal into ordered sub-goals (locate, acquire, transform, deliver). Complete each before moving to the next.
2. **Systematic exploration**: Search each surface and container exactly once before revisiting. Open closed containers (drawers, cabinets, fridge) before judging them empty.
**Locate-phase search mode**: When the goal object is neither held nor visible and the current observation does not contain it, do not choose `look` or `examine` as a substitute for an available `open` or `go to` search step. If the just-arrived location is closed, choose `open` for it before leaving. Otherwise choose a `go to` location from the menu; if the current observation or either of the two most recent action observations shows that a listed location contains only non-goal objects, prefer a different available `go to` or `open` when the menu offers one. When the just-reached location is an open numbered location (for example `cabinet 4`, `stoveburner 3`, `countertop 2`, or `shelf 1`) and the current observation shows it contains only non-goal objects, check the menu for an admissible higher-numbered location in that same class. Except when the class-sampling rule below applies, when choosing between locations of the just-checked class, prefer a higher-numbered one over a lower-numbered one (for example choose `go to cabinet 5` or `open cabinet 5` after `cabinet 4`, `go to stoveburner 4` after `stoveburner 3`, or `go to countertop 3` after `countertop 2`); open the chosen container if it is closed. If the menu has no higher-numbered member of that class, do not choose a lower-numbered member of the just-checked class merely because it is in that class; choose an admissible `go to` or `open` in a different class instead. A directly offered `open` for a closed container is also a valid search step before redundant inspection. If the goal object appears, take it and continue with the required transform/delivery path. If no `open` or `go to` is admissible, use the best remaining admissible search action rather than repeating the just-checked surface.

**Locate-phase class-sampling rule**: When, across the current observation and either of the two most recent step observations, two different numbered surfaces/containers of the same class are each shown to contain only non-goal objects, and the current menu still offers at least two higher-numbered members of that class, do not choose the next higher-numbered member. Instead choose an admissible `go to` or `open` for a different class; if the chosen container is closed and its `open` command is admissible, open it. If no different-class `go to` or `open` is admissible, continue with the higher-numbered same-class member or the best remaining admissible search action. If the goal object is visible or held, take it if needed and proceed with the required transform/delivery path. After the different-class step, apply the ordinary locate-phase rules to the new observation and menu; do not rely on a remembered visited list, a resume marker, or knowledge that a class is fully searched.
3. **Grab immediately**: When a required object is visible and reachable, take it right away before moving elsewhere. Exception: in a two-instance placement task, do not take the first delivered instance while it is visible at a receptacle and the second instance is still undelivered; follow the Two-Instance Placement section.
4. **Transform before placing**: If the task requires cleaning, heating, or cooling, perform the state change at the appropriate appliance before heading to the final destination.
5. **Direct delivery**: Once holding the transformed (or untransformed) goal object, navigate straight to the target receptacle and place it. In a two-instance placement task, follow the Two-Instance Placement section to determine the destination before delivering the second instance.
6. **Track progress**: Maintain an internal count of how many objects still need to be found and placed. Only stop searching when the count reaches zero.
7. **Avoid loops**: Never repeat the same action more than twice in a row. If stuck, move to a different unexplored location.
8. **Only choose admissible actions**: Always pick an action from the admissible action list. Do not invent actions.

---

## Common Mistakes to Avoid

- **Revisiting searched locations**: Keep track of which surfaces/containers have been checked; do not re-examine them.
- **Ignoring visible objects**: If the target object appears in the observation, pick it up immediately. Exception: in a two-instance placement task, do not pick up the first delivered instance while the second instance is still undelivered; follow the Two-Instance Placement section.
- **Skipping state changes**: Do not place an object at the destination without first cleaning/heating/cooling it when required.
- **Premature termination**: Do not stop the episode until all goal conditions are verified as met.
- **Action loops**: Repeatedly toggling or examining the same object wastes steps. Move on to new locations instead.

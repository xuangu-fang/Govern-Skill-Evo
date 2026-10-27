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
2. **Systematic exploration**: Search each surface and container exactly once before revisiting. Open closed containers (drawers, cabinets, fridge) before judging them empty.
3. **Grab immediately**: When a required object is visible and reachable, take it right away before moving elsewhere.
4. **Transform before placing**: If the task requires cleaning, heating, or cooling, perform the state change at the appropriate appliance before heading to the final destination.
5. **Direct delivery**: Once holding the transformed (or untransformed) goal object, navigate straight to the target receptacle and place it.
6. **Track progress**: Maintain an internal count of how many objects still need to be found and placed. Only stop searching when the count reaches zero.
7. **Avoid loops**: Never repeat the same action more than twice in a row. If stuck, move to a different unexplored location.
8. **Only choose admissible actions**: Always pick an action from the admissible action list. Do not invent actions.

---

## Acquisition Search (Before the Target Is Held)

Use these rules while the required object has not yet been acquired.

**Sweeping numbered container classes**
- An empty surface, or an empty container you have opened, is evidence only about that single location. It never means the object is unavailable, and it is not a reason to recheck the same spot.
- When a checked closed container does not contain the target, continue to another closed container. Prefer the next remaining instance of the same numbered container class (for example, the next cabinet or drawer) before switching to an unrelated open surface.
- Once you start sweeping a numbered container class, keep selecting further instances of that same class as long as the class still has at least one admissible instance other than the one you just checked. Prefer the next higher-numbered instance over a lower-numbered one. Do not leave the class for another class or surface while such an instance remains, and do not return to an instance you just checked.
- After the current class is exhausted, move to a different container class or surface candidate from the admissible destination list. Open any closed container on arrival before judging it empty.
- Keep broadening to additional container classes and surface candidates until the target is found. Do not stop within the first few checked cabinets, drawers, or surfaces, and do not treat their emptiness as proof that the object is unavailable.

**Avoiding revisit cycles**
- Do not choose as your next destination either of the last two locations you visited when the target was not observed there.
- If the next candidate would repeat one of the last two checked locations, or a location you just observed to be empty or lacking the target, choose a different admissible destination: a new container, a different container class, or an uninspected surface.
- Break short revisit cycles: never alternate between the same two recently checked locations while the target remains missing.
- This anti-revisit restriction applies only until the target is acquired. After taking the target, required returns to a sink, appliance, or previously visited final receptacle are allowed and should be made directly; do not extend the anti-revisit rule to transformation or delivery steps.

**On finding the target**
- Once the target becomes visible and reachable, take it immediately and stop searching. Then perform any required state change and deliver it directly to the goal receptacle.

---

## Common Mistakes to Avoid

- **Revisiting searched locations**: Keep track of which surfaces/containers have been checked; do not re-examine them.
- **Ignoring visible objects**: If the target object appears in the observation, pick it up immediately.
- **Skipping state changes**: Do not place an object at the destination without first cleaning/heating/cooling it when required.
- **Premature termination**: Do not stop the episode until all goal conditions are verified as met.
- **Action loops**: Repeatedly toggling or examining the same object wastes steps. Move on to new locations instead.

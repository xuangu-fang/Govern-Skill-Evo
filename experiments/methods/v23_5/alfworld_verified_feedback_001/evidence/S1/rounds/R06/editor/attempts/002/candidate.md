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
2. **Systematic exploration**: Search each surface and container exactly once before revisiting. Open every closed container (drawers, cabinets, fridge) you arrive at before leaving it, so a target hidden inside is not missed. When sweeping a numbered family of locations (for example cabinet N, drawer N, shelf N), after an instance does not contain the target, continue to a higher-numbered instance that appears in the admissible list rather than reversing to a lower-numbered instance you already checked; reaching the family's highest index is not required.
3. **Grab immediately**: When a required object is visible and reachable, take it right away before moving elsewhere.
4. **Transform before placing**: If the task requires cleaning, heating, or cooling, perform the state change at the appropriate appliance before heading to the final destination.
5. **Direct delivery**: Once holding the transformed (or untransformed) goal object, navigate straight to the target receptacle and place it.
6. **Track progress and source reuse**: Maintain an internal count of how many objects still need to be found and placed. Only stop searching when the count reaches zero. In a task requiring two or more instances of the same object, when the observation at the source location where you take the first instance also shows one or more additional instances of that same object, treat that location as the source for the remaining instances. After you place the first instance at the goal receptacle, make retrieving the next instance your immediate next sub-goal: navigate back to that same source location and take the remaining instance there, rather than resuming a broad search sweep or re-checking unrelated locations. Do not abandon or re-sweep past that source while it still offers an additional instance of the required object; only widen the search for the remaining instance if the source no longer shows the expected instance. This retrieval priority applies only during the acquisition/retrieval phase, takes precedence over the general locate-phase widening rules in Principle 7 (including any preference for untried destinations), and does not add extra transforms or intermediate stops. The source may appear in your recent observations and actions, but it remains the correct destination while it still offers the expected remaining instance. Keep the existing locate-take-deliver ordering and continue until the required number of instances has been placed at the goal receptacle.
7. **Advance to new instances, cover untried locations, and avoid stalls**: In the locate/acquire phase, while the required object(s) have not yet been acquired and are not held, choose each `go to` so that it advances to a destination that does not already appear as your current location or in your recent observations and actions whenever the admissible list contains such an untried destination. This widening rule does not require avoiding a known already-observed source that still offers the remaining required instance of a two-or-more-instance task; follow Principle 6 instead. Treating a different location type as automatic progress is not enough: rotating through already-checked instances of different types (for example one countertop, then one drawer, then one cabinet) is still a stall and must be broken. After arriving at an instance of a numbered family and observing that it does not contain the target, prefer advancing to a higher-numbered instance of that same family over returning to a lower-numbered instance you have already checked or to an already-checked instance of another type; do not let this preference replace widening coverage, though: once two consecutive instances of the same numbered family have not contained the target, prefer a `go to` destination of a different location type you have not yet arrived at (especially an open surface such as countertop, diningtable, shelf, dresser, or sidetable) over yet another instance of that family while such an untried destination is admissible. Open surfaces such as countertop, diningtable, sidetable, shelf, or dresser reveal their contents as soon as you arrive, so avoid spending many consecutive steps inside one closed-container family while such surfaces remain untried. If your recent observations and actions show you returning to the same few already-checked locations without gaining new information, treat the search as stalled and break the cycle by choosing an instance of a location family you have not yet checked at all; when no entirely new family is available, pick a genuinely new instance, preferably of a location type differing from those in your recent observations and from your current location. Because your visible history is short, when you cannot tell whether a destination was already checked, prefer an instance whose index is higher than any instance appearing in your recent observations and actions; use this higher-index preference only as a tie-breaker among genuinely new destinations, not as a reason to keep sweeping one numbered family while untried location types remain. Never repeat the same action more than twice in a row. Do not conclude that the required object is absent, and do not stop the search, while admissible `go to` destinations to instances you have not yet arrived at remain available; keep widening coverage until the object is found. Exit this search rule as soon as the required object is acquired or already held, and also when an already-observed source still offers the remaining required instance of a two-or-more-instance task; in that case, treat that source as the retrieval destination. Afterward resume the normal transform-then-deliver behavior without adding extra searches.
8. **Only choose admissible actions**: Always pick an action from the admissible action list. Do not invent actions.

---

## Common Mistakes to Avoid

- **Revisiting searched locations without purpose**: Keep track of which surfaces/containers have been checked; do not re-examine them, except when returning to a known source that still offers a remaining instance of the required object in a task requiring two or more instances.
- **Ignoring visible objects**: If the target object appears in the observation, pick it up immediately.
- **Skipping state changes**: Do not place an object at the destination without first cleaning/heating/cooling it when required.
- **Premature termination**: Do not stop the episode until all goal conditions are verified as met.
- **Action loops**: Repeatedly toggling or examining the same object wastes steps. Move on to new locations instead.

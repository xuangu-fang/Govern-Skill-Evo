# Original / 新格式A / 原B 完整产物对照

本表仅保存全文；两份有效输出Prompt不同，不是Memory单变量对照。

## Original Plan

```json
{
  "goal": "Make search for the exact requested object coverage-oriented and step-efficient so the target is found, conditioned if required, and placed before the step budget is exhausted, without picking up, conditioning, or placing a substitute. Preserve the successful desklamp behavior (hold/co-locate the target and turn the lamp on at its receptacle), the direct acquire-then-place flow, and the correct clean/cool-then-place ordering already demonstrated.",
  "updates": [
    {
      "id": "u1",
      "text": "During any search for the exact requested object (or for the desklamp once the target is in hand), treat the search as coverage of distinct candidate receptacles rather than a loop over a few. When the current observation shows the requested item is absent, move to a receptacle not yet inspected in this search, while retaining the existing rule to open a closed cabinet/drawer/fridge on arrival and inspect its contents. Sweep a numbered series of same-type containers in one direction without returning to earlier ones; once that series is exhausted without the target, switch to a different receptacle type (e.g., from drawers to cabinets, countertops, fridge, shelves, or sinkbasin) before re-entering the series. Use the most recent observations to notice when the next move would revisit a receptacle just left empty or repeat the same small set of locations, and in that case choose a different uninspected candidate. This is coverage for finding the exact target within the step budget; it does not permit picking up, conditioning, or placing a substitute object.",
      "basis": [
        "G2",
        "G3",
        "G4",
        "P3:8",
        "P6:6",
        "P6:14",
        "P6:16",
        "P8:9",
        "P10:6"
      ]
    },
    {
      "id": "u2",
      "text": "Do not spend steps on actions that cannot change the world or reveal new information. If an action returns 'Nothing happens,' if a 'look' repeats the description you already have for the current receptacle, or if 'inventory' is issued while carrying nothing, do not repeat that action or an equivalent one. Instead immediately take a state-changing action: move to a new uninspected receptacle, open a closed container, take the target, perform the required clean/cool/heat, or place the target at the destination.",
      "basis": [
        "P1:4",
        "P7:11",
        "P7:12",
        "P8:39",
        "P10:25"
      ]
    }
  ],
  "checks": [
    {
      "id": "c1",
      "update_ids": [
        "u1"
      ],
      "question": "After a receptacle is inspected and the target is absent, does the Actor move to a new uninspected receptacle or switch receptacle type rather than returning to one already seen empty or re-sweeping the same series?"
    },
    {
      "id": "c2",
      "update_ids": [
        "u2"
      ],
      "question": "Does the Actor avoid repeating no-op actions ('Nothing happens,' duplicate 'look,' empty-handed 'inventory') and instead choose a state-changing action?"
    },
    {
      "id": "c3",
      "update_ids": [
        "u1",
        "u2"
      ],
      "question": "When the exact target is found, does the Actor still complete the required conditioning and final placement with that target, and preserve the desklamp on-while-co-located success pattern?"
    }
  ]
}
```

## 新格式A Preconditioner

```json
{
  "decision": "ready",
  "reason": "Both proposed Updates are directly grounded in the supplied executions and are executable under the Actor's constraints, so no behavioral adjustment is justified. Update u1 targets the repeated small-set search loops visible in P3:5-P3:11 (drawers 1-4 swept, then re-swept before leaving the series), P6:6-P6:17 (drawer 1/countertop 1/drawer 2 cycled repeatedly), P8:9-P8:49 (cabinets 1-4 and sinkbasin 1 cycled many times), and P10:6-P10:31 (fridge 1/countertop 1/countertop 2/cabinet 1 cycled for ~30 steps before finding apple 1). Update u2 targets the observed no-op actions: the inadmissible 'go to shelf 2' returning 'Nothing happens' at P1:4, the duplicated 'look' with an unchanged observation at P7:11-P7:12, and the empty-handed 'inventory' at P8:39 and P10:25. Both Updates retain the Parent Skill's desklamp and acquire-condition-place behaviors, and the numbered-series/type-switch heuristic makes the coverage requirement implementable with the Actor's two-step history. Memory is empty, so no historical edit-behavior response argues for changing strategy, narrowing scope, or withdrawing either Update.",
  "adjustments": [],
  "checks": null
}
```

## 新格式A Effective Plan

```json
{
  "goal": "Make search for the exact requested object coverage-oriented and step-efficient so the target is found, conditioned if required, and placed before the step budget is exhausted, without picking up, conditioning, or placing a substitute. Preserve the successful desklamp behavior (hold/co-locate the target and turn the lamp on at its receptacle), the direct acquire-then-place flow, and the correct clean/cool-then-place ordering already demonstrated.",
  "updates": [
    {
      "id": "u1",
      "text": "During any search for the exact requested object (or for the desklamp once the target is in hand), treat the search as coverage of distinct candidate receptacles rather than a loop over a few. When the current observation shows the requested item is absent, move to a receptacle not yet inspected in this search, while retaining the existing rule to open a closed cabinet/drawer/fridge on arrival and inspect its contents. Sweep a numbered series of same-type containers in one direction without returning to earlier ones; once that series is exhausted without the target, switch to a different receptacle type (e.g., from drawers to cabinets, countertops, fridge, shelves, or sinkbasin) before re-entering the series. Use the most recent observations to notice when the next move would revisit a receptacle just left empty or repeat the same small set of locations, and in that case choose a different uninspected candidate. This is coverage for finding the exact target within the step budget; it does not permit picking up, conditioning, or placing a substitute object.",
      "basis": [
        "G2",
        "G3",
        "G4",
        "P3:8",
        "P6:6",
        "P6:14",
        "P6:16",
        "P8:9",
        "P10:6"
      ]
    },
    {
      "id": "u2",
      "text": "Do not spend steps on actions that cannot change the world or reveal new information. If an action returns 'Nothing happens,' if a 'look' repeats the description you already have for the current receptacle, or if 'inventory' is issued while carrying nothing, do not repeat that action or an equivalent one. Instead immediately take a state-changing action: move to a new uninspected receptacle, open a closed container, take the target, perform the required clean/cool/heat, or place the target at the destination.",
      "basis": [
        "P1:4",
        "P7:11",
        "P7:12",
        "P8:39",
        "P10:25"
      ]
    }
  ],
  "checks": [
    {
      "id": "c1",
      "update_ids": [
        "u1"
      ],
      "question": "After a receptacle is inspected and the target is absent, does the Actor move to a new uninspected receptacle or switch receptacle type rather than returning to one already seen empty or re-sweeping the same series?"
    },
    {
      "id": "c2",
      "update_ids": [
        "u2"
      ],
      "question": "Does the Actor avoid repeating no-op actions ('Nothing happens,' duplicate 'look,' empty-handed 'inventory') and instead choose a state-changing action?"
    },
    {
      "id": "c3",
      "update_ids": [
        "u1",
        "u2"
      ],
      "question": "When the exact target is found, does the Actor still complete the required conditioning and final placement with that target, and preserve the desklamp on-while-co-located success pattern?"
    }
  ]
}
```

## 原B Preconditioner

```json
{
  "decision": "ready",
  "reason": "Keep the no-op avoidance update unchanged because it directly targets observed repeated looks/empty inventory and remains executable. Adjust the search update to breadth-first coverage across receptacle types using only the last two observations, because current runs and historical Memory show that exhaustive same-type sweeps or cycling consume the step budget and that the Actor cannot reliably track an entire inspected set. Preserve exact-target/no-substitute behavior.",
  "adjustments": [
    {
      "from": [
        "u1"
      ],
      "to": [
        {
          "id": "u1",
          "text": "During any search for the exact requested object (or for the desklamp once the target is in hand), search as breadth-first coverage of distinct listed receptacles rather than exhausting one long same-type series. When the current observation shows the exact object is absent, use the current observation and the last two pre-action pairs to avoid repeating a receptacle just seen empty or the same small set; choose a different listed receptacle or type not present in that recent history. Do not open an entire numbered drawer/cabinet series while other receptacle types remain unvisited or the step count is already high; after sampling a few same-type containers without finding the target, switch to another type (for example drawers, cabinets, countertops, diningtable/sidetable, shelves, fridge, sinkbasin, or other open surfaces), opening each closed container immediately on arrival and inspecting its contents. Return to remaining numbers in a series only after other plausible types or locations have been sampled. Continue until the exact target is found or all plausible candidate types or locations have been inspected once. This is coverage for finding the exact target within the step budget; it never permits picking up, conditioning, or placing a substitute object."
        }
      ],
      "basis": [
        "M6",
        "M3",
        "M8",
        "P6:20",
        "P6:50",
        "P8:50",
        "P10:32"
      ],
      "reason": "The recorded failures show long same-type sweeps or cycling through a small set consuming the 50-step limit, while P10 eventually finds the exact apple on the diningtable after cycling. Historical M6 and M3 indicate that anti-revisit and broader-search language is often not followed reliably and can still miss a listed location, and the Actor only sees the last two pre-action observations, so the original instruction to sweep a numbered series before switching requires tracking the Actor does not have. Recrafting u1 as breadth-first sampling across receptacle types with recent-history cycling checks better fits Actor capabilities; M8 supports retaining the explicit no-substitute constraint."
    }
  ],
  "checks": null
}
```

## 原B Effective Plan

```json
{
  "goal": "Make search for the exact requested object coverage-oriented and step-efficient so the target is found, conditioned if required, and placed before the step budget is exhausted, without picking up, conditioning, or placing a substitute. Preserve the successful desklamp behavior (hold/co-locate the target and turn the lamp on at its receptacle), the direct acquire-then-place flow, and the correct clean/cool-then-place ordering already demonstrated.",
  "updates": [
    {
      "id": "u1",
      "text": "During any search for the exact requested object (or for the desklamp once the target is in hand), search as breadth-first coverage of distinct listed receptacles rather than exhausting one long same-type series. When the current observation shows the exact object is absent, use the current observation and the last two pre-action pairs to avoid repeating a receptacle just seen empty or the same small set; choose a different listed receptacle or type not present in that recent history. Do not open an entire numbered drawer/cabinet series while other receptacle types remain unvisited or the step count is already high; after sampling a few same-type containers without finding the target, switch to another type (for example drawers, cabinets, countertops, diningtable/sidetable, shelves, fridge, sinkbasin, or other open surfaces), opening each closed container immediately on arrival and inspecting its contents. Return to remaining numbers in a series only after other plausible types or locations have been sampled. Continue until the exact target is found or all plausible candidate types or locations have been inspected once. This is coverage for finding the exact target within the step budget; it never permits picking up, conditioning, or placing a substitute object.",
      "basis": [
        "G2",
        "G3",
        "G4",
        "P3:8",
        "P6:6",
        "P6:14",
        "P6:16",
        "P8:9",
        "P10:6"
      ]
    },
    {
      "id": "u2",
      "text": "Do not spend steps on actions that cannot change the world or reveal new information. If an action returns 'Nothing happens,' if a 'look' repeats the description you already have for the current receptacle, or if 'inventory' is issued while carrying nothing, do not repeat that action or an equivalent one. Instead immediately take a state-changing action: move to a new uninspected receptacle, open a closed container, take the target, perform the required clean/cool/heat, or place the target at the destination.",
      "basis": [
        "P1:4",
        "P7:11",
        "P7:12",
        "P8:39",
        "P10:25"
      ]
    }
  ],
  "checks": [
    {
      "id": "c1",
      "update_ids": [
        "u1"
      ],
      "question": "After a receptacle is inspected and the target is absent, does the Actor move to a new uninspected receptacle or switch receptacle type rather than returning to one already seen empty or re-sweeping the same series?"
    },
    {
      "id": "c2",
      "update_ids": [
        "u2"
      ],
      "question": "Does the Actor avoid repeating no-op actions ('Nothing happens,' duplicate 'look,' empty-handed 'inventory') and instead choose a state-changing action?"
    },
    {
      "id": "c3",
      "update_ids": [
        "u1",
        "u2"
      ],
      "question": "When the exact target is found, does the Actor still complete the required conditioning and final placement with that target, and preserve the desklamp on-while-co-located success pattern?"
    }
  ]
}
```

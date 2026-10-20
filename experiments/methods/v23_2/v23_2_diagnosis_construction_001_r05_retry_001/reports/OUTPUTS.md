# R05 用户授权重试：完整输出对照

D2原请求截断，仍保留为技术失败；以下D2-retry为独立追加一次请求的合法输出。

## D0 正式V23

```json
{
  "decision": "revise",
  "reason": "Three clean-and-place runs hit the step limit (P6, P7, P8): P7 explicitly took, cleaned, and placed a knife for a butterknife request, and P6/P8 spent the budget cycling among already-inspected empty containers without reaching uninspected families (P6 never opened cabinets; P8 kept returning to the same cabinets/sinkbasin while shelf and toilet were unchecked). These are actionable behavioral gaps in exact-target verification and search coverage. Successful desklamp co-location (P1, P2) and exact acquisition-condition-placement sequences (P9, P10) should be preserved.",
  "plan": {
    "goal": "Improve target selection and search coverage when the exact requested item is not immediately visible: never satisfy a request with a near-but-different object category, and sweep uninspected receptacle families instead of looping over already-checked empty ones. Preserve the successful desklamp co-location/use pattern and the efficient exact acquire-condition-place sequences observed in completed runs.",
    "updates": [
      {
        "id": "u1",
        "text": "Before acquiring, conditioning, or placing an object, confirm that its exact category name matches the requested target. Do not complete the task with a functionally similar but differently named object: treat a knife as distinct from a butterknife, a soapbottle as distinct from a soapbar, a cup as distinct from a mug, and a spraybottle as distinct from a soapbottle. If only a near-match is present at the current location, leave it untouched and continue searching for the exact category; never clean, cool, heat, or place a near-match in place of the requested object.",
        "basis": [
          "G3",
          "P7:5",
          "P7:7",
          "P7:9",
          "G4",
          "P9:2",
          "P10:33"
        ]
      },
      {
        "id": "u2",
        "text": "When the exact target is not visible, run a single-pass sweep that spreads across distinct receptacle families rather than exhausting or looping over one type. Open each closed container once and read its contents; if it lacks the target, continue to a receptacle you have not yet inspected. Use your most recent observations to avoid returning to a receptacle that was just confirmed empty, and when one family (for example drawers) yields nothing, switch to a different uninspected family (for example cabinets, shelves, countertops/other surfaces, or appliances) before revisiting any earlier location. Keep the sweep within the step budget so that unopened containers and uninspected surfaces are checked before any loop back.",
        "basis": [
          "G3",
          "P6:50",
          "P8:11",
          "P8:22",
          "P8:50",
          "G4",
          "P10:32"
        ]
      }
    ],
    "checks": [
      {
        "id": "c1",
        "update_ids": [
          "u1"
        ],
        "question": "When the exact requested category is absent from the current receptacle, does the Actor ever take, clean/cool/heat, or place a different but similar category (e.g., knife for butterknife, soapbottle for soapbar) as if it were the target?"
      },
      {
        "id": "c2",
        "update_ids": [
          "u2"
        ],
        "question": "After inspecting an empty receptacle, does the Actor move to an uninspected receptacle family instead of cycling back through already-seen empty cabinets/drawers, and does the search reach other families (shelves, surfaces, unopened containers) before the step limit?"
      }
    ]
  }
}
```

## D1 P1

```json
{
  "decision": "revise",
  "reason": "The batch shows two skill-addressable search problems in non-desklamp tasks: P7 used a non-target knife for a requested butterknife, and P6/P8 hit the step limit by cycling among already-inspected empty receptacles instead of covering new candidates; P10 also delayed target discovery by revisiting fridge/countertops while diningtable remained unchecked. Successful P1/P2 show desklamp co-location worth preserving, and P3/P4/P5/P9 show exact-target acquisition and conditioning/placement behavior to preserve.",
  "plan": {
    "goal": "Improve non-desklamp search and acquisition so that the Actor matches requested objects exactly, avoids substituting related objects, and advances through uninspected candidates instead of looping among already-checked receptacles. Preserve the successful desklamp co-location behavior and the successful pattern of acquiring the exact target, performing any required cleaning/cooling, opening a closed destination if needed, and placing the target there.",
    "updates": [
      {
        "id": "u1",
        "text": "Exact-target fidelity: For any non-desklamp retrieval, cleaning, cooling, or placement task, treat the requested object noun as an exact identity check before every take, clean/cool, or move action. If the visible object has a different name, even a closely related one such as a generic knife instead of a butterknife or a soapbottle instead of a soapbar, do not take, condition, or place it as the task object. Leave non-target objects untouched and continue searching. If you have already picked up a non-target by mistake, do not clean/cool or place it as the answer; resume the search for the exact target. Preserve the successful behavior of acquiring the exact target when it is present and then completing the requested conditioning and placement.",
        "basis": [
          "G3",
          "P7:2",
          "P7:5",
          "P7:7",
          "P7:9",
          "G2",
          "P3:14",
          "P5:3",
          "G4",
          "P9:2"
        ]
      },
      {
        "id": "u2",
        "text": "Unvisited-candidate breadth-first search: When the exact target is not visible at the current location in a non-desklamp task, do not cycle among already-inspected receptacles and do not repeat look or inventory actions while carrying nothing as a substitute for moving. After inspecting a candidate and not finding the target, choose a different unvisited candidate instead of returning to an observed empty or no-target receptacle while uninspected candidates remain. Cover distinct candidate categories before exhausting a long same-type group: for example, check a few drawers or cabinets, then switch to an uninspected open surface or fixture, and later return to remaining closed containers. Within a named group, advance to new indices rather than jumping back to earlier ones. Continue until the exact target is found or all plausible candidate categories have been checked once, then use the exact target for the required conditioning and placement.",
        "basis": [
          "G3",
          "P6:2",
          "P6:5",
          "P6:6",
          "P6:7",
          "P6:10",
          "P6:11",
          "P8:4",
          "P8:26",
          "P8:27",
          "P8:28",
          "P8:39",
          "G4",
          "P10:5",
          "P10:6",
          "P10:25",
          "P10:32"
        ]
      }
    ],
    "checks": [
      {
        "id": "c1",
        "update_ids": [
          "u1"
        ],
        "question": "When the requested object is absent from the current container and only similarly named objects are present, does the Actor refrain from taking, cleaning, or moving those substitutes and continue searching for the exact requested noun?"
      },
      {
        "id": "c2",
        "update_ids": [
          "u2"
        ],
        "question": "In a scene with many uninspected receptacles, does the Actor advance to new candidate categories rather than cycling among already-inspected drawers, cabinets, or surfaces, and does it avoid look/inventory while carrying nothing?"
      },
      {
        "id": "c3",
        "update_ids": [
          "u1",
          "u2"
        ],
        "question": "When the exact target is found, does the Actor still acquire it, perform any required cleaning or cooling, open the destination if closed, and place the exact target there without unnecessary detours?"
      }
    ]
  }
}
```

## D2-retry P1-B

```json
{
  "decision": "revise",
  "reason": "Across the batch, successful runs (P1, P2, P4, P5, P9, P10) show the parent procedures are largely adequate for desklamp co-location, direct transfer, and clean/cool-then-place ordering. The failures (P6, P7, P8) are step-limit exhaustions driven by observable search behavior the Actor can control: repeatedly re-entering already-inspected empty receptacles or cycling among the same few locations instead of expanding coverage, plus no-op actions. These are Skill-addressable coverage and step-efficiency problems, distinct from task success/failure alone.",
  "plan": {
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
}
```

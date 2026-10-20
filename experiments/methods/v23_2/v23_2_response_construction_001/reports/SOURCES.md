# 本次实际可见证据索引

以下只摘自各轮冻结输入；P/Q 是来源轮次内引用，不跨轮混用。完整来源仍在原归档，没有后续 Memory 回灌。


## R04

[正式 Preconditioner 原输入](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R04/preconditioner/attempts/002/input.json) · [当时 Active Memory](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R03/memory)

实际 Memory IDs：M1, M2, M3, M4, M5, M6


### P2 — heat some plate and put it in cabinet.

- P2:7: `move plate 3 to microwave 1` → You move the plate 3 to the microwave 1.

- P2:11: `heat plate 3 with microwave 1` → You heat the plate 3 using the microwave 1.

- P2:13: `move plate 3 to cabinet 1` → You move the plate 3 to the cabinet 1.


### P3 — put a hot potato in fridge.

- P3:8: `move potato 3 to microwave 1` → You move the potato 3 to the microwave 1.

- P3:12: `heat potato 3 with microwave 1` → You heat the potato 3 using the microwave 1.

- P3:14: `move potato 3 to fridge 1` → You move the potato 3 to the fridge 1.


### P4 — heat some tomato and put it in countertop.

- P4:8: `examine microwave 1` → The microwave 1 is closed.

- P4:18: `take tomato 2 from microwave 1` → You pick up the tomato 2 from the microwave 1.

- P4:19: `heat tomato 2 with microwave 1` → You heat the tomato 2 using the microwave 1.

- P4:21: `move tomato 2 to countertop 1` → You move the tomato 2 to the countertop 1.


### P6 — put two candle in drawer.

- P6:23: `go to countertop 1` → You arrive at countertop 1. On the countertop 1, you see a candle 2, a candle 1, a cloth 1, a spraybottle 1, a toiletpaper 2, and a toiletpaper 1.

- P6:26: `move candle 1 to drawer 1` → You move the candle 1 to the drawer 1.

- P6:27: `go to countertop 1` → You arrive at countertop 1. On the countertop 1, you see a candle 2, a cloth 1, a spraybottle 1, a toiletpaper 2, and a toiletpaper 1.

- P6:28: `take candle 2 from countertop 1` → You pick up the candle 2 from the countertop 1.

- P6:30: `move candle 2 to drawer 1` → You move the candle 2 to the drawer 1.


### P8 — find two newspaper and put them in sofa.

- P8:1: `go to coffeetable 1` → You arrive at coffeetable 1. On the coffeetable 1, you see a laptop 1, a newspaper 2, a newspaper 1, and a pen 1.

- P8:4: `move newspaper 1 to sofa 1` → You move the newspaper 1 to the sofa 1.

- P8:5: `go to sidetable 1` → You arrive at sidetable 1. On the sidetable 1, you see a keychain 2, and a keychain 1.

- P8:6: `open drawer 1` → You open the drawer 1. The drawer 1 is open. In it, you see nothing.

- P8:7: `go to coffeetable 1` → You arrive at coffeetable 1. On the coffeetable 1, you see a laptop 1, a newspaper 2, and a pen 1.

- P8:8: `take newspaper 2 from coffeetable 1` → You pick up the newspaper 2 from the coffeetable 1.

- P8:10: `move newspaper 2 to sofa 1` → You move the newspaper 2 to the sofa 1.


### M4 原文

The actual diff added a temperature-transformation step to the general non-desklamp procedure: after acquiring the exact target, go to the fridge for cooling or the microwave for heating; if the explicit “cool X with fridge” or “heat X with microwave” action is already admissible, perform it immediately while holding the target and without first inserting it; open the appliance only when needed; and do not treat moving the object into the appliance, closing/reopening the door, or examining the appliance as completing the temperature change, with final placement renumbered to follow. In the three paired temperature tasks where the exact target was located, the Candidate displayed this pattern and the Parent did not, with large step differences. In the cool-pot pair, the Parent carried the pot to the closed fridge, opened it, and only then cooled it (18 steps), while the Candidate executed “cool pot 2 with fridge 1” at the still-closed fridge while holding the pot and then placed it (11 steps). In the hot-apple pair, the Parent moved the apple into the microwave, closed and reopened the door, took the apple out, carried it to the fridge, later retrieved it, returned to the microwave and only heat it then, and finally carried it back to the fridge (35 steps); the Candidate heated the apple with the microwave while holding it at the closed microwave, without inserting it or toggling the door, and then moved it to the already-open fridge (9 steps). In the heat-egg pair, the Parent inserted the egg and repeatedly toggled the microwave door open/closed before finally taking the egg out, heating it while holding, and placing it (40 steps); the Candidate opened the closed microwave once and then heated the egg while holding, without insertion or door toggling (15 steps). Across these pairs the Candidate’s behavior matches the edited instruction that the explicit temperature action can and should be applied while holding the target, and the Parent’s extra insertion/toggling steps are consistent with the behavior the edit targets. Because the Parent nevertheless succeeded in all three tasks, the evidence does not show that the edit is necessary for task success; it supports step and manipulation savings under these conditions. In the temperature tasks where the exact target was never found (cool-a-pan, heat-a-mug), both Parent and Candidate hit the step limit, so the temperature guidance had no observable opportunity there, and one stochastic trial per task means the step differences cannot be attributed to this clause alone.

来源：S1_R03/diff, S1_R03/P7:14, S1_R03/P7:15, S1_R03/P7:16, S1_R03/P7:18, S1_R03/Q7:8, S1_R03/Q7:9, S1_R03/Q7:11, S1_R03/P8:19, S1_R03/P8:20, S1_R03/P8:21, S1_R03/P8:33, S1_R03/P8:35, S1_R03/Q8:6, S1_R03/Q8:7, S1_R03/Q8:9, S1_R03/P9:24, S1_R03/P9:25, S1_R03/P9:29, S1_R03/P9:36, S1_R03/P9:37, S1_R03/P9:40, S1_R03/Q9:12, S1_R03/Q9:13, S1_R03/Q9:15


### M6 原文

The actual diff also rewrote the search step to add: use current and recent observations to avoid immediate cycling; do not re-examine an already-open empty receptacle or check inventory while carrying nothing; and, if the obvious cabinets/fridge have not yielded the target or the step count is already high, prefer uninspected drawers, shelves, the diningtable, or other listed receptacles and new unopened containers over returning to known-empty locations. The observed response is mixed. Positive case: in one cool-a-bread instance the Parent cycled among the fridge, cabinets and countertops and hit the step limit without finding bread, whereas the Candidate expanded to the diningtable (reached during search), took a bread there, cooled it at the fridge, and placed it on countertop 1, succeeding. Negative case: in a same-task pair with an identical room and identical container contents, the Parent explored countertop 3 and took the bread there, while the Candidate repeatedly visited countertop 2 but never went to countertop 3, cycled among cabinets, shelves and the fridge instead, and hit the step limit. In the cool-a-plate pair the Candidate repeatedly chose an unavailable move to cabinet 3 (falling back to a no-op) and then examined that already-empty location several times, reached the plate in cabinet 9 only at step 49, and exhausted the budget one step later while the Parent completed the same task at step 38 after finding the plate in cabinet 9. In the remaining unsolved tasks (cool a pan, heat a mug) both Parent and Candidate shuttled for many steps among the same cabinets, stoveburners and other receptacles instead of exhausting uninspected locations. Overall, the Candidate showed occasional broader exploration consistent with the edit (the diningtable find) but the anti-cycling/step-budget-priority language was not reliably followed, cycling and step-limit failures persisted, and the net task-level result across the ten pairs was slightly lower for the Candidate (6 successes vs 7), which is within plausible stochastic variation and cannot be attributed to this clause alone; each task was run once and location of the target varied across instances.

来源：S1_R03/diff, S1_R03/P2:15, S1_R03/P2:16, S1_R03/P2:18, S1_R03/P2:20, S1_R03/Q2:25, S1_R03/Q2:30, S1_R03/Q2:50, S1_R03/P4:50, S1_R03/Q4:12, S1_R03/Q4:13, S1_R03/Q4:15, S1_R03/Q4:17, S1_R03/P6:32, S1_R03/P6:33, S1_R03/P6:36, S1_R03/P6:38, S1_R03/Q6:4, S1_R03/Q6:10, S1_R03/Q6:15, S1_R03/Q6:48, S1_R03/Q6:49, S1_R03/Q6:50


## R05

[正式 Preconditioner 原输入](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R05/preconditioner/attempts/001/input.json) · [当时 Active Memory](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R04/memory)

实际 Memory IDs：M1, M2, M3, M6, M7, M8, M9


### P6 — put a clean butterknife in drawer.

- P6:1: `go to drawer 1` → You arrive at drawer 1. The drawer 1 is closed.

- P6:3: `go to countertop 1` → You arrive at countertop 1. On the countertop 1, you see a cup 1, a houseplant 1, a mug 1, and a peppershaker 1.

- P6:18: `go to drawer 4` → You arrive at drawer 4. The drawer 4 is closed.

- P6:49: `open drawer 19` → You open the drawer 19. The drawer 19 is open. In it, you see a dishsponge 1.

- P6:50: `go to drawer 20` → You arrive at drawer 20. The drawer 20 is closed.


### P8 — put a clean soapbar in cabinet.

- P8:11: `open cabinet 2` → You open the cabinet 2. The cabinet 2 is open. In it, you see a candle 2, a soapbottle 2, and a spraybottle 2.

- P8:22: `go to cabinet 2` → You arrive at cabinet 2. The cabinet 2 is open. In it, you see a candle 2, a soapbottle 2, and a spraybottle 2.

- P8:49: `go to sinkbasin 1` → You arrive at sinkbasin 1. On the sinkbasin 1, you see nothing.

- P8:50: `go to sinkbasin 2` → You arrive at sinkbasin 2. On the sinkbasin 2, you see nothing.


## R06

[正式 Preconditioner 原输入](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R06/preconditioner/attempts/001/input.json) · [当时 Active Memory](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R05/memory)

实际 Memory IDs：M1, M2, M6, M7, M9, M10, M11


### P1 — cool some plate and put it in countertop.

- P1:33: `go to countertop 1` → You arrive at countertop 1. On the countertop 1, you see a creditcard 3, a pan 1, a papertowelroll 1, a spatula 1, and a winebottle 1.

- P1:34: `go to countertop 2` → You arrive at countertop 2. On the countertop 2, you see a bread 1, a fork 3, a fork 2, a houseplant 1, a knife 2, a mug 2, a pan 2, a plate 1, a pot 1, and a statue 2.

- P1:35: `take plate 1 from countertop 2` → You pick up the plate 1 from the countertop 2.


### P2 — put a cool tomato in microwave.

- P2:7: `go to countertop 1` → You arrive at countertop 1. On the countertop 1, you see nothing.

- P2:8: `go to countertop 2` → You arrive at countertop 2. On the countertop 2, you see a bread 2, a butterknife 1, a knife 1, a mug 1, a pan 2, a potato 2, a potato 1, and a tomato 1.

- P2:9: `take tomato 1 from countertop 2` → You pick up the tomato 1 from the countertop 2.


### P3 — heat some apple and put it in diningtable.

- P3:8: `open cabinet 2` → You open the cabinet 2. The cabinet 2 is open. In it, you see nothing.

- P3:22: `go to fridge 1` → You arrive at fridge 1. The fridge 1 is open. In it, you see a bowl 1, a cup 1, a egg 1, a lettuce 1, a plate 1, and a tomato 1.

- P3:50: `go to fridge 1` → You arrive at fridge 1. The fridge 1 is open. In it, you see a bowl 1, a cup 1, a egg 1, a lettuce 1, a plate 1, and a tomato 1.


### P4 — heat some tomato and put it in fridge.

- P4:4: `go to microwave 1` → You arrive at microwave 1. The microwave 1 is closed.

- P4:6: `move tomato 2 to microwave 1` → You move the tomato 2 to the microwave 1.

- P4:20: `heat tomato 2 with microwave 1` → You heat the tomato 2 using the microwave 1.


### P5 — heat some tomato and put it in fridge.

- P5:5: `move tomato 2 to microwave 1` → You move the tomato 2 to the microwave 1.

- P5:15: `heat tomato 2 with microwave 1` → You heat the tomato 2 using the microwave 1.


### M10 原文

The general non-desklamp search step was rewritten from a broad 'open closed containers and continue until found, avoiding immediate revisits' instruction into an explicit single-pass family sweep: open each closed container once, use recent observations, and after one family (for example drawers) yields nothing, move to a different uninspected family (cabinets, shelves, countertops or other surfaces, appliances) before revisiting any earlier location, while keeping the sweep within the step budget. In paired non-desklamp tasks this was associated with two additional successes where the exact target lay in a family the Parent never reached: in a put-a-clean-butterknife-in-drawer task the Parent opened many drawers and some countertop/sink locations but hit the step limit without checking countertop2, where the Candidate found the exact butterknife, cleaned it at the sinkbasin, and placed it in drawer1; in a put-a-clean-soapbar-in-cabinet task the Parent cycled among cabinets, sinkbasin, and countertop without checking shelf1, while the Candidate eventually checked shelf1, found the exact soapbar, cleaned it, and placed it in cabinet1. The revised sweep did not reliably prevent cycling: in a clean-butterknife pair where no exact butterknife was present, both executions hit the step limit and the Candidate still cycled among drawers, countertops, and cabinets; in a cool-apple pair both succeeded, but the Candidate required more steps (46 vs 38) and revisited many already-seen empty locations before reaching the diningtable apple. Across the ten paired tasks the Parent succeeded 7/10 and the Candidate 9/10, with no observed regression on tasks the Parent already solved, but each task was run once; the two rescues depended on the exact target being present in an uninspected family, and the evidence does not show that the sweep overcomes step-limit cycling when the target is absent or not located within the budget.

来源：S1_R05/diff, S1_R05/P6:1, S1_R05/P6:31, S1_R05/P6:49, S1_R05/P6:50, S1_R05/Q6:12, S1_R05/Q6:16, S1_R05/Q6:19, S1_R05/Q6:21, S1_R05/P8:18, S1_R05/P8:19, S1_R05/P8:50, S1_R05/Q8:18, S1_R05/Q8:19, S1_R05/Q8:21, S1_R05/Q8:23, S1_R05/P7:5, S1_R05/P7:7, S1_R05/P7:9, S1_R05/P7:50, S1_R05/Q7:2, S1_R05/Q7:50, S1_R05/P10:32, S1_R05/P10:38, S1_R05/Q10:40, S1_R05/Q10:46


### M10 对应的真实历史 Diff

```diff
--- a/SKILL.md
+++ b/SKILL.md
@@ -23,8 +23,8 @@
 
 For ordinary put, clean, or transfer tasks where no desklamp is required, use this procedure instead.
 
-1. Identify and search for the exact requested target. If it is not visible, search systematically: open any closed cabinet, drawer, or fridge immediately upon reaching it and inspect its contents before leaving. Do not immediately revisit an already-open receptacle that visibly lacks the target; choose a different uninspected candidate location instead. Do not repeatedly check inventory while carrying nothing. Continue until the exact target is found or all plausible candidate receptacles have been inspected once.
-2. Manipulate only the exact requested target category. Do not pick up, clean, or place a substitute object when the exact target is absent; for example, do not transfer a soapbottle when the task requests a dishsponge. If the exact target has not yet been found, continue the systematic search rather than completing the transfer with a non-target object.
+1. Identify and search for the exact requested target. If it is not visible, run a single-pass sweep that spreads across distinct receptacle families rather than exhausting or looping over one type. Open each closed container (cabinet, drawer, fridge, etc.) once upon reaching it and read its contents; if it lacks the target, continue to a receptacle you have not yet inspected. Use your most recent observations to avoid returning to a receptacle you just confirmed empty. When one family (for example drawers) yields nothing, switch to a different uninspected family (such as cabinets, shelves, countertops/other surfaces, or appliances) before revisiting any earlier location. Keep the sweep within the step budget so that unopened containers and uninspected surfaces are checked before any loop back. Do not repeatedly check inventory while carrying nothing. Continue until the exact target is found or all plausible candidate receptacles have been inspected once.
+2. Manipulate, condition, or place only the exact requested target category. Before acquiring, cleaning, cooling, heating, or placing an object, confirm that its exact category name matches the requested target. Do not complete the task with a functionally similar but differently named object: treat a knife as distinct from a butterknife, a soapbottle as distinct from a soapbar, a cup as distinct from a mug, and a spraybottle as distinct from a soapbottle. If only a near-match is present at the current location, leave it untouched and continue searching for the exact category; never clean, cool, heat, or place a near-match in place of the requested object. If the exact target has not yet been found, continue the systematic search rather than completing the transfer with a non-target object.
 3. Acquire the exact target. If the task requires the object to be clean, carry it to an appropriate cleaning receptacle such as a sinkbasin and perform the clean action. If no cleaning is requested, skip the cleaning detour.
 4. Go directly to the requested destination. Open it first if it is closed, then place or move the target there. Do not detour to unrelated receptacles or release the target before the requested placement is completed.
 

```


### S1_R05/P6 摘要

P6:1 go to drawer 1；P6:2 open drawer 1；P6:3 go to countertop 1；P6:4 go to drawer 2；P6:5 open drawer 2；P6:6 go to drawer 1；P6:7 go to countertop 1；P6:8 go to sinkbasin 1；P6:9 go to drawer 2；P6:10 go to drawer 1；P6:11 go to countertop 1；P6:12 go to drawer 3；P6:13 open drawer 3；P6:14 go to drawer 2；P6:15 go to countertop 1；P6:16 go to drawer 1；P6:17 go to drawer 3；P6:18 go to drawer 4；P6:19 open drawer 4；P6:20 go to drawer 5；P6:21 open drawer 5；P6:22 go to drawer 6；P6:23 open drawer 6；P6:24 go to drawer 7；P6:25 open drawer 7；P6:26 go to drawer 8；P6:27 open drawer 8；P6:28 go to drawer 9；P6:29 open drawer 9；P6:30 go to drawer 10；P6:31 open drawer 10；P6:32 go to drawer 11；P6:33 open drawer 11；P6:34 go to drawer 12；P6:35 open drawer 12；P6:36 go to drawer 13；P6:37 open drawer 13；P6:38 go to drawer 14；P6:39 open drawer 14；P6:40 go to drawer 15；P6:41 open drawer 15；P6:42 go to drawer 16；P6:43 open drawer 16；P6:44 go to drawer 17；P6:45 open drawer 17；P6:46 go to drawer 18；P6:47 open drawer 18；P6:48 go to drawer 19；P6:49 open drawer 19；P6:50 go to drawer 20


### S1_R05/Q6 摘要

Q6:1 go to drawer 1；Q6:2 open drawer 1；Q6:3 go to countertop 1；Q6:4 go to cabinet 1；Q6:5 open cabinet 1；Q6:6 go to drawer 1；Q6:7 go to drawer 2；Q6:8 open drawer 2；Q6:9 go to countertop 1；Q6:10 go to drawer 1；Q6:11 go to cabinet 1；Q6:12 go to cabinet 2；Q6:13 open cabinet 2；Q6:14 go to countertop 1；Q6:15 go to drawer 1；Q6:16 go to countertop 2；Q6:17 take butterknife 1 from countertop 2；Q6:18 go to sinkbasin 1；Q6:19 clean butterknife 1 with sinkbasin 1；Q6:20 go to drawer 1；Q6:21 move butterknife 1 to drawer 1


### S1_R05/Q8 摘要

Q8:1 go to countertop 1；Q8:2 go to sinkbasin 1；Q8:3 go to sinkbasin 2；Q8:4 go to cabinet 1；Q8:5 open cabinet 1；Q8:6 go to cabinet 2；Q8:7 open cabinet 2；Q8:8 go to cabinet 3；Q8:9 open cabinet 3；Q8:10 go to cabinet 4；Q8:11 open cabinet 4；Q8:12 go to cabinet 1；Q8:13 go to cabinet 2；Q8:14 go to cabinet 3；Q8:15 go to cabinet 4；Q8:16 go to sinkbasin 1；Q8:17 go to countertop 1；Q8:18 go to shelf 1；Q8:19 take soapbar 1 from shelf 1；Q8:20 go to sinkbasin 1；Q8:21 clean soapbar 1 with sinkbasin 1；Q8:22 go to cabinet 1；Q8:23 move soapbar 1 to cabinet 1


### S1_R05/Q10 摘要

Q10:1 go to countertop 1；Q10:2 go to fridge 1；Q10:3 open fridge 1；Q10:4 go to cabinet 1；Q10:5 go to countertop 1；Q10:6 go to countertop 2；Q10:7 go to fridge 1；Q10:8 go to cabinet 1；Q10:9 go to cabinet 2；Q10:10 go to countertop 1；Q10:11 go to fridge 1；Q10:12 go to cabinet 1；Q10:13 go to cabinet 2；Q10:14 go to countertop 1；Q10:15 go to fridge 1；Q10:16 go to cabinet 1；Q10:17 go to drawer 1；Q10:18 go to countertop 1；Q10:19 go to fridge 1；Q10:20 go to cabinet 1；Q10:21 go to drawer 1；Q10:22 go to countertop 1；Q10:23 go to fridge 1；Q10:24 go to cabinet 1；Q10:25 examine cabinet 2；Q10:26 go to countertop 1；Q10:27 go to fridge 1；Q10:28 go to countertop 2；Q10:29 go to cabinet 1；Q10:30 examine cabinet 2；Q10:31 go to fridge 1；Q10:32 go to countertop 1；Q10:33 go to countertop 2；Q10:34 go to cabinet 1；Q10:35 go to fridge 1；Q10:36 go to countertop 1；Q10:37 go to countertop 2；Q10:38 go to cabinet 1；Q10:39 go to fridge 1；Q10:40 go to diningtable 1；Q10:41 take apple 1 from diningtable 1；Q10:42 go to fridge 1；Q10:43 cool apple 1 with fridge 1；Q10:44 go to microwave 1；Q10:45 open microwave 1；Q10:46 move apple 1 to microwave 1

## R06 Actor 初始说明的实际可见窗口

[正式 P3 Actor 轨迹](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R06/parent_runs/val_0013/attempts/001/skill_20261019T014346856944Z_c657f846/trajectory.json)；[原始渲染器](/Users/didi/Desktop/Govern-Skill-Evo/src/adapters/alfworld/actor_prompt.py)。

第 1、2、3 步请求包含初始房间说明，第 4、5 步不包含；这是两个行动前观察窗口的结果。本次只读核查，没有运行 Actor。

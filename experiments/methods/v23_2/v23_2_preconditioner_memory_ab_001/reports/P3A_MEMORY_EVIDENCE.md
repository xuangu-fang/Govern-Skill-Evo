# P3-A 历史响应预注册索引

B组完整保留当轮七条Memory，A组没有这些entries或sources。下文是研究评价说明，不进入任何模型消息，不改写knowledge。不开展新的全面Memory审计；M6沿用P2逐项核查，其余条目用于预登记来源及适用边界。尤其不能把所有B组变化归于M6，也不能把其他条目的“absent”直接视为隐藏环境不存在的已证事实。

[冻结B组Memory](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/config/memory_B.json) 的 `entries[id=...]`、`sources[context/diff]`、`sources[context/Pn或Qn]` 是完整原文，source中含Parent/Diff或run/command_sets。[不可变原文件哈希](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/config/source_hashes.json) 与 [逐Memory引用索引](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/config/memory_source_index.json) 可复核。

## M1

**knowledge原文**

> Adding a new desklamp-conditioned inspection procedure—locate the desklamp and a matching target, establish target-lamp co-location at the desklamp's receptacle (carrying or placing the target there), turn on the lamp, and complete the look/examine while the target is held or co-located, with explicit warnings against repeatedly toggling the lamp from a remote location and shuttling same-type candidates—was associated with the Candidate succeeding on all five paired desklamp tasks, whereas the no-skill Parent failed one. In the Parent failure (a look-at-alarmclock task), the Actor turned the lamp on at a dresser while the alarmclocks remained on a desk, repeatedly examined the desk, moved alarmclocks back and forth, and reached the 50-step limit without completing the inspection; the Candidate in the same task instead picked up one alarmclock, carried it to the dresser holding the desklamp, and turned on the lamp while co-located, finishing successfully in four steps. In the other four desklamp pairs the Parent already succeeded, so the guidance was not necessary for every such task, and the Candidate's behavior was generally consistent with the edited procedure: it ended by activating the lamp while holding or co-locating the target (e.g., carrying a cd, pillow, or clock to the lamp, or taking a lamp-adjacent statue). Exact ordering varied—sometimes the target was placed before activation, sometimes held during activation, and in one task the target was taken only after the lamp was activated—so the evidence supports a general shift toward target-lamp co-location before/at completion rather than strict step-order compliance. The varied success triggers observed across instances (lamp activation versus taking the co-located object) indicate that local task completion rules are not fully uniform, and faster completion beyond the looping case may partly reflect instance variation and cannot be attributed solely to this edit.

**编辑—响应**：S1_R01 新增desklamp共址流程；P1 50步失败，Q1 4步成功，其余四对均成功，完成触发与先后顺序有差异。

**支持的判断**：支持保留目标与灯共址、避免远程反复开关；对u1扩大到lamp搜索的范围有约束。

**不能推出**：不能把先take/先turn-on设成唯一正确顺序；不说明所有任务都应寻找灯。

**原始evidence完整索引**：`S1_R01/diff`、`S1_R01/P1:3`、`S1_R01/P1:10`、`S1_R01/P1:47`、`S1_R01/P1:50`、`S1_R01/Q1:2`、`S1_R01/Q1:3`、`S1_R01/Q1:4`、`S1_R01/P3:11`、`S1_R01/Q3:7`、`S1_R01/P5:12`、`S1_R01/Q5:2`。

## M2

**knowledge原文**

> The new desklamp-oriented skill also included a clause to preserve successful search, acquisition, and placement behavior from non-desklamp transfer tasks. Across the five paired non-desklamp transfer tasks (put-a-cellphone-in-shelf, put-some-newspaper-on-sofa, put-a-pencil-in-desk, put-a-soapbar-in-garbagecan, put-some-statue-on-coffeetable), the Candidate succeeded on every task just as the no-skill Parent did, and no new failures or unwanted behaviors appeared. Step counts were sometimes much lower in the Candidate (cellphone and statue tasks) and otherwise comparable (newspaper, pencil, soapbar), while the Parent sometimes opened many drawers before locating the target. Because the added guidance targets desklamp-conditioned tasks only, these efficiency differences are not clearly attributable to the edit and may reflect exploration or task variation; what the evidence supports is that the desklamp-specific addition did not degrade success or the basic search/acquisition/placement behavior in non-desklamp tasks.

**编辑—响应**：同一desklamp编辑附带保留非灯任务行为；P6–P10/Q6–Q10五对均成功，步数有差异。

**支持的判断**：保留非灯任务的搜索、获取、交付；提示不要因新搜索强制流程破坏直接完成。

**不能推出**：未隔离证明保留子句导致成功；不是任何新搜索策略均无副作用的保证。

**原始evidence完整索引**：`S1_R01/diff`、`S1_R01/P6:16`、`S1_R01/Q6:5`、`S1_R01/P7:13`、`S1_R01/Q7:14`、`S1_R01/P8:10`、`S1_R01/Q8:10`、`S1_R01/P9:5`、`S1_R01/Q9:4`、`S1_R01/P10:16`、`S1_R01/Q10:4`。

## M3

**knowledge原文**

> Appending a general non-desklamp procedure to the existing desklamp-only skill—while also narrowing the desklamp procedure to tasks that explicitly require a desklamp—was examined on 10 paired ordinary put/clean/transfer tasks whose scenes contained no desklamp. Because no desklamp appeared, the scope-boundary clause was never triggered and its effect is unobserved; the operative change was the appended guidance (open closed containers upon reaching them and inspect before leaving; avoid immediately revisiting an already-open empty receptacle; avoid repeated empty-handed inventory checks; act only on the exact requested target rather than a substitute; clean only when the task requires it; then go directly to the destination, opening it if closed, and place). Under these conditions the Parent skill succeeded on 6 of 10 tasks and hit the 50-step limit on 4, while the Candidate succeeded on 7 and hit the limit on 3. The clearest contrast is the paired clean-a-dishsponge-and-put-it-in-shelf task: the Parent cycled among the sinkbasin, cart, shelf 1 and shelf 2 without ever inspecting the bathtubbasin, eventually picked up a soapbottle (a non-target substitute) and moved it to shelf 1 without completing the task (step limit); the Candidate explored additional receptacles, found the exact dishsponge at the bathtubbasin, took it, cleaned it at the sinkbasin, and placed it on shelf 1 for a success. This supports that added search breadth combined with exact-target/no-substitute guidance can rescue a task on which the Parent substituted the wrong object, though the two clauses act together and cannot be isolated. The Candidate also opened closed containers earlier than the Parent in the toiletpaper and knife tasks (e.g., opening drawers and finding the toiletpaper inside drawer 2, or opening the destination drawer before fetching the knife), consistent with the 'open closed containers on reaching' clause; this added inspection steps in otherwise easy tasks (8 vs 4 steps, 7 vs 4, 10 vs 9) but did not prevent success. In simple tasks where the target was immediately reachable and cleaning was required (clean apple into diningtable, clean lettuce into fridge, clean plate into fridge), Candidate and Parent behavior was step-for-step identical (acquire, clean at sinkbasin, open the closed destination, place), and put-only tasks involved no cleaning detour, so the direct-completion and clean-only-if-required clauses did not degrade these cases. However, when the requested object was absent from every inspected receptacle, both Parent and Candidate fell into the same failure mode: in the dishsponge-on-shelf, kettle, and lettuce-to-diningtable tasks both reached the step limit, with the Candidate still shuttling repeatedly among already-inspected receptacles (though in the dishsponge task it opened more distinct cabinets than the Parent). Thus the 'do not immediately revisit an already-open empty receptacle' clause was not reliably followed and did not by itself break the cycling/step-limit failure mode. Limitations: one stochastic trial per task, the success improvement is concentrated in a single paired task, and the desklamp-scope narrowing could not be evaluated because no desklamp task was run.

**编辑—响应**：S1_R02 同时追加通用搜索/精确对象/条件clean/交付并收窄灯任务；P5失败，Q5在bathtubbasin找到dishsponge并clean/place成功；部分简单任务增步，循环仍有。

**支持的判断**：扩大覆盖与精确对象方向可有收益；开闭容器和必要交付要保留，避免宣称反循环提示稳定奏效。

**不能推出**：没有灯任务验证范围收窄效果；联合编辑不证明某顺序、禁止回访或某子句独立收益。

**原始evidence完整索引**：`S1_R02/diff`、`S1_R02/P1:1`、`S1_R02/P1:4`、`S1_R02/Q1:1`、`S1_R02/Q1:2`、`S1_R02/Q1:4`、`S1_R02/Q1:6`、`S1_R02/Q1:8`、`S1_R02/P2:4`、`S1_R02/Q2:3`、`S1_R02/Q2:4`、`S1_R02/Q2:5`、`S1_R02/Q2:7`、`S1_R02/P3:7`、`S1_R02/Q3:7`、`S1_R02/P4:50`、`S1_R02/Q4:19`、`S1_R02/Q4:42`、`S1_R02/Q4:50`、`S1_R02/P5:37`、`S1_R02/P5:42`、`S1_R02/P5:50`、`S1_R02/Q5:19`、`S1_R02/Q5:20`、`S1_R02/Q5:22`、`S1_R02/Q5:24`、`S1_R02/P6:50`、`S1_R02/Q6:12`、`S1_R02/Q6:50`、`S1_R02/P7:9`、`S1_R02/Q7:1`、`S1_R02/Q7:2`、`S1_R02/Q7:10`、`S1_R02/P8:50`、`S1_R02/Q8:50`、`S1_R02/P9:7`、`S1_R02/Q9:7`、`S1_R02/P10:7`、`S1_R02/Q10:7`。

## M6

**knowledge原文**

> The actual diff also rewrote the search step to add: use current and recent observations to avoid immediate cycling; do not re-examine an already-open empty receptacle or check inventory while carrying nothing; and, if the obvious cabinets/fridge have not yielded the target or the step count is already high, prefer uninspected drawers, shelves, the diningtable, or other listed receptacles and new unopened containers over returning to known-empty locations. The observed response is mixed. Positive case: in one cool-a-bread instance the Parent cycled among the fridge, cabinets and countertops and hit the step limit without finding bread, whereas the Candidate expanded to the diningtable (reached during search), took a bread there, cooled it at the fridge, and placed it on countertop 1, succeeding. Negative case: in a same-task pair with an identical room and identical container contents, the Parent explored countertop 3 and took the bread there, while the Candidate repeatedly visited countertop 2 but never went to countertop 3, cycled among cabinets, shelves and the fridge instead, and hit the step limit. In the cool-a-plate pair the Candidate repeatedly chose an unavailable move to cabinet 3 (falling back to a no-op) and then examined that already-empty location several times, reached the plate in cabinet 9 only at step 49, and exhausted the budget one step later while the Parent completed the same task at step 38 after finding the plate in cabinet 9. In the remaining unsolved tasks (cool a pan, heat a mug) both Parent and Candidate shuttled for many steps among the same cabinets, stoveburners and other receptacles instead of exhausting uninspected locations. Overall, the Candidate showed occasional broader exploration consistent with the edit (the diningtable find) but the anti-cycling/step-budget-priority language was not reliably followed, cycling and step-limit failures persisted, and the net task-level result across the ten pairs was slightly lower for the Candidate (6 successes vs 7), which is within plausible stochastic variation and cannot be attributed to this clause alone; each task was run once and location of the target varied across instances.

**编辑—响应**：S1_R03 修改搜索及反循环，联合精确对象/温度处理；Q4 diningtable找到bread获救，Q2漏同类countertop3而失败，Q6非法移动/空检查、49步才取plate导致未完成。

**支持的判断**：历史编辑后的收益与局限可校准覆盖单位、状态前提、预算与效果强度；不能只把它当几个额外失败例子。

**不能推出**：不证明类内穷尽或跨族一定优越，不支持固定阈值/永久动作禁令；7→6是联合单次结果。falling back措辞不代表Adapter fallback。

**原始evidence完整索引**：`S1_R03/diff`、`S1_R03/P2:15`、`S1_R03/P2:16`、`S1_R03/P2:18`、`S1_R03/P2:20`、`S1_R03/Q2:25`、`S1_R03/Q2:30`、`S1_R03/Q2:50`、`S1_R03/P4:50`、`S1_R03/Q4:12`、`S1_R03/Q4:13`、`S1_R03/Q4:15`、`S1_R03/Q4:17`、`S1_R03/P6:32`、`S1_R03/P6:33`、`S1_R03/P6:36`、`S1_R03/P6:38`、`S1_R03/Q6:4`、`S1_R03/Q6:10`、`S1_R03/Q6:15`、`S1_R03/Q6:48`、`S1_R03/Q6:49`、`S1_R03/Q6:50`。

## M7

**knowledge原文**

> Across two successive edits, the general non-desklamp procedure was augmented with temperature-transformation guidance: after acquiring the exact target, go to the fridge for cooling or the microwave for heating; if the explicit cool-X-with-fridge or heat-X-with-microwave action is already admissible, perform it immediately while holding the target and without first inserting it; open the appliance only when needed; do not treat moving the object into the appliance, closing or reopening the door, examining the appliance, or toggling it as completing the temperature change; and after the temperature action succeeds once, go directly to the requested destination for placement. Earlier evidence already showed that when the exact target was located, the Candidate applied the explicit cool or heat action while holding the object and avoided Parent-style insertion and door toggling, with large step savings and success in cool-pot, hot-apple, and heat-egg tasks. The current edit adds a separate temperature-conditioned placement item with the same operative requirements, and the same pattern recurred when the exact target was located: in a hot-potato-to-fridge task the Candidate heated the potato while holding it at the closed microwave and then placed it in 7 steps, while the Parent inserted the potato, closed and reopened the microwave, took it out, heated it, and then placed it in 14 steps; in a heat-tomato task the Candidate heated the tomato while holding it at the closed microwave and placed it on the countertop in 7 steps, while the Parent inserted it, repeatedly closed and reopened the microwave, then took it out and heated it for 21 steps. This supports a robust reduction in appliance manipulation and step use once the exact target has been acquired. However, the guidance does not ensure task success when target discovery fails: in a heat-plate pair the Parent found the plate on a countertop and succeeded in 13 steps, whereas the Candidate never reached that countertop, hit the 50-step limit, and never had an opportunity to apply the temperature action; in a hot-mug pair the exact mug was absent, both executions hit the step limit, and the Candidate's refusal to heat a cup substitute prevented ineffective substitute manipulation but did not produce success. The evidence therefore supports step and manipulation savings conditional on locating the exact target, while leaving search failures and stochastic variation as explanations for cases where the temperature guidance had no chance to help.

**编辑—响应**：S1_R03/R04 直接持物cool/heat、按可见合法动作处理并直送；R04 P3 14步/Q3 7步、P4 21步/Q4 7步；目标未找到时无法应用。

**支持的判断**：支持目标已获取且动作可用时保留明确温度操作和后续交付；校准u2 state-changing示例必须有前提。

**不能推出**：不能从总步数差异分离全部温度子句效应，不能拿来强制所有搜索后必成功或所有设备状态不需open。knowledge中absent类断言不作全局不存在依据。

**原始evidence完整索引**：`S1_R03/diff`、`S1_R03/P7:16`、`S1_R03/Q7:9`、`S1_R03/P8:19`、`S1_R03/P8:20`、`S1_R03/P8:33`、`S1_R03/Q8:7`、`S1_R03/P9:24`、`S1_R03/P9:36`、`S1_R03/P9:37`、`S1_R03/Q9:13`、`S1_R04/diff`、`S1_R04/P3:12`、`S1_R04/Q3:5`、`S1_R04/Q3:7`、`S1_R04/P4:19`、`S1_R04/Q4:5`、`S1_R04/Q4:7`、`S1_R04/P2:13`、`S1_R04/Q2:50`、`S1_R04/P1:28`、`S1_R04/P1:31`、`S1_R04/Q1:17`。

## M8

**knowledge原文**

> The actual diffs in this sequence tightened the exact-category rule by making explicit that a similar category is not a substitute, that near-miss objects must not be picked up, cleaned, cooled, heated, or placed for the requested target, and that search should continue across uninspected receptacles. Earlier evidence came from tasks where the exact target was absent: in a cool-a-pan task the Parent eventually took a pot and cooled and moved it, while the Candidate repeatedly saw the same pot without taking or moving it; in a heat-a-mug task the Parent took and moved a cup, while the Candidate saw the cup and did not manipulate it. Both executions still hit the step limit because the exact pan or mug was not found, so abstention saved only the substitution steps and did not convert those tasks into successes. The current edit adds the same no-substitute principle specifically inside the temperature-conditioned placement guidance, including a cup-versus-mug example. In the current hot-mug task the exact mug was absent, the Parent took cup 2 from the countertop and heated it, and both executions still hit the step limit; the Candidate left the visible cup untouched and continued searching with an empty inventory. This extends the earlier observation to hot-mug placement tasks: when the requested category is absent, the Candidate follows the no-substitute rule and avoids heating a near-miss object, whereas the Parent does not, but the abstention still does not create success because the exact target is not reachable or not located within the budget. The evidence supports only conditional usefulness: the rule prevents ineffective near-miss manipulation when exact targets are absent, but its task-level value depends on the exact target actually existing in an inspectable location; these observations do not show that it improves success by itself, and no observation isolates it from simultaneous temperature and search guidance.

**编辑—响应**：R03/R04 精确类别规则及温度条款共同加强；Parent操作pot/cup替代，Candidate避免相应近似物处理，仍有步限失败。

**支持的判断**：精确对象与不以替代物完成任务需保留；避免把“不操作替代物”误读为已经解决搜索。

**不能推出**：不能证明近似物回避独立提高成功率；absent与未找到需区分，不据此停止搜索。

**原始evidence完整索引**：`S1_R03/diff`、`S1_R03/P5:31`、`S1_R03/P5:35`、`S1_R03/Q5:8`、`S1_R03/Q5:19`、`S1_R03/P10:40`、`S1_R03/P10:41`、`S1_R03/Q10:36`、`S1_R03/Q10:37`、`S1_R04/diff`、`S1_R04/P1:28`、`S1_R04/P1:31`、`S1_R04/Q1:17`、`S1_R04/Q1:50`。

## M9

**knowledge原文**

> The current diff added a multi-instance find-and-place procedure: for tasks requiring multiple instances of the same exact category, treat the requirement as a count and count only exact-category instances; do not use a similar category as a substitute or treat a partial placement as complete; after placing one instance, if the current or recent observation shows another exact instance still at the source, return there and take it before expanding the search; otherwise resume searching uninspected plausible receptacles, including closed containers and open furniture or appliance surfaces; avoid repeatedly revisiting an already-open location that visibly lacks the exact target; and continue until the requested number of exact instances has been placed or all plausible locations have been inspected once. This was examined on five paired two-instance tasks. In a two-newspaper task both Parent and Candidate took one newspaper from the same coffeetable, placed it on the sofa, returned to the coffeetable for the second, and placed it successfully in 10 steps. In a two-saltshaker task both succeeded; the Candidate opened the cabinet, saw two exact saltshakers, took one, placed it on the sidetable, returned to the same cabinet, took the second, and placed it in 9 steps, while the Parent took the first from the countertop and then the second from the cabinet in 10 steps. In a two-candle task both succeeded and no substitute was used; the Candidate searched additional closed drawers 7 and 8 before reaching the countertop with two candles, then after placing the first candle returned to the countertop for the second and completed in 34 steps, whereas the Parent completed in 30 steps. Thus the return-to-source behavior was followed when another exact instance was visibly co-located at the source, and exact-count delivery was preserved, but extra container inspection can add steps before the target is found. In a two-keychain task both executions found and placed one keychain, could not locate a second exact instance, and hit the step limit; the Candidate did not return to the original sidetable because no second keychain was visible there, then searched repeatedly among open empty drawers. In a two-cd task neither execution found any exact cd, both hit the step limit, and the Candidate still revisited already-open empty shelves and drawers. The evidence therefore supports that the multi-instance guidance can preserve or produce exact-count placement when multiple exact instances are reachable, especially by returning to a source that visibly contains another instance, and that it did not cause substitution or regress the tasks where the count was achievable. It did not break the cycling and step-limit failure mode when the requested instances were absent or unlocated, and it can increase steps through broader closed-container inspection; each task was run once, and the multi-instance text was added together with the temperature text, so independent attribution is limited.

**编辑—响应**：R04 新增多实例计数/可见剩余目标回源，联合温度编辑；newspaper双方10步成功，saltshaker与candle回源成功但部分增步，keychain/cd仍失败。

**支持的判断**：约束绝对不回访的范围：来源当前/近期显示剩余目标时回源是有用行为；保留数量和交付，不能把已访问等同耗尽。

**不能推出**：当前R05没有多物体任务，跨任务应用需论证；不支持任意远期记忆、任何访问都可回返，或把多物体调度直接移植到所有搜索。

**原始evidence完整索引**：`S1_R04/diff`、`S1_R04/P8:8`、`S1_R04/Q8:8`、`S1_R04/P8:10`、`S1_R04/Q8:10`、`S1_R04/P9:8`、`S1_R04/P9:10`、`S1_R04/Q9:6`、`S1_R04/Q9:7`、`S1_R04/Q9:9`、`S1_R04/P6:23`、`S1_R04/P6:30`、`S1_R04/Q6:12`、`S1_R04/Q6:13`、`S1_R04/Q6:27`、`S1_R04/Q6:28`、`S1_R04/Q6:31`、`S1_R04/Q6:32`、`S1_R04/Q6:34`、`S1_R04/P7:28`、`S1_R04/P7:35`、`S1_R04/Q7:18`、`S1_R04/Q7:21`、`S1_R04/Q7:50`、`S1_R04/P5:50`、`S1_R04/Q5:50`。

## 四份真实Diff（未改写）

### S1_R01/diff

```diff
--- /dev/null
+++ b/SKILL.md
@@ -0,0 +1,22 @@
+# Desklamp-Conditioned Inspection
+
+Use this procedure when a task requires an object to be looked at or examined under or with a desklamp.
+
+## Procedure
+
+1. Locate the desklamp and one matching target object.
+2. Establish co-location at the desklamp's receptacle before completing the task:
+   - If the target is already on the desklamp's receptacle, remain there.
+   - If the target and lamp are on different receptacles, pick up one candidate target and carry it to the desklamp, or place it at the desklamp's receptacle.
+3. Turn on the desklamp.
+4. Pick up the target there (or keep holding it) and perform the requested look/examine, or use the lamp, while the target is held or otherwise co-located at that receptacle.
+
+## Constraints
+
+- Ensure the desklamp is on and the target is held or otherwise co-located at that receptacle before finishing.
+- Inspecting the receptacle alone is not a substitute for interacting with the requested object.
+- Do not repeatedly toggle the lamp while the target is at a different receptacle.
+- Do not move the target away after turning on the lamp.
+- Do not shuttle multiple same-type candidates between locations; remain at the lamp and finish with one co-located target.
+
+Keep the successful search, acquisition, and placement behavior used in non-desklamp transfer tasks.
```

### S1_R02/diff

```diff
--- a/SKILL.md
+++ b/SKILL.md
@@ -1,6 +1,6 @@
 # Desklamp-Conditioned Inspection
 
-Use this procedure when a task requires an object to be looked at or examined under or with a desklamp.
+Use this procedure only when the task explicitly requires inspecting, examining, or using an object under or with a desklamp. For ordinary put, clean, or transfer tasks where no desklamp is required, do not spend steps searching for, turning on, or co-locating with a desklamp; follow the general retrieval, cleaning, and placement procedure below instead.
 
 ## Procedure
 
@@ -19,4 +19,13 @@
 - Do not move the target away after turning on the lamp.
 - Do not shuttle multiple same-type candidates between locations; remain at the lamp and finish with one co-located target.
 
+## General Non-Desklamp Retrieval, Cleaning, and Placement
+
+For ordinary put, clean, or transfer tasks where no desklamp is required, use this procedure instead.
+
+1. Identify and search for the exact requested target. If it is not visible, search systematically: open any closed cabinet, drawer, or fridge immediately upon reaching it and inspect its contents before leaving. Do not immediately revisit an already-open receptacle that visibly lacks the target; choose a different uninspected candidate location instead. Do not repeatedly check inventory while carrying nothing. Continue until the exact target is found or all plausible candidate receptacles have been inspected once.
+2. Manipulate only the exact requested target category. Do not pick up, clean, or place a substitute object when the exact target is absent; for example, do not transfer a soapbottle when the task requests a dishsponge. If the exact target has not yet been found, continue the systematic search rather than completing the transfer with a non-target object.
+3. Acquire the exact target. If the task requires the object to be clean, carry it to an appropriate cleaning receptacle such as a sinkbasin and perform the clean action. If no cleaning is requested, skip the cleaning detour.
+4. Go directly to the requested destination. Open it first if it is closed, then place or move the target there. Do not detour to unrelated receptacles or release the target before the requested placement is completed.
+
 Keep the successful search, acquisition, and placement behavior used in non-desklamp transfer tasks.
```

### S1_R03/diff

```diff
--- a/SKILL.md
+++ b/SKILL.md
@@ -1,6 +1,6 @@
 # Desklamp-Conditioned Inspection
 
-Use this procedure only when the task explicitly requires inspecting, examining, or using an object under or with a desklamp. For ordinary put, clean, or transfer tasks where no desklamp is required, do not spend steps searching for, turning on, or co-locating with a desklamp; follow the general retrieval, cleaning, and placement procedure below instead.
+Use this procedure only when the task explicitly requires inspecting, examining, or using an object under or with a desklamp. For ordinary put, clean, cool, heat, or transfer tasks where no desklamp is required, do not spend steps searching for, turning on, or co-locating with a desklamp; follow the general retrieval, cleaning, temperature-transformation, and placement procedure below instead.
 
 ## Procedure
 
@@ -19,13 +19,14 @@
 - Do not move the target away after turning on the lamp.
 - Do not shuttle multiple same-type candidates between locations; remain at the lamp and finish with one co-located target.
 
-## General Non-Desklamp Retrieval, Cleaning, and Placement
+## General Non-Desklamp Retrieval, Cleaning, Temperature Transformation, and Placement
 
-For ordinary put, clean, or transfer tasks where no desklamp is required, use this procedure instead.
+For ordinary put, clean, cool, heat, or transfer tasks where no desklamp is required, use this procedure instead.
 
-1. Identify and search for the exact requested target. If it is not visible, search systematically: open any closed cabinet, drawer, or fridge immediately upon reaching it and inspect its contents before leaving. Do not immediately revisit an already-open receptacle that visibly lacks the target; choose a different uninspected candidate location instead. Do not repeatedly check inventory while carrying nothing. Continue until the exact target is found or all plausible candidate receptacles have been inspected once.
-2. Manipulate only the exact requested target category. Do not pick up, clean, or place a substitute object when the exact target is absent; for example, do not transfer a soapbottle when the task requests a dishsponge. If the exact target has not yet been found, continue the systematic search rather than completing the transfer with a non-target object.
+1. Identify and search for the exact requested target. If it is not visible, search systematically. Use the current and recent observations to avoid immediate cycling. Open any closed cabinet, drawer, or fridge immediately upon reaching it and inspect its contents before leaving. If an already-open receptacle visibly lacks the exact target, do not re-examine it or check inventory while carrying nothing; choose a different listed receptacle instead. If the obvious cabinets or fridge have not yielded the target, inspect uninspected drawers, shelves, the diningtable, or other listed receptacles instead of returning to empty locations already seen. Continue opening new containers or visiting new locations until the exact target is found or all plausible candidate receptacles have been inspected once. If the step count is already high and the target remains unfound, prefer a new unopened container or unvisited listed location over another check of a prior empty receptacle.
+2. Manipulate only the exact requested target category. A similar category is not a substitute: a pot is not a pan, and a cup is not a mug. If only near-miss objects are visible at a location, treat the requested target as not found there and continue searching uninspected receptacles. Do not pick up, clean, cool, heat, or place a near-miss object, because doing so consumes steps without satisfying the task. For example, do not transfer a soapbottle when the task requests a dishsponge.
 3. Acquire the exact target. If the task requires the object to be clean, carry it to an appropriate cleaning receptacle such as a sinkbasin and perform the clean action. If no cleaning is requested, skip the cleaning detour.
-4. Go directly to the requested destination. Open it first if it is closed, then place or move the target there. Do not detour to unrelated receptacles or release the target before the requested placement is completed.
+4. For tasks requiring a temperature change, go to the appropriate appliance after acquiring the exact target: the fridge for cooling and the microwave for heating. If the explicit "cool X with fridge" or "heat X with microwave" action is already admissible, perform it immediately, including while holding the target and without first inserting it. Open the appliance only when needed to make the action available or to handle the target. Do not treat moving the object into the appliance, closing or reopening the door, or examining the appliance as completing the temperature change, and do not leave the object in the appliance without applying the temperature action.
+5. After any required cleaning or temperature action succeeds, go directly to the requested destination. Open it first if it is closed, then place or move the target there. Do not detour to unrelated receptacles or release the target before the requested placement is completed.
 
-Keep the successful search, acquisition, and placement behavior used in non-desklamp transfer tasks.
+Keep the successful exact-target search, acquisition, cleaning, temperature transformation, and placement behavior used in non-desklamp tasks.
```

### S1_R04/diff

```diff
--- a/SKILL.md
+++ b/SKILL.md
@@ -28,4 +28,8 @@
 3. Acquire the exact target. If the task requires the object to be clean, carry it to an appropriate cleaning receptacle such as a sinkbasin and perform the clean action. If no cleaning is requested, skip the cleaning detour.
 4. Go directly to the requested destination. Open it first if it is closed, then place or move the target there. Do not detour to unrelated receptacles or release the target before the requested placement is completed.
 
+5. Temperature-conditioned placement: If the task requires the exact object to be hot or cool before placement, first identify and acquire the exact requested object category. Do not heat, cool, carry, or place a similar substitute (for example, do not treat a cup as a mug or a pot as a pan) when the exact category has not been found. If the exact target is not visible, continue the systematic search across uninspected receptacles, including closed drawers, cabinets, the fridge, and open surfaces, rather than settling for a nearby similar object. Once holding the exact target, go to the appropriate appliance. If the explicit "heat X with microwave" or "cool X with fridge" action is already admissible, perform it immediately while holding the target and without first inserting it. If the action is not yet admissible, open the appliance only as needed to make it available, then perform the temperature action while holding the target. Do not treat moving the object into the appliance, closing or reopening its door, examining the appliance, or toggling it as completing the temperature change, and do not leave the object in the appliance without applying the temperature action. After the required temperature action succeeds once, go directly to the requested destination and perform the required placement or move; do not return to the heat/cool source or repeat open/close/move cycles after the temperature action.
+
+6. Multi-instance find-and-place: For tasks requiring multiple instances of the same exact target category to be found and placed, treat the requirement as a count and count only exact-category instances; do not use a similar category as a substitute or treat a partial placement as complete. After placing one instance, if the current or recent observation shows another exact instance still at the source, return there and take it before expanding the search; a source that visibly contains another exact instance is not an empty revisit. Otherwise resume searching for another exact instance and choose an uninspected plausible receptacle type, including closed containers (opened when reached) and open furniture or appliance surfaces such as countertops, diningtables, coffeetables, sidetables, stoveburners, shelves, cabinets, drawers, fridge, sofa, armchair, bed, and dresser, not only the most obvious drawers, shelves, or cabinets. If zero or one instance has been found, do not repeatedly revisit a location that is already open and visibly lacks the exact target; use the current and recent observations to avoid immediate cycling. Continue until the requested number of exact instances has been placed or all plausible listed receptacles and containers have been inspected once; if the count is still unmet after that, do not substitute a different object or stop as if the count were complete.
+
 Keep the successful search, acquisition, and placement behavior used in non-desklamp transfer tasks.
```

来源执行全文已经在冻结Memory sources中，不再复制独立轨迹。M6具体核查见P2报告；当轮sources只展开被引用run，不代表完整重放所有历史任务。B是整个Active包的处理，不是M6单条消融。即使B差异涉及M6，M3/M7/M8/M9和上下文组织也可能共同影响。

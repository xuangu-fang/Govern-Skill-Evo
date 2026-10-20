# P2：M6 / M10 语义保真核查

**结论：M6 的主要混合反馈准确，不需要先改写。M10 确认存在“新位置→新类别”的事实单位混淆，以及“未找到→不存在”的证据越界；准确 Diff 和被引用执行仍在 R06 实际请求中。不能据此证明 Memory 偏差造成了 Keep，更不能保证改写后会改善决策。**

只分析正式 Train。未使用 Test，未使用 R06 结束后的 M12/M13。原始文件、JSON 字段、task/game 哈希见[来源与原始执行索引](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_memory_evidence_audit_001/reports/SOURCE_INDEX.md)；离线结果见[离线核验结果](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_memory_evidence_audit_001/results/receipt.json)。

## 1. 快照与传递链

| 调用 | 实际 Active 所在目录 | Active IDs | 本次关注 |
|---|---|---|---|
| R05 | rounds/R04/memory | M1 M2 M3 M6 M7 M8 M9 | M6；**没有 M10** |
| R06 | rounds/R05/memory | M1 M2 M6 M7 M9 M10 M11 | M6 与 M10 |

两轮由 `preconditioner/result.json` 定位实际 attempts/001。核验 `request.body.messages == messages_for(saved)`，解析出的 Memory 与保存 input、round_input 以及当时 Active/commits 重载完全一致。两轮有 HTTP 响应、response 和 valid 结果；这是历史实际请求，不仅是磁盘存在或静态装配。仅凭客户端归档不能判断服务端注意力或模型是否理解每条事实。

M6 两轮内容完全相同，来源 S1_R03。M10 来源 S1_R05，只用于 R06。`load_memory` 对每项 evidence 加入完整 Parent/Diff/Execution Context；引用某一步会展开该条历史 run 的完整 initial、before/action/after/feedback/outcome 及相关完整候选表，**不等于展开该历史轮的全部任务**。

- M6 自身引用 P2/Q2、P4/Q4、P6/Q6；当时其他 Active entries 还带入 S1_R03 的 P5/Q5、P7/Q7、P8/Q8、P9/Q9、P10/Q10。共 8 对，未含 P1/Q1、P3/Q3，不能仅凭该请求独立重算十对 7/10→6/10。
- M10 引用且 R06 实际携带 S1_R05 的 P6/Q6、P7/Q7、P8/Q8、P10/Q10，共 4 对；完整十对在不可变 archive，本次离线核对 7/10→9/10。其余六对不在 R06 sources，不声称所有汇总依据都逐条传入。
- 本次从原始 record 重建 S1_R03、S1_R05 全部 40 条 facts，核对源 run、候选、反馈及配对 task/game/seed；严格应用实际 Diff 得到原 Candidate。不是重跑环境，也不是对事实概括的自动语义评分。

## 2. M6 原文与实际支持

原文来自 R05/R06 `memory.entries[id=M6].knowledge`，完全相同：

> The actual diff also rewrote the search step to add: use current and recent observations to avoid immediate cycling; do not re-examine an already-open empty receptacle or check inventory while carrying nothing; and, if the obvious cabinets/fridge have not yielded the target or the step count is already high, prefer uninspected drawers, shelves, the diningtable, or other listed receptacles and new unopened containers over returning to known-empty locations. The observed response is mixed. Positive case: in one cool-a-bread instance the Parent cycled among the fridge, cabinets and countertops and hit the step limit without finding bread, whereas the Candidate expanded to the diningtable (reached during search), took a bread there, cooled it at the fridge, and placed it on countertop 1, succeeding. Negative case: in a same-task pair with an identical room and identical container contents, the Parent explored countertop 3 and took the bread there, while the Candidate repeatedly visited countertop 2 but never went to countertop 3, cycled among cabinets, shelves and the fridge instead, and hit the step limit. In the cool-a-plate pair the Candidate repeatedly chose an unavailable move to cabinet 3 (falling back to a no-op) and then examined that already-empty location several times, reached the plate in cabinet 9 only at step 49, and exhausted the budget one step later while the Parent completed the same task at step 38 after finding the plate in cabinet 9. In the remaining unsolved tasks (cool a pan, heat a mug) both Parent and Candidate shuttled for many steps among the same cabinets, stoveburners and other receptacles instead of exhausting uninspected locations. Overall, the Candidate showed occasional broader exploration consistent with the edit (the diningtable find) but the anti-cycling/step-budget-priority language was not reliably followed, cycling and step-limit failures persisted, and the net task-level result across the ten pairs was slightly lower for the Candidate (6 successes vs 7), which is within plausible stochastic variation and cannot be attributed to this clause alone; each task was run once and location of the target varied across instances.

### 真实编辑边界

S1_R03 actual.diff 的搜索修改加入当前/近期观察、当明显 cabinets/fridge 未找到时转向 drawers/shelves/diningtable/其他位置、高步数优先新位置；同时联合修改精确类别、直接持物温度处理和处理后交付。Parent 已有打开闭容器、避免立即空回访、空手 inventory、全部合理位置检查一次等基础规则。因此 knowledge 的 `rewrote ... to add` 不能解释为每个提到的子句都是新创造，但未发现它据此错误分配独立收益。

实际修改全文在来源索引的 R03 actual.diff；不含固定批次、类内穷尽后才能换类、永久动作禁令。

| 原始配对证据 | 可支持认识 | 不能推出的要求／核查判断 |
|---|---|---|
| S1_R03 P4 50步失败；Q4:12 到 diningtable，13 取 bread，15 cool，17 place 成功 | Candidate 这一次扩大到了有目标的位置，行为与扩展搜索方向一致 | 不能分离搜索和新增温度处理的贡献，更不能证明 diningtable 必须优先或固定跨类别顺序最优。M6 已用 consistent / mixed 限定，准确 |
| P2:15 countertop 3、16 取 bread、18 cool、20 place 成功；Q2 50步失败，多次 countertop 2（25/30/36），没有到 countertop 3 | 同类别实例仍可能遗漏；联合新 Skill 并不稳定避免循环／遗漏 | 不支持“类别轮换导致遗漏”或“必须穷尽类别后切换”。两端同 task/game hash/seed/初始状态；并非不同任务难度解释此对差异。M6 没有写出强制反向规则 |
| P6:31 到 cabinet 9，32 open，33 取 plate，36 cool，38 place；Q6:47 到 cabinet 9、48 open、49 take、50 到 fridge 结束 | Candidate 找得太晚，未留下足够完成步骤；动作/覆盖效率是局限 | 不证明应固定保留多少步，也不能把退化归因于某一个搜索子句 |
| Q6:4/10/15/20/26/37 选不可用 `go to cabinet 3`，结果 Nothing happens；其后多次 examine 空位置 | 当时动作前提不成立、重复无进展；当前候选及状态应参与选择 | raw `fallback` 为 null，不能将 knowledge 的 `falling back to a no-op` 当作 Adapter 自动 fallback。它可描述无效结果，但工程机制措辞不准；不支持永久禁止 go/examine，M6 也没有提出这种禁令 |
| P5/Q5 cool pan、P10/Q10 heat mug 均50步失败；全十对7→6 | 混合反馈、循环仍存在；新编辑未稳定解决问题 | “within plausible stochastic variation”是合理可能性而非统计检验；各实例一次且联合编辑，因果未隔离。M6 明确保留此限制 |

**M6 判定：** 核心观察、反例、条件与单次联合编辑的不确定性保真；没有发现足以要求先重写 M6 的策略级错误。仅需在研究解释中避免把 no-op 称为程序 fallback、把略降结果称为已证实随机波动。M6 已能约束“新方向必然覆盖所有实例/稳定无循环”等过强解释，不能唯一决定搜索调度。策略优劣未知不等于 Memory 错误。

## 3. M10 原文与实际支持

原文来自 R06 `memory.entries[id=M10].knowledge`：

> The general non-desklamp search step was rewritten from a broad 'open closed containers and continue until found, avoiding immediate revisits' instruction into an explicit single-pass family sweep: open each closed container once, use recent observations, and after one family (for example drawers) yields nothing, move to a different uninspected family (cabinets, shelves, countertops or other surfaces, appliances) before revisiting any earlier location, while keeping the sweep within the step budget. In paired non-desklamp tasks this was associated with two additional successes where the exact target lay in a family the Parent never reached: in a put-a-clean-butterknife-in-drawer task the Parent opened many drawers and some countertop/sink locations but hit the step limit without checking countertop2, where the Candidate found the exact butterknife, cleaned it at the sinkbasin, and placed it in drawer1; in a put-a-clean-soapbar-in-cabinet task the Parent cycled among cabinets, sinkbasin, and countertop without checking shelf1, while the Candidate eventually checked shelf1, found the exact soapbar, cleaned it, and placed it in cabinet1. The revised sweep did not reliably prevent cycling: in a clean-butterknife pair where no exact butterknife was present, both executions hit the step limit and the Candidate still cycled among drawers, countertops, and cabinets; in a cool-apple pair both succeeded, but the Candidate required more steps (46 vs 38) and revisited many already-seen empty locations before reaching the diningtable apple. Across the ten paired tasks the Parent succeeded 7/10 and the Candidate 9/10, with no observed regression on tasks the Parent already solved, but each task was run once; the two rescues depended on the exact target being present in an uninspected family, and the evidence does not show that the sweep overcomes step-limit cycling when the target is absent or not located within the budget.

### 真实 Diff 与 summary 的差别

S1_R05 actual.diff 的关键原句：

> run a single-pass sweep that spreads across distinct receptacle families rather than exhausting or looping over one type.

后文要求新位置、近期观察避免空回访；一族没有收获后切到不同未检查族，再回访先前位置；预算内扩大容器与表面覆盖；直到找到精确目标或所有合理 **receptacles** 一次。另一个联合编辑强化 knife/butterknife 等精确类别。

M10 保留了跨族方向、single-pass、换族先于回访、预算及混合反馈；**省略了 `rather than exhausting` 这个直接影响调度比较的限定**。保留的 `after one family ... yields nothing` 可被理解成查部分或查完一族，弱化了策略对比的清晰度。但它没有明确要求类内穷尽；也不能把 Diff 反对困在一类解释为隔离实验证明所有类内穷尽都坏。

| 判断点 | 原轨迹／字段 | 结论与支持边界 |
|---|---|---|
| butterknife 修复是否是进入新类别 | S1_R05 P6:3 已到 countertop 1，后续7/11/15又到；Q6:3 也到 countertop 1，16 到 countertop 2 看见 butterknife，17取、19clean、21place；Parent50失败 | **确认事实单位混淆。** countertop 1 与2是同类不同实例。支持到达此前遗漏的位置，不能把该修复称为 Parent 从未进入的 family。M10 自己同时写 Parent 到过 countertop，内部已可发现张力 |
| soapbar 修复 | P8 50步无 shelf 1；Q8:18 到 shelf1、19取、21clean、23place | 这里确实新增了 shelf 类覆盖；但Q8先开cabinet1–4且仍回访，不是严格无循环调度的示范。该例不能替 butterknife 例纠正覆盖单位 |
| “no exact butterknife was present” | P7/Q7均50步未找到；初始候选含 cabinet1–18 等。P7只到部分 cabinets、Q7更少；仍有多个未查位置 | **现有来源不足以证明环境中不存在目标。** 应区分未发现与全局不存在。不是已证明物体实际存在，也不能用任务名称作为存在性 oracle |
| near-match 的联合影响 | P7:5取 knife，7clean，9place；Q7未重复此替代物处理，但仍失败 | 整体失败不等于所有行为无改善；成功／失败不能独立归因于搜索策略 |
| 循环与增步 | P10 apple38步成功；Q10到diningtable为40、最终46步；均成功但Q多次回访 | M10准确保留局限；不能承诺跨族一定更快或不再循环 |
| 总结果7→9、已成功任务无新增失败 | archive全部十对离线核对一致；R06 sources仅其中四对 | 汇总准确，单次联合编辑；统计与因果边界未消失。`rescues depended ... uninspected family`对两次救回一并使用仍错误扩大单位 |

### 对实际策略决策的影响分层

1. **已证实的语义问题**：新实例被概括为新类别；未发现被提升为不存在；省略 actual.diff 的反类内耗尽限定。
2. **决策风险**：容易把覆盖收益理解成“类别级调度已获支持”；模糊的 family yields nothing 可被不同调度吸收；目标不存在断言可能误导停止边界。但这些是风险，不能断言实际发生某种停止调整。
3. **实际已观察的决策**：正式 R06 `preconditioner.reason` 写 `M6/M10 support the uninspected-family sweep as a direction even though it is not a guaranteed cure`，并据两步历史认为 ordered memory-independent sweep 合适，adjustments=[]。最终保留原始类内穷尽 Update，未在显式理由中解释与原 Diff 调度的差别。**这证明支持范围没有在显式判断与最终变换中充分展开，不证明 M10 概括是造成 Keep 的原因。**准确 Diff/轨迹确实在输入；Goal、当前证据解释及随机性也可能相关。

因此归类为“**概括存在偏差，但关键原始依据已传入**”。部分断言是重要事实边界错误，并非全面证据缺失。为评估纠偏作用，未来可以单独冻结修正概括的实验副本；本次不改历史 Memory，不把这种试验混入 R05有/无Memory主比较，更不能承诺修正后必有效。

## 4. 对后续的约束

- R05只可用当时 M6 等 Active；M10不是其历史，不能为了有利反例加入。
- M6可提供“过去真实编辑后的混合响应”，超出当前循环事实；但不决定唯一搜索顺序。
- M10支持研究具体遗漏位置/类别与调度假设的关系；不支持固定类别排序、采样阈值、永久禁回访、未找到就宣告不存在。
- 原始 source 的可获得性与正确使用必须分别检验。下一阶段有无Memory比较才可能观察增量决策作用；本阶段没有这种结果。

方法、Prompt、Memory、历史归档未由本次修改；零新增模型、Token及环境调用。见[保护核验](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_memory_evidence_audit_001/results/protection.json)。

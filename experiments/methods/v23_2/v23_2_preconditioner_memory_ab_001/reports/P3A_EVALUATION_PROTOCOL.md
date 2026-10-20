# P3-A：预注册评价与归因协议

**本协议在任何P3-B模型调用前冻结。A/B响应字段全部留空。本文研究注释不进入请求。**

## 1. 比较前先独立评价

先验证输出契约与编译，再依次读每组完整reason、adjustments（含basis、reason及to.text）、有效Checks和Effective updates。明确ready/Keep、局部撤回、no_change及need_evidence；记录被改、未改、合并拆分的所有行为要求，不以Adjustment数判断。

逐项记录策略、触发条件、适用范围、强制程度、顺序、完成/停止前提及保留行为。Goal程序原样保留，不能把Goal文字仍在当成Update必然保留了行为。Checks是未来观测问题，不能当成Actor会执行的补救指令。

不以关键词、篇幅或更谨慎的措辞评分；不预设类内穷尽错误、跨类别轮换正确；大幅调整及明确操作均可合理。区分明确可纠正的前提错误、支持不足的必要性主张和仍值得探索的新假设。

## 2. 两组共同拥有的事实与判断边界

| 项目 | 当前实际证据 | 可纠正／保留 | 不可推导 |
|---|---|---|---|
| 覆盖/循环 | P3:7–11重复空drawer，P6/P8遗漏与循环，P10:32晚找到 | 减少无信息重复，不能把局部观察当全局已检查；目标发现后进入必要处理交付 | 某一种编号穷尽/类别轮换/排序已被证明最优 |
| Actor能力 | 原Execution Context：当前观察/候选、两组行动前历史、步数 | 要求全局耗尽状态需可恢复依据；允许依当前编号或近期结果的局部探索 | 当前没出现等于从未访问；只要使用编号就天然可执行或天然错误 |
| no-op/信息获取 | P1:4不可用移动；P7:11–12相同look；P8:39、P10:25空inventory | 把无效重复限定于相关状态和前提；保存有新信息/前提改变后的必要操作 | 单次无效证明以后所有等价动作都无效；所有信息动作都应禁止 |
| 有效行为 | Parent/Goal/G1、P1:2/8/9；P3:14/16；P7替代knife失败；P10:33/35/38 | 精确对象、灯共址、获取、必要处理及交付；寻找新位置不得无条件排除有用目的地 | 原轨迹未选全文就说明该行为从未发生；仅凭Goal保留便可忽略Update冲突 |

这些修正即使只出现在B，仍可能是Memory促发模型注意当前证据，**不能直接叫作独有历史信息收益**。A没修正不等于A没有相应证据。

## 3. 历史包的额外信息及来源

[Memory原文、Diff和source引用](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/reports/P3A_MEMORY_EVIDENCE.md)保存七条knowledge原文、每项实际Diff/执行索引、支持与不支持的判断。B整体包含M1/M2/M3/M6/M7/M8/M9，不是M6独立消融。

M6最重要的增量不是又出现了循环，而是：**过去确实写过某些扩展搜索/反循环规则，执行既出现覆盖收益，也留下同类遗漏、无效移动和过晚获取；效果与方向并不等价。** 这种编辑与响应联系可以限制效果保证或改变适用条件，但不唯一决定替代调度。

M1/M2灯与非灯行为保留、M3通用联合编辑混合响应、M7直接温度操作前提、M8近似物回避但未救回、M9有条件回源与计数，均可能影响B。因此评估时逐项定位所用Memory/source；多个共同支持时全部列出，不虚构单条归因。

本实验不纠偏旧knowledge，也不视其为真值oracle。M7/M8等出现absent措辞时，只能按实际sources判断“未找到”的范围，不得据此新增全局不存在/搜索结束条件。对未专门审计的断言标明不确定性，不在本阶段扩大为全面Memory审计。

## 4. 四类结果与两级历史作用

| 分类 | 操作判据 | 如何报告 |
|---|---|---|
| 当前证据纠正 | 改动的理由可由两组共有当前事实/任务/Actor能力成立；无具体历史响应额外链条 | 修正可以有价值，但不直接算Memory增量。若仅B修正，记录“B独有当前证据纠正，机制归因未明” |
| 历史响应增量线索 | B与A有实质差异；历史真实编辑、对应行为响应和当前差异适用关系可追溯；差异本身合理且未破坏保留要求 | 分开历史信息影响与编辑—响应预条件化，均只称单次线索 |
| 无依据新承诺 | 原/新要求增加顺序、次数、排他、终止、效果保证等，却无对应证据或清楚可检验问题假设；或有动机但附带约束超出其支持 | 不算改善。即使引用Memory、发生Adjustment或A也犯错也不豁免 |
| 无实质更新差异 | Effective行为语义等价；只有reason引用、措辞、ID或篇幅不同 | 未观察到具体Update增量。Checks差异可单列“观测设计变化”，不冒充Actor策略变换 |

四类是研究判定，不加入模型Schema；同一个Update可有局部历史增量和局部新风险，不能用一个“通过”掩盖混合结果。

**历史信息影响**：B用了额外案例/总结，产生可定位的不同要求，但未把实际编辑与响应联系起来。例如只借旧任务中某目标位置给出新规则。这最多是历史信息相关线索；若有不当推广，仍属无据承诺。

**编辑—行为响应预条件化线索**必须同时具备：

1. 指明旧Skill具体修改（source Diff），不是只有相似任务目标。
2. 指明对应实际行为改善/反例/副作用及适用条件，保留联合编辑归因限制。
3. 说明该联系为何改变当前Update某一具体要求，而非给reason加一条引用。
4. 在最终Effective文本中找到实际改变，或有依据保留了A错误删掉的要求；核查其他有效行为没有被无据破坏。

若模型未明确提供链条，而研究者从sources推断有联系，必须标为“与历史相容的研究者推断”，不能补写成模型已利用该机制。显式reason也只证明其表述依据，不证明隐藏因果推理。

## 5. 组间判定流程

1. **锁定对照有效性**：哈希、唯一Memory差异、服务端模型/参数一致；任一失败不做正常AB归因。
2. **每组独立评价**：对u1/u2逐项区分有效要求、可探索假设、过强/不可执行承诺、新退化；准备/Keep本身不等于错。
3. **语义差异定位**：写出A/B实际句子和行为差异，不能仅列reason或调整数量。合并拆分按原u1/u2来源追踪，不只对ID。
4. **先扣除共有依据**：列出共有当前证据已能支持的部分。A修正、B同样修正不算增量；B独有修正也需查历史是否提供不同支持。
5. **追溯历史增量链**：Memory ID→Diff→配对动作/条件→对当前差异的支持/局限。分事实、判断、探索假设，禁止将整体胜负归因单条编辑。
6. **检查附带损害**：固定阈值/顺序、绝对禁回访、一次类别采样就停、保证进展或额外任务限制是否有独立依据；不因一个差异合理而整体通过。
7. **给限定结论**：当前纠正、历史信息线索、响应预条件化线索、无依据变化或无实质变化。B Keep/A Adjust允许前者合理；A提出与历史相似的策略不构成偷偷使用Memory。
8. **结果/停点完整性**：合法语义停点按原契约，缺失响应/技术失败不当作语义失败。只有一组有效时可独立分析，不能声称已完成两组增量比较。

单次对照没有排除生成随机性、不同上下文长度/注意力、顺序及后端变化；没有检验Skill行为，因此不能独立证明任何具体编辑的因果收益。

## 6. 冻结评价模板

机器模板：[evaluation_template.json](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/config/evaluation_template.json)。以下结果格为空；P3-B在新结果目录复制填写，不改本模板。

### u1

**Original Update原文**

> During any search for the exact requested object (or for the desklamp once the target is in hand), treat the search as coverage of distinct candidate receptacles rather than a loop over a few. When the current observation shows the requested item is absent, move to a receptacle not yet inspected in this search, while retaining the existing rule to open a closed cabinet/drawer/fridge on arrival and inspect its contents. Sweep a numbered series of same-type containers in one direction without returning to earlier ones; once that series is exhausted without the target, switch to a different receptacle type (e.g., from drawers to cabinets, countertops, fridge, shelves, or sinkbasin) before re-entering the series. Use the most recent observations to notice when the next move would revisit a receptacle just left empty or repeat the same small set of locations, and in that case choose a different uninspected candidate. This is coverage for finding the exact target within the step budget; it does not permit picking up, conditioning, or placing a substitute object.

| 字段 | 内容 |
|---|---|
| 已知问题/当前依据 | P3:7–11空drawer回访、13–16找到mug后交付；P6/P8循环且部分位置未到；P10:32才发现apple，33/35/38获取处理交付。支持减少重复和覆盖遗漏，不证明唯一顺序。当前/候选/两步历史不等于全局visited；G1和Goal提示有用回返/共址要保留。 |
| 历史增量 | M6的真实搜索编辑既有diningtable收益，也有同类countertop3遗漏和49步才获取的预算失败；M3混合覆盖与精确目标反馈；M9有条件回源及增步；M1/M2/M7/M8提供应保留行为及条件。 |
| A组决策/reason/Adjustment/Checks |  |
| B组决策/reason/Adjustment/Checks |  |
| Effective A |  |
| Effective B |  |
| 具体差异：策略/条件/范围/强度/组合 |  |
| 差异依据：当前或历史Diff/轨迹 |  |
| 新承诺与必要行为风险 |  |
| 归因边界 |  |
| 结论 |  |

### u2

**Original Update原文**

> Do not spend steps on actions that cannot change the world or reveal new information. If an action returns 'Nothing happens,' if a 'look' repeats the description you already have for the current receptacle, or if 'inventory' is issued while carrying nothing, do not repeat that action or an equivalent one. Instead immediately take a state-changing action: move to a new uninspected receptacle, open a closed container, take the target, perform the required clean/cool/heat, or place the target at the destination.

| 字段 | 内容 |
|---|---|
| 已知问题/当前依据 | P1:4不可用go shelf2→Nothing happens；P7:11/12重复look；P8:39/P10:25空手inventory。支持状态不变时避免无信息重复，不支持状态改变后永久禁止同动作或等价动作，也不证明一切信息获取都应立即换成state-changing。 |
| 历史增量 | M6候选仍重复不可用移动与空位置检查，提示反循环条款未稳定落实而非应禁止整类动作；M7动作可用/持物温度处理及交付条件，M8精确对象，M9有效回源提供范围保留。 |
| A组决策/reason/Adjustment/Checks |  |
| B组决策/reason/Adjustment/Checks |  |
| Effective A |  |
| Effective B |  |
| 具体差异：策略/条件/范围/强度/组合 |  |
| 差异依据：当前或历史Diff/轨迹 |  |
| 新承诺与必要行为风险 |  |
| 归因边界 |  |
| 结论 |  |

Goal全文与原Checks保留在机器模板及原Plan快照。检查u1/u2的联合依赖：收窄u1不能使u2无前提去处理/交付，改u2也不能允许替代物完成任务。未调用Editor，不能判断实际Patch会怎样实现。

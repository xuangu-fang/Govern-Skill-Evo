# P3-C1 承诺追溯

本报告只使用最近合法同格式Prompt配对：[A_format_001](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/p3b_A_format_001/runs/A/preconditioner.json)、[B_format_001](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/p3b_B_format_001/runs/B/preconditioner.json)。Original来自[R05 P1-B授权重试Diagnosis](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23_2/v23_2_diagnosis_construction_001_r05_retry_001/R05/attempts/001/diagnosis.json)的`plan`。不混用原B、无效A或旧正式Plan。没有新增模型、环境、编译输出或Candidate。

[材料路径及哈希](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_commitment_analysis_001/config/comparison_manifest.json)核验：完整请求删除唯一`memory`字段后相同；A空Memory，B为M1/M2/M3/M6/M7/M8/M9，无M10；当前完整runs仍P1/P3/P6/P7/P8/P10，Grouping G1—G4相同。A Effective等于Original；B只改u1文本，Goal/u2/Checks不变。格式补充是已授权协议修订，不是P3-A原Prompt逐字不变。


## 1. 如何读取证据

- O/A/B字段均为`updates[id=...].text`；下文S/N编号仅为研究定位，不写入任何正式Update。逐条引文已经以子串核验，A每项均与Original相同。Original/Effective全文仍在原文件，未重写。
- 当前事实：[共同输入](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/config/common_payload_without_memory.json)的`runs[ref=Pn].steps[step=Pn:s]`。P2/P4/P5/P9仅已有Grouping摘要，不能把其全文作为A/B可用证据。
- 历史事实：[真实Memory](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/config/memory_B.json)的`entries[id=Mx]`、`sources["S1_Rxx/diff"].diff`、`sources["S1_Rxx/Qn"].run.steps[step=Qn:s]`。历史Pn/Qn必须带轮次，避免与当前R05混淆。
- [精简证据索引](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_commitment_analysis_001/results/evidence_index.json)保留选定步的行动前观察、候选引用/哈希、动作、执行后反馈和结果。合法性均按`before.commands_ref`核查，未用after候选替代。不复制整批轨迹。
- 研究者展开sources的结论不等于模型实际叙述过的推理。B只显式引用M3/M6；其余Memory用于研究保留条件，不能声称B据其调整。

## 2. 关键来源事实与支持边界

| 来源 | 实际修改/行为 | 能支持什么，不能支持什么 |
|---|---|---|
| 当前P3:7–11，13/14/16 | 空drawer回访后在diningtable找到mug，获取交付成功 | 改善低信息重复和具体位置覆盖；不是“换类必然优于扫描”的隔离证据 |
| 当前P6:6/14/16、18–50 | 早期drawer/其他位置循环，后段长drawer推进，50只到达closed drawer20而未检查其内容 | 长同类安排与预算问题；不得把whole run说成只访问一类或已查完20个 |
| 当前P8:9–50；P10:32–38 | P8重复cabinet等且未去shelf1；P10晚到diningtable后取apple、cool、place成功 | 改善搜索机会分配，保留后续处理；P8也访问过bathtub/countertop，不能抹去这些类别 |
| M3 / S1_R02/diff + P5/Q5 | 添加通用搜索/开容器/避回空/精确对象/条件clean/直接交付等联合条款；Parent替代soapbottle失败，Q5:19到bathtubbasin取dishsponge，22clean，24交付成功 | 有条件的拓展覆盖与精确目标联合收益，且别的任务仍循环；没有独立证明类别采样是有效成分 |
| M6 / S1_R03/diff + P4/Q4 | 加current/recent反循环、缺目标/高步数时扩展新位置；Q4:12到diningtable找到bread，13取、15cool、17交付；P4步限 | 支持再次审视原覆盖安排；不确定最优类别顺序/切换尺度 |
| M6 / S1_R03/P2:15/16/20 vs Q2:25/30/50 | Parent到countertop3找到bread并成功；Candidate回countertop2但从未到3，最终失败 | 同类别实例仍有价值。类别访问不代表该类检查完；不能反推必须类内穷尽 |
| M6 / S1_R03/Q6:4/10/15、48–50 | 多次go cabinet3不在行动前候选且Nothing happens；48开cabinet9、49取plate、50到fridge，未完成；Parent38成功 | 旧反循环/预算优先文字未稳定兑现；支持当时动作前提校验、留意后处理预算，不支持永久禁用动作类 |
| M1/M2 | 灯共址与普通任务行为保留；M1记录不同成功动作顺序 | 保留任务条件，不能锁唯一严格灯步骤顺序 |
| M7 / S1_R04/Q3:5/7 | 持potato时合法heat并交付成功，Diff有条件直接温度处理 | 当前目标/动作前提成立时保留处理；无目标时不能保证成功。M7中“robust”等词不当独立因果证明 |
| M8 | 近似物不替代，未发现精确物时仍失败 | 不替代有任务依据；“没找到”不当作隐藏世界不存在/可以停止 |
| M9 / S1_R04/Q9:6/7/9 | 当前/近期可见源处有剩余精确saltshaker时回源取第二个并交付 | 有效回访与盲目空回访不同；本轮主要是单物/灯，不能强行新增多物流程；不能普遍禁止已访问位置 |

所有历史比较为单次联合编辑，不隔离子句因果收益。M6 knowledge并未规定类别一次停止；实际Diff仍是`all plausible candidate receptacles have been inspected once`。

## 3. Parent、Goal、Checks的约束谱系

Parent一般检索第一项：

> 1. Identify and search for the exact requested target. If it is not visible, search systematically: open any closed cabinet, drawer, or fridge immediately upon reaching it and inspect its contents before leaving. Do not immediately revisit an already-open receptacle that visibly lacks the target; choose a different uninspected candidate location instead. Do not repeatedly check inventory while carrying nothing. Continue until the exact target is found or all plausible candidate receptacles have been inspected once.

Parent自身已有全局未查/全部位置检查一次边界；这不证明它可观测，也不保证全部可达。其下一项又说未找到就继续系统搜索，存在“穷尽但未找到”如何处理的模糊。Original u1没有新增明确停止标准，也没有明确撤销Parent边界。B新增的是类别级更弱完成标准，不是从完全没有停止边界凭空增加停止概念。

Goal（A/B逐字相同）：

> Make search for the exact requested object coverage-oriented and step-efficient so the target is found, conditioned if required, and placed before the step budget is exhausted, without picking up, conditioning, or placing a substitute. Preserve the successful desklamp behavior (hold/co-locate the target and turn the lamp on at its receptacle), the direct acquire-then-place flow, and the correct clean/cool-then-place ordering already demonstrated.

Goal保留精确对象、必要处理/交付、灯共址和直接获取放置。B没有新增成功保证；其`effective ingredient`位于reason，是过强的解释性成分归因。Update中的within budget是目的，不应机械判为guarantee。当前Parent全文没有明确heat/cool专节；相关保留依据来自Goal、u2列举、当前P10 cool和历史M7，不把后轮Candidate Skill混作Parent。

Checks（A/B均返回null，原条目保留）：

- `c1` / `checks[id=c1].question`：After a receptacle is inspected and the target is absent, does the Actor move to a new uninspected receptacle or switch receptacle type rather than returning to one already seen empty or re-sweeping the same series?
- `c2` / `checks[id=c2].question`：Does the Actor avoid repeating no-op actions ('Nothing happens,' duplicate 'look,' empty-handed 'inventory') and instead choose a state-changing action?
- `c3` / `checks[id=c3].question`：When the exact target is found, does the Actor still complete the required conditioning and final placement with that target, and preserve the desklamp on-while-co-located success pattern?

C1关注新位置/换类与空回访，却没有直接检验类别一次退出时是否仍有剩余合理位置；C2关注避免no-op，不单独检验状态变化后的重试；C3保留获得精确目标后的处理交付。Checks不是Actor指令，不能弥补Update缺失的条件。本次不修改它们。

## 4. 行为承诺逐项矩阵

### S01 · 搜索作用阶段

| 字段 | 分析 |
|---|---|
| 原文定位 | updates[id=u1].text |
| Original | During any search for the exact requested object (or for the desklamp once the target is in hand) |
| Effective A | 原文不变（同上） |
| Effective B | During any search for the exact requested object (or, once the target is in hand, for the desklamp) |
| 来源/谱系 | Parent灯任务/一般检索；Original合并检索范围 |
| 实际变换 | 保留 |
| 行为及适用条件 | 精确目标尚未获得；或已持物但需找灯 |
| 对象单位 | 任务阶段/目标 |
| 强制程度 | 条件要求 |
| 证据定位 | Goal；Parent灯Procedure；当前P1:2/8/9，Grouping G1 |
| 支持边界/可执行性 | 灯搜寻阶段下一句仍说exact item absent，范围衔接不够清楚；不能解释为已经有物也应无目的搜索；既有模糊，非B独有。 |
| 判断 | 保留有据；阶段条件存在继承性模糊 |

### S02 · 覆盖方向

| 字段 | 分析 |
|---|---|
| 原文定位 | updates[id=u1].text |
| Original | treat the search as coverage of distinct candidate receptacles rather than a loop over a few |
| Effective A | 原文不变（同上） |
| Effective B | do not restrict the search to one container type or to a small set of locations |
| 来源/谱系 | Parent系统搜索；Original位置覆盖；B强调类别 |
| 实际变换 | 扩大覆盖维度/替换重点 |
| 行为及适用条件 | 持续搜索未找到 |
| 对象单位 | 位置→位置+类别 |
| 强制程度 | 方向性要求，B有否定式约束 |
| 证据定位 | 当前P3:7–13/P6:6–50/P8；M3 Q5/M6 Q4 |
| 支持边界/可执行性 | 反重复和位置覆盖有据；跨类别是合理探索，不证明每个任务都必须访问多类别。找到即结束应优先。 |
| 判断 | 方向有据；具体调度是探索 |

### S03 · 局部缺失触发

| 字段 | 分析 |
|---|---|
| 原文定位 | updates[id=u1].text |
| Original | When the current observation shows the requested item is absent |
| Effective A | 原文不变（同上） |
| Effective B | When the current observation shows the exact requested item is absent |
| 来源/谱系 | Original继承Parent visibly lacks |
| 实际变换 | 保留 |
| 行为及适用条件 | 当前观察中未见精确目标 |
| 对象单位 | 当前位置 |
| 强制程度 | 条件要求 |
| 证据定位 | Parent先开闭容器；当前P6:18/50到达时drawer仍closed |
| 支持边界/可执行性 | 未看到不等于已检查或全局不存在；结合S08先开容器。B移动句不能盖过开容器前提。 |
| 判断 | 可保留，需局部且已可检查的解释 |

### S04 · 移动可用性

| 字段 | 分析 |
|---|---|
| 原文定位 | updates[id=u1].text |
| Original | 该Update未明示，须结合Parent/Goal判断谱系 |
| Effective A | 同Original，无此独立子句 |
| Effective B | choose the next destination from the admissible 'go to' list |
| 来源/谱系 | Actor基础协议已有，B在u1显式化 |
| 实际变换 | 新增到Update文本，继承环境约束 |
| 行为及适用条件 | 选择移动时 |
| 对象单位 | 动作/位置 |
| 强制程度 | 合法候选约束 |
| 证据定位 | 当前P1:4移动不在before候选→no-op；M6 S1_R03/Q6:4/10/15同类问题 |
| 支持边界/可执行性 | 当前证据已足够；候选提供合法移动，不提供访问进度，不保证每个合法移动有用。 |
| 判断 | 有依据的明确化；不能计为历史独有增量 |

### S05 · 全局新颖性

| 字段 | 分析 |
|---|---|
| 原文定位 | updates[id=u1].text |
| Original | move to a receptacle not yet inspected in this search |
| Effective A | 原文不变（同上） |
| Effective B | sample a receptacle type not yet used in this search |
| 来源/谱系 | Original/Parent全局未查位置；B换为类别 |
| 实际变换 | 替换状态单位，未消除依赖 |
| 行为及适用条件 | 需要判断此次搜索从未使用 |
| 对象单位 | 位置→类别 |
| 强制程度 | 条件要求 |
| 证据定位 | Execution Context；当前候选不含visited；M3/M6混合覆盖响应 |
| 支持边界/可执行性 | 局部近期新颖性可以探索；全局未用类别需可恢复状态。类别更少不等于两步历史足够。 |
| 判断 | 已有信息依赖换了单位仍未解决 |

### S06 · 类别切换优先级

| 字段 | 分析 |
|---|---|
| 原文定位 | updates[id=u1].text |
| Original | once that series is exhausted without the target, switch to a different receptacle type |
| Effective A | 原文不变（同上） |
| Effective B | rather than another instance of the type just swept or a location you just saw was empty |
| 来源/谱系 | Original先耗尽；B不再明示耗尽门槛 |
| 实际变换 | 替换；放松耗尽门槛，同时偏向未用类别 |
| 行为及适用条件 | 当前未见目标、刚扫过一类/刚看过空位置 |
| 对象单位 | 类别/实例 |
| 强制程度 | 选择优先且rather than有排他性 |
| 证据定位 | 当前P6长drawer段；M3 Q5新位置；M6 Q4扩展成功/Q2遗漏同类 |
| 支持边界/可执行性 | 有动机早换探索，未验证最佳切换尺度；just swept是否整类不明，不能声称B指定严格逐次轮换。 |
| 判断 | 合理探索，排他强度/阶段定义尚不充分 |

### S07 · 同类重新进入条件

| 字段 | 分析 |
|---|---|
| 原文定位 | updates[id=u1].text |
| Original | before re-entering the series |
| Effective A | 原文不变（同上） |
| Effective B | go to cabinets, countertops, shelves, fridge, diningtable, or sinkbasin before re-entering the drawer series |
| 来源/谱系 | Original耗尽后先换类再重入；B例示保留并移动触发点 |
| 实际变换 | 继承局部先换类顺序，可能提前适用 |
| 行为及适用条件 | 一段抽屉搜索未得目标 |
| 对象单位 | 类别与同类剩余实例 |
| 强制程度 | 局部前置顺序；不是全类别完成要求 |
| 证据定位 | M6 Q2未访问countertop3；M9已知目标回源；当前G1 P2摘要 |
| 支持边界/可执行性 | 原文or是可选类别，不是全局固定排序；无“所有其他类别都采样后才返回”的明文。无条件推迟已知有价值同类位置不受证据支持。 |
| 判断 | 局部探索可留；更强全类别禁返解读不成立 |

### S08 · 编号推进与回访限制

| 字段 | 分析 |
|---|---|
| 原文定位 | updates[id=u1].text |
| Original | Sweep a numbered series of same-type containers in one direction without returning to earlier ones |
| Effective A | 原文不变（同上） |
| Effective B | While sweeping the numbered instances of one container type, move in one direction and do not return to an instance you just left empty |
| 来源/谱系 | Original新增单向系列；Parent仅避免立即回空 |
| 实际变换 | 部分保留/收窄禁返对象 |
| 行为及适用条件 | 处于一次类内扫描，刚离开位置为空 |
| 对象单位 | 编号实例/近期位置 |
| 强制程度 | 单向扫描+条件禁返 |
| 证据定位 | 当前P3:7–11空回访；M3/M6旧避返未稳定落实；M9条件回源 |
| 支持边界/可执行性 | 无return to earlier ones变成just left empty，较局部；仅单向编号可借当前编号/候选执行，不能因此保证全局遍历；合理回源不应由单向扫描跨阶段禁止。 |
| 判断 | 收窄有据；单向作为启发式可探索 |

### S09 · 先检查闭容器

| 字段 | 分析 |
|---|---|
| 原文定位 | updates[id=u1].text |
| Original | open a closed cabinet/drawer/fridge on arrival and inspect its contents |
| Effective A | 原文不变（同上） |
| Effective B | open a closed cabinet/drawer/fridge on arrival and inspect its contents before leaving |
| 来源/谱系 | Parent已明确before leaving；Original省略该短语；B恢复 |
| 实际变换 | 保留/恢复完整前提 |
| 行为及适用条件 | 到达且闭合、仍需找目标 |
| 对象单位 | 具体容器/动作 |
| 强制程度 | 条件要求 |
| 证据定位 | 当前P6:18/50 closed；M3 Diff及开容器响应 |
| 支持边界/可执行性 | 不能将“未观察到目标”直接理解为离开闭容器；到达闭容器并未完成采样。额外开容器在易例可增步，不推广到与任务无关操作。 |
| 判断 | 有据保留，防止采样与检查混同 |

### S10 · 近期循环检测

| 字段 | 分析 |
|---|---|
| 原文定位 | updates[id=u1].text |
| Original | Use the most recent observations to notice when the next move would revisit a receptacle just left empty or repeat the same small set of locations |
| Effective A | 原文不变（同上） |
| Effective B | a location you just saw was empty |
| 来源/谱系 | Parent/Original近期回空；B部分压缩 |
| 实际变换 | 保留即时空回访，删去显式小集合循环检测 |
| 行为及适用条件 | 近期可见且无新目标/状态变化 |
| 对象单位 | 近期位置 |
| 强制程度 | 避返条件 |
| 证据定位 | P3:7–11；P6:6/14/16；M6反循环未稳定兑现 |
| 支持边界/可执行性 | 近期线索可执行；较长小集合循环本来也超两步，删除不等于降低已证有效行为；B全局类别不能替代可见局部信号。 |
| 判断 | 局部保留合理；长周期能力仍有限 |

### S11 · 发现目标的检索出口

| 字段 | 分析 |
|---|---|
| 原文定位 | updates[id=u1].text |
| Original | 该Update未明示，须结合Parent/Goal判断谱系 |
| Effective A | 同Original，无此独立子句 |
| Effective B | Continue until the exact target is found |
| 来源/谱系 | Parent已有；Original依赖Goal/Parent；B显式化 |
| 实际变换 | 新增文本但继承任务阶段 |
| 行为及适用条件 | 当前发现精确目标 |
| 对象单位 | 目标/检索阶段 |
| 强制程度 | 结束搜索而非结束任务 |
| 证据定位 | 当前P3:13/14/16；P10:32/33/35/38；M3 Q5/M6 Q4 |
| 支持边界/可执行性 | 找到≠获得/处理/交付；Goal保留后续流程。灯任务找灯出口有S01模糊，不应把整任务结束混入。 |
| 判断 | 继承有据；不支持任务直接终止 |

### S12 · 类别采样终止

| 字段 | 分析 |
|---|---|
| 原文定位 | updates[id=u1].text |
| Original | 该Update未明示，须结合Parent/Goal判断谱系 |
| Effective A | 同Original，无此独立子句 |
| Effective B | or every receptacle type available in the room's action list has been sampled once |
| 来源/谱系 | Original无此条件；Parent是all plausible candidate receptacles inspected once |
| 实际变换 | 新增到Update；将Parent位置穷尽边界换成类别采样边界 |
| 行为及适用条件 | 目标未找到但每类已采样一次 |
| 对象单位 | 位置检查→类别代表采样 |
| 强制程度 | 独立的替代结束条件 |
| 证据定位 | M6 P2:15/16 vs Q2遗漏countertop3；Parent首步全文；M3/M6 Diff仍为receptacles |
| 支持边界/可执行性 | 部分实例不等于整类，更不等于全部合理位置。B未把它限定为一轮探索结束后继续搜；也不能推断Actor已经提前结束。调度动机不足以支持此完成标准。 |
| 判断 | 新增越界承诺；文本风险已确认，行为后果未知 |

### S13 · 预算目标

| 字段 | 分析 |
|---|---|
| 原文定位 | updates[id=u1].text |
| Original | This is coverage for finding the exact target within the step budget |
| Effective A | 原文不变（同上） |
| Effective B | This is coverage for finding the exact target within the step budget |
| 来源/谱系 | Original已有，B原样保留 |
| 实际变换 | 保留 |
| 行为及适用条件 | 50步总预算下搜索 |
| 对象单位 | 任务预算 |
| 强制程度 | 目的性表述，非保证 |
| 证据定位 | 当前P10:32–38；M6 Q6:48–50、P6:38完成 |
| 支持边界/可执行性 | 不是guarantee；不含数值预留预算，也未规定处理交付保底。不能说B删了原有明确数值预算，因为Original不存在。 |
| 判断 | 目的保留；后处理预算执行边界仍未明确 |

### S14 · 精确目标/不替代

| 字段 | 分析 |
|---|---|
| 原文定位 | updates[id=u1].text |
| Original | it does not permit picking up, conditioning, or placing a substitute object |
| Effective A | 原文不变（同上） |
| Effective B | it does not permit picking up, conditioning, or placing a substitute object |
| 来源/谱系 | Parent/Original已有 |
| 实际变换 | 保留 |
| 行为及适用条件 | 目标尚未找到或仅近似物可见 |
| 对象单位 | 物体类别/获取处理交付 |
| 强制程度 | 任务正确性约束 |
| 证据定位 | 当前P7 knife非butterknife失败；M3 Q5；M8旧Diff/响应 |
| 支持边界/可执行性 | 不操纵替代物不等于能够成功，也不证明目标不存在；M8不支持提前停止。 |
| 判断 | 有依据保留 |

### N01 · 无信息无变化动作

| 字段 | 分析 |
|---|---|
| 原文定位 | updates[id=u2].text |
| Original | Do not spend steps on actions that cannot change the world or reveal new information. |
| Effective A | 原文不变（同上） |
| Effective B | Do not spend steps on actions that cannot change the world or reveal new information. |
| 来源/谱系 | Original概括Parent反空查 |
| 实际变换 | 保留 |
| 行为及适用条件 | 可知动作无状态变化且无新信息 |
| 对象单位 | 动作/状态 |
| 强制程度 | 原则性避免 |
| 证据定位 | P7:11/12；M6 Q6重复不可用移动 |
| 支持边界/可执行性 | or允许有信息价值的非状态变化动作；不能读作所有look/inventory禁止；预先准确判断无新信息仍有认识边界。 |
| 判断 | 原则有据；不是全面信息动作禁令 |

### N02 · no-op触发不重复

| 字段 | 分析 |
|---|---|
| 原文定位 | updates[id=u2].text |
| Original | If an action returns 'Nothing happens,' |
| Effective A | 原文不变（同上） |
| Effective B | If an action returns 'Nothing happens,' |
| 来源/谱系 | Original新增广义反馈触发 |
| 实际变换 | 保留 |
| 行为及适用条件 | 刚收到no-op |
| 对象单位 | 动作/当时前提 |
| 强制程度 | 与N03组成不重复约束 |
| 证据定位 | 当前P1:4 off-list；M6 Q6:4/10/15 off-list |
| 支持边界/可执行性 | 反馈证明当时未奏效，不证明后续所有状态都无效；原文无until state changes时限，也未明示永久。需收窄歧义而非断言已永久禁令。 |
| 判断 | 状态作用域不足；当前事实可识别 |

### N03 · 等价动作禁重试

| 字段 | 分析 |
|---|---|
| 原文定位 | updates[id=u2].text |
| Original | do not repeat that action or an equivalent one |
| Effective A | 原文不变（同上） |
| Effective B | do not repeat that action or an equivalent one |
| 来源/谱系 | Original新增，Parent限立即回空/重复空inventory |
| 实际变换 | 保留 |
| 行为及适用条件 | no-op/重复look/空inventory任一触发后 |
| 对象单位 | 动作等价类/状态 |
| 强制程度 | 排他要求，等价/时间边界不清 |
| 证据定位 | M6 Q6同一不可用移动；当前P1:4 |
| 支持边界/可执行性 | 历史只支持当时同无效前提，未测试全部等价动作。无证据要求永久禁止，亦无证据说已发生禁用有效重试。 |
| 判断 | 需条件限定；M6提示旧规则未兑现而非证明更强禁令 |

### N04 · 重复look

| 字段 | 分析 |
|---|---|
| 原文定位 | updates[id=u2].text |
| Original | if a 'look' repeats the description you already have for the current receptacle |
| Effective A | 原文不变（同上） |
| Effective B | if a 'look' repeats the description you already have for the current receptacle |
| 来源/谱系 | Original显式新增look触发；Parent有空位置避免重访 |
| 实际变换 | 保留 |
| 行为及适用条件 | 同位置内容已知且本次look重复 |
| 对象单位 | 观察/当前位置 |
| 强制程度 | 避免继续重复条件 |
| 证据定位 | 当前P7:11/12相同反馈；M6空位置exam重复 |
| 支持边界/可执行性 | 这次look无新增信息可观察；状态变化后可能有用，不应排除；历史不提供最佳查询频率。 |
| 判断 | 局部要求有据；后续适用边界需保留 |

### N05 · 空手inventory

| 字段 | 分析 |
|---|---|
| 原文定位 | updates[id=u2].text |
| Original | if 'inventory' is issued while carrying nothing |
| Effective A | 原文不变（同上） |
| Effective B | if 'inventory' is issued while carrying nothing |
| 来源/谱系 | Parent已Do not repeatedly；Original扩大为一次触发 |
| 实际变换 | 保留Original强化 |
| 行为及适用条件 | 当前已知空手而发inventory |
| 对象单位 | 持物状态/信息动作 |
| 强制程度 | 一次空查后禁重复 |
| 证据定位 | P8:39/P10:25；M3/M6 Diff反重复空查 |
| 支持边界/可执行性 | 已知空手时反复空查无益；仅实际空手不等于Actor事先可知，首次查询可用于消除不确定性。不可机械禁止全部inventory。 |
| 判断 | 重复限制有据，空手知识前提不清 |

### N06 · 立即状态改变

| 字段 | 分析 |
|---|---|
| 原文定位 | updates[id=u2].text |
| Original | Instead immediately take a state-changing action |
| Effective A | 原文不变（同上） |
| Effective B | Instead immediately take a state-changing action |
| 来源/谱系 | Original新增替代动作强度 |
| 实际变换 | 保留 |
| 行为及适用条件 | 信息/no-op触发后下一步 |
| 对象单位 | 动作选择 |
| 强制程度 | 立即且限定state-changing |
| 证据定位 | P1:4、P7:11/12浪费；M6 Q6重复无效 |
| 支持边界/可执行性 | 避免无信息重复不逻辑蕴含下一步只能改变状态；若必要新信息不可由观察得，应允许获取。可用动作/任务阶段需另满足。 |
| 判断 | 附带强度依据不足，现有材料无实际B退化证明 |

### N07 · u2残留全局新位置

| 字段 | 分析 |
|---|---|
| 原文定位 | updates[id=u2].text |
| Original | move to a new uninspected receptacle |
| Effective A | 原文不变（同上） |
| Effective B | move to a new uninspected receptacle |
| 来源/谱系 | Original继承Parent/u1进度要求 |
| 实际变换 | 保留 |
| 行为及适用条件 | 决定转去搜索 |
| 对象单位 | 位置/搜索进度 |
| 强制程度 | 替代动作之一 |
| 证据定位 | Execution Context；S05全局信息边界 |
| 支持边界/可执行性 | u1变为类别不解决u2全局未查；不是新B引入。移动可选项非每次必须移动。 |
| 判断 | 继承性能力问题未修正 |

### N08 · 任务相关动作备选

| 字段 | 分析 |
|---|---|
| 原文定位 | updates[id=u2].text |
| Original | open a closed container, take the target, perform the required clean/cool/heat, or place the target at the destination |
| Effective A | 原文不变（同上） |
| Effective B | open a closed container, take the target, perform the required clean/cool/heat, or place the target at the destination |
| 来源/谱系 | Original整合Parent/Goal任务流程 |
| 实际变换 | 保留 |
| 行为及适用条件 | 依闭合/目标可取/持有/处理完成等实际前提 |
| 对象单位 | 动作/任务阶段 |
| 强制程度 | 可选动作列举，非顺序强制 |
| 证据定位 | P3:14/16；P10:33/35/38；M7 Q3:5/7 |
| 支持边界/可执行性 | or不是命令任意执行未满足前提动作；需Actor现有候选和Goal约束。heat有历史条件证据，当前六条无成功heat。 |
| 判断 | 有效行为文本保留；不能据此保证所有前提完整 |

## 5. u2未变意味着什么

M6额外提供的是“加入反循环/反空查指导后仍有重复不可用移动与预算失败”的响应，不是仅又一条no-op示例。它可以促使重新检查指导怎样落地、可用动作前提是否明确；当前P1:4本已能发现合法动作问题。B对u1显式补go-to候选，却对u2只用“与观察相符”解释Keep，没有处理N03等价/时间作用域和N06立即state-changing边界。这是最终文本未体现这些边界，不是证明模型没读M6。

M6并没有展示同一动作在前提改变后重试成功，因此不能说Memory已直接验证某一种重试规则。相关限制来自状态依赖逻辑、当前能力与原规则的范围核查。也不能说u2必须改才代表Memory被正确使用；有充分前提解释的Keep可能合理，这份输出未给出足以消解歧义的解释。N01本来允许有新信息的动作，N08的or是备选，不能据关键词编造全面禁令。

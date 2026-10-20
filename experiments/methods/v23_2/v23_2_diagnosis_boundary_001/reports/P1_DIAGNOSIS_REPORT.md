# P1：Diagnosis Goal—Update边界固定材料验证

本阶段只评价Diagnosis自身。没有Preconditioner模型调用、Memory更新、Editor、Candidate、Gate、Replay或ALFWorld执行；不能据本结果宣称下游预条件化或Skill性能改善。

## 变更、冻结与P0基线

P0读取真实Grouping→Diagnosis交接与原始请求，未根据下游输出重建输入。三轮原Parent、当前轨迹、Grouping、Actor背景和模型配置均固定，Memory只用于离线归因，未进入请求。[P0报告](P0_BASELINE.md)、[固定材料及SHA-256](../config/cases.json)、[P0冻结](../config/p0_freeze.json)。R04实际容量1,000,000字符／1,500,000字节，R05/R06为4,000,000／6,000,000；保留历史实际值。

P1只替换正式V23 Diagnosis第三节的Goal定义和策略表达两处：Goal保留行为目标与必要约束，具体实现放在Updates；仍要求具体策略，允许有动机的新探索，并通过reason／Checks区分预期与观察、避免无据保证和附带强制要求。[完整Prompt](../config/diagnosis_prompt.md)、[精确Diff](../config/v23.diff)、[设计](P1_DESIGN.md)、[调用前冻结](../config/p1_freeze.json)。没有改变Schema、数据流、默认配置或Actor能力说明，也未覆盖旧V23.2实验模板。

实现仅为独立实验[run.py](../run.py)，复用既有local_validation、HTTP生成器、解析与校验；[新增确定性测试](../tests/test_profile.py)及[代码Diff](../config/code.diff)。本次严格每轮一次实际请求，失败停止该案例，不使用原入口的自动重试预算。统计、对照和核验由离线[analyze.py](../analyze.py)生成。

## R04：具体策略仍在，但把成功轨迹的冗余操作固定成目标和流程

原Goal强调heat-then-place、多实例、精确目标、直送和避免循环；新Goal加入`use a bounded microwave sequence`，并要求保留`the short move/close/open/take/heat/place sequences of P2, P3, and P4`。这里不仅保留任务条件，还把具体设备操作顺序认定为成功模式，职责边界比原Goal更混杂。

原Diagnosis u1要求精确目标、heat后直接交付，没有规定每次都先插入／关门／重开；新方案拆成u1精确类别、u2温度流程、u3多实例。新u2明确：`Open the microwave, move the target in, close it, reopen and take the target, then apply the heat action once while holding it`。这不是空泛策略，而是明确但依据不足的强制顺序。

**当前证据即可核查，无需M4。** 原始R04行动前候选：P2:6闭门microwave已提供`heat plate 3 with microwave 1`；P3:7提供`heat potato 3 with microwave 1`；P4:5提供`heat tomato 2 with microwave 1`。这些步骤实际选择了open。轨迹后续成功只证明包含该操作链的一次执行成功，不证明整条前置链必要。新reason把这些成功概括为应保留的短流程，Goal和u2继承该过度认识。u2后面又说heat已available时不重复这些cycles，但没有说明可以直接跳过前置链，文本存在张力。

新u3写`search only receptacles that have not yet been inspected`，交付一件后继续找`remaining uninspected locations`。当前P6:23看见两支candle，27回原countertop、28取第二支并成功；P8:1看见两份newspaper，7回coffeetable、8取第二份并成功。查过位置不等于没有剩余目标。新规则可能排除有效回源，至少没有表达原Goal要求保留的该行为。它还删除原u2的“全合理位置检查一次”边界，改为只到计数满足；没有解释为何这种延续条件合理。没有执行过新Skill，以上是文本冲突／风险，不是已发生的行为退化。

P0特别区分：原Diagnosis没有后来Preconditioner提供的完整“可用时直接持物heat”条款，故本次失败不是删除原案已有那条完整策略，而是**新增了与当前可用动作相冲突的必要前置链**。原始和新全文、basis及checks均见[输出对照R04](OUTPUTS.md#r04)。

| 项目 | 原Diagnosis | 新Diagnosis／判断 |
|---|---|---|
| 改善目标 | 精确热处理交付、多实例、保留desklamp | 大方向保留 |
| A Goal | 行为目标为主，含systematic search | 绑定bounded sequence和具体成功动作链，未改善 |
| B 策略具体性 | 2条可落实更新 | 3条明确策略，未空泛化，但具体不等于正确 |
| C 策略承诺 | 未规定强制插入链 | 将成功轨迹顺序当作必要流程；无显式成功保证但仍过强 |
| D 边界 | 尚有搜索方法措辞 | Goal明确预定u2实现，未通过 |
| E 新退化 | 全局未检查状态依赖已存在 | 新增冗余操作链；only uninspected与有效回源有冲突，未通过 |

## R05：Goal较清楚，Update又把类别覆盖写成停止边界

原Goal包含`sweep uninspected receptacle families`，新Goal改为精确匹配、避免替代、到达未查候选而非循环，并保留desklamp与获取→必要处理→交付。没有把特定breadth-first或批次写进Goal，操作词主要对应任务完成和必要条件，**A／D有局部改善**，不是删除一切操作术语。

新u1仍明确精确类别、近似类别不可替代，并补充误拿非目标后不能当答案处理。当前P7:5取knife、7 clean、9 move而请求butterknife，提供直接问题依据；当前成功获取／处理／交付亦被保留。它不是空泛建议。

新u2明确标为`Unvisited-candidate breadth-first search`，提出先覆盖不同类别、`check a few drawers or cabinets, then switch ... and later return to remaining closed containers`，类内前进到新索引。当前P6前段回访、后段长扫drawer，P8反复cabinet／sink，P10晚到diningtable，足以形成分散探索的合理动机。**“few”是未定尺度，不是固定两次／三次阈值**；不能只因策略尚未验证或与原案不同就判错。但reason和checks未清楚区分该具体调度的预期与当前已观察结果。

主要新增问题是终止条款：`Continue until the exact target is found or all plausible candidate categories have been checked once, then use the exact target ...`。Parent已有的边界是**all plausible candidate receptacles inspected once**，原Diagnosis u2没有把“每类一次”列为结束条件。本次从位置覆盖变成类别覆盖，且前文允许每类只查few后换类，与“later return to remaining”存在张力。最宽松解读可把“类别checked”理解为其成员全部查完，但文本没有这样定义；不能声称一定早停，也不能忽略类别采样即可触发结束的明显风险。若未找到目标，随后`then use the exact target`也缺少成立前提。

全局unvisited／uninspected categories依赖仍在；当前动作候选不提供累计访问状态，原Parent／Original也已有同类依赖。本次没有证明修复，不能因Goal去掉具体算法就判断整项可执行。没有新增排他性的“只有近期见目标才允许回访”，也没有确定性效果保证；未将历史M6遗漏偷偷输入，所有判断只基于本轮Parent事实。

| 项目 | 原Diagnosis | 新Diagnosis／判断 |
|---|---|---|
| 改善目标 | 精确类别、扩覆盖、保留成功行为 | 保持，Goal减少具体方法绑定 |
| B 具体策略 | 跨类single-pass、不穷尽一类 | 分段跨类、再回剩余位置、索引前进；仍具体且允许探索 |
| C 承诺 | 单遍／换类强度已有风险 | 无成功保证；few尺度未说明，类别一次终止缺支持 |
| D 边界 | Goal预写family sweep | 算法留在Update，有改善 |
| E 新退化 | 历史进度依赖 | 依赖未修复；新增类别／位置尺度歧义及未找到目标时的交付前提问题 |

参见[原文及引用](OUTPUTS.md#r05)。总体不是保守化，但未满足“无新增无据要求”的P1验收。

## R06：目标解绑和效果承诺有实质改善，仍不能认定全程可执行

原Goal：`Make target search converge ... by using an ordered memory-independent sweep`。新Goal：`Improve convergence during target search and remove wasted conditioning-appliance toggling`，随后保留精确类别、单次容器检查、必要交付及双物体计数。**没有指定全局排序、类内穷尽或memory-independent实现。** “single-pass container opening”仍是操作性保留要求，但来自Parent既有指导，不能机械地因Goal出现操作词就判定绑定某个搜索算法。

新旧Update编号发生交换，应按行为对应比较：旧u2搜索对应新u1，旧u1温度对应新u2。

**搜索候选仍然具体。** 新u1使用当前／近期信息避免ping-pong；若连续几个同类容器没有目标，换类或表面；无法从近期记录识别明确未查位置时，偏好近期未出现的名称／编号／类别。它删除旧案的类内升序穷尽和`guarantee progress`，没有以更短或更空泛的建议代替策略。当前P3长期重复、P1/P2到countertop2取得目标，对试验局部避循环／拓展位置有问题动机。

它还明确说`If the available recent history does not identify a clearly uninspected location, prefer ...`，没有把“近期未出现”直接断言为“全局未访问”。这是信息判断更谨慎的具体改善。但该优先仍是待验证启发式，不能保证覆盖。前段要求不同`uninspected family`，后段采用近期fallback；如何决定类别确已未查、`a few consecutive`的尺度及其与“当前未找到就换不同类别／表面”的关系仍不充分明确。没有固定数值阈值，不能把few读成任意两次或三次强制规则。

**温度策略有条件依据。** 新u2明确heat/cool已在持物时可用就立即执行，避免重复门切换和取出／插入，完成后直送。当前P4/P5有可用heat候选却先做冗余操作；P4的目标从最终目的地fridge取出、加热后返回，亦支持不能以放进设备代替温度动作。没有出现R04的无条件插入链。对动作不可用时的minimal placement／retrieval／single door transition仍是通用备用描述，具体如何确定最小操作尚未验证。

**保留和遗漏。** 精确目标、两实例交付、无desklamp绕行仍在Goal和checks，未因搜索调整删除。旧搜索u2明确`keep enough remaining steps ... conditioning and final placement`，新搜索只写`Continue ... until ... found`，没有同样明确保留后处理预算，预算只出现在观察Check中。Check不是Actor指令；这项删除没有独立解释，不能因为总体仍要交付就视为完全等价。缺预算要求是否实际造成退化未知，没有Actor执行。

| 项目 | 原Diagnosis | 新Diagnosis／判断 |
|---|---|---|
| A Goal | 绑定ordered memory-independent扫描 | 行为改善与保留约束为主，明显改善 |
| B 具体策略 | 类内升序穷尽再换类 | 当前／近期避循环、换类及fallback；仍有执行意义的候选 |
| C 承诺 | guarantee progress、memory-independent | 未再写进展保证；启发式的效果仍待验证，reason未充分展开各细节预期 |
| D 边界 | Goal锁定扫描方式 | 具体搜索放在Update，后续可改；未调用下游，不能说下游已改善 |
| E 新退化 | 全局进度依赖、强穷尽 | 近期fallback改善部分信息依据，残留类别进度／尺度歧义；后处理预算要求未明确保留 |

参见[原文及引用](OUTPUTS.md#r06)。R06满足本次主要目标解绑和删除无据效果保证的局部观察，但不足以认定所有策略要求都可执行或无副作用。

## 验收结论与P2条件

| P1验收项 | 结果 |
|---|---|
| Goal与Update边界更清楚 | R05/R06改善；R04更强地绑定温度流程，整体未通过 |
| 仍能生成具体、可执行候选 | 三轮均有具体候选，未空泛化；全程可执行性没有共同通过 |
| 不把探索直接当已验证效果保证 | R06删除显式保证，三轮无新成功保证；但R04把成功伴随的冗余动作当必要流程，认识越界仍在 |
| R04有效策略不明显退化 | 未通过：无条件插入链及only uninspected回源风险 |
| 无新增无据强制要求 | 未通过：R04操作链、R05类别一次边界；R06仍有未明尺度及预算保留问题 |
| 契约及其他模块不变 | 通过：179项离线测试、真实三输出原解析通过、历史文件一致 |

**总体：P0完成，P1实现与规定验证完成，但语义验收未通过，不满足按本轮标准进入P2的条件。** 不晋升默认Diagnosis，不自动进入P2，不追加修订或调用。

当前可确认的改善是R05/R06这两份输出的Goal不再绑定具体调度，R06不再要求类内穷尽和保证进展；具体策略构造能力仍在。尚未修复的是**Diagnosis仍会把观察到的成功流程或失败现象扩大为必要实现／强制边界**，R04尤为明显。仅靠规则强调Goal—Update区分，没有稳定阻止这种语义越界。

进入P2之前仍需明确处理／决策的事项：R04成功轨迹的冗余操作为何被保留为必要流程，以及搜索Update的覆盖边界、回源例外和必要完成预算如何保持一致。这里记录尚未满足的验收项，不设计新Prompt、不规定后续实现。当前只有每例一次随机输出，不能把局部改善视为稳定规律，也不能把失败归因于某一句Prompt。更不能推出Preconditioner或ALFWorld性能改变。

## 调用、测试、成本与历史保护

离线禁网运行既有V23.2测试、V23 Diagnosis／Preconditioner契约测试及新增8项检查：**179 passed，5.67秒**。[测试日志](../results/offline_tests.log)、[结果](../results/offline_tests.json)。新增检查覆盖冻结源码／默认、模板两处替换、三轮原始请求与Memory缺席、原解析和下游纯装配／编译兼容、timeout／截断／结构失败各只一次请求。模拟输出仅在pytest临时目录，未当作真实实验结果。

P1于**2026-10-20 12:40:28 +08:00**冻结，首个实际请求12:40:40开始。三轮均合法revise、finish=stop，无失败、无重试、无语义重采样。仅3次Diagnosis逻辑调用、3次HTTP请求，Actor及其他模型调用为0。[真实全文与请求链接](OUTPUTS.md)、[逐请求记录](../results/attempts.json)、[输入参数核验](../results/verification.json)。

| 案例 | Input tokens | Output tokens | 其中reasoning | Total tokens | 请求及校验耗时 |
|---|---:|---:|---:|---:|---:|
| R04 | 61,018 | 5,631 | 4,356 | 66,649 | 27.317秒 |
| R05 | 65,445 | 12,797 | 11,924 | 78,242 | 67.176秒 |
| R06 | 45,858 | 9,182 | 8,194 | 55,040 | 46.526秒 |
| 合计 | 172,321 | 27,610 | 24,474 | **199,931** | 全轮墙钟 **141.201秒** |

Reasoning包含在Output中，不重复累计。API报告输入缓存命中合计5,376 tokens，其余输入166,945。没有账单金额或可核验的本次计费费率，故只报告实测Token，不编造货币成本。[汇总](../results/summary.json)。准备阶段有一次离线容量字段别名冲突，已在P0冻结前按原有恢复规则修正；无模型请求，详见[准备记录](../results/setup_notes.md)。

**12,215个历史保护文件集合与SHA-256相同**：[保护核验](../results/protection.json)。保护V23/V23.2源码及原Prompt、正式Campaign、Skill、Memory和Test字节、全部旧实验、相关测试、设计文档和原有五个已修改README／日志文件。Test仅计算保护哈希，未用于分析。默认仍为原V23，旧实验保持可重读。本次新增内容全部位于独立实验目录及对应artifacts目录，没有改任何原有文件。

最后核对见[final_verification.json](../results/final_verification.json)：P0/P1冻结内容未变、全部请求发生在冻结之后、恰好3次Diagnosis请求、无其他阶段产物、引用路径有效；`git diff --check`通过。完成P0与P1后停止，未进入P2。

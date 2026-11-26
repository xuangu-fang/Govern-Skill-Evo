# R05 / R06：执行 → Replay → Memory → 模块输入审计

2026-10-28。默认 Preconditioner 已退回 v7；本报告只读历史归档，不修改 Replay / Memory，不调用模型、执行 Actor 或重算评分。结论针对实际收到的信息，不以最终输出反推当时可见事实。

**主要结论：未发现 Memory 存储或投影丢失 active 经验；确认了 Replay 的局部事实概括／归因问题，以及 Preconditioner 对已提供经验的范围扩大和事实误读。两类问题并存，不能统一归咎于输入不足，也不能据此认定整个 Replay / Memory 设计失效。**

## 1. 审计对象与时间顺序

| 经验 | 产生轮次 | R05 / R06 中实际用途 |
|---|---|---|
| M1、M4 | R01 | R05 原始及 v7/v8 的公式缓存、同次执行修正、直接值路径 |
| M7 | R03 | R05 原始 u3 的公式缓存正向参照；v7/v8 没有继续显式引用 |
| M8 | R04 | R05 原始 u1 的键匹配正向经验、u3 的缓存退步；v7 u3 仍引用缓存退步 |
| M9 | R05 完成 Candidate、Replay 和发布后 | R06 原始及 v7 u3 的文本归一化／标识符边界 |

R05 输入为 M1–M8，共 8 entries、26 Knowledge items；R06 为 M1–M9，共 9 entries、34 items。M9 **尚未存在于 R05 Preconditioner 决策时**，不能用其中后来出现的 Candidate 成功或边界查找来解释此前 R05 为什么 KEEP。

原始 R05 还用 `M1`–`M8` 的范围表述概括“无历史反例”；逐项有实质用途的是上表经验。本文附上这些经验的全部条目，重点核对被引用的主张，并检查相关反例。R06 u1（答案位置）、u2（合并表）原始和 v7 输出都未显式引用 Memory；不能为它们虚构 Memory 归因。v8 R06 无完整输出，不纳入语义审计。

证据：[五份模块实际引用与理由](../../../artifacts/methods/v25/analysis/replay_memory_r05_r06_audit_20261028_001/module_evidence.md)；[全部相关 Memory 原文](../../../artifacts/methods/v25/analysis/replay_memory_r05_r06_audit_20261028_001/memory_evidence.md)。

## 2. 传递过程：哪些信息存在，哪些没有提供

| 环节 | 实际检查与结果 | 结论 |
|---|---|---|
| 原始执行 → 当前 Replay 输入 | 重建 R01–R05 共 150 份 Actor 记录，核对执行代码、运行结果、初始输入和评分；与 Replay 归档及实际 user 消息一致 | 没有发现相关执行事实在这个阶段被意外丢弃 |
| 时间线压缩 | 删除重复的 `request_messages`，按初始消息、执行响应与反馈可重建；实际执行代码、结果与评分保留 | 是选定执行视图内的去重；不等于 Replay 获得每个未执行的格式错误响应 |
| Replay → 发布审查 → Memory | R01、R03 的相关条目原样发布；R04、R05 经一次定向 Repair；最终 candidate 与 Memory commit 一致 | 必须审查发布后经验，不能把被修好的 Replay 草稿错误算作最终 Memory 错误 |
| Memory 存储 → Preconditioner 输入 | 五份输出归档全部重读通过；active entries 文本及 evidence 数组完整、顺序一致，没有检索筛选或字符截断 | 本组案例不支持“相关经验没检索到”或“存储压缩丢掉条件”的结论 |
| 历史 sources → 模块输入 | 完整历史来源在 Memory archive 中；Knowledge Only 明确不传原始历史代码、预览、评分和 pair，不提供回读工具 | 模块只能使用经验文字及引用 ID，不能独立验证这些历史主张；这是明确的信息边界 |

Replay 在产生某轮新经验时有该轮完整的允许执行证据；该经验成为历史后，下游通常只看到经验文字。这使 Replay 的概括错误可能完整、无损地传下去。`sources` 存在于磁盘，不等于当次模型看到了它。

证据：[逐环节机器校验](../../../artifacts/methods/v25/analysis/replay_memory_r05_r06_audit_20261028_001/lineage_audit.json)；[Memory 投影实现](/Users/didi/Desktop/Govern-Skill-Evo/src/skill_evolution/v25/memory_view.py:26)；[Knowledge Only 明示边界](/Users/didi/Desktop/Govern-Skill-Evo/src/skill_evolution/v25/benchmarks/spreadsheetbench/prompts/knowledge_only_view.md:8)；[执行视图投影](/Users/didi/Desktop/Govern-Skill-Evo/src/skill_evolution/v25/benchmarks/spreadsheetbench/timeline.py:74)。

## 3. M1 / M4 / M7：有实际用途的经验，没有证据要求整体重写

R01 Q6 的执行记录直接包含 `computed total: -10600 K6 read back: None`，并得到 hard 0；对应 Parent hard 1。M1 保留了“公式存在不等于缓存可读”的重要对照，也保留了公式加缓存成功的反向证据。M4 保留公式和直接值两条成功路径，并明确多条 Skill 同时变动，不能把收益只归给答案区域验证。

R05 原始、v7、v8 都从这些已提供经验中得到同次执行内纠正缓存的方向，并保留必需公式。v7 明确承认注入机制或公式本身的具体失败原因尚未分清。这是经验被有效使用的例子，不宜因为其他 KEEP 问题就删除这类泛化。

M7 记载的是公式／缓存加 literal fallback 的程序路径，不是所有成功都已证明由“公式缓存分支”单独完成；原始 R05 用它支持不撤回公式方向尚可，但不能将它扩写为必需公式可以被值替代的证据。v7 没有继续引用 M7。本次没有据此新增替代规则。

**分类：** Q6 的缓存读回失败有直接事实；Q11/Q14 等全错不能仅凭分数确认同一具体根因。相关经验和 v7 已保留一定边界。不存在该主张在 Memory 到输入阶段丢失的证据。

证据：[M1/M4 原文](../../../artifacts/methods/v25/analysis/replay_memory_r05_r06_audit_20261028_001/memory_evidence.md#L5)；[M7 原文](../../../artifacts/methods/v25/analysis/replay_memory_r05_r06_audit_20261028_001/memory_evidence.md#L45)；[R01 Q6 及相邻对照执行](../../../artifacts/methods/v25/analysis/replay_memory_r05_r06_audit_20261028_001/R01_execution_evidence.md)；[R05 v7 用法](../../../artifacts/methods/v25/analysis/replay_memory_r05_r06_audit_20261028_001/module_evidence.md#L33)。

## 4. M8 缓存退步：事实已提供，原始 Preconditioner 读反了

R04 P8 的直接值程序 22/22，Q8 的公式程序 13/22。Memory M8 `knowledge[6]` 明确写着：Q8 为 9 个 run-end 行注入缓存，**错误恰好也是这 9 格，其余应为空的格子匹配**；原因只说与缓存不可读一致，没有确认具体注入失败机制。

R05 原始 u3 却概括为 “cached values were injected for only 9 of the required rows, leaving the other required cells unreadable”，据此强调不是只覆盖部分目标格。它把“已尝试注入的 9 格出错”读成“未覆盖的其他目标格出错”。这个区别就在当次 Memory 文字中，不需要回读历史源码才能识别。

发布前 Repair 确实修过本条经验，但修的是另一个事实：P2/Q2 并非双方都用公式缓存，Parent P2 实际写直接值。修正后的 Memory 仍保留了完整的 9 格对照。v7 已按“run-end 行注入且恰是这些格错误”复述，不再沿用原始误读。

**分类：事实利用错误，发生在原始 Preconditioner；不是关键事实缺失，也不是 Memory 存储丢失。** “检查所有目标格”作为一般保护仍可合理，但不能用被读反的事件来证明它是这次退步的根因修复。

证据：[M8 knowledge[6]](../../../artifacts/methods/v25/analysis/replay_memory_r05_r06_audit_20261028_001/memory_evidence.md#L141)；[R04 执行和错误格](../../../artifacts/methods/v25/analysis/replay_memory_r05_r06_audit_20261028_001/R04_execution_evidence.md#L253)；[原始 R05 u3](../../../artifacts/methods/v25/analysis/replay_memory_r05_r06_audit_20261028_001/module_evidence.md#L25)；[R04 发布审查](../../../artifacts/methods/v25/v25_skilladam_execution_only_actor48k_20261027_001_v25/campaign/rounds/R04/knowledge_review/result.json)；[R04 Verifier 指出的问题](../../../artifacts/methods/v25/v25_skilladam_execution_only_actor48k_20261027_001_v25/campaign/rounds/R04/verifier/attempts/002/verifier.json)。

## 5. M8 键匹配成功：经验基本局部，下游把支持范围放大

M8 `knowledge[4]` 记录三个任务保持成功：动态定位 `Grand Total` / `0-15`、两键字典匹配、收集以 `PK` 开头的文本。实际程序分别使用具体标签判别、完整键匹配和 prefix 匹配；Memory 总结的是这些 normalized single-key / multi-key 能力在本轮没有被破坏，没有规定所有标签都应默认 substring。

R05 原始 u1 用这条经验及“无历史反例”支撑归一化加默认子串规则，超过了该经验的操作语义范围。完整键相等、前缀、关键词包含可以共享部分归一化机制，但成功并不能互相替代匹配语义。

v7 的 R05 u1 没有显式引用 M8，而转用本轮 P1/P4 并承认两格失败原因未分清。因此，不能把 v7 同样 KEEP 全部归因于 M8；它还有独立的当前证据使用问题。

**分类：下游经验泛化过宽。** Memory 已给出任务和操作差异，缺少历史源码并非解释这一错误的必要条件。此处不支持收紧所有归一化；应保留对同一语义关系的合理迁移。

证据：[M8 knowledge[4]](../../../artifacts/methods/v25/analysis/replay_memory_r05_r06_audit_20261028_001/memory_evidence.md#L125)；[Q3 动态标签](../../../artifacts/methods/v25/analysis/replay_memory_r05_r06_audit_20261028_001/R04_execution_evidence.md#L573)；[Q10 前缀匹配](../../../artifacts/methods/v25/analysis/replay_memory_r05_r06_audit_20261028_001/R04_execution_evidence.md#L806)；[原始 R05 与 v7 对照](../../../artifacts/methods/v25/analysis/replay_memory_r05_r06_audit_20261028_001/module_evidence.md#L3)。

## 6. M9 文本改进：Replay 把未知分支与局部成功概括得过于确定

R05 P1/Q1 从 14/16 变为 16/16。Replay 实际看到了两侧完整代码及错误坐标，但初始预览只有前五行，E10/E11 及对应 F 值没有展示，执行日志也没有记录这两行的分支和值。评分提供错误坐标，不提供预测值和参考值。

代码里不止文本判断不同：P1 已接受数值字符串并采用 `1e-9` 整数容差；Q1 同时改变大小写／空白／子串判断、括号负数处理及不可解析值的处置。不能将“Candidate 成功”直接拆成已确认的某一个差异奏效。

M9 `knowledge[1]` 却写成 “clear single-clause improvement”、P1 “leaving E10 and E11 unchanged”，并称 Q1 “converting all 16 graded cells”。这里至少有两层问题：

- E10/E11 只是被评分判错；当次可见记录没有证明它们原值未改，更没有证明是 strict equality 导致漏匹配。解释可以作为假设保留，不应写成已观察到的事件。
- 16/16 是评分通过数，不是改写行数。Q1 只改匹配行，预览里 American Express、Comcast 等明确不匹配的行会保持原值。把全部评分格写成全部转换，混淆了结果数量与行为数量。

本条经验通过 Verifier 的 `SUPPORTED`，没有被 Repair 改动，按原文进入 M9，再进入 R06。原始 R06 u3 将其作为“strict whole-cell 漏掉的值被归一化修好”的历史依据；v7 则至少明确将 label/keyword membership 与 record-identifier joins 区分开，没有将子串默认搬到标识符。

**分类：原始事实缺失（两行实际值／分支）与 Replay 事实利用／归因过强同时存在；Memory 传输本身无失真。** 支持保留归一化修复假设，不支持把这次成功当作普遍子串默认的验证。

证据：[P1 的实际可见预览](../../../artifacts/methods/v25/analysis/replay_memory_r05_r06_audit_20261028_001/R05_execution_evidence.md#L9)；[P1 已有数值容差](../../../artifacts/methods/v25/analysis/replay_memory_r05_r06_audit_20261028_001/R05_execution_evidence.md#L82)；[Q1 完整执行代码](../../../artifacts/methods/v25/analysis/replay_memory_r05_r06_audit_20261028_001/R05_execution_evidence.md#L191)；[M9 knowledge[1]](../../../artifacts/methods/v25/analysis/replay_memory_r05_r06_audit_20261028_001/memory_evidence.md#L169)；[R06 原始及 v7 用法](../../../artifacts/methods/v25/analysis/replay_memory_r05_r06_audit_20261028_001/module_evidence.md#L115)。

## 7. M9 数值改进：漏记了已在代码里的重要竞争解释

R05 P3/Q3 从 135/189 变为 189/189。Replay 将改进主要概括为实际读取 min/max、逐格约束和残差传递。但两侧代码还有直接可见的重大区别：

- P3：`res < 0` 时加，`res > 0` 时减。
- Q3：`residual > 0` 时加，负数时减。

**正负号对应的加减方向被整体反转。** Replay 已看到两侧代码，却没有在 M9 `knowledge[3]` 中保留这个会影响归因的重要变化。无需增加输入，就能记录它是竞争解释；本次不声称已证明它才是唯一根因。

此外，Q3 同时有标签查找、数值行启发式、缺失时 `0/inf` 回退。没有输出 min_row/max_row 或实际取到的边界。Memory 写“从 header text 定位并读取 actual bounds”比可见运行证据更确定。成功分数不能单独证明哪条查找分支被执行，更不能证明以后每个任务的边界一定存在于工作簿。

**分类：已见事实未利用（符号方向变化）＋未提供运行分支事实却被写成确定观察。** 逐格边界和传播方向仍是合理修复，不需要因为归因未隔离就撤回。该条存在于 R06 输入，但 R06 输出未显式用它决策；目前证实的是经验内容缺口，不能宣称它已经造成 R06 某项错误。它也不能解释更早的 R05 Preconditioner 决策。

证据：[P3 加减分支](../../../artifacts/methods/v25/analysis/replay_memory_r05_r06_audit_20261028_001/R05_execution_evidence.md#L409)；[Q3 完整查找与分支](../../../artifacts/methods/v25/analysis/replay_memory_r05_r06_audit_20261028_001/R05_execution_evidence.md#L512)；[Q3 正数加法](../../../artifacts/methods/v25/analysis/replay_memory_r05_r06_audit_20261028_001/R05_execution_evidence.md#L648)；[M9 knowledge[3]](../../../artifacts/methods/v25/analysis/replay_memory_r05_r06_audit_20261028_001/memory_evidence.md#L185)。

## 8. M9 邮编查找：审查修正有效，不应继续算作已发布错误

Replay 草稿 `knowledge[7]` 称 Parent / Candidate “filled unmatched rows differently”。Verifier 实际拿到了两份代码，指出它们都写 `#N/A`；Repair 删除了该错误描述。最终 M9 保留“删除全部内部空白”与“折叠成单个空格”的差异，同时明确四格改善的原因未隔离。

这条修正后的经验完整进入 R06 原始输入，其 u3 也保留“record does not isolate the cause”。这是发布前事实审查和下游使用有效的实例。`-` / `/` 是否可归一化仍需结合当前标识符语义判断；不能因邮编任务改善就直接证明分隔符等价，但也不必禁止保留意义组件的合理探索。

证据：[最终 M9 knowledge[7]](../../../artifacts/methods/v25/analysis/replay_memory_r05_r06_audit_20261028_001/memory_evidence.md#L217)；[R05 Verifier 原判断](../../../artifacts/methods/v25/v25_skilladam_execution_only_actor48k_20261027_001_v25/campaign/rounds/R05/verifier/attempts/002/verifier.json)；[定向 Repair 输入](../../../artifacts/methods/v25/v25_skilladam_execution_only_actor48k_20261027_001_v25/campaign/rounds/R05/knowledge_review/repair_input.json)；[R06 对经验的使用](../../../artifacts/methods/v25/analysis/replay_memory_r05_r06_audit_20261028_001/module_evidence.md#L115)。

## 9. 发布审查为何没有覆盖所有问题

R04 的一处角色混淆、R05 的一处 unmatched 分支错误得到修正；但 M9 文本和数值经验仍通过。本次核对确认 Verifier 输入中包含 P1/Q1、P3/Q3 的执行代码，因此不能把这些漏检笼统归因于没有给它代码。

它的实际 prompt 将任务限定为明显、重要事实错误筛查，明确 `SUPPORTED` 不意味着每个断言都已证实，也不要求完整因果审计。结构校验又主要检查引用可用性、字段和补丁，不检查每条经验的因果支持程度。因此，发布成功不是“全部历史解释已验证”的保证；目前发现的是一部分漏检和职责覆盖边界，不等于需要把 Verifier 变成全面因果证明器。

证据：[当次 R05 Verifier 输入](../../../artifacts/methods/v25/v25_skilladam_execution_only_actor48k_20261027_001_v25/campaign/rounds/R05/verifier/attempts/002/input.json)（`source_records.P1:1/Q1:1/P3:1/Q3:1.record.executed_code`）；[当次 Verifier prompt](../../../artifacts/methods/v25/v25_skilladam_execution_only_actor48k_20261027_001_v25/campaign/rounds/R05/verifier/attempts/002/prompt.md)；[发布及 repair 轨迹](../../../artifacts/methods/v25/analysis/replay_memory_r05_r06_audit_20261028_001/lineage_audit.json)。

## 10. 研究优先级与本次未做事项

1. 优先研究 Replay 如何保持“实际行为差异、已观察结果、待验证解释”的区别，尤其是已有代码中的重要竞争解释；这里已有具体证据，不必先扩大输入或重做 Memory 架构。
2. 针对 E10/E11、min/max 查找分支等，承认输入没有记录实际值／路径。以后若需要确认根因，可针对性设计补充证据；本轮不补充，也不凭缺少证据撤回合理修复。
3. Memory 的 active entry 存储与投影未显示数据丢失，不优先改检索或存储。Knowledge Only 使下游依赖摘要质量，是明确权衡；当前不能认定长上下文导致了某次误读。
4. 已看到的下游误读和不合理泛化继续作为回归案例保留，不能期待只改 Replay 就自动消失。v7 中已有部分改善，也仍有未解决的 KEEP 范围问题。

本次已恢复 v7 默认、保留 v8 模板与实验，完成 38 项离线测试、150 份历史执行投影校验及五份 Preconditioner 原生重读。历史文件和 Replay / Memory 实现哈希未变；详见 [回退说明](/Users/didi/Desktop/Govern-Skill-Evo/docs/methods/v25/PRECONDITIONER_V7_DEFAULT.md) 和 [校验记录](../../../artifacts/methods/v25/analysis/replay_memory_r05_r06_audit_20261028_001/rollback_validation.json)。没有新实验、模型调用、Actor 执行或评分。

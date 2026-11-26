# Replay 局部修改草案与验证方案

2026-10-28。状态：仅完成可审阅草案、请求准备和离线校验。未修改生产代码或默认 prompt，未注册新版本，未调用模型，未发布 Memory。默认仍为 Replay v3 / 输入视图 v4，Preconditioner v7。

## 1. 依据与范围

依据[单配对上下文消融](../../replay_single_pair_diagnostic_20261028_001/reports/README.md)：R05 条件对照更完整，但实际边界读取仍被过度确认；R06 没有完整对齐 name/code 回退条件，比较中已出现的 code 优先未进入 Knowledge，并把相同错误坐标过度推成因果排除。

本草案只处理三个已定位环节：重要决策的条件对照、形成 Knowledge 时的重要区别保留、评分相同情况下的推断边界。不修改输入视图、模块拆分、Memory 发布、历史修订契约或默认调用次数。

三个方向落实为五处替换，生产草案和诊断草案采用完全相同的语义改动：

| 位置 | 修改 | 对应问题 |
|---|---|---|
| §1 Observation 的末尾 | 将等分/同错误坐标的限制扩展到“不能单凭此排除行为影响或失败机制” | R06 一边承认错值可能不同，一边断言键变化不解释错误 |
| §3 开头及三条比较要求 | 以决策输入/状态条件对齐双方；必要时追踪信息来源、选择、优先级、回退及下游使用 | condition 只复述任务；把不同键选择统一概括成 item |
| §3 三类响应名称 | adherence without added benefit 改为 adherence with no measured outcome change | 避免把没有测得结果变化写成机制没有收益 |
| §4 text 形成要求的一句 | 明确按条件性经验价值选择比较，不要求每条比较独立成为 Knowledge；压缩时执行 §6 检查 | 防止保留要求演变为逐项抄写或规则膨胀 |
| §6 当前比较核验段 | 核对删去条件/优先级/回退/竞争变化是否改变读者理解；必要时恢复区别或收窄结论 | code 优先进入比较后又被 Knowledge 省略；单分支事实扩成整程序 |

## 2. 具体替换文本

### 2.1 §3：把比较落到决定动作的条件

替换现有 §3 开头与三条列表，保留其后“再联系实际 edit”、联合干预和非对称结果要求：

> For each relevant verified pair, compare the decisions that could change the interpretation, **before selecting a Skill clause as the explanation**. Align both programs under the same task-relevant input or state conditions, even when their branch labels or intermediate representations differ. A condition should distinguish when a choice or action changes, rather than only restate the task. Establish as evidence permits:
>
> - For a material decision, compare the information each side uses, its selection condition and priority, any fallback trigger and action, and the consequence for the next relevant operation. Follow dependencies only far enough to distinguish the behaviors. A shared label for an operand or key does not establish that it is constructed, selected or used equivalently.
> - Identify consequential shared and changed behavior under those conditions, including direction, bounds and preparation when relevant. Preserve the branch scope of a difference instead of extending one branch's behavior to the whole program. Do not enumerate incidental details, exhaust every branch, or force a fixed number of comparisons.
> - What improved, regressed or remained effective locally, separately from whole-task hard and the distinct attempt/execution/request counts, within the evidence limits in section 1.

预期 R05 保留正负分支各自的动作及 Parent 已有延续；R06 对齐决定物料键的选择和回退条件，并追踪它们怎样影响分组。这里的预期只在人工方案中，模型草案不写入 R05/R06 的具体答案、任务编号或目标单元格。

### 2.2 §4 与 §6：选择可以压缩，关键区别不能消失

§4 原先“Keep it concise without dropping...”的一句替换为：

> Select comparisons for their contribution to the conditional lesson; not every comparison needs a Knowledge item. Keep the selected understanding concise and use the comparison-to-Knowledge fidelity check in section 6 when compressing it.

§6 当前比较核验段中，原有“检查一致性、修正例外、因果 caveat 不修复错误前提”等句子合并为：

> Compare each proposed Knowledge with the material behavioral comparison it summarizes: would an omitted condition, selection priority, fallback or competing change make different behaviors appear equivalent, extend a branch-specific observation to the whole program, or suggest an isolated cause? If so, restore the necessary distinction in that Knowledge or narrow its claim. Merging wording is allowed; retaining only the existence of alternatives is insufficient when the rule choosing between them changes the lesson. This check preserves material meaning, not every implementation detail or a fixed number of items. Check consistency with other Knowledge items; correct, qualify or split claims when useful. A general caveat does not repair a false factual premise or an unsupported causal exclusion. Retain valid comparisons and useful hypotheses.

这是一项压缩后的语义检查，不新增输出字段或逐项操作标签。它不要求所有比较写入 Memory；但在选择保留某个经验后，不能省略改变该经验解释的区别。R06 的目标是保留选择规则，而不只留下“两张库存表”。R05 的目标是保留分支限定，而不把单一分支扩成整个程序。

### 2.3 §1 与 §3：将测量结果和因果排除分开

§1 Observation 的末尾替换为：

> Correct-cell counts are not write counts, and mismatched coordinates do not establish unchanged inputs. Equal scores or mismatch sets establish no change in those reported measurements; they do not establish equal output values, absence of a behavioral effect, or exclusion of a mechanism as a contributor to failure. Distinguish an outcome observation from a causal exclusion; qualify each inference by its supporting evidence.

§3 的响应类别相应改为：

> **No observed opportunity**, **an opportunity with non-adherence**, and **adherence with no measured outcome change** are different responses.

这限制的是从等分直接推出因果排除，不禁止有独立证据支持的因果判断，也不禁止未隔离验证的机制假设。预期 R06 可以保留“键选择可能影响库存池”的条件性解释，同时准确记录当前评分和错位坐标未变，而不是断言键差异不可能参与失败。

## 3. 重复与冲突检查

- §3 原比较段被替换，未在末尾再追加一套相近要求；继续承担“如何比较”。
- §4 的旧简洁性提醒被替换，负责“哪些比较值得进入 Knowledge”；具体保真检查集中在 §6。
- §1 负责测量与因果边界；§3 中容易暗示效果无效的类别名称同步收紧，§6 检查具体断言是否违反该边界。
- 未修改“有依据的机制假设可以保留、无需先隔离证明”“按共同语义与机制泛化”“不限制示例数量或原任务身份”的原段落。
- 未强制完整分支穷举、固定比较数量、每对一个 Knowledge、每个分支一个 Knowledge，或额外分析输出。
- 生产草案仍仅输出 entries；诊断草案仍输出原来的 comparisons + entries。各自 §7 及后续视图说明逐字不变。
- 历史 Memory 修订规则逐字不变。无 new label、need_evidence、confidence 或操作字段。

离线校验确认五处替换可完整反向还原基线。按空白分词，生产学习模板由 2,839 增至 3,041 词（+202）；诊断模板由 2,995 增至 3,197 词（+202）。不是零增长，但新增内容集中于具体判别与压缩检查，没有额外新增章节。字数不等于 tokenizer token 数。

## 4. 验证方案：先单配对同期对照，再决定是否扩大

下一轮计划共 4 次初始调用，尚未执行：

| 轮次 | B0 | B1 |
|---|---|---|
| R05 单配对 | 原 B 诊断 system | 本次局部修改后的 B system |
| R06 单配对 | 原 B 诊断 system | 本次局部修改后的 B system |

两组使用完全相同的单配对 user 输入、原 Memory、原调用参数、相同输出 schema。B0 重新调用，不直接拿一次历史输出当成同期对照。B1 仅替换学习模板，执行背景、共享输入说明和其他 system 尾部逐字不变。初始请求不含旧回答、格式反馈或本方案中的目标答案。只有原有格式/技术错误机制可以重试，语义遗漏不能触发答案提示或重采样。

分别在比较产物与 Knowledge 中按 complete / partial / missing / contradictory 人工判读，不以关键词出现或条目数量作为成功标准：

| 标准 | 必须检查的语义 |
|---|---|
| R05 分支对齐 | 双侧正负动作映射正确；Parent 正残差本就跨格延续；第一格停止只属于其负残差分支 |
| R05 经验保留 | 上述重要区别进入 Knowledge；不把所有改善归于边界规则；保留实际 135/189 → 189/189 |
| R06 完整选择规则 | Parent 名称为空才回退 code；Candidate 先看 code 库存键是否命中再回退 name；双表存在本身不算完整 |
| R06 下游意义 | 能说明选择会影响分组/库存池的条件性机制，不伪造 H12/H13 上的实际触发或贡献 |
| R06 经验保留 | Knowledge 保留双侧重要选择与回退区别，可以合并成自然语言，不强制逐字段抄写 |
| R06 因果边界 | 准确保留 15/17 和 H12/H13 未变；不据此排除键机制；允许有证据基础的假设 |
| 防退化 | H2:H18、任务身份和引用正确；没有新增重要事实错误；不把所有经验退化为“无法判断” |

R05 实际边界值读取和 0/∞ fallback 是单独跟踪的既有未解决项。本草案没有加入专门的边界读取规则；若它仍存在，应明确记录，而不能将局部目标改善宣称为所有问题已经解决。

判读后的动作：

- B1 完成 R06 关键对照及保留、避免因果排除，同时维持 R05 正确条件：作为有希望的初筛结果，之后再决定完整批次和匹配重复验证。
- B0 同样完成：不把成功直接归因于修改，需要重复样本区分波动。
- 比较完整、Knowledge 仍丢失：优先分析保留/概括环节。
- 比较仍不完整：检查实际选择了什么条件、在哪里截断依赖关系，不继续堆同义提醒。
- 内容更详细但新增重要事实错误：不以长度增长判为有效。

一个样本不能建立稳定效果；完整批次与重复验证的规模在后续执行前固定，不按“直到成功”为止追加调用。机器可读方案见 [validation_protocol.json](../../../../../artifacts/methods/v25/analysis/replay_local_revision_proposal_20261028_001/validation_protocol.json)。

## 5. 可审阅交付物

- [生产格式完整草案](../../../../../artifacts/methods/v25/analysis/replay_local_revision_proposal_20261028_001/production_candidate.md)及[相对 v3 的差异](../../../../../artifacts/methods/v25/analysis/replay_local_revision_proposal_20261028_001/production.diff)：仅供审阅，尚未安装为默认。
- [诊断格式完整草案](../../../../../artifacts/methods/v25/analysis/replay_local_revision_proposal_20261028_001/diagnostic_candidate.md)及[相对 B 的差异](../../../../../artifacts/methods/v25/analysis/replay_local_revision_proposal_20261028_001/diagnostic.diff)：用于拟议的小规模实验，不改变诊断 schema。
- [R05 B0 请求](../../../../../artifacts/methods/v25/analysis/replay_local_revision_proposal_20261028_001/R05/baseline_messages.json)、[R05 B1 请求](../../../../../artifacts/methods/v25/analysis/replay_local_revision_proposal_20261028_001/R05/candidate_messages.json)。
- [R06 B0 请求](../../../../../artifacts/methods/v25/analysis/replay_local_revision_proposal_20261028_001/R06/baseline_messages.json)、[R06 B1 请求](../../../../../artifacts/methods/v25/analysis/replay_local_revision_proposal_20261028_001/R06/candidate_messages.json)。
- [离线校验结果](../../../../../artifacts/methods/v25/analysis/replay_local_revision_proposal_20261028_001/offline_validation.json)：包含输入一致性、输出约定、泛化规则和历史规则不变，以及生产与旧实验文件哈希。

以上请求文件仅已准备，未发送；API 调用数为 0。没有将草案命名或注册成正式 v4，避免与输入视图 v4 混淆。

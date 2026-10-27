# V23.4 Replay 条件性认识统一优化与真实验证

2026-10-22。**建议保留现有 P4 学习 Prompt，不采用本次候选替换它。** 候选在 R05 补回历史整合和正确对象能力保持，但没有校准过强的“不存在”条件，且遗漏当前 apple 搜索改善；R06 丢失已有零局部温变收益与多实例能力保持比较，并新增历史响应的错误归并。成本变化没有形成足以抵消这些退化的收益。

这是两个冻结案例、各一份首个合法输出的初步选择，不证明 P4 稳定可靠，也不否定按条件组织学习的总体方向。本轮到此结束，不自动继续 Prompt 迭代。

## 候选与真正的设计变化

完整主 Prompt：[replay_conditional_learning_v2.md](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_4/conditional_learning_001/replay_conditional_learning_v2.md)。独立标识为 `v23_4_replay_multi_knowledge_conditional_v2_candidate`，仅保存在实验目录，未加入生产注册表或覆盖默认版本。

候选基于 `v23_4_replay_multi_knowledge_v1`。P4 本来已经要求核对范围、机会、历史与证据，本次没有把这些说成新发现。主要重组如下：

| 决策 | 候选相对 P4 的变化 |
|---|---|
| 先比较什么 | 由实际编辑的行为要求和适用范围确定比较对象；全局任务概览用于寻找相关材料，不直接作为 Knowledge 的组织骨架 |
| 怎样解释响应 | 围绕实际条件比较变化、保持、未触发或未知、退化与能力保持；区分规则适用、可观察执行和新增收益 |
| 什么成为 Knowledge | 从支持的响应形成可用于未来修改的条件性认识，再按关系和边界决定粒度；不生成 D/S/C 标签或更新指令 |
| 怎样修订历史 | 先明确当前证据提供的支持与限制，再协调旧认识；将保留历史观察与保留旧解释区分，输出完整数组 |

保留实际 Diff 优先于 Plan、真实 Pair、独立时间轴、局部与整体区分、重要不对称比较、每项独立 Evidence、完整数组替换和一次 Replay 调用。合并了原先分散的学习、粒度、历史复核表述；不是在末尾追加规则。没有对象专用规则。

主 Prompt 从16,084减至12,890字符，约减少19.9%；完整 System 从23,173减至19,979字符。**长度减少不是效果依据。** 输出契约从 P4 原样复制。详细设计及预先识别的泛化/历史遗漏风险见 [DESIGN.md](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_4/conditional_learning_001/DESIGN.md)。

## 冻结条件与实际调用

使用 P6 实际发送的 R05/R06 HTTP 请求，以及 P4 冻结完整 bundle。程序只替换 System 的主学习 Prompt 前缀，User 字符串完全相同；Actor 执行背景、Memory v3、Pair 和多 Knowledge 说明后缀逐字相同。R05 User 为884,531字符，R06为857,205字符。

初始配置均为 deepseek-v4.1-flash、temperature=1、thinking enabled/medium、max_tokens=32768、非流式，复用原端点、超时和单请求传输。原 `validate_entries`、Memory contract、commit/load、Memory v3 和 Preconditioner 投影函数不变。

基线不重跑：采用 P4 学习 Prompt 在 P6 的首次合法输出——R05 attempt_002、R06 attempt_001。候选每案例取得一份合法输出后停止，不按语义评价重采样。实际发生两次已授权技术/格式重试：

| 案例/尝试 | max_tokens | 输入 tokens | 输出 tokens 含 reasoning | finish_reason | 结果 |
|---|---:|---:|---:|---|---|
| R05 / 1 | 32,768 | 286,421 | 32,768 | length | 达到输出上限，不采用 |
| R05 / 2 | 65,536 | 286,421 | 49,186 | stop | 首份结构合法结果 |
| R06 / 1 | 32,768 | 276,845 | 17,699 | stop | 现有引用校验拒绝 `S1_R05/Q8:50`；该历史执行仅23步 |
| R06 / 2 | 32,768 | 276,845 | 29,562 | stop | 首份结构合法结果 |

**R05 第二次沿用既定 length 重试规则提高输出上限，因此其合法结果并非与基线完全同输出预算的对照。** Prompt 和事实没变，但不能把差异都归因于 Prompt。R06 的两次均保持原32,768上限。两组都只重启一次，没有耗尽最多三次重启额度，没有 HTTP429 或 Actor/Editor 重跑。引用错误没有手工修补；语义错误没有触发调用。

本轮共4次 HTTP、2份合法提案，总输入1,126,532、输出129,215、合计1,255,747 tokens。基线历史调用（R05两次、R06一次）合计924,316 tokens，仅作历史成本参照，不是本轮重新消耗。

## 四方面比较

完整逐 Knowledge 审查在 [SEMANTIC_REVIEW.md](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_4/conditional_learning_001/SEMANTIC_REVIEW.md)，支持事实与原始提案引文在 [EVIDENCE.json](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_4/conditional_learning_001/EVIDENCE.json)。审查关注是否实质影响后续更新，没有为每个瑕疵设计新机制。

### 条件性认识质量

R05 的进步是真实的：不再出现将历史 drawer8 动作错归当前 Q7:25；用当前位置实例而非 receptacle types 描述新增探索；正确分解 soapbar-to-toilet 的8→6，指出 Parent 多出的格式异常与 inventory，而不直接归因合法动作条款。

但核心边界未改善：当前 butterknife、soapbar 与历史 near-match 任务仍被描述为目标 absent。当前未去 cabinet18/shelf1的事实在输入中清楚可见，证据只能支持未找到。搜索主题还把范围外 bowl-with-desklamp 的保持纳入“搜索改写没有退化”的说明，且完全遗漏当前 apple14→11的三步搜索改善。旧 P4 至少保留了 apple 总数及双方引用。

R06 保留 heat plate 的13成功/50失败，写明没触发不能证明无效，这是延续基线的有效能力。与此同时，温变成功条目将历史 pot 等 Parent 统一概括为插入并循环门；pot Parent 实际只是开 fridge 后直接冷却，没有插入或门循环。它还删除了基线对当前 cool tomato 的关键限制：两侧取物后五个动作相同，18→10全部差在取得目标之前，不能视为新增温变节省。

**判断：没有形成一致的条件性质量提升。** 某些句子更像条件性认识，但其条件仍可能未经证据确认，重要限制也可能在综合时消失。

### 历史经验保持与校准

R05 从基线单纯新增，转为修订 M8/M6并新增合法动作主题。历史 bread 的改善与反向失败、plate 的38成功/50失败，以及历史 cup搬运/加热的区别都得到保留。当前成功 butterknife 的8/8步能力保持也补回，这是有用增量。

代价是更偏重旧认识复述，旧 absent 解释被继续继承；当前 apple 有效响应从新提案和引用中消失。更多历史文字不等于完成历史校准。

R06 仍修订 M7/M10，历史 butterknife/soapbar修复、cool apple38→46退化、heat plate不对称均在。但历史 `no exact butterknife present` 原样延续；当前 creditcard24→9与多实例能力保持不再出现。历史 R03 mug 未在新温变条目中复述，但仍留在未修订 M11，因此没有把它误判为整个 Active 的丢失。

**判断：历史重要观察基本有保留，但解释校准未达成；相对 P4，当前重要响应覆盖退化。** 这不是仅仅少列了某个例子：遗漏改变了对“搜索何时改善”和“温变何时只有能力保持”的认识。

### 对 D/S/C 的潜在价值

| 维度 | 可参考的内容 | 影响采用的限制 |
|---|---|---|
| D 方向 | 强化精确对象措辞仍不能稳定制止替代，且正确目标获取能力应保留；部分效率差可归为搜索/格式行为 | R05搜索正向比较丢失，可能造成单侧负面认识；R06把不同温变响应错误概括成同一种改善 |
| S 条件、范围与强度 | 机会不对称被保留，部分观察有明确任务条件 | absent并非已证条件；局部零收益边界丢失，会影响适用范围与强化程度判断 |
| C 协调 | cool plate 的额外搜索开销与少开门同时存在，仍能提示不要用整体步数代替局部判断 | 当前多实例能力保持缺失；没有新增可确认的条款交互证据，不能因分了主题就认定协调认识更好 |

上述仅是潜在用途评价，没有调用 Preconditioner 生成 Adjustment/Patch，也没有运行下一轮 Actor。结构兼容不等于 D/S/C 决策质量得到改善。

### 成本与复杂度

| 指标 | R05 P4 | R05候选 | R06 P4 | R06候选 |
|---|---:|---:|---:|---:|
| 新提案 Entry / Knowledge | 1 / 4 | 3 / 6 | 2 / 5 | 2 / 5 |
| 新提案 Knowledge 文本字符 | 3,502 | 7,719 | 6,592 | 5,663 |
| 最长新 Knowledge 字符 | 941 | 1,874 | 1,947 | 1,496 |
| 新提案 Evidence 引用次数 / 去重数 | 43 / 29 | 115 / 105 | 114 / 99 | 62 / 56 |
| 替换后 Active Entry / Knowledge | 8 / 11 | 8 / 11 | 7 / 10 | 7 / 10 |
| Active Knowledge 文本字符 | 19,430 | 19,499 | 16,688 | 15,759 |
| 下一轮 Memory v3 字符（原始口径） | 819,075 | 868,760 | 817,146 | 734,780 |
| 固定 Preconditioner User 字符（原始口径） | 1,001,947 | 1,051,632 | 957,526 | 875,160 |
| Memory v3 字符变化（统一实验 ID 长度） | — | +5.94% | — | −10.09% |
| Preconditioner User 字符变化（统一实验 ID 长度） | — | +4.85% | — | −8.60% |

R05 提案文字增加120.4%，但因替换了旧长条目，Active 文字只增加0.36%；输入增长主要还包含更多历史 Evidence 展开的窗口，不能只由提案大小推断。R06 Active 文字减少5.57%，但输入减小的一部分来自有效来源和窗口减少，不能全部当作压缩收益。

确定性投影显示：

- R05 补入当前成功 butterknife P6/Q6完整八步窗口，但当前 apple P10/Q10不再保留为来源；pillow P2/Q2也不再保留。P8:8仍不在详细窗口。
- R06 不再保留当前 creditcard P7/Q7，以及历史 hot apple/heat egg 的 Parent来源 S1_R03/P8、P9；文本仍谈到后两者的 Parent 对照，独立 Evidence 因而不足。
- R06当前 tomato 的详细窗口从 P2:10–18/Q2:2–10缩成P2:10–14/Q2:2–6；冷却动作本身仍在完整 trace，但其详细状态不再展开。

下游规模来自**同一份固定 Preconditioner 探针**、替换不同隔离 Memory 的离线投影；不是实际下一轮 Diagnosis，也不是实际 token 计费。统一实验 ID 长度只用于公平计数，没有改写归档。详细值、窗口和引用见 [COMPARISON_METRICS.json](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_4/conditional_learning_001/COMPARISON_METRICS.json)。

候选真实 Replay 的合法调用输入比基线各少647 tokens，但输出 tokens：R05 23,502→49,186（且上限不同），R06 20,723→29,562。主 Prompt 更短没有转化为更低的本轮调用成本。

## 采用决定与下一阶段

**不采用本次候选替换 P4；P4 继续作为下一阶段的 Replay 主对照版本，本候选仅归档。** 不将本轮两份提案发布到 Active Memory，不从失败或合法输出中手工挑句拼装成“改进结果”。

理由不是追求每句话零错误，而是两组都没有同时满足“条件性更好、有效经验不退化、无严重新增问题”：R05的改进伴随关键正面比较消失和错误条件；R06已有边界退化、旧解释仍未校准，节省的输入部分来自证据损失。R05的输出预算变化也限制了严格因果比较。

这一选择是当前候选与 P4 的相对判断，**不代表 P4 的旧 P6 提案全部可直接发布或自动学习已稳定**。既有语义审查结论继续有效。下一阶段可以按现行 P4 和正式已有 Memory 推进 Skill 更新方法比较；无需因本轮结果立刻开启另一次 Replay Prompt 专项研究。本轮未启动这些后续实验。

## 原始结果和完整性

- [R05候选原始合法 JSON](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_4/conditional_learning_001/runs/R05_replay/attempt_002/parsed.json)；[P4基线](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_4/multi_knowledge_p6_001/runs/R05_replay/attempt_002/parsed.json)。
- [R06候选原始合法 JSON](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_4/conditional_learning_001/runs/R06_replay/attempt_002/parsed.json)；[P4基线](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_4/multi_knowledge_p6_001/runs/R06_replay/attempt_001/parsed.json)。
- 选择记录、尝试结果、提案及必要失败证据保留在 `runs/`；完整请求、HTTP响应和其余调用数据按原相对层级存入 [调用归档](../../../../artifacts/methods/v23_4/conditional_learning_001/runs/)，未修补。完整 Memory 预览与投影见 [Memory 归档](../../../../artifacts/methods/v23_4/conditional_learning_001/cases/)。
- [输入对照核验](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_4/conditional_learning_001/config/INPUT_COMPARISON.json)、[调用审计](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_4/conditional_learning_001/AUDIT.json)、[预先固定协议](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_4/conditional_learning_001/PROTOCOL.md)。
- 隔离提交、原样重载、幂等性、历史档案保持、所有 Knowledge 引用进入来源解析及详细窗口、Preconditioner 读取、未来 Replay Pair兼容均通过：[R05链路检查](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_4/conditional_learning_001/cases/R05/results/MEMORY_AUDIT.json)、[R06链路检查](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_4/conditional_learning_001/cases/R06/results/MEMORY_AUDIT.json)。这些只是技术完整性，不作为语义采用证明。

候选、运行脚本、事实和协议在调用前冻结；生产代码、P4 Prompt、Schema、Memory v3算法、D/S/C与Patch算法及模块职责未变。**12,493个既有受保护文件哈希核验一致。** 所有新增文件、Memory预览和报告只在本隔离目录，正式Active Memory未发布任何本轮结果。

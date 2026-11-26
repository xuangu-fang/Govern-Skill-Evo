# v28.4 Prompt 修订审阅

状态：保留第 1—3 步的 Prompt 设计审阅，四份提示词原文未改动；第 4—5 步独立实现与离线验收现已完成，见 [IMPLEMENTATION.md](IMPLEMENTATION.md)。本文审阅自然语言职责与传递关系；**没有调用真实模型或启动正式训练/Test**。静态检查只能证明文本、版本、接口描述和冻结边界的一致性，不能证明模型会正确选择操作或提升 EM。

## 1. 修改位置与理由

| Prompt 段落 | v28.3 风险 | v28.4 修订 |
|---|---|---|
| Diagnosis / Examine current evidence | 已提示查看 Parent，但未完整明确修正选择；失败仍可能被转成重复提醒 | 按缺失、误导、冲突、可执行性等关系选择新增、修改、合并、替换、删除或不修改；无操作偏好 |
| Diagnosis / Construct complete, scoped Updates | independently justified 等措辞可能把组织重心放在各项是否单独可评估；旧文又有 prefer revising 偏好 | 依据共同问题和修正方向，保留必要配合，不按任务或未来 Gate 去留拆分；移除预设修改优先 |
| Diagnosis / Update text 与局部协调 | 实施所需旧规则处理可能只出现在 reason；强制逐行要求可能分裂一个完整修正 | text 承载选定修正及旧指导处理；可用段落/列表，条件就近，不增加 schema 或必须逐项填写的清单 |
| Diagnosis / Organize guidance for execution | 缺少可执行的组织方向 | Workflow / Error Avoidance 可选，已有清晰结构可保留；不填模板、不设数量和长度要求 |
| Preconditioner / Frozen proposal | 可能只评估新行为是否合理，未检查旧指导怎样变化 | 理解并审查修正方式及 Parent 的处理；允许在 Original 内有依据地调整 |
| Preconditioner / Coordination、KEEP、REPLACE | 合理主方向可能掩盖附带改变或留下旧冲突；完整修正丢在 reason | 整条审查；完整 REPLACE 包含最终策略、旧指导处理与保护边界；区分规则合并和 ID 合并 |
| Preconditioner / 组织指导 | 组织建议可能成为强制改写的理由 | 不因标题、条目数、长度或操作比例改变判断；只调整与 Original 实质相关的组织问题 |
| Editor / Input and implementation scope | 能修改旧规则，但仍可能以追加替代落实；也可能擅自重新决定修正方式 | Effective Update 决定行为方案，Editor 决定准确措辞和 patch；修改/删除落实到相关原文，必要局部整理不越界 |
| Editor / Organize authorized guidance | 简洁要求可能被误读为删条件，或每条 Update 新建一节 | 可读的段落/列表与可选组织；不改变授权行为，不压成一句，不要求每个 ID 独立章节 |

四份完整 Prompt 在 [prompts](prompts/)，相对冻结 v28.3 的统一 diff 在 [diffs](diffs/)。Diagnosis/Preconditioner 的 input-view 名称仅更新为计划 v28.4 身份，序列化结构不变。Replay 全文不变。

## 2. 保留项

逐字保留三个修改模块的 SearchQA 执行/编辑边界与 Frozen Actor protocol/runtime 段落；Diagnosis 保留实体/关系、答案边界、参考形式的专门分析和题目语义要求。没有把 SearchQA 替换为通用文档问答，也没有要求看不到的图片、隐藏 reasoning 或外部检索。

保留完整 task.question/context、原始 user 消息以及现有三项通用去重。Diagnosis 的 Evidence、精确 JSON 输出与执行引用列表保持原文；Preconditioner 的完整编译、引用和精确输出合同保持原文；Editor 自 Exact unnumbered patch 起的定位、组合、空串/null、输出协议保持原文。Replay、Gate、Memory、恢复及预算不改变算法。

当前改动没有添加 operation、rule_id、Checks、长短评分、条目上限、分类字段或单独压缩请求。没有把必须包含 Workflow/Error Avoidance 或“修改优先”写入响应验证条件。源自 SkillAdam 的组织启发不等于采用其完整算法、Stage0 或规则数量政策。

## 3. 手工审阅场景与后续验收设计

以下为抽象/合成场景，不来自 Test 的实例答案。它们是审阅预期，**不是已经运行的模型测试**。第 4—5 步已用合成响应验证合同与接线；这 15 个场景仍是自然语言审阅预期，不代表 15 次模型测试。自然语言选择是否合理仍需后续真实输出审阅。

| 场景 | 预期决策或实施边界 | 需要排除的误行为 |
|---|---|---|
| A. Parent 未提供一个有证据支持的判断步骤 | Diagnosis 可以新增，说明条件及与已有指导的关系 | 为提高“修改比例”强行改写不相关规则 |
| B. Parent 的通用简短要求使必要限定被省略 | Update 修改其范围并保留有效简短要求；Editor 落实旧规则处理 | 保留冲突的通用要求，只在末尾加相反提醒 |
| C. 两条相关规则对同一条件给出相反选择 | 同一完整 Update 可授权协调/合并，保留不同条件下有效分支 | 仅因句子各自可能得分就拆开，或删去必要例外换短文本 |
| D. 某项旧的无条件限制有支持证据表明有害 | 可删除/替换该限制，保护其余有效行为 | 认为删除不是合法改进，或借机删除整个章节 |
| E. Parent 已覆盖要求，但一次短答错误无法揭示原因 | 允许有依据的可执行性修订，也允许 no_change；说明不确定性 | 为制造规则缺口编造内部机制，或机械新增同义句 |
| F. 多题有同一修正，另一些题只有同一错误标签 | 前者可同一 Update；后者由真实修正方向决定 | 按题强拆，或把所有“实体错误”强合 |
| G. Original 主方向合理，但附带统一名称形式要求无依据 | Preconditioner 用完整 REPLACE 去掉/修正附带要求，保留必要条件及旧规则处理 | KEEP 整条，或仅在 reason 说不执行附带要求 |
| H. 历史有相关退化，但缺少历史上下文 | 用可见 Knowledge 限定判断；可保持、修订或撤回，不编造历史事实 | 把缺失当不存在，把 Defer 当无效，把无关联当成功保持 |
| I. Effective Update 明确要求修改一条旧规则 | Editor 可选择具体措辞/位置，并处理其必要关联文字 | 自行选择不同策略、加无关检查步骤、纯粹全文重写 |
| J. Effective text 缺少不可回避的关键行为选择 | Editor 返回具体 null blocker；缺少任务原文或未验证效果本身不构成阻塞 | 猜策略、偷删要求，或因条件由 Actor 判断就拒绝实现 |
| K. 初始占位 Skill 或已有清晰的其他标题 | 仅组织授权内容，可选 Workflow/Error Avoidance 或保留现有结构 | 强制两节、增加默认未授权规则、空脚手架、每 Update 一节 |
| L. 两 Update 使用相邻位置或共享只读 context | 保持 ID 各自映射到原 Parent，允许可组合修改；真正冲突按原合同处理 | 将相邻视为冲突，或合并 IDs、让一项 patch 偷载另一项修正 |
| M. 参考接受两个名称形式，标点/冠词不同 | 区分接受性与优越性，遵守 SearchQA 归一化及题目明确要求 | 用归一化已消除的差异解释翻转，或泛化成统一缩写规则 |
| N. 修正需要新增详细条件，Skill 因而更长 | 按证据、可执行性及实际效果判断，允许合理增长 | 按长度直接拒绝，或以少规则/短文本宣告成功 |
| O. 一项依赖被撤回或选中 patch 子集产生新组合 | 沿用依赖协调和来源标记；未执行组合不继承完整 Candidate 的已验证表现 | 隐藏依赖以通过结构检查，或增加整体接受兜底改变 Gate |

## 4. 检查分层

第 1—3 步文档静态核对：冻结副本与当前来源一致；预算和批次记录一致；完整 Prompt 与 diff 可追溯；保留段落及输出 JSON 示例不变；新身份仅为计划；链接有效；原代码/配置/旧文档和受保护实验未变化；暂停 PID 状态只读确认。结果见 [design_validation.json](design_validation.json)。

第 4—5 步已完成的实现验收：字段及引用权限、Original 冻结/REPLACE 编译、patch 映射与组合、Replay EM 翻转、Gate 选择、Memory 原子发布、恢复与请求额度；仅 SearchQA 口径，DocVQA 不作为依赖。

后续行为评估：审阅问题→Parent 关系→Original→Effective→patch→Selected 是否连贯，是否存在无效重复、未落实的旧规则变更、丢失必要条件或 Editor 越权；再比较实际 EM/F1 和成本。操作分布、规则数量和长度可辅助解释，不作为奖励、验收阈值或预定成功比例。

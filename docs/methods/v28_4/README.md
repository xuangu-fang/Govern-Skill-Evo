# SearchQA v28.4 设计稿

状态：2026-11-04，**第 1—5 步已完成，独立实现与 SearchQA 离线验收通过；正式训练已于 18:04（Asia/Shanghai）启动，完整成功后自动运行最终 Test。** 本目录 Prompt 仅由独立 v28.4 链路加载，现有 v28.3 运行器不变。v28.3 原实验保持原样，v28.2 继续暂停。实现入口、537 项离线测试及保证边界见 [IMPLEMENTATION.md](IMPLEMENTATION.md)。

核心原则：**以问题和现有指导的关系决定修正方案，以完整 Update 约束实施，以清楚的组织承载有效条件。** 优化目标是生成更合理、可执行、有效的 Skill。长度下降可以是结果，不是独立目标、接受条件或规则数量约束。

## 1. 基线与问题

直接基线是撤回 SearchQA question/context 字符范围表示后的 v28.3。冻结材料在 [baseline](baseline/)，逐文件来源与计划版本见 [source_map.json](source_map.json)。所有新提示词以冻结的 v28.3 为起点，不重新套用 DocVQA 提示词。

已完成的 v28.3 实验表现出有效能力，也暴露了持续积累复杂规则的风险：最终 Skill 为 29,703 字符、45 个列表项；此前与同 benchmark SkillAdam 的配对分析显示，Test EM 为 1187/1400 对 1174/1400。在相同 Test user 消息和执行参数下，v28.3 每题输入比 SkillAdam 多 4,776 tokens。这些观察说明有必要改善规则形成及实施方式，**不说明长规则一定无效、短规则一定更好，也不能从一次实验断言泛化效果稳定更优**。

不把所有增长都归咎于 Editor 追加，也不假定每次失败都是 Parent 缺规则。v28.4 要解决的是：新增、修订、整合和删除相关指导的选择能否明确基于问题与 Parent 的关系；选择能否完整传至 Editor；实施是否准确保留必要条件并消除被替换的旧冲突。有效的细分条件和例外可以继续增长。

保留的原实验目录：

- 训练：`experiments/campaigns/v28_3_searchqa600_batch30_20261104_022828`
- Test：`experiments/evaluations/v28_3_searchqa600_batch30_20261104_022828_test1400`
- 监督记录：`experiments/automations/v28_3_searchqa600_batch30_20261104_022828`
- 暂停的 v28.2：`v28_2_searchqa600_batch30_promptv2_20261104_010013`，PID 30019、30020 不发送继续或终止信号。

上述实验只作为设计背景保留；新 Prompt 不加入 Test 题目、答案、任务 ID 或从 Test 反推的具体规则。由于已查看过 v28.3 的 Test 结果，后续同一 Test 对比应如实说明这一方法设计背景，不能包装成完全未接触的盲测。

## 2. 三个模块的职责

| 模块 | 必须完成 | 不承担 |
|---|---|---|
| Diagnosis | 对照当前执行与 Parent/base 指导，确定有依据的行为修正；将修正方式、必要旧规则处理和保护边界放入完整 Original Update | 不为每个错误自动新增；不按未来 Gate 成败拆分；不读历史 Memory，不写 patch |
| Preconditioner | 用当前引用证据和相关 Memory，在 Original 问题边界内审查/调整方向、范围和协调关系，形成完整 Effective Update | 不重新扫描发现无关修复；不拆分或合并 IDs；不把修改旧规则降格为追加警告 |
| Editor | 忠实实施 Effective Update，选择准确措辞、位置和 patch，实现授权的新增、改写、合并、替换或删除及必要局部整理 | 不重新选择行为策略；不主动扩展修复范围；不为变短而删条件或重组全篇 |

### Diagnosis：先看问题与现有指导的关系

比较任务要求、完整上下文、普通回答、评分差异以及 Parent/base 的实际指导。判断其缺失、误导、冲突、条件不明确、难以落实，或证据不足以支持修改。已有规则不意味着问题已解决；一次失败也不意味着需要再增加同义规则。

选择最能解决问题的方式：新增、修改、合并相关指导、替换、删除有问题的指导，或不修改。**不预设新增或修改更好，不要求每轮包含某种操作，不设比例。** 合并或删除须服务于有依据的行为修正，例如消除冲突选择或不当限制；不单独提议行为不变的文字压缩。

Update 按共同问题与修正方向形成。多个任务可以支持同一项修正；相同错误标签不必对应相同修正。同一修正所需的动作、条件、例外、优先级、旧规则处理和依赖保持完整，包括跨不同段落的必要配合。不按任务数、句子数或未来去留拆分，也不要求独立因果证明。

每条 Update text 应让下游知道改变什么行为、何时适用、相关旧指导需要怎样处理、哪些有效分支保留。可用自然语言指出相关规则的内容或可辨识措辞，不新增 operation/rule_id 字段，不要求行号或草拟 patch。reason 说明依据与不确定性，不能成为实施要求的唯一载体。

### Preconditioner：审查完整修正，而非只赞同主方向

保留 Direction / Scope / Coordination。除触发、动作、强度和例外，还审查选定修正方式及相关旧指导处理。当前证据或历史可以支持改变修正方式，但必须留在原问题和既有 IDs 内。既不因“旧规则存在”机械撤回，也不因“主方向有效”保留无依据的附带要求。

KEEP 表示全文可作为合理试验；部分需修正时用完整 REPLACE。REPLACE 传递最终行为、旧指导处理、条件、例外、优先级和依赖，不能仅在 reason 中说“同时删除旧限制”。WITHDRAW 仍需处理其撤回对其他 Original 的必要依赖。合并 Skill 中相关规则与合并 Update IDs 是不同操作：前者可由完整 Update 授权，后者仍禁止。

参考接受性、当前成功与干预改善不能混用：多种 reference 可得分不表示其中一种更优；实际执行保持成功只提供该任务的有限保持证据；未执行提案没有已验证收益；无 Knowledge 关联也不证明保持成功。保留 v28.3 对历史未知、联合干预和 EM 翻转证据的边界，不增加新类别或统计字段。

### Editor：准确实施，不再诊断

Effective Update 已决定行为修正，Editor 的裁量是实现措辞、定位与 patch。要求改写/删除旧规则时应落实到该规则及必要受影响文字，不能只在末尾加“例外”而保留原冲突。要求新增时，也不能为了少一条规则而强行合并。必要的相关局部整理随该 Update 实施；无关有效规则保留。

缺少任务原文不是阻塞理由：完整 Update 可要求 Actor 在运行时检查上下文条件。若 Update 本身留有实施所必需而无法确定的行为选择，Editor 不猜策略，使用现有 `patch=null` 合同报告具体阻塞。`patch=""` 仍仅表示原 Parent/base 已充分满足要求；不得依赖另一 patch 的未来内容作此判断。

## 3. 组织方向：建议，不是模板

推荐在合适时用 Workflow 承载可复用的判断流程和条件分支，用 Error Avoidance 承载具体误用及边界。两者是表达工具，不是固定分类体系。

- 不强制英文标题、恰好两个章节、规则数量、单条长度或总字数。
- 清楚的既有组织可以保留；不为套模板重写全部 Skill。
- 条件、例外、优先级靠近对应决策，不在两个章节重复同一规则，不把例外与适用动作割裂。
- 初始 Skill 无已学习规则时，只组织 Update 授权的行为，不预填新的工作流程，不创建等待填充的空章节。
- 排版或位置若改变适用范围、优先级或行为，必须由 Update 授权；Editor 的表达自由不包含新策略。

SkillAdam 的迭代提示词提供了这类组织参考；其 Stage0 两节硬约束、达到数量后删并规则的规则，以及偏向避免新增的要求均不迁移。本地 SearchQA Stage0 关闭，初始 Skill 沿用相同占位文本，不注入预写 Workflow/Error Avoidance 规则。

## 4. 不变的链路与 SearchQA 适配

链路仍为：Parent 全批执行 → Diagnosis → Preconditioner → Editor → Candidate 全批执行 → Replay → Gate → Memory/Selected Skill。没有 Grouping、压缩器、附加审查模型或独立的组织重写阶段。

机器字段、证据权限、冻结 Original、按 Update 映射的 patch、EM 翻转 Replay、确定性 Gate、顺序 Memory 提交与轻量恢复均沿用 v28.3，完整定义见 [CONTRACTS.md](CONTRACTS.md)。Replay Prompt 逐字保留；Gate 不引入长度惩罚或净收益兜底。合同中自然语言质量要求不变成规则数量、标题或操作比例校验器。

SearchQA 必须保留的边界：

- 完整 question/context 可见；上下文中存在某信息不证明 Actor 实际使用了它；普通回答不证明隐藏推理过程。
- 单轮无工具 Actor、固定 base protocol、answer 元素与现有提取逻辑。
- 实体/关系、答案边界、名称/参考形式的区分；保留题目要求的限定、单位、时间、粒度，优先最小充分答案单位，而非最短字符串。
- 原生 EM/F1 与归一化；冠词/标点变化不能直接解释得分翻转；F1=1 不必然 EM=1。Replay/Gate 只用 EM 翻转，F1-only 不投票。
- 当前执行、历史事件、Update 关联、Gate 选择的区分；未归因事件保留而不分配具体 Update 的票。
- 三项通用去重保留：重复请求、重复普通回答、相同完整 system/Skill。**完整 task.question/context 与 Actor 原始 user message 均保留，不启用字符范围引用。** Replay 原有 P/Q 同题 user 消息共享保留。

DocVQA 不作为运行依赖或必需验收对象。v28.3 数据与结果不改写为 v28.4；未来新链路使用独立身份、独立目录和独立 Memory。

## 5. 冻结配置与预算

配置的逐项基准是原样快照 [baseline/v28_3_config.json](baseline/v28_3_config.json)。此文件记录 v28.3，不是可执行 v28.4 配置。第 4 步已按该基准生成独立 [v28.4 运行配置](../../../experiments/configs/v28_4_searchqa_train600_batch30.json)，仅隔离方法身份、Prompt 绑定和输出位置，实验参数不变。

| 项目 | 保持值 |
|---|---|
| Actor | deepseek-flash，thinking enabled，reasoning_effort=medium，temperature=1.0 |
| Actor 输出上限 | 32,768 tokens；单轮、无工具 |
| Diagnosis / Preconditioner / Replay 输出上限 | 各 65,536 tokens |
| Editor 输出上限 | **32,768 tokens** |
| 模块模型设置 | 同一 endpoint/model/thinking/reasoning_effort/temperature |
| Actor 超时 / 连接超时 | 300 / 10 秒 |
| 模块超时 | 600 秒 |
| 请求额度 | 每调用最多 6 次总请求；Actor SDK retries=0；恢复不重置 |
| Actor / 模块重试间隔 | 1 / 2 秒 |
| 输入限制 | max_input_chars=4,000,000；max_message_utf8_bytes=6,000,000 |
| 优化数据 | 原 600 题、20 批 × 30，ID 与批次顺序完全相同 |
| 最终 Test | 原独立 1,400 题，仅评估，不反馈优化 |
| 训练 / Test workers | 15 / 15 |
| 初始 Skill | 原 104 字节占位文本，无已学习规则；不使用 v28.3 最终 Skill 热启动 |
| 初始 Memory | `{"rounds":[]}` |
| 其他 | continue_no_change=true，semantic_resampling=false，knowledge_review=disabled_v1 |

Actor 原始提示词和运行说明快照在 [baseline/actor](baseline/actor/)。请求及重试参数、评分、数据拆分、初始化、归档与恢复保持原配置。输入安全限制不是新增 Skill 长度目标。设计时预留的新身份已按 [CONTRACTS.md](CONTRACTS.md) 第 1 节绑定；source_map 同时保留 planned_identity 和实际 bound_identity，逐项一致。

## 6. 交付与后续顺序

第 1 步已冻结基线和实验边界；第 2 步已定义职责、接口与不变量；第 3 步已形成可供后续绑定的完整英文提示词和逐项审阅材料：

- [Diagnosis](prompts/diagnosis.md)、[Preconditioner](prompts/preconditioner.md)、[Editor](prompts/editor.md)、[Replay（不变）](prompts/replay.md)。
- [Prompt 审阅及验收场景](PROMPT_REVIEW.md)，[逐模块差异](diffs/)。
- [来源与计划版本](source_map.json)，[文档静态核对记录](design_validation.json)。

第 4 步已实现独立 v28.4 包、CLI、身份绑定和冻结配置，不改 v28.3 运行代码/Prompt。第 5 步已完成仅针对 SearchQA 的离线合同、恢复、映射与组合验收，共 537 项通过，其中 v28.4 专项 134 项。合成输入覆盖新增、修改、合并、替换、删除与无修改；手写响应不替代真实 Prompt 决策评估。详细结果见 [IMPLEMENTATION.md](IMPLEMENTATION.md)，原设计快照与静态记录保留。

正式运行已另获授权，使用独立目录 `v28_4_searchqa600_batch30_20261104_180344`，由监督器先训练再独立 Test。运行状态见 [status.json](../../../experiments/automations/v28_4_searchqa600_batch30_20261104_180344/status.json)。后续评估应记录每轮 Original→Effective→patch→Selected 的一致性，以及条目被修改而非叠加、必要条件是否保留、是否存在无授权整理。观察 EM/F1、每轮变化、token/成本和 Skill 结构；不以 Update 数量、KEEP/REPLACE 比例或短文本作为优化成功证据。当前设计不能保证提高成功率，真实收益和行为稳定性仍待实验验证。

# OfficeQA v26.2 实验设计

后续正式训练和评测见[实验归档入口](../../../experiments/methods/v26_2/v26_2_officeqa_train74_20261117_013308/README.md)。

设计日期为 2026-11-17（Asia/Shanghai）。本文规定 v26.2 的训练调度、完整 Preconditioner 提示词和评估口径，供实现前评审。

**实验问题**　在同一批 74 道优化题上，把八轮调整为七轮，并让 Preconditioner 围绕 Actor 的具体选择审查每条提案，最终选出的 Skill 在 172 道 OfficeQA 测试题上表现如何？七轮调度同时改变每批证据和 Skill 获得更新的次数。v26.2 与 v26.1 的整体比较只能回答两项改动合用后的效果。

| 设计项 | v26.1 | v26.2 |
|---|---|---|
| 训练调度 | 10 / 10 / 10 / 10 / 10 / 10 / 10 / 4 | 11 / 11 / 11 / 11 / 10 / 10 / 10 |
| Preconditioner 核心判断 | 用 Direction / Scope / Coordination 组织说明 | 从 Actor 当时能看到的线索出发，判断提案会改变哪个选择、何时适用，以及与其他指引共同生效时会怎样 |

完整英文 system prompt 单列为本文附件，可直接通读。其余实验条件以 v26.1 正式训练配置和方法合同为基线。[v26.2 完整 Preconditioner](prompts/preconditioner.md) · [v26.1 正式训练配置](../../../experiments/campaigns/v26_1_officeqa_train74_roles_20261105_202041/config.json) · [v26.1 方法合同](../v26_1/CONTRACTS.md)

## 1. 数据与七轮调度

使用 OfficeQA Full 的固定 release `763a8366abf2a3605c381d53586d844dc60fa756`。将原 Train 50 题与 Validation 24 题依次拼接，保留来源标记，作为一个优化池按顺序走完一遍。初始状态采用 v26.1 正式运行的初始 Skill 和空 Memory `{"rounds":[]}`。历史运行只提供比较数据。测试集依照同一 release 的 172 个 Test ID 及顺序，与优化池无交集。[数据清单](../../../data/officeqa/releases/763a8366abf2a3605c381d53586d844dc60fa756/prepared/manifest.json) · [初始 Skill](../../../experiments/campaigns/v26_1_officeqa_train74_roles_20261105_202041/initial_skill.md) · [基线调度与 Test ID](../v26_1/experiment_plan.json)

下表位置从 1 起算。题目栏省略共同前缀 `UID`，每个四位编号均为实际 ID 的后缀。R05 前六题来自 Train，后四题来自 Validation；这一交界保留了 v26.1 的输入顺序。

| 轮次 | 位置 | 题数 | 题目，按输入顺序 |
|---|---|---:|---|
| R01 | 1–11 | 11 | 0002, 0007, 0014, 0017, 0018, 0019, 0026, 0028, 0030, 0031, 0033 |
| R02 | 12–22 | 11 | 0034, 0044, 0046, 0049, 0056, 0063, 0065, 0073, 0079, 0083, 0085 |
| R03 | 23–33 | 11 | 0087, 0092, 0098, 0101, 0110, 0115, 0122, 0123, 0133, 0141, 0144 |
| R04 | 34–44 | 11 | 0145, 0150, 0151, 0162, 0163, 0165, 0166, 0169, 0189, 0195, 0202 |
| R05 | 45–54 | 10 | 0212, 0222, 0228, 0229, 0238, 0241, 0001, 0027, 0039, 0041 |
| R06 | 55–64 | 10 | 0052, 0070, 0072, 0086, 0091, 0109, 0142, 0154, 0159, 0161 |
| R07 | 65–74 | 10 | 0170, 0190, 0213, 0217, 0220, 0233, 0234, 0235, 0239, 0240 |

从 R01 起，Diagnosis 和后续同批比较看到的样本组合便与 v26.1 不同。轮号仅表示各版本内部的更新顺序。七轮提供七次更新机会，包括可能保留原 Skill 的轮次。

## 2. Preconditioner 如何审查一条提案

开场交代职责和交接对象。输入为完整 Parent、冻结的 Original Plan、Plan 引用的本轮完整执行记录，以及按轮追加的历史 Memory。Diagnosis 看到全批，Preconditioner 只看到 Plan 引用的执行。模型应区分决策当时已可见的材料、随后返回的工具观察，以及只在执行结束后产生的评分。

四段已选英文作为一个连续段落组逐字收录于 **Review each proposed change**。第一段把 Parent 的措辞、Actor 实际表现和 Original 要求的选择放回同一个决策点。第二段用表格列歧义和已明确的表头检验适用边界，并要求权衡有记录的历史退化或无目标收益。第三段将提案放回完整 Parent，与其他提案一起检查冲突、重复和依赖。第四段给出每条 Original 的动作判据。[四段英文原文](prompts/preconditioner.md#review-each-proposed-change)

四段之后沿用 v26.1 的三条约束。新增阈值、优先级、执行顺序或停止条件须有证据支持。撤回某项 Update 若移除了另一项的必要前提，应相应修订或撤回受影响项。若在 Original 的问题范围内无法化解实质风险，应撤回该提案，避免将适用范围缩到实际不起作用。[三条约束](prompts/preconditioner.md#conditions-for-a-supported-correction)

其后的 **Effective Plan and Editor handoff** 只说明程序怎样编译 Effective Plan、Editor 能读到什么、如何保留提案 ID 和来源。末尾 **Exact output contract** 定义唯一的 JSON 结构，每个 Original 对应一个含 `target`、`action`、`text`、`reason` 的调整项。KEEP 和 WITHDRAW 的 `text` 为 null；REPLACE 的 `text` 是与原文不同的完整指令。Editor 只接收 Parent、Goal 和保留项的 ID/text，因此执行所需的条件和优先级须写入有效文本。模型在 `reason` 中简述决定性依据即可。[交接段](prompts/preconditioner.md#effective-plan-and-editor-handoff) · [输出契约](prompts/preconditioner.md#exact-output-contract)

附件包含 OfficeQA 域指导、Actor 基础协议及工具 schema、正式执行与无损输入视图、历史 Memory 的证据边界和引用规则。训练方法继续使用 v26.1 的其余三份完整提示词。[Diagnosis](../v26_1/prompts/diagnosis.md) · [Editor](../v26_1/prompts/editor.md) · [Replay](../v26_1/prompts/replay.md)

## 3. 每轮执行、选择与提交

| 阶段 | 输入、动作与交付 |
|---|---|
| Parent 与 Diagnosis | 本轮 Parent 独立执行整批题目。Diagnosis 读取 Parent 和全批正式记录，返回 no_change 或含 Goal 和 Original Updates 的 Plan。 |
| Preconditioner 与 Editor | Preconditioner 逐项审查。程序保留 Original 顺序、ID 和 basis，编译 Effective Plan。Editor 对每个保留的 ID 给出一个 patch；程序从同一 Parent 应用有效改动，形成联合 Candidate。 |
| Candidate 与 Replay | Candidate 在同批题目上独立执行。程序按 task ID 核对完整配对后，只把 EM 从 0 到 1 或从 1 到 0 的题交给 Replay。每个翻转只产生一个事件，可关联一个实际改动的 Update，也可为 null。F1 用于描述结果。 |
| Gate 与 Selected | 对每个有改动的 Update 统计获归因的改善题数 G 和退化题数 L。仅有改善时 Retain，仅有退化时 Reject，混合或零票时 Defer。空 patch 的决定为 null。程序在 Parent 上组合 Retain 的 patches，得到 Selected。 |
| Memory 与下一轮 | 将本轮 Effective Updates、Gate 决定和事件按既有合同提交，Selected 成为下一轮 Parent。若 Selected 与已执行的 Parent、Candidate 均不同，本轮 Selected 分数留空。 |

Diagnosis 给出 no_change 或 Preconditioner 全部 WITHDRAW 时，归档本轮并携带 Parent 进入下一批，无新增 Memory。Editor 全部返回空 patch 时，记录 Effective Updates 和空事件后继续。任一 Editor patch 为合法 null 表示无法忠实编辑，训练在该处停止。Candidate 无 EM 翻转时跳过 Replay 模型，按零票执行 Gate。恢复时使用本版本对应的已提交状态和原请求额度。各短路分支、联合候选的归因边界及原子提交约定见[完整合同](../v26_1/CONTRACTS.md)。

## 4. 执行条件与预算

| 项目 | v26.2 采用的值 |
|---|---|
| Actor 与四个方法模块 | deepseek-flash，thinking enabled，reasoning effort medium，temperature 1.0；direct HTTP |
| Actor 输出 | 默认 32,768 tokens。训练 UID0007 的 Parent 与 Candidate 均为 65,536。172 道 Test 统一 32,768。 |
| 题内执行 | 每题最多 24 个已接受模型轮次，含最终回答。Actor 只能使用题目许可的本地 glob、grep、read。初始材料每页最多 24,000 字符，合计最多 80,000 字符；read 最多 4,000 字符，grep 最多 20 条，glob 最多 50 条。 |
| 方法调用与输入保护 | Diagnosis、Preconditioner、Editor、Replay 每次输出均为 32,768 tokens 上限。沿用 4,000,000 字符和 6,000,000 UTF-8 字节的输入保护。11 题整批的最大输入需纳入后续离线容量检查。 |
| 并发、超时与重试 | Train 和 Test 各 4 workers。请求超时 300 秒，连接超时 10 秒。Actor 每模型轮、方法模块每次调用各最多 6 次请求（含首次），共用技术错误、length 和结构纠错额度，退避基数 2 秒。 |

标准答案仅供本地评分器使用。提供给方法模块的成绩为原生 normalized EM 和 token F1，可见证据以正式初始消息、已接受响应和工具返回为准。沿用 Actor 与方法传输各自的错误分类、暂停与恢复语义。24 轮正常用尽按已完成空答案计分；技术重试耗尽记为未完成。完整参数和底层行为见[v26.1 正式配置](../../../experiments/campaigns/v26_1_officeqa_train74_roles_20261105_202041/config.json)和[实验规格](../v26_1/EXPERIMENT.md)。

## 5. 评估、报告与可比性

七轮完成后导出最终 Selected Skill。独立 Test 使用这份逐字一致的 Skill 和固定的 172 题。主要指标为精确匹配题数及 EM，辅助指标为平均 F1。完整覆盖才报告全量指标；发生技术中止时报告完成题数、pending ID 和错误，完整集 EM/F1 留空。测试结果不进入 Memory 或 checkpoint 选择。

v26.1 使用 32,768 预算的原始 Test 完成了 171 题，UID0111 未完成。该题后来以 65,536 补测，合并结果为 **124/172，EM 72.09%，F1 72.38%**。报告 v26.2 时须标明这项预算差异。若需要看同预算的逐题变化，可以另列双方在相同预算下都完成的题目、分母以及错转对和对转错题数。该共同子集单列，完整集指标仍按上段口径报告。[v26.1 原始 Test 状态](../../../experiments/evaluations/v26_1_officeqa_train74_roles_20261105_202041/incomplete.json) · [补测合并报告](../../../experiments/evaluations/v26_1_officeqa_UID0111_65536_20261105_225536/combined_report.json)

训练报告按轮列出题数、Parent/Candidate 的 EM 和 F1、配对翻转、三种调整动作计数、实际 patch、Gate 决定与 Selected 来源。审阅新版提示词时，沿同一 Update ID 对照 Original、调整理由、有效文本及实际 patch，核对决定性的触发条件、例外或优先级是否传到 Editor。将未归因事件、未执行的 Selected 组合、请求数、工具调用、耗时与可得 token 用量单列。前四轮各有 11 题，跨版本解读原始计数时须同时给出样本分母。

## 6. 后续实现的验收依据

- **调度与完成条件**　核对 release、七批完整 ID、顺序和训练/Test 隔离；R07 完成后才可导出最终 Skill。重点覆盖 R05 的来源交界和 UID0007 的两侧训练预算。
- **提示词与接口**　核对实际发送的 Preconditioner 全文与本设计附件逐字一致。输入视图、引用权限、输出校验、三种动作的编译和 Editor 接收字段沿用 v26.1。实现时分别识别 v26.2 的调度及提示词版本，防止复用 v26.1 的请求或断点。
- **运行与报告**　用离线样例覆盖 11 题输入、正常提交、全 WITHDRAW、空 patch、合法 null、未归因翻转、恢复和未完整 Test，核对七轮终态与报告分母。真实训练及独立 Test 属于后续实验阶段。

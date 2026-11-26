# OfficeQA v26.3 完整训练与测试设计

定稿日期为 2026-11-17。v26.3 从初始 Skill 和空 Memory 开始，在 74 道优化题上走完七轮自进化，用最终 Selected Skill 评估独立的 172 道测试题。本版关注一个具体问题：当同一条 Update 包含多个行为要求时，Preconditioner 能否保留有证据支持的动作，并把适用条件写成 Actor 在决策时可以辨认的指令？训练和测试参数以 v26.2 **正式运行归档**为准。[正式训练配置](../../../experiments/campaigns/v26_2_officeqa_train74_20261117_013308/config.json) · [正式测试配置与有序题目清单](../../../experiments/evaluations/v26_2_officeqa_train74_20261117_013308/evaluation.json)

**附件：[定稿后的完整英文 Preconditioner system prompt](prompts/preconditioner.md)。** 全文以 v26.2 正式调用发送的 system message 为底稿，将 `Review each proposed change` 的第二段替换为商定的两段英文。附件包含 OfficeQA 域指导、Actor 协议、工具及预算、执行证据视图、历史 Memory、审查与交接规则、JSON 输出契约。定稿文件的 SHA-256 为 `cb59b127b989017d3c1c7fc399d3f171c67bb519dfb729bccf07c136d1e9e115`。[v26.2 正式调用原文](../../../experiments/campaigns/v26_2_officeqa_train74_20261117_013308/rounds/R02/preconditioner/attempts/001/prompt.md)

## Preconditioner 怎样判断适用范围

每次审查读取完整 Parent、冻结的 Original Plan、Plan 直接引用的本轮 Parent 执行，以及历史 Memory。Diagnosis 看全批，Preconditioner 能使用的本轮轨迹限于交接给它的引用。判断触发条件时，以 Actor 当时能看到的题面、已给材料和此前已经返回的工具结果为依据。执行后的评分可供审查者判断这次尝试的结果；Actor 作答时看不到该分数。

1. **逐个动作判断证据能支持什么。** 一条 Update 可能同时要求选取数据、换算单位、决定答案写法。对每个将被改变的动作，考察哪条可见线索足以要求这样做，哪条只支持将其作为偏好或选项。单题中的明确要求也可以支持一条可迁移的修正。
2. **把提案按字面用在条件重叠的情形。** 如果已有执行或 Memory 中能找到相邻案例，就检验 Actor 能否同时遵守两项要求，以及原先满足题意的行为是否还能成立。若相似改动曾退化或未带来目标收益，考虑当前线索、动作或语境具体有何不同。
3. **把判断交给 Editor。** 每个 Original ID 仍只产生一个调整。完整措辞已有充分依据时选 `KEEP`；部分动作仍有价值时，用 `REPLACE` 给出完整有效文本，修订或删去依据不足的要求；在该 Original 的问题范围内已无有效修正时选 `WITHDRAW`。Editor 只接收 Parent、Goal 和保留项的 ID/text，因此会影响执行的条件、例外和优先级都写进有效文本。`reason` 用于解释依据。

**训练案例。** v26.2 R02 的 `u1` 同时涉及答案标签、舍入精度和百分号。同批 `UID0079` 明确要求 *“Report your answer as a percent and round to the nearest hundredths place.”*，Parent 输出 `11.73%` 并获 EM=1。若提案一方面要求保留百分号，另一方面又笼统要求“凡指定小数位就输出裸数”，Actor 在这道题上会收到冲突指令。按本设计审查，可以保留简洁作答和舍入要求，并将后者的作用限定于数值精度。这个例子解释设计动机；实际训练中的决定取决于当轮 Parent、Plan 和执行证据。[R02 原提案](../../../experiments/campaigns/v26_2_officeqa_train74_20261117_013308/rounds/R02/diagnosis/attempts/001/parsed.json) · [R02 Parent 记录](../../../experiments/campaigns/v26_2_officeqa_train74_20261117_013308/rounds/R02/parent_runs/actor/results.jsonl)

## 数据与七轮调度

使用 OfficeQA release `763a8366abf2a3605c381d53586d844dc60fa756` 的 prepared 数据和同 release 的本地解析文本。原 Train 50 题与 Validation 24 题按正式顺序拼成一个优化池，各走一遍。初始 Skill 取 v26.2 的训练起点，初始 Memory 为 `{"rounds":[]}`。[数据清单](../../../data/officeqa/releases/763a8366abf2a3605c381d53586d844dc60fa756/prepared/manifest.json) · [初始 Skill](../../../experiments/campaigns/v26_2_officeqa_train74_20261117_013308/initial_skill.md) · [初始 Memory](../../../experiments/campaigns/v26_2_officeqa_train74_20261117_013308/initial_memory.json)

| 轮次 | 题数 | 有序题号（省略共同前缀 UID） |
|---|---:|---|
| R01 | 11 | 0002, 0007, 0014, 0017, 0018, 0019, 0026, 0028, 0030, 0031, 0033 |
| R02 | 11 | 0034, 0044, 0046, 0049, 0056, 0063, 0065, 0073, 0079, 0083, 0085 |
| R03 | 11 | 0087, 0092, 0098, 0101, 0110, 0115, 0122, 0123, 0133, 0141, 0144 |
| R04 | 11 | 0145, 0150, 0151, 0162, 0163, 0165, 0166, 0169, 0189, 0195, 0202 |
| R05 | 10 | 0212, 0222, 0228, 0229, 0238, 0241, 0001, 0027, 0039, 0041 |
| R06 | 10 | 0052, 0070, 0072, 0086, 0091, 0109, 0142, 0154, 0159, 0161 |
| R07 | 10 | 0170, 0190, 0213, 0217, 0220, 0233, 0234, 0235, 0239, 0240 |

## 每轮训练与最终选择

| 阶段 | 运行方式 |
|---|---|
| Parent 与 Diagnosis | Parent 独立作答整批。Diagnosis 读取 Parent 和全批正式执行，返回 `no_change` 或含 Goal、Original Updates 及依据的 Plan。 |
| Preconditioner 与 Editor | 程序按 Original 的顺序、ID 和 basis 编译有效 Plan。Editor 为每个保留项生成 patch，各 patch 作用于同一 Parent，合成联合 Candidate。 |
| Candidate 与 Replay | Candidate 在同批独立作答。按 task ID 配对后，仅 EM 的 0→1、1→0 进入 Replay。每个翻转至多归因到一项实际改动，也可标为未归因。 |
| Gate 与 Selected | 对每个非空 patch 统计本轮归因改善数 G、退化数 L。G>0 且 L=0 时 Retain，G=0 且 L>0 时 Reject，其余 Defer。Gate 在 Parent 上仅应用 Retain 的 patches。Selected 若等于本轮已执行文本，记录其执行来源；若为新的组合，当轮 Selected 分数留空，直接作为下一轮 Parent。 |
| Memory 与终态 | 按原合同提交有效 Updates、决定与事件。七轮结束时导出最终 Selected Skill。某些轮次沿用 Parent 时，最终文本可能来自更早的轮次。 |

Diagnosis 给出 `no_change` 或全部提案被 WITHDRAW 时，携带 Parent 进入下一轮，Memory 沿用前态。Editor 的合法空字符串表示该项没有文本改动，决定为空；全部为空时记录有效 Updates 与空事件后继续。合法 `null` patch 表示无法忠实编辑，训练停在该处。Candidate 无 EM 翻转时跳过 Replay 模型，Gate 按零票处理。断点恢复沿用已提交状态和已消耗的请求额度。[阶段与恢复合同](../v26_1/CONTRACTS.md) · [Gate 选择规则](../../../src/skill_evolution/v26_1/gate.py)

## 正式执行参数

| 项目 | v26.3 设计值 |
|---|---|
| 模型与路由 | Actor、Diagnosis、Preconditioner、Editor、Replay 均使用 `deepseek-v4.1-flash`，通过 direct HTTP 请求 `http://llm-proxy.intra.xiaojukeji.com/chat/completions`。thinking enabled，reasoning effort 为 `medium`，temperature 为 1.0。 |
| 生成预算 | Actor 每次请求默认 32,768 个输出 tokens。训练题 UID0007 的 Parent 和 Candidate 均为 65,536；Test 的全部 172 题均为 32,768。四个方法模块各次调用的输出上限均为 32,768。 |
| 题内执行与工具 | 每题最多 24 个已接受的模型轮次，包含最终回答。仅使用本地 glob、grep、read。初始页面每页最多 24,000 字符，合计最多 80,000；glob 最多返回 50 项，grep 最多 20 个匹配，read 最多 4,000 字符。 |
| 并发与输入保护 | 训练和测试各 4 workers。方法输入沿用 4,000,000 字符、6,000,000 UTF-8 字节的上限。 |
| 超时与重试 | 请求超时 300 秒，连接超时 10 秒。Actor 每个模型轮、方法模块每次调用各最多 6 次请求（含首次），退避基数 2 秒。技术错误、长度终止、结构或输出校验纠正按对应调用的原策略共用额度。 |

训练沿用正式运行的 Diagnosis、Editor、Replay 提示词和既有执行视图。Actor 只接收当题的执行上下文；参考答案仅供本地评分器使用。正常耗尽 24 轮按已完成的空答案计分；技术尝试耗尽按未完成记录。[正式配置](../../../experiments/campaigns/v26_2_officeqa_train74_20261117_013308/config.json) · [正式 Actor 运行记录](../../../experiments/campaigns/v26_2_officeqa_train74_20261117_013308/runtime.json)

## 独立测试与结果解读

训练结束后，对导出的最终 Selected Skill 做一次正式 Test，使用与 v26.2 相同的 172 个有序 Test ID。测试集与优化池互斥，测试结果仅用于报告。主要指标为归一化精确匹配（EM），同时报告答对数、完成数和平均 token F1。评分沿用 `officeqa_em_f1_no_reference_answers_v1`：本地评分器提取答案并归一化，与可用参考答案比较；百分号参与匹配。完整覆盖时，全量 EM 为答对数除以 172。[测试身份与配置](../../../experiments/evaluations/v26_2_officeqa_train74_20261117_013308/evaluation.json) · [正式测试及计分汇总流程](../../../src/skill_evolution/v26_1/evaluation.py)

若测试技术中止，列出已完成数、其中答对数、pending ID 和中止原因，全量 EM/F1 留空。历史比较另取同预算且双方都完成的 ID 交集，写明分母、双方答对数、错→对和对→错。v26.2 首测与复测均完成相同的 171 题，分别答对 120 和 118 题，均缺 UID0111；v26.1 公布的 124/172 包含为该题单独提高预算的补测。比较时标明使用的历史运行。一次完整训练与测试描述本版学出的 Skill 和实际得分，版本间分差仅作历史参照。[v26.2 首测状态](../../../experiments/evaluations/v26_2_officeqa_train74_20261117_013308/incomplete.json) · [v26.2 复测记录](../../../experiments/launches/v26_2_officeqa_final_test172_repeat_20261117_111113/stop_report.json) · [v26.1 补测口径](../../../experiments/evaluations/v26_1_officeqa_UID0111_65536_20261105_225536/combined_report.json)

训练结束后的复盘沿同一 Update ID 对照 Original、调整理由、有效文本、Editor patch 与 Gate 决定。优先说明在条件重叠时，哪些动作有直接依据、哪项要求被修订，以及 Actor 最终收到的 Skill 是否表达了这个区别。结合每轮 Parent/Candidate 成绩、EM 翻转、归因和 Selected 来源解读；调整次数本身不能说明规则适用范围判断得好坏。

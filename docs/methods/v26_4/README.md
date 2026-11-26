# OfficeQA v26.4 训练与测试设计

2026-11-17 · 设计稿

v26.4 希望学到这样的 Skill：几道题在同一个决策点失分时，一条修正能解释它们；后来遇到相似失败时，能判断已有规则是否足够，或明确指出应改写哪一句。四个模块的固定提示词均删除了预设的领域错误清单和单题预算特例。Diagnosis 负责从整批记录中提出可迁移的修正，Preconditioner 负责判断修正相对当前 Skill 增加了什么行为。Editor 根据有效提案修改 Parent，Replay 使用真实评分规则和配对轨迹解释 EM 翻转。

## 哪些经验值得写进 Skill

v26.1 R02 的三道训练题分别多写了方向说明、货币尺度和“percentage points”。回放显示，Parent 和 Candidate 用的是相同数值。一条关于“哪些文字属于题目所求答案”的修改获得了三项归因改善。v26.3 R03 则从一道双序列统计题保留了四条指令，其中包含船数与净登记吨位、一月至三月等原题细节。R04 审查输出尺度时，又把 Parent 尚未点名的“percentage points”视为增加具体措辞的理由。前者说明共同修正可以跨题成立，后两者分别暴露了提案展开过细和审查已有规则覆盖不足的问题。[v26.1 R02 回放](../../../experiments/campaigns/v26_1_officeqa_train74_roles_20261105_202041/rounds/R02/replay/attempts/001/parsed.json) · [v26.3 R03 Selected](../../../experiments/campaigns/v26_3_officeqa_train74_20261117_125845/rounds/R03/selected.md) · [v26.3 R04 审查记录](../../../experiments/campaigns/v26_3_officeqa_train74_20261117_125845/rounds/R04/preconditioner/attempts/001/parsed.json)

### Diagnosis 如何形成 Original Update

Diagnosis 读取完整 Parent 和本批全部 Parent 执行。先把一次可能的修正放回每条相关轨迹：当时已有哪条线索，Actor 实际取了什么数、采取了什么动作或输出了什么，照提案执行会具体改变哪一步？同一修正能解释多道题时，只提一次，把支撑轨迹放入该项的 `basis`。若某题需要另一个修正才能解释，应分开诊断。再用本批相近的成功作答检查边界，并引用能区分两种情形的记录。一次执行中的明确要求和可见偏差，也足以提出值得测试的修正。

写 `Update.text` 时，逐项考察删去某步骤、例子或例外后，未来 Actor 会作出什么不同选择。保留影响动作的条件、必要步骤及其依赖，原题的重建细节留在所引执行中。例如，R03 可以提出“计算双序列统计量前，按题目指定的期间配对，并核对每个序列所取的度量”。若还要 Actor 写出三元组或重新计算，应能说明它解决了哪项尚未处理的偏差。这个例子用于解释设计，真实提案取决于当轮证据。

### Preconditioner 如何审查 Parent 的覆盖

Preconditioner 读取完整 Parent、冻结的 Original Plan、Plan 引用的本轮执行和历史 Memory。在同一个已引用的决策点固定 Actor 可见的信息，先按 Parent 的相关段落判断应做什么，再加上提案判断动作、条件或优先级发生了什么变化。相近成功例有助于检验应保留的分支。一次失分可以提示旧规则难以识别、措辞含糊或两条指令竞争；仅凭得分无法区分这些解释。

| 证据支持的判断 | 交给 Editor 的决定 |
|---|---|
| 提案补足了会改变选择的条件，整条文字已准确表达行为与边界 | `KEEP`，使用 Original 原文。 |
| 有实质增量，但部分条款重复；或者现有措辞会让两种读法产生不同动作 | `REPLACE`，给出完整有效文本，指明应改写的旧规则和需要保留的分支。 |
| 删去词例和重复条款后，已没有有依据的行为变化 | `WITHDRAW`。 |

以 R04 的百分点为例：若 Actor 遵守现有尺度规则就能给出所求数值，添入新词只扩充了例子；若“以百分点表示两个率的差”会同时触发已有的百分号指令，则应定位冲突，把这一区别整合进既有规则。两种结论取决于 Parent 的具体文字和可见证据。每个 Original 仍得到一个调整，必要条件写进有效文本，Editor 才能落实到补丁。

## 提示词交付范围

| 模块 | 相对 v26.3 的定稿改动 |
|---|---|
| Diagnosis | 替换 `Examine current evidence` 的开头段，以及 `Construct complete, scoped Updates` 中以 “Use text as one string” 开头的段落。第一处处理跨题证据，第二处决定哪些细节进入长期指令。[完整英文稿](prompts/diagnosis.md) |
| Preconditioner | 替换 `Review each proposed change` 中以 “Read the affected Parent passages” 开头的段落。并读 Parent 与提案，判断覆盖和局部改写；前文继续审查 Actor 可见线索及条件重叠的情形。[完整英文稿](prompts/preconditioner.md) |
| Editor 与 Replay | 沿用原有输入输出契约。Editor 只接收 Parent 和有效提案。Replay 保留评分器归一化细节，输出格式示意使用占位文字。[Editor](prompts/editor.md) · [Replay](prompts/replay.md) |

四份英文提示词均移除了预设的错误类别、成功范例以及后文重复的领域提示。四个模块只需知道同题两侧使用相同的每请求输出预算。下表中的单题预算由运行配置执行。

## 完整训练与独立测试

| 项目 | v26.4 设计 |
|---|---|
| 起点与数据 | 从正式初始 Skill 和空 Memory 开新一轮完整训练。使用 OfficeQA release `763a8366abf2a3605c381d53586d844dc60fa756`，按原顺序拼接 Train 50 题和 Validation 24 题，七批依次为 11、11、11、11、10、10、10 题。[初始 Skill](../../../experiments/campaigns/v26_2_officeqa_train74_20261117_013308/initial_skill.md) · [逐批 ID 与执行参数](../../../experiments/configs/v26_3_officeqa_train74.json) |
| 调用与预算 | Actor 和四个方法模块沿用正式内网代理的 `deepseek-v4.1-flash`，thinking enabled、medium、temperature 1.0，训练和测试各 4 workers。默认输出上限 32,768 tokens；训练 UID0007 两侧均为 65,536；Test 统一 32,768。工具、24 轮题内上限、重试、超时、输入容量及断点恢复沿用正式配置。[v26.2 正式配置](../../../experiments/campaigns/v26_2_officeqa_train74_20261117_013308/config.json) |
| 每轮选择 | Parent 执行整批，Diagnosis 提案，Preconditioner 审查，Editor 在同一 Parent 上生成联合 Candidate。Candidate 在同批独立作答；Replay 处理配对 EM 翻转。Gate 对每项实际修改统计归因改善 G 和退化 L：仅有改善时 Retain，仅有退化时 Reject，其余 Defer。保留项组成 Selected，按原合同提交 Memory 并进入下一批。新组合的当轮分数留空。[阶段与提交合同](../v26_1/CONTRACTS.md) |
| 最终测试 | 七轮完成后，以最终 Selected Skill 做一次独立 Test，使用固定的 172 个 Test ID。报告完成数、答对数、归一化 EM 和平均 token F1。技术中止时列出已完成题中的答对数、pending ID 和原因，全量 EM/F1 留空。历史成绩按同预算、双方均完成的 ID 配对，注明分母与双向翻转。[测试清单与评分配置](../../../experiments/evaluations/v26_2_officeqa_train74_20261117_013308/evaluation.json) |

## 训练后如何判断设计是否奏效

1. **从多道题追到一个选择。** 沿 Original ID 检查所引执行，指出同一修正在每题会改变哪个可观察的动作，以及它在相近成功例上会保留什么。记录证据只支持单题假设的情形。
2. **从重复失分追到旧规则。** 对重现的问题并排读 Parent、Original、有效文本、Editor patch 和 Selected。说明具体增加了哪个选择、改清了哪处歧义，或哪段只有新词例的文字被撤回。区分审查理由中的判断与 Actor 最终收到的文字。
3. **结合结果读 Skill。** 按轮报告 Parent/Candidate 的 EM、改善与退化、归因和 Selected 来源。列出各轮 Selected 的条目数与字符数，结合实际差异解释增长来自新决策、必要分支还是重复举例。最终效果看独立测试；长度、引用题数和 WITHDRAW 次数只作描述，不作为 Gate 门槛。v26.1 的完整测试可作历史参照，v26.3 只用已提交轮次对照 Skill 的演化。[v26.1 历史结果](../../../experiments/evaluations/officeqa_checkpoints_20261111/逐轮测试结果.md) · [v26.3 第五轮 Skill](../../../experiments/campaigns/v26_3_officeqa_train74_20261117_125845/rounds/R05/selected.md)

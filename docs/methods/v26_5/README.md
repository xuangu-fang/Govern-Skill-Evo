# OfficeQA v26.5 训练与测试设计

2026-11-17 · 设计稿

v26.5 调整 Preconditioner 和 Editor 的固定英文提示词，检验两件事：训练证据能否支持保留下来的每个分句，以及 Gate 部分采纳补丁后，Actor 能否依据最终文字作出计划授权的选择。两项检查都在现有模块调用内完成。完整英文稿见 [Preconditioner](prompts/preconditioner.md) 和 [Editor](prompts/editor.md)。

## v26.4 暴露的问题

第 2 轮 UID0073 的回放记录了同一个月份的两个数值。后一份公告明确将数值从 58,486 修订为 58,172，Candidate 给出的答案与采用修订值一致。到第 3 轮，Selected Skill 同时要求优先取 “later supplied source” 和 “later published value”。若两份文件在输入中的顺序与发布日期顺序相反，这两句话会选中不同的值。交换输入顺序可以发现歧义；要判断哪一条行为值得保留，仍需回到原轨迹中实际可见的修订标记。第 3 轮另有一道题发生退化，Replay 未能将其归因于某个当轮补丁。这个案例供设计审查使用，四个模块的固定提示词都不列举这类题。[第 2 轮回放](../../../experiments/campaigns/v26_4_officeqa_train74_20261117_151911/rounds/R02/replay/attempts/001/parsed.json) · [第 3 轮 Selected](../../../experiments/campaigns/v26_4_officeqa_train74_20261117_151911/rounds/R03/selected.md) · [第 3 轮回放](../../../experiments/campaigns/v26_4_officeqa_train74_20261117_151911/rounds/R03/replay/attempts/001/parsed.json)

第 1 轮中，联合 Candidate 包含四项修改，Gate 只采纳了一项。Editor 写进某个补丁的默认行为，可能在没有其他补丁的情况下直接进入下一轮。如果这个行为必须依赖另一项修改提供例外，就应在编辑时发现并处理。[第 1 轮归因与选择](../../../experiments/campaigns/v26_4_officeqa_train74_20261117_151911/rounds/R01/round_summary.json)

## 两处英文替换

| 模块与位置 | 如何判断 | 检查后如何改写 |
|---|---|---|
| Preconditioner，`Review each proposed change`，替换 v26.4 第 164–168 行 | 固定 Actor 当时可见的信息，将 Original 与 Parent、基础协议并读。临时删去一个分句，指出哪一项动作、必要步骤或识别条件会消失。每删一次都重读剩余整条指令。 | 同一动作可合写一次，留下识别各分支所需的线索。有歧义时，用假设情形区分读法，用所引执行、相关 Memory 或题目明确要求决定范围。证据只支持排除某种做法时，让其余选择保持开放。[原文](../v26_4/prompts/preconditioner.md) · [完整替换稿](prompts/preconditioner.md) |
| Editor，`Input and implementation scope`，替换 v26.4 第 112–114 行 | 在原 Parent 上先单独读每个补丁，再读联合修改后的段落。对实际写出的默认情形、例外和重叠条件，检查遵守一条要求是否会违反另一条。把标题、嵌套范围和“可以／优先／必须”的区别一起读。 | 在同一 Update 的范围内就地改写旧规则，把必要例外与默认行为写在一起。删除复述后仍应能识别所有必要分支。只有 Effective Plan 给出了优先级，Editor 才据此消解冲突；计划允许的多种做法继续开放。[原文](../v26_4/prompts/editor.md) · [完整替换稿](prompts/editor.md) |

Preconditioner 对每个 Original 仍给出一个决定。原文已经完整表达有依据的修正时用 `KEEP`；有行为增量但需要合并、收窄或补明例外时用 `REPLACE`，在 `text` 中写出 Editor 可直接落实的完整修正；去除重复部分后已无增量时用 `WITHDRAW`。依据写进 `reason`。Editor 只接收 Parent、Goal 和有效的 ID/text，各项补丁都定位到同一个原始 Parent。旧文字已经满足要求时使用空补丁；在本 ID 的授权范围内确实无法解决实质冲突时，使用现有的 `patch=null` 并说明冲突。两个模块都沿用原有输出字段。

## 正式实验口径

以 v26.4 实际运行的配置为基准。v26.5 从正式初始 Skill 和空 Memory 开始独立训练。Diagnosis 继续从整批轨迹提出共同修正；Replay 继续用配对轨迹和真实归一化规则解释 EM 翻转。两者使用 v26.4 正式英文全文。Gate 按原归因结果选择补丁并提交 Memory。分句检查和补丁阅读均由模块在原调用中完成，实验不增加独立确认、Actor 回放或单变量预实验。[v26.4 正式配置](../../../experiments/campaigns/v26_4_officeqa_train74_20261117_151911/config.json) · [初始 Skill](../../../experiments/campaigns/v26_4_officeqa_train74_20261117_151911/initial_skill.md) · [Diagnosis](../v26_4/prompts/diagnosis.md) · [Replay](../v26_4/prompts/replay.md)

| 项目 | 设计 |
|---|---|
| 训练 | OfficeQA 同一 release、相同题序，Train 50 题加 Validation 24 题，七批依次为 11、11、11、11、10、10、10 题。 |
| 模型与预算 | 内网代理 `deepseek-v4.1-flash`，thinking enabled、medium、temperature 1.0，训练和测试各 4 workers。默认输出上限 32,768 tokens，训练 UID0007 的 Parent 和 Candidate 均为 65,536；所有测试题均为 32,768。单题预算仅由运行配置指定。 |
| 选择与测试 | Candidate 在同批独立作答，Gate 只采纳有归因改善且无归因退化的实际修改。部分采纳形成的新组合，其当轮分数留空。七轮结束后，使用最终 Selected Skill 在固定 172 题上做一次独立测试，报告完成数、答对数、归一化 EM 和平均 token F1。 |

## 如何判断设计是否奏效

1. **查看提案被怎样改写。** 沿同一 Update ID 对照 Original、引用的轨迹、调整理由和有效文本。删掉的分句原本改变了什么选择？合并后，原先依靠不同线索触发的分支是否仍能识别？遇到歧义时，检查最终优先级能否追溯到真实证据。假设情形只用于辨别读法。
2. **查看采纳后 Actor 实际读到什么。** 对涉及旧规则的补丁，分别读 Parent、单项补丁的结果、联合 Candidate 和实际 Selected，优先审查 Gate 只采纳部分修改的轮次。看默认行为和例外是否仍在同一作用范围，以及计划中的偏好是否被写成了义务。这项审查使用归档文本。
3. **把文字变化与成绩一起报告。** 每轮列出 Parent/Candidate 答对数、双向 EM 翻转、归因与选择结果，以及 Selected 的顶层条目数和字符数。v26.4 已提交的前三轮依次为 11 条／1,735 字符、19 条／3,192 字符、20 条／3,771 字符，可按同一批次比较增长发生在哪里。条目数、长度和撤回次数只作描述。v26.4 尚无独立测试成绩；最终测试比较应使用有实测记录的历史版本，按相同预算、两侧都完成的题目报告分母及双向翻转。一次完整运行可以观察组合设计的表现，对单个模块的独立效果仍需谨慎解释。

# v29.8 DocVQA 设计稿

v29.8 将 Diagnosis 的提案写法与 Preconditioner 的规则整合纳入同一版设计。Diagnosis 从当前批次找出有依据的行为修正和直接相关的反例；Preconditioner 结合 Memory、当前执行记录和完整 Parent，决定采纳、修订或撤回。基线为 v29.7 第二次独立训练实际使用的四份英文提示词。[训练归档](../../../experiments/campaigns/v29_7_repeat_docvqa160_20261105_131347/implementation.json) · [Diagnosis 差异](diagnosis.diff) · [Preconditioner 差异](preconditioner.diff) · [静态核对记录](design_validation.json)

## 目标与依据

一条可作写作范本的规则，应让读者在相近案例间找到决定性的线索，知道去哪里核实、选哪个对象，或者返回什么内容。只有一种合理处理方式时，一条直接指令即可。不同案例要求不同行为时，必要的分支值得占用篇幅。

v29.7 第二次训练最终采纳的七条规则沿用了交给 Editor 的更新措辞，其中三条来自 Diagnosis 原稿，四条经过 Preconditioner 改写。SkillAdam 对齐版的一次原位修订提供了另一种写法：原先“只答数字”会把文字拼写的数量也改成数字，改为“只答数量，保留印刷形式”后，一句规则即可兼容两种印刷方式。v29.8 借鉴这种针对具体判断修订旧句的写法。两次训练产物的差异只能提供设计动机，提示词效果有待独立验证。[v29.7 第六轮编辑输入](../../../experiments/campaigns/v29_7_repeat_docvqa160_20261105_131347/rounds/R06/editor/base_messages.json) · [SkillAdam 对应改稿](../../../experiments/baselines/docvqa_skilladam/docvqa160_evidence_v2_20261108_192230/execution/optimizer/iter_001/iteration_patch_01.json)

## Diagnosis 如何形成 Original

每项提案先说明当前证据支持改变哪个决定，以及 Actor 能看到什么线索。查找或比较题中，如果题目索取的对象影响答案，就在提案中区分，例如极值及其对应标签。对于一项限定，检查省去它是否可能丢失所问内容、误选证据或答错形式。相关成功样本和反例的执行引用进入 `basis`，诊断依据与不确定性进入 `reason`，Actor 真正用得上的条件和动作进入 `text`。[Diagnosis 英文提示词](prompts/diagnosis.md)

R06 的编号提案还复述了表格单位规则，单位样本无法说明编号分隔符该如何抄录。R03 的日期提案则需要保留年份、完整日期及相邻标题中的年份这几种情形，因为它们会改变答案。两例共同说明如何判断某项限定是否属于当前 Original。[R06 原稿](../../../experiments/campaigns/v29_7_repeat_docvqa160_20261105_131347/rounds/R06/editor/input.json) · [R03 原稿](../../../experiments/campaigns/v29_7_repeat_docvqa160_20261105_131347/rounds/R03/editor/input.json)

## Preconditioner 的三项判断和交付边界

| 判断 | Preconditioner 怎样使用输入 | 对本次更新的影响 |
|---|---|---|
| 历史经验是否适用 | 对照 Memory 中实际提出的动作、报告的收益或退化，以及使该动作适用的可见条件。历史只有采纳标签时，可据此确认发生过的决定，效果仍待证据支持。 | 条件部分重合时只迁移有依据的部分。缺少相关历史时，依据当前执行记录与现有 Skill 判断。 |
| 本轮错误是否支持改 Skill | 对照所给的当前执行记录、Original（待审提案）和 Parent（当前 Skill），指出一次有依据的行为变化。短答案可能只暴露了结果差异，无法揭示 Actor 实际看了哪一行。 | 现有指导充分覆盖且没有进一步改进依据时可撤回。现有指导笼统、证据又支持具体的定位或核实办法时，可修订。 |
| 新要求怎样与已有指导配合 | 找到直接指导同一决定的旧句，也检查其他位置的相关例外。确定哪些可见条件要求相同动作，哪些会改变取证、选择或输出。 | 在相关条款中修订条件或动作；出现独立决定时单列；规则冲突时明确边界或优先级；相同条件下的同义要求可合并。 |

`KEEP`、`REPLACE`、`WITHDRAW` 的对象是 Original。原提案已充分说明如何修订旧条款时，Preconditioner 可以 `KEEP`，随后由 Editor 修改 Parent。提案仍有价值、但行为或边界需要调整时才 `REPLACE`。实施所需的条件必须进入有效更新文本，因为 Editor 只接收 Parent 和有效计划；历史依据与不确定性写入 `reason`。[Editor 输入与职责](prompts/editor.md)

## 相对 v29.7 的改动

| 位置 | 改动及理由 |
|---|---|
| Diagnosis · Construct complete, scoped Updates | 合并原提案的三段写作要求，明确所问对象、可见线索和动作，并说明什么样的限定与反例应进入提案。 |
| Preconditioner · Frozen proposal and available input | 删除 “Use the relationship to Parent to select the treatment” 及其四项列表，将分散的整合选择集中到 C 段。相邻的执行记录解释仍负责防止把一次错误误判为规则缺口。 |
| C — Coordination | 整段替换。写作者先指出有依据的判断变化，再选择旧句修订、条件分支、合并或新增。限定词和通用示例的保留依据是它能帮助判断什么；改得更短或更漂亮本身不足以改变调整决定。 |

Memory 的证据解释、D（方向）、S（范围）、跨更新依赖与最终调整契约沿用基线。完整英文提示词可用于复核从提案到写回的职责边界。[Preconditioner](prompts/preconditioner.md) · [Editor](prompts/editor.md) · [Replay](prompts/replay.md)

## 一个设计例子

假设 Parent 要求“摘取足以回答问题的最短片段”。当前记录显示题目点明字段，Actor 仍多答了字段标签。Original 提议“遇到编号一律只返回值”。若相关 Memory 同时报告去掉多余标签的收益，以及误删正式标识符限定词的退化，则有理由将提案收窄为 `REPLACE`。有效文本可指示 Editor 修订已有的最短片段条款，并给出以下行为：

> 问题已点明字段时，只抄字段值。属于正式名称或标识符的限定词随值保留；问题要求完整印刷措辞时，抄录完整短语。

若 Parent 已覆盖这些分支，且证据不能支持新的核实办法，同一宽泛提案可撤回。若 Parent 仍缺少区分，但 Original 本身已经准确写出边界及旧条款的处理方式，则可保留 Original。以上是供评审的假设情形。

## 实现与验证

训练与独立评测入口已接入，116 项离线测试已通过。首次正式实验已于 2026-11-12 完成，最终 Skill 在 374 题中完全匹配 333 题。[正式评测摘要](../../../experiments/evaluations/v29_8_docvqa160_20261112_125216_test374/summary.json)[运行配置与离线验收](IMPLEMENTATION.md)

## 后续验证计划

1. **核对 Diagnosis 的提案。** 在同一批当前执行记录上检查 Original，分别用 R06 编号题和 R03 日期题核对是否排除了无关保护项、保留了有直接证据的分支。另用 R05 极值题核对提案是否区分所问对象，以及所选执行引用能否支持提案范围。
2. **检验 Preconditioner 的判断是否随证据改变。** 用同一 Original 构造成对输入，每对只变动一项。换入适用的混合历史，检查有效文本是否收窄并保留有依据的收益；换入表面同题型而机制无关的历史，检查有无错误迁移。分别改变当前记录对核实办法的支持程度、Parent 对行为的覆盖程度，检查决定和依据能否解释这些差异。允许合理的相同决定，逐对核对 `action`、`reason` 和交给 Editor 的有效文本。
3. **匿名评审成稿。** 向 v29.7 与完整 v29.8 提供相同的 Parent、当前批次与历史条件，各自生成提案并调整，配同一 Editor，把改动放回各自完整相关段落，打乱顺序。覆盖应合并的重复要求、必须保留的条件分支，以及无需修改的原提案。评审者指出决定性的可见线索和动作，用一个近似反例检查边界，再说明相对 Parent 多教会了什么。记录偏好、平局和原句依据，字符数仅供描述。
4. **端到端验证。** 正式实验时，沿用基线的初始 Skill、160 道优化题、11 批划分、模型及预算，比较固定 374 题的完全匹配和平均 ANLS，并对各自冻结的最终 Skill 复测。v29.7 第二次训练的同一 Skill 在两次测试中分别为 330/374 和 328/374。联合改动的成绩归属于完整 v29.8。结合成对案例、盲评及重复测试判断是否采用 v29.8，单次一两题波动不足以支持稳定收益。[基线实验记录](../../04_EXPERIMENT_LOG.md)

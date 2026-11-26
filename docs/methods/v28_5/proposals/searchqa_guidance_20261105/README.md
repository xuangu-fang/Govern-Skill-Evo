# v28.5 SearchQA 领域指导修订方案

日期：2026-11-05。状态：**完整 Prompt 提案，供审阅；未接入运行入口，未启动实验、自动化或模型调用。**

本方案以当前 `docs/methods/v28_5/prompts/` 四份文件为基线，参考仓库固定的 SkillAdam `b6c9640f7a9e0d5e3a500c25bc4e6369eeca78f1` 中 SearchQA 领域材料。它不是从最终训练 Skill 反推规则，也没有将已观察过的 Test 题目、答案或退步案例写入 Prompt。历史 Test 已参与前期讨论，后续使用同一 Test 时仍应披露开发背景。

## 1. 阅读入口

- [四份完整 Prompt 合集](FULL_PROMPTS.md)：连续阅读稿，每份可独立使用，不需要运行时拼接或外部 include。
- [完整 unified diff](diffs/all.diff)：相对于本次冻结的当前 v28.5 文本。
- [逐项修改与来源](CHANGES.md)：删除、替换、迁移、保留的具体说明。
- [静态核对结果](validation.json)：文本、接口段落、来源、diff 和原文件未变核对；不代表模型遵循或效果验收。

| 模块 | 完整稿 | 与 v28.5 的差异 |
|---|---|---|
| Diagnosis | [diagnosis.md](prompts/diagnosis.md) | [diagnosis.diff](diffs/diagnosis.diff) |
| Preconditioner | [preconditioner.md](prompts/preconditioner.md) | [preconditioner.diff](diffs/preconditioner.diff) |
| Editor | [editor.md](prompts/editor.md) | [editor.diff](diffs/editor.diff)，空文件表示逐字不变 |
| Replay | [replay.md](prompts/replay.md) | [replay.diff](diffs/replay.diff) |

## 2. 本次设计决策

**以更具体的 SearchQA 分析词汇和示例，替换 Diagnosis 中分散、重叠的领域说明；让 Preconditioner 使用同一套概念判断提案。** 不整体复制 SkillAdam 的优化 Prompt。

迁移的是五类失败问题、四类成功模式、Jeopardy 题型与关系消歧、题目与上下文支持的规范答案形式，以及仅删除真正冗余内容的最小充分答案单元，以及“已有规则未落实时，不自动新增同义规则”的示例。已有准确的评分说明和证据边界保留。

这是一份“领域指导对齐”的适配方案，不声称两边 Prompt 逐字相同或领域先验已经完全等价。为兼容 v28.5，分类只用于自然语言分析，不新增强制逐题分类、输出字段或持久化状态；示例不授权向最终 Skill 写入实例答案。

## 3. 保持的核心方法

```text
Parent batch → Diagnosis → Original Plan
  → Preconditioner(Parent + referenced current evidence + Memory)
  → Effective Plan → Editor → Candidate batch
  → Replay → existing Gate → append Memory + publish Selected
```

Parent 仍提供当前规则的覆盖、重复、冲突与相互作用；Memory 仍提供历史有效更新、采用决定与已报告的行为响应。Preconditioner 继续联合两者对 Original 做 Direction、Scope、Coordination 调整。

以下保留，不借领域迁移另改机制：

- Diagnosis 的 `decision/reason/plan`、Update 的 `id/text/basis` 及引用筛选。
- Preconditioner 的 Parent 全文与原有 Memory 输入；D/S/C；逐 Original 的 KEEP／REPLACE／WITHDRAW；Goal、ID、顺序、basis 冻结；必要行为要求必须写进 text。
- Editor 只读 Parent 与 Effective Plan，每 Update 一个 patch，原有空／null 及组合合同。
- Replay 只读当前 EM 翻转，逐题生成 Knowledge，原有 update_id／null 关联语义。
- Gate 的 G/L 条件、F1 不投票、Memory 字段与原子发布、Selected 子集执行来源标记。
- Actor 协议、模型、数据、预算、批次、并发、重试以及训练／测试隔离。

Preconditioner 从 `Historical Memory by round` 开始的现有正文全部逐字保留，只在其前面加入领域理解与角色衔接段落。这样能够直接核对原有 Parent＋Memory 机制没有被重写。

## 4. 四模块修改方案

### Diagnosis：主要修改

1. 将原 `Examine current evidence` 中分散的缺失指导、执行不明、实体／关系、答案边界及参考形式分析，替换为明确的失败／成功模式。
2. 引入 `rule_missing / rule_wrong / rule_ignored / answer_format / other` 和 `applied_rule / disambiguation / concise_normalization / other`。它们是分析词汇，不作为新的必填枚举，也不要求每题分类报告。
3. 给出具体 SearchQA 任务特点：this X、关系方向、整体与实例、历史与当前名称、冗余修饰、必要名称成分和单复数。
4. 加入 SkillAdam CPU／USB／ROM 过度展开示例的适配版，只说明如何识别已有规则的执行问题。示例不构成本轮证据，不进入 basis，不作为固定答案注入 Skill。
5. 合并后文重复的名称形式、短答案、泛化说明，保留可见条件、必要限定、禁止答案表和评分辅助修正。
6. 保留单案例可支持有范围的试验，不把“多例更有说服力”改成强制多例门槛。保留 Diagnosis 不做 Parent 全面整合、不读取历史 Memory 的职责边界。

### Preconditioner：共享领域概念，保留预条件判断

1. 内嵌与 Diagnosis 逐字一致的领域指导，避免同一名称形式问题在两个阶段被解释为不同类型。
2. 明确分类只是理解工具：相同分类不等于相同机制；与 Parent／Memory 的比较仍依赖具体行为及适用条件。
3. 仍可 KEEP、完整 REPLACE 或 WITHDRAW；不由类别直接决定动作，不为 `rule_wrong` 自动 Reject，不为 `concise_normalization` 自动 Retain。
4. 不复制 Momentum 的问题状态，不改 Memory 格式，也不要求为显示作用而引用历史。

### Editor：完整保留

Editor 不看任务证据，已有忠实实施、整合旧文字、避免重复和禁止答案表要求。无需让它重新分类失败或自行判断哪种名称更正确。因此完整稿逐字保留，diff 为空。

### Replay：最小术语与解释适配

将现有“观察实体／内容／词形变化”的段落改为更清楚地区分实体或关系变化与同一对象的答案形式变化，并保持所有同时变化的记录要求。明确格式改善不自动证明实体推理改善，也不凭标签建立归因。后续关联规则、null 语义和 Knowledge 输出不变；不要求分类字段或历史重新分类。

## 5. 来源、改写与不迁移内容

| 来源 | 本次采用 | 为保持合同所作处理 |
|---|---|---|
| SkillAdam `failure_types.md` | 五类失败词汇及其修正方向 | 不强制每题唯一分类；rule_ignored / rule_wrong 不声称观察到了隐藏推理；other 不自动等同噪声 |
| SkillAdam `success_types.md` | 应用已有规则、消歧、简洁规范、无可迁移模式 | applied_rule 改为行为与指导相符，不把成功视为内部因果证明；不增加 success 分类存储 |
| SkillAdam `iteration_example.md` | CPU／USB 过度展开、ROM 成功的对比；已有规则具体化而非重复新增 | 不迁移 JSON／patch 输出格式；不把示例事实当成当前证据；不采用向 Skill 写具体 gold/predicted 对的做法 |
| SkillAdam `metric_interpretation.md` | gold/predicted 与 EM/F1 的语义作核对来源 | 保留 v28.5 更精确的现有 scorer 描述；不复制其中整包阈值 Gate 的说明；不把 F1=0 写成必然语义全错 |
| v28.5 现有领域说明 | 最小充分答案、保留必要限定、区分参考匹配与语义、禁答案表 | 与新分类内容合并，删除重复表述；技术合同保留 |

不迁移：SkillAdam 通用的五条 Error Avoidance 后先合并要求、固定 Skill 章节、编辑预算、Momentum、双指标 Gate、Stage0 生成、额外模型阶段；也不把最终 Skill 中学到的具体规则移植为优化器先验。

归一化中特别保留：删除标点不等于用空格替换标点；F1=1 不推出 EM=1；名称形式偏好必须受任务与上下文约束。它们是现有 scorer／证据语义，不是额外设计的解题策略。

上游快照与 MIT 许可在 [reference/skilladam](reference/skilladam/)，逐文件哈希在 [source_map.json](source_map.json)。这是基于固定本地版本的适配，不声称已核对上游最新代码。

## 6. 公平性与验证边界

本次只统一部分可共享的领域指导，保留方法差异。它不能单独证明完整公平性：预算、轮数、数据使用及候选选择规则仍须在实际对照中分别说明。暂不把“规则条数约束”等方法政策混入这次改动，便于后续判断领域指导本身的作用。

本次仅做静态检查：来源快照、完整文本、diff 可重建、关键合同与 D/S/C 未变、公共领域段落一致、Markdown 引用可定位、原运行文件未修改。没有调用模型做验收，也没有训练或测试结果。

原运行入口直接读取 `docs/methods/v28_5/prompts/`，因此审阅稿独立放在本目录，避免把尚未审阅的文本自动绑定到既有方法身份。本目录中的版本号沿用 v28.5 仅用于表达兼容合同。后续若实施，应为修订 Prompt 建立明确的新身份与冻结记录；不覆盖历史实验快照、不在旧轮次中途换 Prompt。本次未执行这些后续步骤。

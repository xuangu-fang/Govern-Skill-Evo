# SearchQA v28.5：结合 Parent 与 Memory 的更新预条件调整

状态：实验 `v28_5_searchqa600_batch60_workers60_editor64k_20261104_232720` 于 2026-11-05 00:37:03 完成训练、1,400 题 Test 和比较。Test 正确 1,150 题（EM 82.1429%，F1 90.3023%），最终 Skill 14,151 字符；v28.3 为 1,187 题与 29,703 字符。逐题比较退步 57 题、改善 20 题。自动跟进已删除，无新实验计划。

本次为 10×60，训练并发 60、测试并发 15；Editor max_tokens=65,536，Actor=32,768。批次、并发、Editor 预算与 Prompt 同时变化，不能分离各项贡献。分析见 [analysis.json](/Users/didi/Desktop/Govern-Skill-Evo/experiments/analysis/v28_5_searchqa600_batch60_workers60_editor64k_20261104_232720_failure_analysis/analysis.json)。

## 1. 目标与基线

以 v28.3 为唯一方法与实验基线，重点强化 Preconditioner：根据当前 Parent 的覆盖、重复和规则交互，结合 Memory 中相关行为响应，对 Original Update 的方向、范围与协调方式进行调整，减少最终 Skill 的冗余、无依据分支和冲突。Replay 小幅修订事实忠实度与解释边界；Diagnosis 减轻整体协调职责；Editor 只做实施适配。

v28.3 本次归档 Test 为 1187/1400，v28.4 为 1169/1400；最终 Skill 分别为 29,703 与 28,108 字符。这些是既有单次运行的背景，不能证明某一 Prompt 改动的独立因果效果。v28.4 的训练案例仅用于说明审阅风险，不将其 Prompt 整体迁入 v28.5。

- [四份完整 Prompt](#3-交付文件)可独立阅读，不依赖对话中的片段。
- [冻结基线](baseline/README.md)保存 v28.3 原文、接口合同、配置、初始化与 Actor 文本。
- [来源与版本身份](source_map.json)列出逐文件来源与独立运行绑定。

## 2. 方法设计

```text
Parent batch → Diagnosis → Preconditioner → Editor → Candidate batch
  → Replay → Gate → append Memory + publish Selected Skill
```

| 模块 | 核心判断 | 本版变化 |
|---|---|---|
| Diagnosis | 当前任务与执行支持什么行为修正？ | 保留 Parent 作为执行背景；不再承担全面查重及旧规则整合；Original 仍须具体、有条件、有证据 |
| Preconditioner | 该修正进入当前 Skill 后，是否必要、范围是否合理、如何与旧规则共存？ | 联合分析 Parent 与相关 Memory；识别真正增量；明确相关旧指导的替代、限定、整合、删除及保护边界 |
| Editor | 怎样忠实、简洁地实施 Effective Update？ | 修改受影响旧文字，避免只追加；在本次调用内检查实施引入的重复与冲突，不另起行为策略 |
| Replay | 实际发生什么变化，哪些解释有证据？ | 完整描述影响解释的同时变化，核对归一化，将行为关联与得分解释分开 |
| Gate / Memory | 按既有证据选择并存储 | 字段、事件资格、选择规则和持久化方式不变 |

Parent 提供当前规则状态；Memory 提供已报告的历史行为响应。Preconditioner 不必每次引用历史，也不必为表现作用而修改 Original。两类信息能否改善更新质量，由后续真实训练轨迹、最终 Skill 和 Test 结果判断；整版结果不能单独证明各模块的独立贡献。

### Preconditioner 的判断顺序

1. 从当前证据理解 Original 的问题与拟改变的行为。
2. 阅读整个 Parent 中与该问题相关的指导，识别已有覆盖、真正增量和重叠条件；检查相关段落，不只检查拟插入位置。
3. 用相关 Memory 调整方向、条件、强度和保护边界；保留历史不确定性，不把缺失细节解释为条件不存在。
4. 确定相关旧规则应怎样改变或停止适用，以及哪些有效分支保留。已有指导不充分时可以修订；确有新行为需要时可以新增。
5. 审查所有存活 Updates 与 Parent 的预期共同含义，再选择 KEEP、完整 REPLACE 或 WITHDRAW。

这些是判断职责，不新增强制输出清单。reason 简要记录决定性依据，所有实施条件必须进入 text。

### 复杂度控制方式

- 无行为增量的重复提案可以撤回；当前失败不自动证明需要再写一条规则。
- 对同一决策的相关重复指导，允许在修正范围内整合，并明确旧文字去留。
- 优先保留有证据支持的条件差异，不用假设性保护清单维护一个过宽规则。
- 完整 Update 表示行为要求完整，不表示复制整个 Parent、历史说明或所有保护条款。
- 不以更少列表项替代更简单的决策；不把多条分支挤进一个长句，也不为变短丢掉必要条件。

没有字数上限、规则数量要求、章节模板、操作比例或 KEEP/REPLACE 配额。没有独立压缩器、额外 Reviewer 或全篇重写阶段。

## 3. 交付文件

| 文件 | 用途 |
|---|---|
| [Diagnosis](prompts/diagnosis.md) | 完整当前批次诊断 Prompt |
| [Preconditioner](prompts/preconditioner.md) | 完整 Parent / Memory 预条件 Prompt |
| [Editor](prompts/editor.md) | 完整实施 Prompt，保留原 patch 合同 |
| [Replay](prompts/replay.md) | 完整事件 Knowledge Prompt |
| [接口与职责合同](CONTRACTS.md) | 输出、证据边界、职责转移及沿用项 |
| [逐模块修改与审阅](PROMPT_REVIEW.md) | 每项改动的动机、定位、静态结论与未验证项 |
| [固定实验边界](EXPERIMENT_PLAN.md) | 参数、直接训练与测试流程及现有选择机制限制 |
| [静态检查记录](design_validation.json) | 文件一致性、完整性和接口保留检查；不是模型验收 |
| [实现与必要检查](IMPLEMENTATION.md) | 独立运行入口、冻结配置与离线检查结果 |

逐模块差异：[Diagnosis](diffs/diagnosis_from_v28_3.diff)、[Preconditioner](diffs/preconditioner_from_v28_3.diff)、[Editor](diffs/editor_from_v28_3.diff)、[Replay](diffs/replay_from_v28_3.diff)。差异相对于本目录冻结副本，可用普通 unified-diff 工具审阅。

## 4. 保持不变与已知边界

Memory 继续只保存 Effective Updates、Gate 决定和 EM 翻转 Knowledge；不增加未翻转响应、Editor 实际补丁或历史原始执行。现有 null 关联的存储与解释合同保持原样，不另设新的利用机制。Replay 仍读取已有 patch/diff 输入来判断实际修改，但不将它们作为新字段写入 Memory。

Gate 不变：G>0 且 L=0 才 Retain，混合结果或 0/0 为 Defer。纯文字精简没有 EM 改善时仍可能不能保留；本版主要控制有行为依据的更新如何进入 Skill，不承诺每轮缩短。完整 Candidate 被执行，不代表后续筛选出的 patch 子集已执行；现有 selected_execution_source 仍如实标记来源。Prompt 自查不提供任意子集语义一致性保证。

除批次调整为 10×60、训练并发 60 和 Editor 预算 65,536 外，数据、Actor、评分器、初始化、预算、重试、完整证据视图、逐 Update patch、Memory 原子发布和轻量恢复均继承 v28.3。详见 [固定实验边界](EXPERIMENT_PLAN.md)。独立配置和 CLI 仅隔离版本身份与运行目录；没有新增自动化。

## 5. 本次完成范围与下一阶段

已完成基线冻结、四份完整 Prompt、差异和逐项审阅材料，并建立独立实现。按用户调整，不设置独立验收场景和训练前固定输入模型对照；必要的软件检查见 [实现说明](IMPLEMENTATION.md)。这些检查不能证明模型会遵循 Prompt、最终 Skill 更短、Test 提升或预条件机制有独立收益。

旧实验及修订后从第一轮启动的新实验目前均已暂停。当前 Editor 已撤回压缩修改，实验冻结快照保留当时原文；本次未恢复任何实验。旧启动记录见 [实验目录](../../../experiments/automations/v28_5_searchqa600_batch30_20261104_220800/README.md)。既有 Test 结果已参与版本讨论，后续报告保留该开发背景，不将同一 Test 描述为完全未接触的盲测。

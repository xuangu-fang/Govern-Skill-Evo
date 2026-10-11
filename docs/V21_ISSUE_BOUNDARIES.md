# v21 补强第 2 步：issue 写回与复查边界

日期：2026-10-09。已完成写回约束、来源区分和 Fusion/Review 提示调整；未调用真实模型、重新 rollout 或发布活动 head。

后续 [当前认识与历史消费](V21_CURRENT_UNDERSTANDING.md)已实现同次更新维护 issue 综合认识，以及按需历史读取；原问题和归属边界继续保留。下文数字与版本是本步当时记录，当前预检默认路径为 `artifacts/v21_current_understanding/report.json`。

## 1. 本步约定

**一个 issue 围绕原来的问题积累认识。联合提案、共同 edit 或共同轨迹允许共享证据，不自动合并问题范围，也不让每个 issue 继承整段联合修改建议。**

现有 issue 的 `problem` 原文作为固定范围锚点。普通 Memory 更新不能改写它；修订对方法、条件及双维结果的认识，写入相关 attempt 的 `assessment`。发现不同问题时，使用已有 NEW issue 机制及原始事件引用；没有实际修改时可以没有 attempt。不得因此重复建立已有问题。

这是当前写回接口的明确限制：即使提供了合法新事件，改写旧 `problem` 也会被拒绝。它防止在原 ID 下替换复查对象，不等于程序能够识别所有文字中的语义偏移，也不自动清洗过去已经混杂的记录。

## 2. 实际改动

### 来源区分

`open_memory_evidence` 增加一个输入派生映射 `issue_source_refs`：每个已加载 issue 对应自己的来源、各 attempt 来源及沿 `source_refs` 正向可达的历史记录。它不沿共享 edit 的反向关系认领其他记录。

原有完整读取范围保持：通过共享 edit 展开的其他记录、配对双侧、上下文和已知反证仍在 `source_records`/`events` 中。映射只区分已有来源链与其他上下文，不裁剪证据，也不表示来源内的每句话都属于该 issue 或已经正确归因。旧的显式来源本身可能混杂，模型仍须回到原问题判断。

映射不新增 Memory 持久化字段、效果状态或第二套目录。短引用表示能够完整还原它；Memory 调用前重建输入，篡改 issue 与来源的绑定会被拒绝。

### Memory 写回

- 既有 `problem` 必须原文保留；已有 attempt 身份仍只能在所属 issue 下更新。
- 新评价自动保留本 issue 显式历史来源中的反证，不再把通过共享 edit 连带加载的其他 issue 的全部反证自动复制成自己的评价附件。
- 共享反证仍在完整档案和后续 Review 中。若新观察确实与本问题相关，模型可引用其原始事件并说明关联；不禁止跨问题的真实影响。
- Prompt 要求 `approach`/`assessment` 只写与本 issue 相关的行为、修改后观察及限制。联合提案/Review gap 的整段文字不能机械复制到每个关联 issue。
- edit 的账本覆盖要求仍对本次更新整体生效，不要求每个关联 issue 都记一份。确有依据时，同一实际 edit 可对应多个 issue 下分别表述的尝试，不宣称隔离效果。

### Fusion 与 Review

Fusion 以原 `problem` 为范围锚点。仅共同任务、规则或 edit 不足以合并独立问题；相关问题可以联合提出，但须在原有 `reason` 中交代关联。

Review 接收原 `memory_issues`、来源映射及完整相关证据。Prompt 明确：Fusion 的 `issue_statement` 是修改方向，不能替换历史问题；旧 attempt 中混入的其他议题或共享轨迹里的偶发问题，不能成为扩大 gap 的理由。无法为选中问题证明修改必要性时，使用既有 `NO_EDIT`。联合 Review 仍是一个调用，不增加逐 issue/逐 edit 的重复审阅表。

当前规则中已有相关文字只能证明文字覆盖，不能证明运行成功或程序合规；Review 需在原有 `reason` 中区分这些结论。

## 3. 验证与限制

新增 [10 项边界测试](../tests/skill_evolution/test_issue_boundaries_v21.py)，包括：

- 两个问题共享 edit 时，来源链保持各自边界，共享原文仍可读取；
- 只更新 A 时，B 不变，B 的反证不被自动写成 A 的新评价附件；
- 同一实际修改可形成两个分别表述的 issue assessment；
- 即使有合法事件，也拒绝替换既有 problem 或跨 issue 搬用 attempt 身份；
- 原范围、来源映射、共享反证能够进入下一轮 Review；联合问题仍只装配一个 Review；
- 旧显式混杂链接保留为历史，不按未经验证的语义判断删除。

这些测试使用构造的模型响应验证通路。程序能强制固定锚点、身份归属、来源绑定及自动继承规则；能否正确划分相关行为、避免自然语言跑题，仍需真实模型实验，不能由测试通过宣称解决。

新增专项连同既有 v21 更新/消费/证据/表示及 v20/Replay 回归，共 **189 项通过**。

历史真实产物只读预检仍保留 **9 组配对、675 个事件**，包括上一步补入的 T005/T022/T036。Memory 代理输入从 99,405 变为 **99,761**，新增 356 tokens；Fusion 为 13,127，六个历史 Review 为 20,872–61,287。所有原始事件、配对与已知反证计数和上一步一致，并通过无损还原校验。

报告：[report.json](../artifacts/v21_issue_boundaries/report.json)。它由下列命令生成；此前退化覆盖与输入优化报告保留，当前目录的 `check.json` 是本步中间报告。

```bash
/Users/didi/miniforge3/envs/tau2/bin/python scripts/preflight_v21_input_budget.py
```

数字是 cl100k_base 代理估计，不是网关实测。各阶段使用历史构造请求，不构成一轮真实 v21 campaign。

## 4. 版本与后续

当前局部证据视图为 `memory_evidence_view_v21.2`，Memory 输入为 `memory_update_input_v21.3`；Memory/Fusion/Review Prompt 分别为 `memory_update_v21.4`、`issue-fusion-v21.2`、`evidence-review-v21.3`。Memory 持久化和三个模型响应格式不变。v20 默认路径不变。

已保存规范证据和 Memory 仍可读取。新输入/Prompt 不能冒充旧请求恢复；旧调用或生成审计若与重建输入不符会被拒绝，应使用新独立运行目录。

下一步是整理每个 issue 的简明当前认识及历史消费，避免跨轮重复增长。本步没有实现历史语义清洗、摘要压缩、完整 campaign 或真实 Pilot。

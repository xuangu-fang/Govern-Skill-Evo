# v21 补强第 3 步：简明当前认识与历史消费

日期：2026-10-09。已实现同次更新维护 issue 当前认识，以及 Fusion/Review 的分层读取；未调用真实模型、新建真实 rollout 或发布活动 head。

## 1. 当前认识怎样维护

现有一次 Memory 更新响应中，每个被更新 issue 增加一个 `current_understanding` 段落；继续保留 `problem` 固定锚点和各 attempt 的 `assessment`。不增加摘要 Agent、第二次更新调用、状态分类或逐 edit 分析。

Prompt 要求综合本问题的相关尝试，写清：哪些方向有证据支持及其适用条件，任务成功/程序合规各自暴露过什么问题和反例，最新尝试相对以前改变了什么，以及仍然未知的部分。压缩时不能只保留修改建议主体。Skill 中出现了文字与运行验证了效果必须区分。

当前认识限制为不超过 **2,000 个字符**，这是输入规模约束，不是完整性证明。超过上限或只有空白时拒绝更新，不自动截断，也不启动隐式修复调用。issue 级 `source_refs` 必须引用已加载原始事件，并包含本轮 Replay；程序还合并本次被修改 attempts 的事件引用，并保留该 issue 已有的显式反证。

一段新认识覆盖“当前读取位置”，不覆盖历史事实。未返回的 issue 保持原样。新发现的问题可以没有实际 attempt，但仍须有认识和原始事件依据。

## 2. 保存方式

完整 Memory 仍使用 `issue_memory_v20.1` 的原有字段。程序把当前认识保存成已有档案结构中的 `UNDERSTANDING_V21/...` 来源记录，再将引用追加到该 issue 的 `source_refs`；最新的一条是当前认识。

该记录复用 `statement`、`evidence_refs`、`counterevidence_refs`、`source_refs`，直接关联观察及配对，不虚构一个“汇总 attempt”，也不把所有旧摘要逐层链接到新摘要。完整 attempts、旧认识、原始事件和旧来源仍留在 Memory/档案中，原有完整回查接口继续可用。

因此只新增一个模型响应文本字段，没有增加持久化效果状态或另建记忆系统。消费方通过可信 evidence bundle 读取当前认识；单独的旧 Memory JSON 不能冒充已经包含新综合认识。

## 3. 下一轮怎样读取

| 场景 | 默认读取 | 需要历史细节时 |
|---|---|---|
| Fusion：已有当前认识 | 原 problem、一段当前认识、attempt ID/approach 目录及原有绑定信息 | 在已有 `memory_attempt_refs` 中选择需要比较、重试或核查的尝试 |
| Review：已有当前认识 | 当前认识及其原始依据、当前选中 Findings、已知反证、此前关联的双维标签退化配对 | 加载 Fusion 显式选择的完整 attempts、原始依据及联合依赖 |
| 旧 issue 尚无当前认识 | 保持原完整历史路径 | 不用截断或拼接旧 assessment 冒充新认识 |
| 修改后的 Memory 更新 | 保留相关问题完整历史及修改后证据，同时显示上一段当前认识 | 在同一次调用中综合修订，避免仅凭摘要再摘要 |

Review 使用现有 `memory_attempt_refs`，不增加检索 Agent 或额外 Review。选中有利尝试不能隐藏已知反例：程序在本地对原完整来源范围做索引，强制保留所有已知 `counterevidence_refs` 对应完整轨迹；过去关联配对中任一维度 `true → false` 的双方原文也保留，即使旧更新把它们记为普通证据而非反证。

当前认识引用、已知反例或显式选择可能仍然打开较大的相关范围；这是保留限制和反证的代价，不通过固定最近 N 条或机械截断降低成本。未加载的历史仍在本地，不等于已经无效。如果现有材料不足以证明修改必要性，Review 应使用既有 `NO_EDIT` 并说明限制，不能猜测未读历史。

前一步的 issue 边界继续生效：共享证据不自动拥有同一个归因结论；普通更新不能改写原 problem。当前认识可以改写解释和条件，但不能换成另一个问题。

## 4. 验证与成本边界

专项构造测试覆盖：同次调用写入认识、完整历史保存、更新后只读取最新综合认识、长度/引用约束、Fusion 目录化、选择性历史回查、已知反例和历史退化不可隐藏、旧数据回退、错误来源拒绝，以及未涉及 issue 保持不变。构造了 12 条重复旧 attempt 的场景，验证完整 attempts 仍在本地，而 Fusion 不再重复携带其 assessment，代理输入确实减少。

这是工程通路测试，摘要文本由测试提供；不能证明真实模型已经保留全部语义限制，也不是研究效果或实际成本实验。

新增专项 **16 项**，连同既有 v21 更新/消费/来源/表示及 v20/Replay 回归，共 **205 项通过**。

真实历史材料预检报告：[report.json](../artifacts/v21_current_understanding/report.json)。使用此前 v20 历史产物，**6 个历史 issue 都尚无新格式当前认识**，因此全部回退完整历史。默认更新仍覆盖 **9 组配对、675 个事件**，包括此前补齐的三个退化案例。当前代理输入为 Memory **100,026**、Fusion **13,240**、六个历史 Review **20,986–61,401**；不能把这些尚未生成真实摘要的数据宣称为摘要压缩效果。Memory 更新保留完整相关历史，其长期增长也未被本步宣称解决。

所有数字是 cl100k_base 代理估计。旧预检报告保留；当前复现命令为：

```bash
/Users/didi/miniforge3/envs/tau2/bin/python scripts/preflight_v21_input_budget.py
```

## 5. 实现与兼容

- [current_understanding_v21.py](../src/skill_evolution/current_understanding_v21.py)：当前认识读取、按需历史展开及反证/退化保留。
- [memory_update_v21.py](../src/skill_evolution/memory_update_v21.py) 与 Prompt：同次生成并保存综合认识，保留完整历史和显式恢复。
- [memory_consumption_v21.py](../src/skill_evolution/memory_consumption_v21.py)：Fusion 目录视图、原有选择字段和 Review 适配。
- [test_current_understanding_v21.py](../tests/skill_evolution/test_current_understanding_v21.py)：专项测试。

Memory 输入为 `memory_update_input_v21.4`；该步 Prompt 为 `memory_update_v21.5`，后续[退化证据跨轮保留](V21_REGRESSION_RETENTION.md)更新至 v21.6，2,000 字符限制不变。Fusion 输入明确为 `issue_fusion_input_v21.1`，Fusion/Review Prompt 当前为 v21.6/v21.9；[语义定向修订](V21_SEMANTIC_FOLLOWUP.md)引入任务/操作原文对照，[缺陷依据与修改授权调整](V21_DEFECT_GROUNDING.md)进一步要求原文可推翻上游缺陷假设，新增程序义务须有依据。此前的[提案依据要求](V21_FUSION_PROPOSAL_BASIS.md)和[证据比较要求](V21_EVIDENCE_COMPARISON.md)继续保留。为复用原 Fusion 身份/归属校验，v20 输入类型只增加默认恒等的校验视图入口；v21 适配目录字段，内部占位文本不进入模型。v20 默认行为、Memory 格式、Fusion/Review 响应和 Gate 不变。

旧可信证据档案可读。旧模型响应缺少新认识字段，或旧请求与新输入/Prompt 不一致时，不能假装恢复为新版运行；需新的独立调用目录。没有自动历史回填或额外模型调用。

按后续讨论，完整 v21 运行与恢复、Skill/Memory 原子发布之前，先做小规模真实模型验证：检查摘要中的条件/反例是否保留，以及 Fusion/Review 是否据此形成合理修改决策。本次已完成[案例与判定依据准备](V21_SMALL_VALIDATION_CASES.md)，保留 2,000 字符硬限制，尚未调用真实模型。只在验证暴露具体不足时做最小强化，之后再接通完整调度并进行两轮 Pilot。

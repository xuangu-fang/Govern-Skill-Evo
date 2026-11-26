# v25.3 Diagnosis、Preconditioner 与 Replay 职责调整

2026-11-06 实施，修订标识 `v25_3_roles_replay_v1`。本次修改三个模块的提示词，保留已有 SpreadsheetBench 领域指导及运行接口，完成离线验证。

## 模块职责

| 模块 | 本次落实的职责 |
|---|---|
| [Diagnosis](../../../src/skill_evolution/v25_3/prompts/diagnosis.md) | 从完整当前批次的任务要求、提交程序、执行反馈和评分中找出行为问题，对照成功、失败与反例提出完整修正。Parent 用于理解执行背景和可见冲突；完整覆盖检查、旧条款处理与提案协调交给 Preconditioner。每项 Update 保留触发条件、动作、强度、必要依赖、保护分支及当前依据。 |
| [Preconditioner](../../../src/skill_evolution/v25_3/prompts/preconditioner.md) | 对照完整 Parent、Original Plan、直接引用的当前 runs 和相关 Memory，判断已有覆盖、需要改变的行为及历史响应。空 Memory 时仍能根据 Parent 与当前证据完成预条件。维持每个原 ID 的 KEEP / REPLACE / WITHDRAW。 |
| [Replay](../../../src/skill_evolution/v25_3/prompts/replay.md) | 分开陈述可见行为变化、与实际 Update/patch 的联系、对 hard 翻转的解释。保留同时发生的变化与不确定性，生成脱离本轮原始轨迹仍可理解的 Knowledge，供后续 Preconditioner 使用。 |

Preconditioner 的 D/S/C 继续是一次综合判断：

- **D（Direction）**：当前问题需要鼓励、改变或停止什么行为；相关历史支持、反例是否要求调整方向。
- **S（Scope）**：什么可见条件下采用、约束多强、哪些例外和有效分支需要保留。新增顺序、优先级、阈值和停止条件也属于行为变化。
- **C（Coordination）**：定位 Parent 中相关旧条款，明确替换、限定、合并或移除的要求，并协调存活提案的重叠条件与优先级。每项修正应在其他 Update 被暂缓时仍完整。

必要的旧条款处理、条件和优先级进入完整有效文本。reason 保存判断依据与不确定性；Editor 仍只读 Parent、goal 和有效 id/text。无需新增字段，也不拆并原 ID。

## 从 DocVQA 合理迁移到 SpreadsheetBench

原版 v29.6 的职责分配与事件解释方法可以跨 benchmark 采用，领域对象、可见证据与评分含义需要替换。

| 原参考中的领域背景 | v25.3 的具体适配 |
|---|---|
| 图像区域、文档阅读与答案文本 | 使用任务要求、工作簿预览、实际提交程序、执行记录和所提供的评分。关注源表与目标表、表头和数据边界、控制输入、写入区域及公式/值要求。 |
| 文本回答变化与 ANLS 等文本评分解释 | 使用原有 whole-task hard 翻转作为事件入口，per-cell 等指标辅助解释。比较语义以供应给模块的执行上下文为准。 |
| 单轮回答 | 追溯真正生成已评分提交的程序，并区分实际反馈引发的恢复、最终可打开工作簿和目标单元格正确性。 |
| 文本答案中可直接看到的差异 | 区分代码意图、可确认的执行行为与评分结果。代码分支出现不证明它执行，错格坐标不揭示标准答案，也不能单独证明公式缓存是失败原因。 |

Replay 的小优化包含两点：多个可见变化可以属于同一项明确关联的修正，不因变化数量自动置 null；同时，行为与 patch 对应也不等于独立解释了整题得分。当多个 Update 或其联合效果无法区分时，仍保留 null，并陈述观察到的变化和解释限度。每个事件保存实际 0→1 或 1→0 方向，回归采用同样标准。

## 来源与迁移范围

使用原版 v29.6 的修订前快照：

- [Diagnosis 来源](../v29_6/revisions/docvqa_domain_v1/before/prompts/diagnosis.md)
- [Preconditioner 来源](../v29_6/revisions/parent_memory_delta_v1/before/src/skill_evolution/v29_6/prompts/preconditioner.md)
- [Replay 来源](../v29_6/revisions/docvqa_domain_v1/before/prompts/replay.md)

Preconditioner 来源路径中的 `parent_memory_delta_v1/before` 是该后续优化实施前的快照。本次没有迁入 `parent_memory_delta_v1` 的专项方法。

第二项优化引入的共享 SpreadsheetBench 领域块逐字保留。Editor、执行上下文、四模块结构化输出、Gate、Memory 结构和运行代码保持不变；Actor、初始 Skill、评分器继续继承 v25.2。

## 离线验证

19 项 unittest 全部通过，覆盖提示词实际路由、共享领域块与输出合同，以及合成工作簿闭环中的逐项选择、完整 REPLACE、下一轮 Parent/Memory、恢复、特殊分支和请求预算。原测试中冻结旧方法正文的断言已改为保留输出合同，以允许此次授权的职责调整。

验证使用临时合成工作簿、预设模型响应和本地执行替身，期间阻断 HTTP 和子进程调用。另核验 8 个受保护文件、3 个原版来源的哈希，检查提示词渲染和领域块保留情况。离线结果验证接口与执行链兼容性，不能据此判断真实模型行为或效果提升。未启动正式实验。

- [修改前提示词](revisions/roles_replay_v1/before/)
- [来源、修改前及受保护文件哈希](revisions/roles_replay_v1/manifest.json)
- [离线结果及提示词长度](revisions/roles_replay_v1/offline_validation.json)

复跑用例：`python -m unittest tests.skill_evolution.v25_3.test_campaign tests.skill_evolution.v25_3.test_domain_guidance`。

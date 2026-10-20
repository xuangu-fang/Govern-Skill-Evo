# 方法 V23 文档

[文档总索引](../../README.md) · [V22 方法](../v22/README.md)

更新日期：2026-10-18。

V23 围绕基于诊断预条件化的持续 Skill 自进化，按分组、Diagnosis、Preconditioner、Editor、Replay／Memory 等模块逐项设计。Preconditioner 替代 Fusion 的名称，继续结合历史更新响应调整原始更新。

| 文档 | 内容与状态 |
|---|---|
| [模块串联与轮次调度设计](EVOLUTION_ORCHESTRATION_DESIGN.md) | 已确认的 Orchestrator 设计：同批 Train Gate／Replay、轮次冻结、有限重试、resume、Skill／Memory 统一发布；机制设计；正式实现见下一项 |
| [统一轮次调度正式实现](EVOLUTION_DESIGN.md) | run／resume／status、独立尝试与统一发布；513 项测试及 19 个子测试通过，真实验证结果见报告 |
| [自动分组设计方案](AUTOMATIC_GROUPING_DESIGN.md) | 已确认的模块职责、共享事实输入、before／after 步骤表示、Actor 可见候选过滤、五字段输出、正式英文提示词及验收要求 |
| [V23 上游模块使用说明](../../../src/skill_evolution/v23/README.md) | 运行、转换、持久化复用及模块间数据读取接口 |
| [Grouping 实现验证](../../../experiments/methods/v23/v23_grouping_001/reports/REPORT.md) | 102 项测试及 19 个子测试通过；24 条历史执行转换；一次真实调用及保留的语义问题 |
| [Diagnosis 设计方案](DIAGNOSIS_DESIGN.md) | 已确认共享事实加分组输入，以及 decision／reason／plan、goal／updates／checks 输出；正式实现完成 |
| [Diagnosis 实现验证](../../../experiments/methods/v23/v23_diagnosis_001/reports/REPORT.md) | 175 项测试及 19 个子测试通过；一次真实调用生成 4 项 Update、3 项 Check，记录语义限制与复用结果 |
| [Grouping 与 Diagnosis Prompt 统一验证](../../../experiments/methods/v23/v23_prompt_alignment_001/reports/REPORT.md) | 当前正式 Prompt、单一执行背景、update_ids 迁移及旧档案只读交接；210 项测试与 19 个子测试，两次真实调用及语义限制 |
| [Preconditioner 设计方案](PRECONDITIONER_DESIGN.md) | 已确认直接证据与历史响应输入、四字段增量调整、来源依据继承、Checks 命名兼容及 Effective Plan 构造；正式 Prompt、确定性编译和无历史验证已完成 |
| [Preconditioner 实现与无历史验证](../../../experiments/methods/v23/v23_preconditioner_001/reports/REPORT.md) | 284 项测试与 19 个子测试；单次真实 Keep、确定性编译及零调用复用，记录能力判断限制 |
| [Editor 设计方案](EDITOR_DESIGN.md) | 两字段输入输出、正式 Prompt 与严格补丁应用已实现；离线通过，单次真实补丁无效，未生成 Candidate |
| [Editor 实现与验证](../../../experiments/methods/v23/v23_editor_001/reports/REPORT.md) | 384 项测试与 19 个子测试；一次真实调用后严格应用失败，原文保留，无重试或 Candidate Replay |
| [Editor 单次技术恢复](../../../experiments/methods/v23/v23_editor_recovery_001/reports/REPORT.md) | 相同请求额外一次授权调用，生成可严格应用的 23 行 Candidate；原失败不变，语义限制保留 |
| [Replay 与 Memory 设计方案](REPLAY_MEMORY_DESIGN.md) | 七字段输入、三字段 Memory 提案、Archive／Active 与来源装配已实现；首次真实学习及非空 Memory 对照完成，跨轮修订／行为收益待验证 |
| [Replay／Memory 真实验证](../../../experiments/methods/v23/v23_replay_memory_001/reports/REPORT.md) | 434 项测试与 19 个子测试；4 条 Candidate／133 步，一次 Replay 形成 3 条 Memory，原始事实与语义限制保留 |
| [真实 Memory 的 Preconditioner 对照](../../../experiments/methods/v23/v23_preconditioner_with_memory_001/reports/REPORT.md) | 同新 Prompt 两侧各一次；空侧 Keep，真实侧调整 u1／u3；仅同批更新构造验证，不证明行为收益 |

当前已实现 Grouping、Diagnosis、Preconditioner、Editor、Replay 与 Memory 维护。Editor 首次真实 Patch 格式失败保持原样；授权技术恢复得到的 23 行 Candidate 也未改写，本次完成了四条配对 Candidate 执行和一次响应学习。Replay 形成 3 条真实 Memory，非空 Memory 的匹配对照已观察到引用历史响应的 u1／u3 调整。原始及新 Plan 仍有有限历史条件、基础协议重复和归因表述问题；本次仅验证同批更新构造，未验证新调整的行为收益。Gate 已完成独立工程验证：既有四组 Train 配对 Parent 3／Candidate 2，RETAIN，未提交 Skill 状态。统一调度已完整运行两轮，Gate 均 RETAIN、Memory 跨轮新增至 M1/M2/M3，第二轮实际消费历史来源。真实旧认识修订、独立泛化与长期效果仍待验证；已有输出的事实混淆和过度概括见调度报告。

- [Gate 设计与接口](GATE_DESIGN.md)
- [Gate 实现与真实档案验证](../../../experiments/methods/v23/v23_gate_001/reports/REPORT.md)：479 项测试与 19 个子测试；零模型调用、零新增环境任务。

2026-10-19：[ALFWorld 正式实验准备](../../../experiments/methods/v23/v23_alfworld_formal_001/README.md)完成。39 Train＋18 Selection／134 Test 逐条核对；用户确认采用官方顺序，六轮 10/10/10/10/10/7；S0/S1 配置冻结，531 项测试与 19 个子测试通过。**仅准备，尚未启动。**

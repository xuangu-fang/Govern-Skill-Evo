# V23.4 实验材料与运行归档

[方法实验总索引](../README.md) · [方法文档](../../../docs/methods/v23_4/README.md) · [运行说明](../../../docs/methods/v23_4/BENCHMARK_RUNBOOK.md)

本版本按实验 ID 保留研究定义、Prompt、配置、报告、候选或提案、逐任务指标、必要失败证据及 Memory 审计。完整输入、轨迹、HTTP 数据、Memory 预览和运行日志位于 [artifacts/methods/v23_4](../../../artifacts/methods/v23_4/)，各实验 README 说明具体边界。正式配置继续保留在实验目录。

## 实验入口

| 目录 | 材料范围 |
|---|---|
| [benchmark_readiness_audit_001](benchmark_readiness_audit_001/README.md) | Benchmark 就绪审计与历史失败证据 |
| [semantic_generation_001](semantic_generation_001/README.md) | 首轮语义生成与重试记录 |
| [semantic_generation_002](semantic_generation_002/README.md) | R06 修订后重启 |
| [semantic_generation_003](semantic_generation_003/README.md) | R06 双向一致性生成 |
| [semantic_generation_004](semantic_generation_004/README.md) | R06 新 Diagnosis 与 Plan |
| [semantic_generation_005](semantic_generation_005/README.md) | R06 Editor 忠实性验证 |
| [semantic_generation_006](semantic_generation_006/README.md) | R05 生成与审查 |
| [semantic_generation_007](semantic_generation_007/README.md) | 后续语义生成与审查 |
| [r05_actor_comparison_001](r05_actor_comparison_001/README.md) | R05 Parent / Candidate 执行比较 |
| [r06_actor_comparison_001](r06_actor_comparison_001/README.md) | R06 Parent / Candidate 执行比较 |
| [r05_replay_memory_001](r05_replay_memory_001/README.md) | R05 早期 Replay 与 Memory |
| [r06_replay_memory_001](r06_replay_memory_001/README.md) | R06 早期 Replay 与 Memory |
| [replay_input_view_001](replay_input_view_001/README.md) | Replay 输入视图与离线材料 |
| [replay_input_view_live_001](replay_input_view_live_001/README.md) | 新输入视图真实 Replay |
| [replay_prompt_candidate_001](replay_prompt_candidate_001/README.md) | 候选 Prompt 验证 |
| [multi_knowledge_contract_001](multi_knowledge_contract_001/README.md) | 多 Knowledge 契约与依赖审计 |
| [multi_knowledge_p2_001](multi_knowledge_p2_001/README.md) | 多 Knowledge 存储 |
| [multi_knowledge_p3_001](multi_knowledge_p3_001/README.md) | 多 Knowledge 链路适配 |
| [multi_knowledge_p4_001](multi_knowledge_p4_001/README.md) | 学习 Prompt 与准备输入 |
| [multi_knowledge_p6_001](multi_knowledge_p6_001/README.md) | P6 真实提案与 Memory 审计 |
| [p6_root_cause_analysis_001](p6_root_cause_analysis_001/README.md) | P6 根因分析 |
| [replay_layered_diagnostic_001](replay_layered_diagnostic_001/README.md) | 分层诊断、全部回答与评分 |
| [conditional_learning_001](conditional_learning_001/README.md) | V2 条件学习候选验证 |
| [replay_v3_validation_001](replay_v3_validation_001/README.md) | V3 验证及第二轮离线修订 |
| [v23_design_comparison_001](v23_design_comparison_001/README.md) | 与 V23 的设计比较 |
| [campaign_integration_001](campaign_integration_001/README.md) | 总运行器集成与离线验收 |
| [output_budget_recovery_001](output_budget_recovery_001/README.md) | 请求级输出预算修订 |
| [v23_4_alfworld_formal_001](v23_4_alfworld_formal_001/README.md) | 正式配置、固定任务与结果入口 |

## 正式运行与历史时间点

2026-10-27 读取已有归档：正式 S1 的 [状态](../../../artifacts/methods/v23_4/v23_4_alfworld_formal_001/S1/state.json) 为 `next_round=7`；[Test 完成记录](../../../artifacts/methods/v23_4/v23_4_alfworld_formal_001/evaluation/result.json) 为 `complete`，其 [汇总](../../../artifacts/methods/v23_4/v23_4_alfworld_formal_001/evaluation/S1/summary.json) 记录 134 条任务、106 成功、28 失败。配置、最终 Parent/Memory 和结果入口见 [正式实验 README](v23_4_alfworld_formal_001/README.md)。本次整理没有重新执行实验或评估。

历史报告保留当时结论：2026-10-22 集成验收时尚未启动真实 Benchmark，2026-10-23 预算恢复报告记录当时的恢复进程。后续优化与 Test 结果属于更晚的阶段，不能用来改写历史检查点，也不能将全程描述为未修订的固定输出预算。

## 读取与保留规则

[archive_io.py](archive_io.py) 支持按原实验路径读取迁移数据、合并枚举及定位归档输出。已经迁移的实验入口和跨实验读取按此布局适配；历史 JSON 中的来源路径保持原文。只读源码或 JSON 记录并不等于重新运行历史冻结校验。

既有冻结记录、保护记录、研究 inventory 和源码快照继续作为研究证据保留。它们不是此次迁移生成的清单。正式配置中的完整环境材料也保留原结构，避免改变 Benchmark、Test 与 V23.5 的读取契约。

归档目录被 Git 忽略，仅克隆 Git 不包含完整原始数据。必要失败原文、合法提案和审计结果留在实验目录；引用合法、结构通过与语义采用是不同结论。各报告中的测试数量均注明其历史阶段，文件整理不会自动更新这些数字。

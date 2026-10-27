# V23.3 实验导航

本目录保存方法设计、实验定义、报告、精选输出、必要失败证据和人工夹具。完整运行数据位于 [artifacts/methods/v23_3](../../../artifacts/methods/v23_3/)，按相同实验 ID 和相对层级保存。

## 设计与阶段决策

- [P0_P1_DECISION](P0_P1_DECISION.md)
- [V23_3_BASELINE](V23_3_BASELINE.md)
- [V23_3_EDITOR_PATCH_AUDIT](V23_3_EDITOR_PATCH_AUDIT.md)
- [V23_3_METHOD_DESIGN](V23_3_METHOD_DESIGN.md)
- [V23_3_PATCH_INTEGRATION](V23_3_PATCH_INTEGRATION.md)
- [V23_3_PRECONDITIONING_ALGORITHM](V23_3_PRECONDITIONING_ALGORITHM.md)
- [V23_3_VALIDATION_PLAN](V23_3_VALIDATION_PLAN.md)

## 实验入口

| 实验 | 材料 |
|---|---|
| [p1r_multiline_001](p1r_multiline_001/README.md) | P1-R 多行表示与 Patch 兼容验证 |
| [p2_offline_001](p2_offline_001/README.md) | P2 离线实现与 Mock 链验证 |
| [p3a_first_live_comparison_001](p3a_first_live_comparison_001/README.md) | 首次真实 A/B 比较 |
| [p3a_transport_retry_001](p3a_transport_retry_001/README.md) | 首次 A/B 比较的传输恢复 |
| [memory_compaction_offline_001](memory_compaction_offline_001/README.md) | Memory 视图离线压缩与证据保留验证 |
| [memory_compaction_live_validation_001](memory_compaction_live_validation_001/README.md) | Memory 视图真实理解验证 |
| [memory_compaction_v2_validation_001](memory_compaction_v2_validation_001/README.md) | Memory v2 视图验证 |
| [memory_compaction_v3_validation_001](memory_compaction_v3_validation_001/README.md) | Memory v3 视图验证 |
| [memory_v3_integration_001](memory_v3_integration_001/README.md) | Memory v3 接入与 A/B 比较 |
| [p3c1_r05_replay_001](p3c1_r05_replay_001/README.md) | R05 候选与 Replay 实验 |
| [p3c1_r05_replay_restart_001](p3c1_r05_replay_restart_001/README.md) | R05 Replay 第一次重启 |
| [p3c1_r05_replay_restart_002](p3c1_r05_replay_restart_002/README.md) | R05 Replay 第二次重启及并行恢复 |
| [p3c1_r05_replay_restart_003](p3c1_r05_replay_restart_003/README.md) | R05 Replay 第三次重启 |
| [p3c1_r05_replay_restart_004](p3c1_r05_replay_restart_004/README.md) | R05 Replay 第四次重启 |
| [p3c1_completion_001](p3c1_completion_001/README.md) | R05 Replay 完成审计与行为比较 |
| [p3_audit_001](p3_audit_001/P3_AUDIT_REPORT.md) | 独立审计报告，无原始数据需要迁移 |
| [p3a2_train_batch1_001](p3a2_train_batch1_001/README.md) | Batch-1 训练、并行及追加生成的完整研究记录 |

## 读取边界

- [archive_io.py](archive_io.py) 负责剩余实验的文件解析、合并枚举和临时加载视图；Batch-1 的入口见其 README。
- 报告中的实际文件链接已更新；历史 JSON 和冻结记录保留当时的原路径。解析旧路径时，若文件已迁移，读取工具会定位到对应的本地归档。
- 新文件或子目录跟随最近已有父目录的位置：父目录仅在归档中时，新增内容写入归档；父目录在实验目录中时，新文件仍留在实验目录。已有保留文件优先，已有归档文件不会因新增路径处理而移回原处。
- 只克隆 Git 不会取得完整运行数据。复现历史归档读取或 Memory 视图测试，需要对应 artifacts；不会自动调用模型来补齐。
- Python 缓存仍由仓库全局规则忽略，不作为实验原始数据归档。

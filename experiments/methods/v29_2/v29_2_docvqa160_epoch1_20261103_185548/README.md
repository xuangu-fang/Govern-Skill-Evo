# v29.2 完成的迁移续跑 DocVQA 历史实验

原实验 ID 为 `v29_2_docvqa160_epoch1_20261103_185548`。在 160 道优化题上完成 11 轮。实际受测的最终 Skill 来自 R11，DeepSeek Flash 终测 Hard 为 **326/374**，平均 ANLS 为 **93.68%**。 [终测摘要](results/v29_2_docvqa_test374_20261103/summary.json)

[冻结训练配置](config/config.json) · [训练结项](results/training_summary.json) · [最终受测 Skill](results/final_skill.md) · [原始训练目录](../../../campaigns/migrations/v29_2_references_v4_20261103/v29_2_docvqa160_epoch1_20261103_185548) · [冻结实现与提示词](config/implementation.json)

## 运行经过

1. 原运行提交 R06 后停在 R07 Replay。 [原运行](reports/original_stopped/README.md)
2. 第一次迁移续跑停止。删除回执涵盖旧迁移和两次失败的准备目录。 [首次迁移](reports/superseded_migration/README.md) · [准备失败 1](../v29_2_references_v4_20261103_prepare01_failed/README.md) · [准备失败 2](../v29_2_references_v4_20261103_prepare02_failed/README.md)
3. 缩短 Prompt 后的续跑保留前 6 轮的 Skill，完成 11 轮。独立 Test 绑定到这次完成的迁移目录。 [续跑完成状态](reports/v29_2_prompt_compact_restart_20261103/status.json) · [Test 完成状态](../../../benchmarks/docvqa/launches/v29_2_docvqa_test374_20261103/status.json)

## 逐轮保留的 Skill

| 完成轮次 | 保留文本来自 | 训练证据 |
| --- | --- | --- |
| R01 | [R01](results/rounds/R01/selected.md) | [轮次回执](results/rounds/R01/result.json) |
| R02 | [R02](results/rounds/R02/selected.md) | [轮次回执](results/rounds/R02/result.json) |
| R03 | [R02](results/rounds/R03/selected.md) | [轮次回执](results/rounds/R03/result.json) |
| R04 | [R02](results/rounds/R04/selected.md) | [轮次回执](results/rounds/R04/result.json) |
| R05 | [R05](results/rounds/R05/selected.md) | [轮次回执](results/rounds/R05/result.json) |
| R06 | [R06](results/rounds/R06/selected.md) | [轮次回执](results/rounds/R06/result.json) |
| R07 | [R07](results/rounds/R07/selected.md) | [轮次回执](results/rounds/R07/result.json) |
| R08 | [R07](results/rounds/R08/selected.md) | [轮次回执](results/rounds/R08/result.json) |
| R09 | [R09](results/rounds/R09/selected.md) | [轮次回执](results/rounds/R09/result.json) |
| R10 | [R10](results/rounds/R10/selected.md) | [轮次回执](results/rounds/R10/result.json) |
| R11 | [R11](results/rounds/R11/selected.md) | [轮次回执](results/rounds/R11/result.json) |

[DocVQA 实验索引及离线复算命令](../../DOCVQA.md)

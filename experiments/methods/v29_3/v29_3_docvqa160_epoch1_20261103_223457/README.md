# v29.3 初版 DocVQA 历史实验

原实验 ID 为 `v29_3_docvqa160_epoch1_20261103_223457`。在 160 道优化题上完成 11 轮。最终 Skill 来自 R11，用于 DeepSeek Flash 的 Test374。

[冻结训练配置](config/config.json) · [冻结实现与提示词](config/implementation.json) · [训练结项](results/training_summary.json) · [初始 Skill](config/initial_skill.md) · [最终受测 Skill](results/final_skill.md) · [原始训练目录](../../../campaigns/v29_3_docvqa160_epoch1_20261103_223457) · [调度状态](reports/v29_3_docvqa160_epoch1_20261103_223457/status.json)

## 独立评测

| 受测轮次 | 类型 | Hard | 平均 ANLS |
| --- | --- | ---: | ---: |
| R11 | 终测首测 | [322/374](results/v29_3_docvqa_test374_20261103/summary.json) | 94.03% |

首次启动失败，轻量运行恢复后用同一份受测 Skill 完成 374 题，归入同一个评测 ID。 [首次失败](../../../benchmarks/docvqa/launches/v29_3_docvqa_test374_20261103/status.json) · [恢复完成](../../../benchmarks/docvqa/launches/v29_3_docvqa_test374_20261103_light_runtime/status.json)

## 逐轮保留的 Skill

| 轮次 | 保留文本来自 | 轮次结果 |
| --- | --- | --- |
| R01 | [R01](results/rounds/R01/selected.md) | [轮次回执](results/rounds/R01/result.json) |
| R02 | [R02](results/rounds/R02/selected.md) | [轮次回执](results/rounds/R02/result.json) |
| R03 | [R03](results/rounds/R03/selected.md) | [轮次回执](results/rounds/R03/result.json) |
| R04 | [R04](results/rounds/R04/selected.md) | [轮次回执](results/rounds/R04/result.json) |
| R05 | [R05](results/rounds/R05/selected.md) | [轮次回执](results/rounds/R05/result.json) |
| R06 | [R06](results/rounds/R06/selected.md) | [轮次回执](results/rounds/R06/result.json) |
| R07 | [R07](results/rounds/R07/selected.md) | [轮次回执](results/rounds/R07/result.json) |
| R08 | [R07](results/rounds/R08/selected.md) | [轮次回执](results/rounds/R08/result.json) |
| R09 | [R07](results/rounds/R09/selected.md) | [轮次回执](results/rounds/R09/result.json) |
| R10 | [R10](results/rounds/R10/selected.md) | [轮次回执](results/rounds/R10/result.json) |
| R11 | [R11](results/rounds/R11/selected.md) | [轮次回执](results/rounds/R11/result.json) |

[DocVQA 实验索引和复算命令](../../DOCVQA.md)

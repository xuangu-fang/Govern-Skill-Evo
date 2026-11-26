# v29.9 DocVQA 历史实验

原实验 ID 为 `v29_9_docvqa160_20261117_121927`。使用 160 道优化题并完成 11 轮训练。最终 Skill 由 `deepseek-flash` 评测，Hard 为 **326/374（87.17%）**，平均 ANLS 为 **93.89%**。 [终测摘要](results/v29_9_docvqa160_20261117_121927_test374/summary.json)

[冻结训练配置](config/config.json) · [冻结实现与提示词](config/implementation.json) · [训练结项](results/training_summary.json) · [初始 Skill](config/initial_skill.md) · [最终受测 Skill](results/final_skill.md) · [原始训练目录](../../../campaigns/v29_9_docvqa160_20261117_121927) · [原配对对照报告](../../../benchmarks/docvqa/comparisons/v29_9_docvqa160_20261117_121927_vs_v29_8_test374/reports/v29_9_docvqa160_20261117_121927_vs_v29_8_test374.json)

## 逐轮保留的 Skill

| 轮次 | 保留文本 | 该轮结果 | Test374 |
| --- | --- | --- | --- |
| R01 | [R01](results/rounds/R01/selected.md) | [轮次回执](results/rounds/R01/result.json) | — |
| R02 | [R02](results/rounds/R02/selected.md) | [轮次回执](results/rounds/R02/result.json) | — |
| R03 | [R02](results/rounds/R03/selected.md) | [轮次回执](results/rounds/R03/result.json) | — |
| R04 | [R02](results/rounds/R04/selected.md) | [轮次回执](results/rounds/R04/result.json) | — |
| R05 | [R02](results/rounds/R05/selected.md) | [轮次回执](results/rounds/R05/result.json) | — |
| R06 | [R02](results/rounds/R06/selected.md) | [轮次回执](results/rounds/R06/result.json) | — |
| R07 | [R07](results/rounds/R07/selected.md) | [轮次回执](results/rounds/R07/result.json) | — |
| R08 | [R08](results/rounds/R08/selected.md) | [轮次回执](results/rounds/R08/result.json) | — |
| R09 | [R09](results/rounds/R09/selected.md) | [轮次回执](results/rounds/R09/result.json) | — |
| R10 | [R09](results/rounds/R10/selected.md) | [轮次回执](results/rounds/R10/result.json) | — |
| R11 | [R11](results/rounds/R11/selected.md) | [轮次回执](results/rounds/R11/result.json) | [326/374](results/v29_9_docvqa160_20261117_121927_test374/summary.json) |

逐轮 Skill 和状态来自训练现场，独立评测对应 R11 最终 Skill。

[DocVQA 实验索引及离线复算命令](../../DOCVQA.md)

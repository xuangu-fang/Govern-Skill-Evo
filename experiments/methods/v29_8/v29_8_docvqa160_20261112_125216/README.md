# v29.8 DocVQA 历史实验

原实验 ID 为 `v29_8_docvqa160_20261112_125216`。使用 160 道优化题并完成 11 轮训练。最终 Skill 由 `deepseek-flash` 评测，Hard 为 **333/374（89.04%）**，平均 ANLS 为 **95.37%**。 [终测摘要](results/v29_8_docvqa160_20261112_125216_test374/summary.json)

[冻结训练配置](config/config.json) · [冻结实现与提示词](config/implementation.json) · [训练结项](results/training_summary.json) · [初始 Skill](config/initial_skill.md) · [最终受测 Skill](results/final_skill.md) · [原始训练目录](../../../campaigns/v29_8_docvqa160_20261112_125216) · [原逐轮测试记录](../../../evaluations/docvqa_v29_8_checkpoints_20261112/%E9%80%90%E8%BD%AE%E6%B5%8B%E8%AF%95%E7%BB%93%E6%9E%9C.md)

## 逐轮保留的 Skill

| 轮次 | 保留文本 | 该轮结果 | Test374 |
| --- | --- | --- | --- |
| R01 | [初始 Skill](results/rounds/R01/selected.md) | [轮次回执](results/rounds/R01/result.json) | 沿用 [R00 的 303/374](../../../benchmarks/docvqa/controls/R00/results/summary.json) |
| R02 | [R02](results/rounds/R02/selected.md) | [轮次回执](results/rounds/R02/result.json) | [317/374](results/v29_8_R02/summary.json) |
| R03 | [R02](results/rounds/R03/selected.md) | [轮次回执](results/rounds/R03/result.json) | 沿用 [R02 的 317/374](results/v29_8_R02/summary.json) |
| R04 | [R04](results/rounds/R04/selected.md) | [轮次回执](results/rounds/R04/result.json) | [320/374](results/v29_8_R04/summary.json) |
| R05 | [R04](results/rounds/R05/selected.md) | [轮次回执](results/rounds/R05/result.json) | 沿用 [R04 的 320/374](results/v29_8_R04/summary.json) |
| R06 | [R06](results/rounds/R06/selected.md) | [轮次回执](results/rounds/R06/result.json) | [321/374](results/v29_8_R06/summary.json) |
| R07 | [R07](results/rounds/R07/selected.md) | [轮次回执](results/rounds/R07/result.json) | [325/374](results/v29_8_R07/summary.json) |
| R08 | [R07](results/rounds/R08/selected.md) | [轮次回执](results/rounds/R08/result.json) | 沿用 [R07 的 325/374](results/v29_8_R07/summary.json) |
| R09 | [R09](results/rounds/R09/selected.md) | [轮次回执](results/rounds/R09/result.json) | [328/374](results/v29_8_R09/summary.json) |
| R10 | [R10](results/rounds/R10/selected.md) | [轮次回执](results/rounds/R10/result.json) | [330/374](results/v29_8_R10/summary.json) |
| R11 | [R11](results/rounds/R11/selected.md) | [轮次回执](results/rounds/R11/result.json) | [333/374](results/v29_8_docvqa160_20261112_125216_test374/summary.json) |

6 次独立检查点评测和 R11 终测各有原始回执。沿用成绩的轮次已核对保留文本字节一致。

[DocVQA 实验索引及离线复算命令](../../DOCVQA.md)

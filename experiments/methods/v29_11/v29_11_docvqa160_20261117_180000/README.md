# v29.11 DocVQA 主对照运行

正式训练使用 160 道优化题，共 11 轮。R03 和 R06 的 Parent 全对，未启动 Candidate。最终使用 R11 保留的 Skill。

[冻结训练配置](config/config.json) · [训练或选优回执](results/training_summary.json) · [初始 Skill](config/initial_skill.md) · [最终受测 Skill](results/final_skill.md) · [完整运行原目录](../../../campaigns/v29_11_docvqa160_20261117_180000)

## 终测及独立复测

| 次序 | DeepSeek Flash Hard | 平均 ANLS |
| ---: | ---: | ---: |
| 1 | [330/374](results/v29_11_docvqa160_20261117_180000_test374/summary.json) | 95.39% |
| 2 | [324/374](results/R11_retest/summary.json) | 93.88% |
| 3 | [333/374](results/R11_third/summary.json) | 95.89% |
| 4 | [327/374](results/R11_fourth/summary.json) | 94.44% |
| 5 | [326/374](results/R11_fifth/summary.json) | 94.75% |

现有图按 R02、R05、R08 的首测复用相同 Skill 的轮次。R11 前三次终测的中位数为 330/374，五次中位数为 327/374。

## 逐轮及跨 Actor 评测

| 原评测 | 阶段 | Actor | Hard | 平均 ANLS |
| --- | --- | --- | ---: | ---: |
| [docvqa_v29_11_skilladam_1108_gpt54mini_20261120/v29.11](results/docvqa_v29_11_skilladam_1108_gpt54mini_20261120/v29.11/summary.json) | 跨 Actor | `gpt-5.4-mini` | 341/374 | 95.56% |
| [docvqa_v29_11_checkpoints_20261117/R01](results/R01/summary.json) | 逐轮检查点 | `deepseek-flash` | 315/374 | 92.37% |
| [docvqa_v29_11_checkpoints_20261117/R02](results/R02/summary.json) | 逐轮检查点 | `deepseek-flash` | 318/374 | 94.04% |
| [docvqa_v29_11_checkpoints_20261117/R05](results/R05/summary.json) | 逐轮检查点 | `deepseek-flash` | 328/374 | 94.32% |
| [docvqa_v29_11_checkpoints_20261117/R08](results/R08/summary.json) | 逐轮检查点 | `deepseek-flash` | 329/374 | 94.41% |

[三组主对照与离线验收](../../DOCVQA.md)

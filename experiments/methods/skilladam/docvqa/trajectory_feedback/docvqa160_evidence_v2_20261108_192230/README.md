# SkillAdam DocVQA 主对照运行

11 月 8 日对齐运行使用 160 道优化题，共 11 次迭代。优化证据包含图像路径和参考答案。最终 Skill 在 R10 采纳，R11 沿用。

[冻结训练配置](config/config.json) · [训练或选优回执](results/training_summary.json) · [初始 Skill](config/initial_skill.md) · [最终受测 Skill](results/final_skill.md) · [完整运行原目录](../../../../../baselines/docvqa_skilladam/docvqa160_evidence_v2_20261108_192230)

## 终测及独立复测

| 次序 | DeepSeek Flash Hard | 平均 ANLS |
| ---: | ---: | ---: |
| 1 | [325/374](results/docvqa160_evidence_v2_20261108_192230/summary.json) | 93.47% |
| 2 | [321/374](results/docvqa160_evidence_v2_20261108_192230_test374_repeat2/summary.json) | 93.45% |
| 3 | [319/374](results/docvqa160_evidence_v2_20261108_192230_test374_repeat3/summary.json) | 92.93% |

终测三次中位数为 321/374。逐轮独立复测各有原回执，沿用同一份 Skill 的轮次共用相应检查点。

## 逐轮及跨 Actor 评测

| 原评测 | 阶段 | Actor | Hard | 平均 ANLS |
| --- | --- | --- | ---: | ---: |
| [docvqa_v29_11_skilladam_1108_gpt54mini_20261120/SkillAdam](results/docvqa_v29_11_skilladam_1108_gpt54mini_20261120/SkillAdam/summary.json) | 跨 Actor | `gpt-5.4-mini` | 339/374 | 95.78% |
| [docvqa_checkpoints_20261111/skilladam_R01](results/skilladam_R01/summary.json) | 逐轮检查点 | `deepseek-flash` | 319/374 | 93.27% |
| [docvqa_checkpoints_20261111/skilladam_R02](results/skilladam_R02/summary.json) | 逐轮检查点 | `deepseek-flash` | 314/374 | 93.37% |
| [docvqa_checkpoints_20261111/skilladam_R04](results/skilladam_R04/summary.json) | 逐轮检查点 | `deepseek-flash` | 324/374 | 93.79% |
| [docvqa_checkpoints_20261111/skilladam_R05](results/skilladam_R05/summary.json) | 逐轮检查点 | `deepseek-flash` | 321/374 | 93.38% |
| [docvqa_checkpoints_20261111/skilladam_R06](results/skilladam_R06/summary.json) | 逐轮检查点 | `deepseek-flash` | 321/374 | 93.40% |
| [docvqa_checkpoints_20261111/skilladam_R08](results/skilladam_R08/summary.json) | 逐轮检查点 | `deepseek-flash` | 316/374 | 93.30% |
| [docvqa_skilladam_R02_third_20261111/skilladam_R02](results/docvqa_skilladam_R02_third_20261111/skilladam_R02/summary.json) | 逐轮检查点 | `deepseek-flash` | 317/374 | 92.07% |
| [docvqa_skilladam_checkpoints_retest_20261111/skilladam_R01](results/docvqa_skilladam_checkpoints_retest_20261111/skilladam_R01/summary.json) | 逐轮检查点 | `deepseek-flash` | 322/374 | 92.93% |
| [docvqa_skilladam_checkpoints_retest_20261111/skilladam_R02](results/docvqa_skilladam_checkpoints_retest_20261111/skilladam_R02/summary.json) | 逐轮检查点 | `deepseek-flash` | 328/374 | 94.50% |
| [docvqa_skilladam_checkpoints_retest_20261111/skilladam_R04](results/docvqa_skilladam_checkpoints_retest_20261111/skilladam_R04/summary.json) | 逐轮检查点 | `deepseek-flash` | 324/374 | 93.71% |
| [docvqa_skilladam_checkpoints_retest_20261111/skilladam_R05](results/docvqa_skilladam_checkpoints_retest_20261111/skilladam_R05/summary.json) | 逐轮检查点 | `deepseek-flash` | 321/374 | 93.22% |
| [docvqa_skilladam_checkpoints_retest_20261111/skilladam_R06](results/docvqa_skilladam_checkpoints_retest_20261111/skilladam_R06/summary.json) | 逐轮检查点 | `deepseek-flash` | 315/374 | 91.79% |
| [docvqa_skilladam_checkpoints_retest_20261111/skilladam_R08](results/docvqa_skilladam_checkpoints_retest_20261111/skilladam_R08/summary.json) | 逐轮检查点 | `deepseek-flash` | 322/374 | 93.18% |

[三组主对照与离线验收](../../../../DOCVQA.md)

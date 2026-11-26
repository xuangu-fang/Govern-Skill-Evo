# 早期 SkillAdam 本地训练

原实验 ID 为 `docvqa160_epoch1_20261102_231431`。11 月 2 日开始本地训练，11 次原生迭代均完成，采纳 5 次。最终 Skill 的独立 Test374 为 **325/374**，平均 ANLS 为 **94.07%**。

[冻结配置](config/config.json) · [训练结项](results/training_summary.json) · [原生 checkpoint](results/native/checkpoint.json) · [原生最终 Skill](results/native/final_skill.md) · [导出的最终 Skill](results/final_skill.md) · [恢复记录](reports/resume_attempts.json) · [终测摘要](results/docvqa160_epoch1_20261102_231431/summary.json)

| 迭代 | 采纳结果 | 保留 Skill |
| --- | --- | --- |
| R01 | 沿用 | [保留文本](config/initial_skill.md) |
| R02 | 采纳 | [保留文本](results/execution/rollouts/iter_001/validation_candidate/skill.md) |
| R03 | 沿用 | [保留文本](results/execution/rollouts/iter_001/validation_candidate/skill.md) |
| R04 | 沿用 | [保留文本](results/execution/rollouts/iter_001/validation_candidate/skill.md) |
| R05 | 沿用 | [保留文本](results/execution/rollouts/iter_001/validation_candidate/skill.md) |
| R06 | 采纳 | [保留文本](results/execution/rollouts/iter_005/validation_candidate/skill.md) |
| R07 | 沿用 | [保留文本](results/execution/rollouts/iter_005/validation_candidate/skill.md) |
| R08 | 采纳 | [保留文本](results/execution/rollouts/iter_007/validation_candidate/skill.md) |
| R09 | 采纳 | [保留文本](results/execution/rollouts/iter_008/validation_candidate/skill.md) |
| R10 | 采纳 | [保留文本](results/execution/rollouts/iter_009/validation_candidate/skill.md) |
| R11 | 沿用 | [保留文本](results/execution/rollouts/iter_009/validation_candidate/skill.md) |

[DocVQA 实验索引及复算命令](../../../../DOCVQA.md)

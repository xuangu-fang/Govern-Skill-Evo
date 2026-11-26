# ALFWorld SkillOpt 第一次训练

训练 ID 为 `skillopt_alfworld_native_best_only_20261030_001`。共 4 个 epoch，每轮使用 39 道训练题，在 18 道 Selection 题上选优。训练结束后对 Best Skill 执行 134 题测试。

[配置](skillopt.json) · [冻结输入](manifest.json) · [训练摘要](campaign/summary.json) · [逐步历史](campaign/history.json) · [Best Skill](campaign/best_skill.md) · [Final Skill](campaign/final_skill.md)

R02 的第 0102 题使用第二次尝试的完成轨迹。[本地恢复记录](../../evaluations/alfworld_skillopt_checkpoints_20261121/R02/recovery/test_0102.json)

| 评测 ID 或角色 | 成功题数 | 材料 |
|---|---:|---|
| Best 首测 | 120/134 | [受测 Skill](campaign/best_skill.md) · [摘要](campaign/test_eval/summary.json) · [本地逐题记录](campaign/test_eval/results.jsonl) |
| alfworld_skillopt_checkpoints_20261121/R01 | 111/134 | [受测 Skill](campaign/skills/skill_v0001.md) · [摘要](results/alfworld_skillopt_checkpoints_20261121/R01/summary.json) · [本地逐题记录](../../evaluations/alfworld_skillopt_checkpoints_20261121/R01/results.jsonl) |
| alfworld_skillopt_checkpoints_20261121/R02 | 113/134 | [受测 Skill](campaign/skills/skill_v0002.md) · [摘要](results/alfworld_skillopt_checkpoints_20261121/R02/summary.json) · [本地逐题记录](../../evaluations/alfworld_skillopt_checkpoints_20261121/R02/results.jsonl) |
| alfworld_skillopt_final_retest_20261122_133346/R04 | 118/134 | [受测 Skill](campaign/skills/skill_v0004.md) · [摘要](results/alfworld_skillopt_final_retest_20261122_133346/R04/summary.json) · [本地逐题记录](../../evaluations/alfworld_skillopt_final_retest_20261122_133346/R04/results.jsonl) |

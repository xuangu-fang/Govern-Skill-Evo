# skillopt_searchqa_main200_hard_s42

完成训练，已记录 5 步。

[冻结配置](config/config.json) · [进度回执](reports/summary.json) · [初始 Skill](config/skill_v0000.md) · [原始训练](../../../../results/skillopt_searchqa_main200_hard_s42) · [运行入口](../../../../../external/SkillOpt/scripts/train.py) · [最终 Skill](results/best_skill.md)

[原实验说明](../../../../results/skillopt_searchqa_main200_hard_s42/README.md)

## 评测

| 评测 | Actor | EM 题数 | Token F1 | 证据 |
| --- | --- | ---: | ---: | --- |
| 最佳 Skill | gpt-5.4 | 91/100 | 95.13% | [受测 Skill](results/best_skill.md) · [摘要](results/final/summary.json) · [原始逐题回执](../../../../../external/SkillOpt/outputs/searchqa_main200_hard_s42/test_eval/results.jsonl) |
| 初始 Skill | gpt-5.4 | 90/100 | 94.19% | [受测 Skill](config/skill_v0000.md) · [摘要](results/baseline/summary.json) · [原始逐题回执](../../../../../external/SkillOpt/outputs/searchqa_main200_hard_s42/test_eval_baseline/results.jsonl) |

[历史验收清单](../../../../benchmarks/searchqa/remaining-history.json) · [SearchQA 实验索引](../../../SEARCHQA.md)

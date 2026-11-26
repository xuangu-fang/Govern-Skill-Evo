# SearchQA GPT-5.4-mini 跨 Actor 评测

三组评测沿用主对照各自的最终 Skill，使用同一组 Test1400。逐题评分可从原始 Actor 回执复算。

| 评测 | Actor | EM 题数 | Token F1 | 证据 |
| --- | --- | ---: | ---: | --- |
| SkillOpt | gpt-5.4-mini | 1,141/1,400 | 88.88% | [受测 Skill](../../../../methods/skillopt/searchqa/searchqa_skillopt_retry_20261123_180000/results/searchqa_skillopt_final_gpt54mini_20261124/SkillOpt/skill.md) · [摘要](../../../../methods/skillopt/searchqa/searchqa_skillopt_retry_20261123_180000/results/searchqa_skillopt_final_gpt54mini_20261124/SkillOpt/summary.json) · [评测计划](../../../../../artifacts/analysis/searchqa_skillopt_final_gpt54mini_20261124/evaluation.json) · [原始逐题回执](../../../../../artifacts/analysis/searchqa_skillopt_final_gpt54mini_20261124/SkillOpt/scores.json) |
| SkillAdam | gpt-5.4-mini | 1,140/1,400 | 89.31% | [受测 Skill](../../../../methods/skilladam/searchqa/v28_11_aligned/v28_11_aligned_batch60_20261116_123000/results/searchqa_v28_16_skilladam_1116_gpt54mini_20261119/SkillAdam/skill.md) · [摘要](../../../../methods/skilladam/searchqa/v28_11_aligned/v28_11_aligned_batch60_20261116_123000/results/searchqa_v28_16_skilladam_1116_gpt54mini_20261119/SkillAdam/summary.json) · [评测计划](../../../../../artifacts/analysis/searchqa_v28_16_skilladam_1116_gpt54mini_20261119/evaluation.json) · [原始逐题回执](../../../../../artifacts/analysis/searchqa_v28_16_skilladam_1116_gpt54mini_20261119/SkillAdam/scores.json) |
| v28.16 | gpt-5.4-mini | 1,156/1,400 | 89.32% | [受测 Skill](../../../../methods/v28_16/v28_16_searchqa600_batch60_20261112_132531/results/searchqa_v28_16_skilladam_1116_gpt54mini_20261119/v28.16/skill.md) · [摘要](../../../../methods/v28_16/v28_16_searchqa600_batch60_20261112_132531/results/searchqa_v28_16_skilladam_1116_gpt54mini_20261119/v28.16/summary.json) · [评测计划](../../../../../artifacts/analysis/searchqa_v28_16_skilladam_1116_gpt54mini_20261119/evaluation.json) · [原始逐题回执](../../../../../artifacts/analysis/searchqa_v28_16_skilladam_1116_gpt54mini_20261119/v28.16/scores.json) |

[历史验收清单](../../remaining-history.json) · [SearchQA 实验索引](../../../../methods/SEARCHQA.md)

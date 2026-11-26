# lmb_skillopt_deepseek_flash_repeat_20261123_010400

四轮原生训练使用 35 道 Train 和 18 道 Selection。初始 Selection 和四轮训练与选优分别为 18、53、111、111、93 题次，共 386。第 3 轮慢更新产生最终 Best Skill，Selection 为 17/18。第 4 轮慢更新完成两组各 20 题的对照作答，状态为 `no_content`，因此该轮少一批 18 题的慢更新 Selection。

[原生配置](config/config.json) · [运行清单](config/run.json) · [优化器](config/optimizer.json) · [决策记录](results/history.json) · [训练摘要](results/training_summary.json) · [逐轮 Skill](results/skills) · [最终 Skill](results/final_skill.md) · [归档清单](archive.json)

| DeepSeek Flash 评测 | 答对／已评分 | 计划题数 |
|---|---:|---:|
| [Test124 首测](../../../../../artifacts/methods/skillopt/lmb/lmb_skillopt_deepseek_flash_repeat_20261123_010400/test/summary.json) | 90/124 | 124 |
| [Test124 复测](../../../../../artifacts/methods/skillopt/lmb/lmb_skillopt_deepseek_flash_repeat_20261123_010400/retest1_20261124/test/coverage.json) | 89/122 | 124 |

复测缺少 `202511:24` 和 `202512:31` 的有效评分。

[完整运行](../../../../../artifacts/methods/skillopt/lmb/lmb_skillopt_deepseek_flash_repeat_20261123_010400) · [SkillOpt 历史索引](../README.md)

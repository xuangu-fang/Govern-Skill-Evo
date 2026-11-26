# lmb_skillopt_deepseek_flash

四轮原生训练使用 35 道 Train 和 18 道 Selection。初始 Selection 和四轮训练与选优分别为 18、53、111、111、111 题次，共 404。逐轮 Skill 快照取各轮结束时的保留版本，第 4 轮普通更新产生最终 Best Skill，Selection 为 17/18。

[原生配置](config/config.json) · [运行清单](config/run.json) · [优化器](config/optimizer.json) · [决策记录](results/history.json) · [训练摘要](results/training_summary.json) · [逐轮 Skill](results/skills) · [最终 Skill](results/final_skill.md) · [归档清单](archive.json)

| DeepSeek Flash 评测 | 答对／已评分 | 计划题数 |
|---|---:|---:|
| [Test124 原始回执](../../../../../artifacts/methods/skillopt/lmb/lmb_skillopt_deepseek_flash/test) | 93/123 | 124 |
| [Test124 补测合并](../../../../../artifacts/methods/skillopt/lmb/lmb_skillopt_deepseek_flash/supplement_81920/combined_report.json) | 94/124 | 124 |

首测缺少 `202511:24` 的评分。补测复用受测 Skill，并在输出预算提高至 81,920 tokens 后取得该题评分。合并时按题目 ID 检查覆盖。

[完整运行](../../../../../artifacts/methods/skillopt/lmb/lmb_skillopt_deepseek_flash) · [SkillOpt 历史索引](../README.md)

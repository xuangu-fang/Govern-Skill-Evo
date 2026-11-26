# lmb53_actor65536_20261103_115844

原生检查点与训练完成回执均记录六轮训练，最终 Skill 来自 R04。Test124 从历史检查点续测，原计划中的已评分题被复用，最终覆盖 124 题。续测批次与原测试共用一套逐题结果。训练与选优共 159 题次。

[启动配置](config/config.json) · [冻结配置](config/frozen.json) · [优化器检查点](results/checkpoint.json) · [逐轮 Skill](results/skills) · [最终 Skill](results/final_skill.md) · [归档清单](archive.json)

| 评测 | 受测 Skill | Actor | 答对／评分 | 计划题数 |
|---|---|---|---:|---:|
| [Test124 技术续测汇总](../../../../../artifacts/methods/skilladam/lmb/lmb53_actor65536_20261103_115844/technical_retry_v1/standard_test_summary.json) | [R04](results/skills/R04.md) | `deepseek-flash` | 45/124 | 124 |

各场次缺题 ID 和独立补测记录见[归档清单](archive.json)。

[训练完成回执](results/training_complete.json) · [技术续测报告](../../../../../artifacts/methods/skilladam/lmb/lmb53_actor65536_20261103_115844/technical_retry_v1/REPORT.md) · [完整运行](../../../../../artifacts/methods/skilladam/lmb/lmb53_actor65536_20261103_115844) · [SkillAdam 历史索引](../README.md)

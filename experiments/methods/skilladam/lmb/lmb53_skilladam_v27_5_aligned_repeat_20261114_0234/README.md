# lmb53_skilladam_v27_5_aligned_repeat_20261114_0234

五轮训练使用 53 道优化题。R01 和 R04 采纳更新，最终保留 R04。项目版 Flash 为 `deepseek-v4.1-flash`。R04 项目版原始测试缺四题，四题补测后覆盖 124 题。R01 的项目版测试及 R04 的官方 Flash 场次均有缺题。训练与选优共 159 题次。

[启动配置](config/config.json) · [冻结配置](config/frozen.json) · [优化器检查点](results/checkpoint.json) · [逐轮 Skill](results/skills) · [最终 Skill](results/final_skill.md) · [归档清单](archive.json)

| 评测 | 受测 Skill | Actor | 答对／评分 | 计划题数 |
|---|---|---|---:|---:|
| [官方 Flash](../../../../../artifacts/methods/skilladam/lmb/lmb53_skilladam_v27_5_aligned_repeat_20261114_0234/evaluations/lmb53_skilladam_v27_5_aligned_repeat_20261114_0234_test_official_flash/evaluation.json) | [R04](results/skills/R04.md) | `deepseek-flash` | 16/52 | 124 |
| [项目版 Flash 原始回执](../../../../../artifacts/methods/skilladam/lmb/lmb53_skilladam_v27_5_aligned_repeat_20261114_0234/evaluations/lmb53_skilladam_v27_5_aligned_repeat_20261114_0234_test_project_v41/report.json) | [R04](results/skills/R04.md) | `deepseek-v4.1-flash` | 42/120 | 124 |
| [项目版 Flash 补测合并](../../../../../artifacts/methods/skilladam/lmb/lmb53_skilladam_v27_5_aligned_repeat_20261114_0234/evaluations/lmb53_skilladam_v27_5_aligned_repeat_20261114_0234_test_project_v41/supplement_600s_attempts_007_009/summary.json) | [R04](results/skills/R04.md) | `deepseek-v4.1-flash` | 42/124 | 124 |
| [项目版 Flash R01](../../../../../artifacts/methods/skilladam/lmb/lmb53_skilladam_v27_5_aligned_repeat_20261114_0234/evaluations/lmb124_round_skills_project_v41_20261116/skilladam_R01/report.json) | [R01](results/skills/R01.md) | `deepseek-v4.1-flash` | 44/120 | 124 |

各场次缺题 ID 和独立补测记录见[归档清单](archive.json)。

[完整运行](../../../../../artifacts/methods/skilladam/lmb/lmb53_skilladam_v27_5_aligned_repeat_20261114_0234) · [SkillAdam 历史索引](../README.md)

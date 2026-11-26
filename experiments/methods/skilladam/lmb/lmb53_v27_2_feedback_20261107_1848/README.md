# lmb53_v27_2_feedback_20261107_1848

六轮训练使用 53 道优化题。R01、R03 和 R05 改变了保留 Skill。R06 的 Gate 接受了候选，其 Skill 与 R05 逐字节相同。原始 Test124 缺 `202511:24` 与 `202512:31`，两题补测后覆盖 124 题。训练与选优共 159 题次。

[冻结配置](config/frozen.json) · [优化器检查点](results/checkpoint.json) · [逐轮 Skill](results/skills) · [最终 Skill](results/final_skill.md) · [归档清单](archive.json)

| 评测 | 受测 Skill | Actor | 答对／评分 | 计划题数 |
|---|---|---|---:|---:|
| [Test124 原始回执](../../../../../artifacts/methods/skilladam/lmb/lmb53_v27_2_feedback_20261107_1848/evaluations/lmb53_v27_2_feedback_20261107_1848_test/report.json) | [R06](results/skills/R06.md) | `deepseek-flash` | 54/122 | 124 |
| [Test124 第一次补测合并](../../../../../artifacts/methods/skilladam/lmb/lmb53_v27_2_feedback_20261107_1848/evaluations/lmb53_v27_2_feedback_20261107_1848_test/additional_three/comparison.json) | [R06](results/skills/R06.md) | `deepseek-flash` | 54/123 | 124 |
| [Test124 两次补测合并](../../../../../artifacts/methods/skilladam/lmb/lmb53_v27_2_feedback_20261107_1848/evaluations/lmb53_v27_2_feedback_20261107_1848_test/supplement_81920/comparison.json) | [R06](results/skills/R06.md) | `deepseek-flash` | 54/124 | 124 |

各场次缺题 ID 和独立补测记录见[归档清单](archive.json)。

[完整运行](../../../../../artifacts/methods/skilladam/lmb/lmb53_v27_2_feedback_20261107_1848) · [SkillAdam 历史索引](../README.md)

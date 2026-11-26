# v27_3_lmb53_20261113

6 轮训练使用 53 道优化题。Parent 和 Candidate 共执行 106 题次。保留文本发生变化的轮次为 R01、R02、R03、R04、R05、R06。R06 产生最终 Skill。

[训练配置](config/config.json) · [运行环境](config/runtime.json) · [冻结 Prompt](config/prompts) · [逐轮 Skill](results/skills) · [最终 Skill](results/final_skill.md) · [归档清单](archive.json) · [完整训练](../../../../artifacts/methods/v27_3/v27_3_lmb53_20261113)

| 评测 | 受测节点 | 答对／已评分 | 计划题数 |
|---|---|---:|---:|
| [首测原回执](../../../../artifacts/methods/v27_3/v27_3_lmb53_20261113/evaluations/v27_3_lmb53_20261113_test/report.json) | [R06](results/skills/R06.md) | 54/122 | 124 |
| [合并补测](../../../../artifacts/methods/v27_3/v27_3_lmb53_20261113/evaluations/v27_3_lmb53_20261113_test/additional_three/summary.json) | [R06](results/skills/R06.md) | 55/123 | 124 |

补测第 9 次请求为 `202512:31` 产生有效评分。归档核对了请求与原任务签名、实际使用的 Skill、响应和参考标签。补测后只缺 `202511:24`。

[历史启动材料](../../../launches/v27_3_lmb53_20261113) · [r06_diagnosis_v2_20261113](../../../analysis/v27_3_r06_diagnosis_v2_20261113) · [r06_frozen_20261113](../../../analysis/v27_3_r06_frozen_20261113) · [r06_preconditioner_v2_20261113](../../../analysis/v27_3_r06_preconditioner_v2_20261113) · [r06_preconditioner_v3_20261113](../../../analysis/v27_3_r06_preconditioner_v3_20261113) · [历史对照](../../../comparisons/v27_3_lmb53_20261113)

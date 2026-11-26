# v27_2_precond_v3_lmb53_20261105_131046

6 轮训练使用 53 道优化题。Parent 和 Candidate 共执行 106 题次。保留文本发生变化的轮次为 R02、R03、R06。R06 产生最终 Skill。

[训练配置](config/config.json) · [运行环境](config/runtime.json) · [冻结 Prompt](config/prompts) · [逐轮 Skill](results/skills) · [最终 Skill](results/final_skill.md) · [归档清单](archive.json) · [完整训练](../../../../artifacts/methods/v27_2/v27_2_precond_v3_lmb53_20261105_131046)

| 评测 | 受测节点 | 答对／已评分 | 计划题数 |
|---|---|---:|---:|
| [首测](../../../../artifacts/methods/v27_2/v27_2_precond_v3_lmb53_20261105_131046/evaluations/v27_2_precond_v3_lmb53_20261105_131046_test/report.json) | [R06](results/skills/R06.md) | 50/122 | 124 |

保留 Preconditioner v3 的独立运行。测试缺少 `202511:24` 和 `202512:31` 的有效评分。

[历史启动材料](../../../launches/v27_2_precond_v3_lmb53_20261105_131046) · [diagnosis_v3_r02_r03_20261105](../../../analysis/v27_2_diagnosis_v3_r02_r03_20261105) · [preconditioner_v4_r03_r06_20261105](../../../analysis/v27_2_preconditioner_v4_r03_r06_20261105)

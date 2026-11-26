# v27_2_diag_v3_precond_v3_lmb53_20261105_210532

6 轮训练使用 53 道优化题。Parent 和 Candidate 共执行 106 题次。保留文本发生变化的轮次为 R01、R02、R03、R04、R06。R06 产生最终 Skill。

[训练配置](config/config.json) · [运行环境](config/runtime.json) · [冻结 Prompt](config/prompts) · [逐轮 Skill](results/skills) · [最终 Skill](results/final_skill.md) · [归档清单](archive.json) · [完整训练](../../../../artifacts/methods/v27_2/v27_2_diag_v3_precond_v3_lmb53_20261105_210532)

| 评测 | 受测节点 | 答对／已评分 | 计划题数 |
|---|---|---:|---:|
| [首测](../../../../artifacts/methods/v27_2/v27_2_diag_v3_precond_v3_lmb53_20261105_210532/evaluations/v27_2_diag_v3_precond_v3_lmb53_20261105_210532_test/summary.json) | [R06](results/skills/R06.md) | 55/124 | 124 |
| [32 并发复测](../../../../artifacts/methods/v27_2/v27_2_diag_v3_precond_v3_lmb53_20261105_210532/evaluations/v27_2_diag_v3_precond_v3_test32_20261108_1811/report.json) | [R06](results/skills/R06.md) | 54/123 | 124 |

Diagnosis v3 与 Preconditioner v3 的组合有一份完整首测。复测提高至 32 并发，`202511:24` 的追加尝试没有产生有效评分。

[历史启动材料](../../../launches/v27_2_diag_v3_precond_v3_lmb53_20261105_210532) · [diagnosis_v3_r02_r03_20261105](../../../analysis/v27_2_diagnosis_v3_r02_r03_20261105) · [preconditioner_v4_r03_r06_20261105](../../../analysis/v27_2_preconditioner_v4_r03_r06_20261105)

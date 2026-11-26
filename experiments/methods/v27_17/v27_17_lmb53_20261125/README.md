# v27_17_lmb53_20261125

五轮训练使用 53 道优化题，Parent 和 Candidate 合计执行 106 题次。保留 Skill 在 R01、R02、R03、R04、R05 更新，R05 产生最终 Skill。

[训练配置](config/config.json) · [运行环境](config/runtime.json) · [冻结 Prompt](config/prompts) · [Prompt SHA-256](config/launch_prompt_sha256.json) · [逐轮 Skill](results/skills) · [最终 Skill](results/final_skill.md) · [归档清单](archive.json) · [完整训练](../../../../artifacts/methods/v27_17/v27_17_lmb53_20261125)

测试 Actor 使用官方 `deepseek-flash`。

| 评测 | 答对／已评分 | 计划题数 |
|---|---:|---:|
| [Meta53 首测分片](../../../../artifacts/methods/v27_17/v27_17_lmb53_20261125/evaluations/v27_17_lmb53_20261125_test124/summary.json) | 43/53 | 53 |
| [Other71 补齐分片](../../../../artifacts/methods/v27_17/v27_17_lmb53_20261125/evaluations/v27_17_lmb53_20261125_test124/summary.json) | 37/71 | 71 |
| [合并后的 Test124](../../../../artifacts/methods/v27_17/v27_17_lmb53_20261125/evaluations/v27_17_lmb53_20261125_test124/summary.json) | 80/124 | 124 |
| [独立 Meta53 复测](../../../../artifacts/methods/v27_17/v27_17_lmb53_20261125/evaluations/v27_17_final_meta53_retest1_20261125/runs/batch.json) | 19/23 | 53 |

完整 Test124 按题目 ID 合并 Meta53 的 43/53 和 Other71 的 37/71，两组互斥。独立 Meta53 复测有 23 份评分，缺题 ID 见归档清单。

[历史启动材料](../../../launches/v27_17_lmb53_20261125)

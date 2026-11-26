# v27_15_lmb53_20261125

五轮训练使用 53 道优化题，Parent 和 Candidate 合计执行 106 题次。保留 Skill 在 R01、R03、R04、R05 更新，R05 产生最终 Skill。

[训练配置](config/config.json) · [运行环境](config/runtime.json) · [冻结 Prompt](config/prompts) · [Prompt SHA-256](config/launch_prompt_sha256.json) · [逐轮 Skill](results/skills) · [最终 Skill](results/final_skill.md) · [归档清单](archive.json) · [完整训练](../../../../artifacts/methods/v27_15/v27_15_lmb53_20261125)

测试 Actor 使用官方 `deepseek-flash`。

| 评测 | 答对／已评分 | 计划题数 |
|---|---:|---:|
| [Meta53 首测](../../../../artifacts/methods/v27_15/v27_15_lmb53_20261125/evaluations/v27_15_vs_v27_17_final_meta53_20261125/v27_15) | 17/50 | 53 |

该次 Meta53 评测计划 53 题，实际评分 50 题。缺少 `202511:25`、`202511:27` 和 `202512:11` 的有效评分。混合评测的共用绑定保留在原址。

[历史启动材料](../../../launches/v27_15_lmb53_20261125) · [v27.15 与 v27.16 的冻结回放](../../../analysis/v27_15_vs_v27_16_r02_frozen/结果对照.md)

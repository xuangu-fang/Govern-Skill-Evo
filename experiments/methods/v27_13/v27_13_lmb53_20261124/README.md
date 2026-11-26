# v27_13_lmb53_20261124

五轮训练使用 53 道优化题，Parent 和 Candidate 合计执行 106 题次。保留 Skill 在 R01、R02、R04、R05 更新，R05 产生最终 Skill。

[训练配置](config/config.json) · [运行环境](config/runtime.json) · [冻结 Prompt](config/prompts) · [Prompt SHA-256](config/launch_prompt_sha256.json) · [逐轮 Skill](results/skills) · [最终 Skill](results/final_skill.md) · [归档清单](archive.json) · [完整训练](../../../../artifacts/methods/v27_13/v27_13_lmb53_20261124)

测试 Actor 使用官方 `deepseek-flash`。

| 评测 | 答对／已评分 | 计划题数 |
|---|---:|---:|
| [Test124 首测](../../../../artifacts/methods/v27_13/v27_13_lmb53_20261124/evaluations/v27_13_lmb53_20261124_test_deepseek_flash/summary.json) | 69/124 | 124 |
| [Test124 复测 1](../../../../artifacts/methods/v27_13/v27_13_lmb53_20261124/evaluations/v27_13_lmb53_20261124_test_deepseek_flash_retest1/summary.json) | 73/124 | 124 |
| [Test124 复测 2](../../../../artifacts/methods/v27_13/v27_13_lmb53_20261124/evaluations/v27_13_lmb53_20261124_test_deepseek_flash_retest2/summary.json) | 70/124 | 124 |

三次完整测试均绑定 R05 的同一份 Skill，答对数中位数为 **70/124（56.45%）**。

[历史启动材料](../../../launches/v27_13_lmb53_20261124) · [R04 冻结回放](../../../analysis/v27_13_r04_20261124/结果对照.md)

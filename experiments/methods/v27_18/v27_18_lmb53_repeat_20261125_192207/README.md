# v27_18_lmb53_repeat_20261125_192207

11 月 25 日独立重训完成五轮，执行 85 个训练与选优题次。R04 产生最终 Skill，R05 沿用。

[配置](config/config.json) · [冻结 Prompt](config/prompts) · [训练摘要](results/training_summary.json) · [逐轮 Skill](results/skills) · [最终 Skill](results/final_skill.md) · [评测清单与原始回执](archive.json) · [完整运行](../../../../artifacts/methods/v27_18/v27_18_lmb53_repeat_20261125_192207)

| 节点与评测 | Actor | 答对／已评分 |
|---|---|---:|
| R00 Other71 | DeepSeek Flash | 38/71 |
| R01 Test124 | DeepSeek Flash | 95/124 |
| R04 Test124 首测 | DeepSeek Flash | 90/123，补入 `202511:24` 后 91/124 |
| R04 Test124 复测 1 | DeepSeek Flash | 90/124 |
| R04 Test124 复测 2 | DeepSeek Flash | 86/123，补入 `202512:31` 后 87/124 |
| R04 Other71 复测 | DeepSeek Flash | 38/71 |
| R04 Test124 跨 Actor 评测 | GPT-5.4-mini | 41/124 |

最终 Skill 三次完整 DeepSeek Flash 测试的中位数为 90/124（72.58%）。每个补测前后的分母及对应回执均有记录。

# v27_19_lmb53_20261126

五轮训练使用 53 道优化题。R01、R02、R04 采纳更新，R03 沿用 R02，R05 沿用 R04。每轮训练与选优题次为 22、22、22、20、10，合计 96。

[训练配置](config/config.json) · [运行环境](config/runtime.json) · [冻结 Prompt](config/prompts) · [实施清单](config/implementation.json) · [训练摘要](results/training_summary.json) · [完整运行](../../../../artifacts/methods/v27_19/v27_19_lmb53_20261126) · [归档清单](archive.json)

| 节点 | 保留 Skill | 完整 Test124 |
|---|---|---|
| R00 | [共用初始 Skill](../../lmb/initial_skill.md) | [44](../../lmb/results/evaluations/shared_R00/summary.json) |
| R01 | [受测 Skill](results/skills/R01.md) | [首测 84](results/evaluations/R01_first/summary.json) |
| R02 | [受测 Skill](results/skills/R02.md) | [首测含补测 95](results/evaluations/R02_first/summary.json)、[复测 92](results/evaluations/R02_retest1/summary.json) |
| R03 | [保留 Skill](results/skills/R03.md) | 沿用 R02 |
| R04 | [最终 Skill](results/final_skill.md) | [首测 91](results/evaluations/final_first/summary.json)、[复测 96](results/evaluations/final_retest1/summary.json)、[复测 89](results/evaluations/final_retest2/summary.json) |
| R05 | [保留 Skill](results/skills/R05.md) | 沿用 R04 |

最终 Skill 的 DeepSeek Flash Test124 三次评测中位数为 91/124。[三方法主对照](../../lmb/README.md)

## GPT-5.4 mini 评测

三次评测均使用 R04 保留的同一份 [最终 Skill](results/final_skill.md)。两次 Meta53 复测使用完整测试中预先登记的同一组 53 题。

| 评测 | 答对／评分 | EM |
|---|---:|---:|
| [Test124](../../../../artifacts/methods/v27_19/v27_19_lmb53_20261126/evaluations/v27_19_lmb53_20261126_test124_gpt_5_4_mini) | 60/124 | 48.39% |
| [Meta53 复测 1](../../../../artifacts/methods/v27_19/v27_19_lmb53_20261126/evaluations/v27_19_meta53_gpt_5_4_mini_retest1_20261126) | 33/53 | 62.26% |
| [Meta53 复测 2](../../../../artifacts/methods/v27_19/v27_19_lmb53_20261126/evaluations/v27_19_meta53_gpt_5_4_mini_retest2_20261126) | 31/53 | 58.49% |

[归档清单](archive.json)的 `cross_actor_evaluations` 记录每次评测的原始配置、受测 Skill 哈希和逐题回执入口。[历史归档读回](../../lmb/README.md#历史版本)

# lmb53_skilladam_v27_5_official_flash_20261120_0020

11 月 20 日的五轮训练使用 53 道优化题，每轮分别保存训练、Parent 验证和 Candidate 验证回执。五轮各执行 33、33、33、30、30 题次，合计 159。R02 是唯一采纳更新的一轮。

[启动配置](config/config.json) · [冻结配置](config/frozen.json) · [原生优化器检查点](results/checkpoint.json) · [最终 Skill](results/final_skill.md) · [完整运行](../../../../../artifacts/methods/skilladam/lmb/lmb53_skilladam_v27_5_official_flash_20261120_0020) · [归档清单](archive.json)

| 节点 | 保留 Skill | 完整 Test124 |
|---|---|---|
| R00 | [初始 Skill](../../../lmb/initial_skill.md) | [44](../../../lmb/results/evaluations/shared_R00/summary.json) |
| R01 | [保留 Skill](results/skills/R01.md) | 沿用 R00 |
| R02 | [受测 Skill](results/skills/R02.md) | [首测含补测 61](results/evaluations/final_first/summary.json)、[复测 58](results/evaluations/final_retest1/summary.json)、[复测含补测 61](results/evaluations/final_retest2/summary.json) |
| R03–R05 | [R03](results/skills/R03.md)、[R04](results/skills/R04.md)、[R05](results/skills/R05.md) | 沿用 R02 |

[主对照](../../../lmb/README.md)取该次训练最终 Skill 的三次测试中位数。

## GPT‑5.4 mini 专项评测

2026‑11‑20 的跨 Actor 评测使用与主对照相同的 R02 Skill，Test124 为 **41/124**。[逐题回执与汇总](../../../../../artifacts/methods/skilladam/lmb/lmb53_skilladam_v27_5_official_flash_20261120_0020/evaluations/lmb_v27_12_skilladam_1120_final_gpt54mini_20261120) · [SkillAdam 历史索引](../README.md)

# lmb_skillopt_native_feedback_20261124

11 月 24 日启动的 native feedback 训练。初始 Selection 执行 18 题次，四轮普通更新各执行 35 道 Train 和 18 道 Selection。三次慢更新各用两份 Skill 作答 20 道对照题，再验证候选 Skill 18 题。共执行 404 题次。

[原生训练配置](config/config.json) · [运行清单](config/run.json) · [训练摘要](results/training_summary.json) · [Selection](results/selection.json) · [最终 Best Skill](results/final_skill.md) · [完整运行](../../../../../artifacts/methods/skillopt/lmb/lmb_skillopt_native_feedback_20261124) · [归档清单](archive.json)

| 节点 | 保留 Skill | 完整 Test124 |
|---|---|---|
| R00 | [初始 Skill](results/skills/R00.md) | [44](../../../lmb/results/evaluations/shared_R00/summary.json) |
| R01 | [保留 Skill](results/skills/R01.md) | 沿用 R00 |
| R02 | [受测 Skill](results/skills/R02.md) | [首测 54](results/evaluations/R02_first/summary.json) |
| S2 | [受测 Skill](results/skills/S2.md) | [首测 65](results/evaluations/S2_first/summary.json) |
| R03 | [保留 Skill](results/skills/R03.md) | 沿用 S2 |
| S3 | [受测 Skill](results/skills/S3.md) | [首测含补测 86](results/evaluations/S3_first/summary.json)、[复测 95](results/evaluations/S3_retest1/summary.json)、[复测 81](results/evaluations/S3_retest2/summary.json) |
| R04 | [受测 Best Skill](results/skills/R04.md) | [首测含补测 86](results/evaluations/final_first/summary.json)、[复测 91](results/evaluations/final_retest1/summary.json)、[复测含补测 89](results/evaluations/final_retest2/summary.json) |
| S4 | [保留 Best Skill](results/skills/S4.md) | 沿用 R04 |

S1 的[空占位记录](results/S1_state.json)随训练保留。S3 首测复用 28 份此前的 Meta53 回执。R04 首测由 Meta53、其余 71 题与两份补测合并，第二次复测按当时的汇总使用两份补测回执。最终 Best Skill 的三次测试中位数为 89/124。[三方法主对照](../../../lmb/README.md)

## 专项评测

| Actor | Skill | 评测 | 答对／已评分 | 计划题数 |
|---|---|---|---:|---:|
| DeepSeek Flash | S3 | [Meta53 原始批次](../../../../../artifacts/methods/skillopt/lmb/lmb_skillopt_native_feedback_20261124/evaluations/lmb_skillopt_native_feedback_epoch03_best_meta53_20261124) | 28/28 | 53 |
| DeepSeek Flash | R04 | [Meta53 原始批次](../../../../../artifacts/methods/skillopt/lmb/lmb_skillopt_native_feedback_20261124/evaluations/lmb_skillopt_native_feedback_epoch04_best_meta53_20261125) | 49/53 | 53 |
| DeepSeek Flash | R04 | [Other71 原始批次](../../../../../artifacts/methods/skillopt/lmb/lmb_skillopt_native_feedback_20261124/evaluations/lmb_skillopt_native_feedback_epoch04_best_other71_20261125) | 37/69 | 71 |
| GPT‑5.4 mini | R04 | [Test124 首测](../../../../../artifacts/methods/skillopt/lmb/lmb_skillopt_native_feedback_20261124/evaluations/lmb_test124_gpt54mini_v2718_run2_skillopt_run3_20261126/skillopt_run3/summary.json) | 76/124 | 124 |
| GPT‑5.4 mini | R04 | [Test124 复测](../../../../../artifacts/methods/skillopt/lmb/lmb_skillopt_native_feedback_20261124/evaluations/lmb_skillopt_run3_gpt54mini_test124_retest1_20261126/skillopt_run3/summary.json) | 88/124 | 124 |
| GPT‑5.4 mini | R04 | [Meta53 复测](../../../../../artifacts/methods/skillopt/lmb/lmb_skillopt_native_feedback_20261124/evaluations/lmb_skillopt_run3_gpt54mini_meta53_retest2_20261126/summary.json) | 50/53 | 53 |

Other71 原始批次缺少 `202511:24` 和 `202512:31` 的评分。S3 原始批次缺少 25 题。完整题号与配置绑定收录在[归档清单](archive.json)的 `supplemental_evaluations`，可从 [SkillOpt 历史索引](../README.md)离线读回。

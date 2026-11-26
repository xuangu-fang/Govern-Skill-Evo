# v27_lmb53_actor49152_20261031_152036

6 轮训练使用 53 道优化题。Parent 和 Candidate 共执行 106 题次。保留文本发生变化的轮次为 R01、R03、R06。R06 产生最终 Skill。

[训练配置](config/config.json) · [运行环境](config/runtime.json) · [冻结 Prompt](config/prompts) · [逐轮 Skill](results/skills) · [最终 Skill](results/final_skill.md) · [归档清单](archive.json) · [完整训练](../../../../artifacts/methods/v27/v27_lmb53_actor49152_20261031_152036)

| 评测 | 受测节点 | 答对／已评分 | 计划题数 |
|---|---|---:|---:|
| [49,152-token 首测](../../../../artifacts/methods/v27/v27_lmb53_actor49152_20261031_152036/evaluations/v27_lmb124_actor49152_20261031_152036/report.json) | [R06](results/skills/R06.md) | 58/123 | 124 |

首测缺少 `202512:31` 的有效评分。旧报告对 JSON 编码后的 Skill 字符串取 SHA-256，归档清单另保留 Markdown 字节的 SHA-256。

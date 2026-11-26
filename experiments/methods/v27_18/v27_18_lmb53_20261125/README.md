# v27_18_lmb53_20261125

11 月 25 日首次训练完成五轮，Parent 和 Candidate 合计执行 106 题次。最终 Skill 为 R05。

[配置](config/config.json) · [冻结 Prompt](config/prompts) · [训练摘要](results/training_summary.json) · [逐轮 Skill](results/skills) · [最终 Skill](results/final_skill.md) · [评测清单与原始回执](archive.json) · [完整运行](../../../../artifacts/methods/v27_18/v27_18_lmb53_20261125)

| 评测 | 答对／已评分 | 范围 |
|---|---:|---|
| 最终 Skill Meta53 | 42/53 | 含指定选项的测试子集 |
| 最终 Skill Test124 | 83/122 | 复用前述 53 份回执，与其余题目的分片合并 |
| [R05 加 R04 提案](results/skills/R05_with_R04_update.md) | 51/53 | 独立变体，按 Meta53 评测 |

Test124 缺少 `202511:24` 和 `202512:31` 的有效评分。变体有自身的受测 Skill 和绑定记录。

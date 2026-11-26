# v27_12_lmb53_20261118

五轮训练共用 53 道优化题，Parent 和 Candidate 合计执行 106 题次。R03 产生最终 Skill，R04 和 R05 沿用。配置、四份冻结 Prompt 和受测 Skill 均可从本页定位。

[配置](config/config.json) · [冻结 Prompt](config/prompts) · [Prompt SHA-256](config/prompt_sha256.json) · [训练摘要](results/training_summary.json) · [实际受测 Skill](results/skills) · [完整评测清单与回执位置](archive.json) · [完整运行](../../../../artifacts/methods/v27_12/v27_12_lmb53_20261118)

| 节点 | DeepSeek Flash 答对／已评分 | GPT-5.4-mini 答对／已评分 |
|---|---|---|
| [R00](results/skills/R00.md) | 44/124，含补测，供三方法主对照共用 |  |
| [R01](results/skills/R01.md) | 64/124（首测含补测）、57/124 |  |
| [R02](results/skills/R02.md) | 66/124、74/124、70/124 |  |
| [R03](results/final_skill.md) | 64/124（首测含补测）、61/124、66/124（含补测）、65/124、62/123（部分） | 43/124、43/124（两次独立测试） |
| [R04](results/skills/R04.md)、[R05](results/skills/R05.md) | 沿用 R03 |  |

R03 的第四次复测缺少 `202511:24` 的有效评分，保留 62/123。两次 GPT-5.4-mini 测试的逐题回执独立保存，其中一次与 SkillAdam 同批。共享混合组按各自受测方法归档。

R04 的设计材料沿用原冻结目录，回放脚本和相对引用可在原址查阅。[原版回放](../../../../experiments/analysis/v27_12_r04_frozen_20261118/结果对照.md) · [Preconditioner v2](../../../../experiments/analysis/v27_12_r04_preconditioner_v2_20261118/结果对照.md) · [Diagnosis v2](../../../../experiments/analysis/v27_12_r04_diagnosis_v2_20261118/结果对照.md) · [当时的启动入口](../../../../experiments/launches/v27_12_lmb53_20261118)

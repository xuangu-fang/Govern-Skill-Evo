# SpreadsheetBench v25.1 实验记录

本次训练按 8 批各 15 题完成。R08 保留的 Skill 用于随后的 280 题首测，整题成功 223 题（79.64%），逐题单元格通过率均值为 90.01%。

| 材料 | 位置 |
|---|---|
| 正式训练输入 | [配置](config/config.json) · [初始 Skill](config/initial_skill.md) |
| 首测输入 | [评测配置](config/evaluation/config.json) · [实际评分器](config/evaluation/scoring.py) |
| 训练与测试回执 | [训练](results/training_complete.json) · [测试](results/test_complete.json) |
| 最终 Skill 与受测文本 | [训练导出](results/final_skill.md) · [首测副本](results/v25_v25_1_common_actor_no_review_20261030_001_v25_1_test280/evaluated_skill.md) |
| 首测成绩 | [精选摘要](results/v25_v25_1_common_actor_no_review_20261030_001_v25_1_test280/summary.json) |
| 本机完整记录 | [逐轮训练](../../../../artifacts/methods/v25_1/v25_v25_1_common_actor_no_review_20261030_001_v25_1/campaign) · [逐题终报](../../../../artifacts/methods/v25_1/v25_v25_1_common_actor_no_review_20261030_001_v25_1_test280/summary.json) |
| 方法与离线验收 | [v25.1 方法说明](../../../../docs/methods/v25_1/README.md) |

历史回执、清单及完整终报保留当时的文件内容。旧实验目录有一个本机兼容链接，供已冻结的 v25.2、SkillAdam 校验器和轨迹绝对路径回查。原始运行存放在 Git 忽略的 `artifacts/`，可单独备份。

## 逐轮发布

[发布清单](results/publications.json)记录 R00–R08 的实际保留 Skill、原始位置及 SHA-256。[R00](results/skills/R00.md) · [R08](results/skills/R08.md)

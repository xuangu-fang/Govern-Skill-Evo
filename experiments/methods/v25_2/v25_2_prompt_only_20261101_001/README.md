# SpreadsheetBench v25.2 实验记录

v25.2 完成 8 轮训练，每轮 15 题。保留的最终 Skill 在 280 题首测中整题成功 229 题（81.79%），逐题单元格通过率均值为 91.94%。

| 材料 | 位置 |
|---|---|
| 方法与离线命令 | [方法说明](../../../../docs/methods/v25_2/README.md) |
| 训练输入 | [正式配置](config/config.json) · [初始 Skill](config/initial_skill.md) · [训练运行环境](config/campaign/runtime.json) |
| 评测输入 | [配置](config/evaluation/config.json) · [评分器](config/evaluation/scoring.py) |
| 训练结果 | [完成记录](results/training_complete.json) · [最终 Skill](results/final_skill.md) |
| 测试结果 | [完成记录](results/test_complete.json) · [成绩摘要](results/v25_2_prompt_only_20261101_001_test280/summary.json) · [实际受测 Skill](results/v25_2_prompt_only_20261101_001_test280/evaluated_skill.md) |
| 本机原始材料 | [逐轮记录](../../../../artifacts/methods/v25_2/v25_2_prompt_only_20261101_001/campaign) · [逐题终报](../../../../artifacts/methods/v25_2/v25_2_prompt_only_20261101_001_test280/summary.json) · [R04 与 R06 恢复记录](../../../../artifacts/methods/v25_2/v25_2_prompt_only_20261101_001/recoveries) |
| 当时的文档 | [启动前说明](reports/README.md) · [运行日志](reports/RUN_STATUS.md) |

完整现场位于 Git 忽略的 `artifacts/`。原始回执中的旧路径保留撰写时的值，旧实验目录的本机链接用于回查。

## 逐轮发布

[发布清单](results/publications.json)记录 R00–R08 的实际保留 Skill、原始位置及 SHA-256。[R00](results/skills/R00.md) · [R08](results/skills/R08.md)

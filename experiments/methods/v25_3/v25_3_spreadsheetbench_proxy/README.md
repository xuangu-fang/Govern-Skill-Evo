# SpreadsheetBench v25.3 正式实验

代理线路实验完成全部 8 轮训练，每轮使用 15 题。R08 发布的 Selected Skill 参加完整首测。280 题中整题成功 214 题（76.43%），逐题单元格通过率均值为 85.87%。

| 材料 | 位置 |
|---|---|
| 方法与运行命令 | [v25.3 方法说明](../../../../docs/methods/v25_3/README.md) |
| 训练输入 | [训练配置](config/config.json) · [执行契约](config/campaign/contract.json) · [训练 Docker 环境](config/campaign/runtime.json) |
| 首测输入 | [评测配置](config/evaluation/config.json) · [入口记录的 Python、Docker 环境与评分器](config/runtime.json) |
| 训练结果 | [完成回执](results/training_complete.json) · [最终 Skill](results/final_skill.md) |
| 首测结果 | [成绩摘要](results/v25_3_spreadsheetbench_proxy_test280/summary.json) · [实际受测 Skill](results/v25_3_spreadsheetbench_proxy_test280/evaluated_skill.md) |
| 本机原始记录 | [逐轮训练](../../../../artifacts/methods/v25_3/v25_3_spreadsheetbench_proxy/campaign/rounds) · [恢复记录](../../../../artifacts/methods/v25_3/v25_3_spreadsheetbench_proxy/recoveries) · [完整首测终报](../../../../artifacts/methods/v25_3/v25_3_spreadsheetbench_proxy_test280/summary.json) |

v25.4 的[设计清单](../../../../docs/methods/v25_4/design_manifest.json)从上表读取五份输入。完整训练现场与逐题轨迹存放在 Git 忽略的 `artifacts/`。

## 逐轮发布

[发布清单](results/publications.json)记录 R00–R08 的实际保留 Skill、原始位置及 SHA-256。[R00](results/skills/R00.md) · [R08](results/skills/R08.md)

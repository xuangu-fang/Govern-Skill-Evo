# SpreadsheetBench v25.5 官方线路实验

官方线路使用 `deepseek-flash` 完成 8 轮训练，每轮 15 题。R08 保留的同一份最终 Skill 在同一组 280 题上完成两次评测。两次评测的 Actor 配置仅最大并发数不同。

| 评测 | 整题成功 | 整题成功率 | 最大并发 | 材料 |
|---|---:|---:|---:|---|
| 完整首测 | 225/280 | 80.36% | 4 | [摘要](results/v25_5_spreadsheetbench_deepseek_test280/summary.json) · [受测 Skill](results/v25_5_spreadsheetbench_deepseek_test280/evaluated_skill.md) · [原始终报](../../../../artifacts/methods/v25_5/v25_5_spreadsheetbench_deepseek_test280/summary.json) |
| 同一 Skill 全量复测 | 230/280 | 82.14% | 40 | [摘要](results/v25_5_spreadsheetbench_deepseek_full_40w_20261108_1730/summary.json) · [受测 Skill](results/v25_5_spreadsheetbench_deepseek_full_40w_20261108_1730/evaluated_skill.md) · [原始终报](../../../../artifacts/methods/v25_5/v25_5_spreadsheetbench_deepseek_full_40w_20261108_1730/summary.json) |

- [正式训练配置](config/config.json) · [首测配置](config/evaluation/config.json) · [运行环境](config/runtime.json)
- [训练完成回执](results/training_complete.json) · [最终 Skill](results/final_skill.md) · [监督进程完成记录](reports/watch_status.json)
- [逐轮训练](../../../../artifacts/methods/v25_5/v25_5_spreadsheetbench_deepseek/campaign/rounds) · [当次官方线路启动脚本](../../../../artifacts/methods/v25_5/v25_5_spreadsheetbench_deepseek/supervise.py) · [40 并发复测启动记录](../../../../artifacts/methods/v25_5/v25_5_spreadsheetbench_deepseek/reruns/full_40w_20261108_1730)
- [方法、运行入口和离线验收命令](../../../../docs/methods/v25_5/README.md)

完整训练和逐题轨迹归入本机 Git 忽略的 `artifacts/`。每张摘要记录对应的原始终报路径。

## 逐轮发布

[发布清单](results/publications.json)记录 R00–R08 的实际保留 Skill、原始位置及 SHA-256。[R00](results/skills/R00.md) · [R08](results/skills/R08.md)

# SpreadsheetBench v25.4 实验记录

本次代理线路训练完成 8 轮，每轮 15 题。四次评测使用同一个 R08 最终 Skill。首测和全量复测按相同顺序评估 280 题；复测使用官方调用线路和 40 个并发工作进程。两次定向诊断各自的题号保存在对应摘要中。

| 评测 | 整题成功 | Actor 模型 | 最大并发 | 材料 |
|---|---:|---|---:|---|
| 首次完整测试 | 225/280 | deepseek-v4.1-flash | 4 | [摘要](results/v25_4_spreadsheetbench_proxy_test280/summary.json) · [受测 Skill](results/v25_4_spreadsheetbench_proxy_test280/evaluated_skill.md) · [逐题终报](../../../../artifacts/methods/v25_4/v25_4_spreadsheetbench_proxy_test280/summary.json) |
| 同一 Skill 全量复测 | 222/280 | deepseek-flash | 40 | [摘要](results/v25_4_spreadsheetbench_proxy_full_40w_20261108_1650/summary.json) · [受测 Skill](results/v25_4_spreadsheetbench_proxy_full_40w_20261108_1650/evaluated_skill.md) · [逐题终报](../../../../artifacts/methods/v25_4/v25_4_spreadsheetbench_proxy_full_40w_20261108_1650/summary.json) |
| 4 题定向诊断 | 3/4 | deepseek-v4.1-flash | 4 | [摘要](results/v25_4_spreadsheetbench_proxy_four_test_tasks_20261108_113020/summary.json) · [受测 Skill](results/v25_4_spreadsheetbench_proxy_four_test_tasks_20261108_113020/evaluated_skill.md) · [逐题终报](../../../../artifacts/methods/v25_4/v25_4_spreadsheetbench_proxy_four_test_tasks_20261108_113020/summary.json) |
| 10 题定向诊断 | 8/10 | deepseek-v4.1-flash | 4 | [摘要](results/v25_4_spreadsheetbench_proxy_unique_failures_20261108_101739/summary.json) · [受测 Skill](results/v25_4_spreadsheetbench_proxy_unique_failures_20261108_101739/evaluated_skill.md) · [逐题终报](../../../../artifacts/methods/v25_4/v25_4_spreadsheetbench_proxy_unique_failures_20261108_101739/summary.json) |

- [正式训练配置](config/config.json) · [执行契约](config/campaign/contract.json) · [训练时的 Docker 环境](config/campaign/runtime.json)
- [首次评测配置](config/evaluation/config.json) · [入口记录的 Python、Docker 环境和评分器](config/runtime.json)
- [训练完成回执](results/training_complete.json) · [最终 Skill](results/final_skill.md) · [历史离线验收记录](reports/offline_acceptance.json)
- [逐轮训练](../../../../artifacts/methods/v25_4/v25_4_spreadsheetbench_proxy/campaign/rounds) · [R07 恢复现场](../../../../artifacts/methods/v25_4/v25_4_spreadsheetbench_proxy/recovery_r07) · [全量复测启动记录](../../../../artifacts/methods/v25_4/v25_4_spreadsheetbench_proxy/reruns/full_40w_20261108_1650)
- [方法与验收命令](../../../../docs/methods/v25_4/README.md) · [使用本版作为基线的 v25.5 设计清单](../../../../docs/methods/v25_5/design_manifest.json)

训练现场和四份完整评测保存在本机 Git 忽略的 `artifacts/`。历史输入、回执和轨迹保留原文。

## 逐轮发布

[发布清单](results/publications.json)记录 R00–R08 的实际保留 Skill、原始位置及 SHA-256。[R00](results/skills/R00.md) · [R08](results/skills/R08.md)

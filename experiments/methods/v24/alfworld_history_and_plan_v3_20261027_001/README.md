# ALFWorld v24 正式训练

训练使用 8 个 Actor worker，启用了知识核验。 六轮共 57 个优化任务，最终发布的 Skill 来自 R04。

[版本索引](../README.md) · [训练配置](config/campaign.json) · [运行环境](config/runtime.json) · [Test 题单](data/test.json)

[最终 Skill](results/final_skill.md) · [逐轮训练摘要](results/training_summary.json) · [结果报告](reports/REPORT.md) · [原始发布状态](../../../../artifacts/methods/v24/alfworld_history_and_plan_v3_20261027_001/S1/state.json)

| Test | 成功题数 | 记录 |
|---|---:|---|
| 首测 | 121/134 | [摘要](results/alfworld_history_and_plan_v3_20261027_001_test134/summary.json) · [逐题记录](../../../../artifacts/methods/v24/alfworld_history_and_plan_v3_20261027_001_test134/summary.json) |

已完成的历史 Test 可用[只读归档入口](../../../../scripts/runs/v24/read_archived_test.py)核对。旧回执记录的是整理前的绝对路径，读取时会按路径映射定位轨迹。以本次首测为例，在仓库根目录执行

```sh
python scripts/runs/v24/read_archived_test.py artifacts/methods/v24/alfworld_history_and_plan_v3_20261027_001_test134
```

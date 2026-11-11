# ALFWorld v24.1 正式训练

官方模型配置从[已复审的准备配置](../alfworld_reviewed_no_review_workers10_20261030_001/README.md)派生。Actor 和优化器使用官方 deepseek-flash，训练并发为 10。 六轮共 57 个优化任务，最终发布的 Skill 来自 R06。

[版本索引](../README.md) · [训练配置](config/campaign.json) · [运行环境](config/runtime.json) · [Test 题单](data/test.json)

[最终 Skill](results/final_skill.md) · [逐轮训练摘要](results/training_summary.json) · [结果报告](reports/REPORT.md) · [原始发布状态](../../../../artifacts/methods/v24_1/alfworld_reviewed_no_review_workers10_official_deepseek_flash_20261030_001/S1/state.json)

| Test | 成功题数 | 记录 |
|---|---:|---|
| 首测 | 121/134 | [摘要](results/alfworld_reviewed_no_review_workers10_official_deepseek_flash_20261030_001_test134/summary.json) · [逐题记录](../../../../artifacts/methods/v24_1/alfworld_reviewed_no_review_workers10_official_deepseek_flash_20261030_001_test134/summary.json) |
| 复测 | 119/134 | [摘要](results/v24_1_alfworld_retest134_20261107_231217/summary.json) · [逐题记录](../../../../artifacts/methods/v24_1/v24_1_alfworld_retest134_20261107_231217/summary.json) |

已完成的历史 Test 可用[只读归档入口](../../../../scripts/runs/v24/read_archived_test.py)核对。旧回执记录的是整理前的绝对路径，读取时会按路径映射定位轨迹。以本次首测为例，在仓库根目录执行

```sh
python scripts/runs/v24/read_archived_test.py artifacts/methods/v24_1/alfworld_reviewed_no_review_workers10_official_deepseek_flash_20261030_001_test134
```

[两处模型路由的配置差异](config/provenance/alignment.json) · [当时的联合调度计划](../../../automations/alfworld_v24_1_skilladam_20261030_001/plan.json)

[启动日志与进程回执](../../../../artifacts/methods/v24_1/alfworld_reviewed_no_review_workers10_official_deepseek_flash_20261030_001/launch) · [首测执行记录](results/alfworld_reviewed_no_review_workers10_official_deepseek_flash_20261030_001_test134/execution.json) · [首测日志与退出状态](../../../../artifacts/methods/v24_1/alfworld_reviewed_no_review_workers10_official_deepseek_flash_20261030_001_test134/launch)

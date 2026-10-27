# campaign_integration_001

本目录保存 2026-10-22 总运行器集成与离线验收的历史材料。报告中的“真实 Benchmark 尚未启动”和初始状态对应当时的检查点；后续正式运行情况见 [正式实验入口](../v23_4_alfworld_formal_001/README.md)。

## 保留材料

- [REPORT.md](REPORT.md)、[RESULTS.json](RESULTS.json)：历史结论和测试摘要。
- [首次准备](preparation.json)、[代理路由准备](preparation_proxy.json)、[最终预检](final_preflight.json)、[环境预检](live_environment_preflight.json)。
- 被替换路由的 [原因](superseded_official_route/REASON.txt)、[源码与协议快照](superseded_official_route/campaign/contract.json)、[运行环境](superseded_official_route/campaign/runtime.json)、[初始状态](superseded_official_route/campaign/state.json)、[空初始 Memory](superseded_official_route/campaign/initial_memory/active.json)。这些材料没有对应的真实模型或 Actor 执行。
- 旧方案的 [预算](superseded_official_route/experiment/config/budget.json)、[方法](superseded_official_route/experiment/config/method.json)、[任务清单](superseded_official_route/experiment/data/)。

## 完整日志与旧配置归档

八个完整文件按原相对层级存于 [本地归档](../../../../artifacts/methods/v23_4/campaign_integration_001/)：

- [整体测试日志](../../../../artifacts/methods/v23_4/campaign_integration_001/pytest.log)：历史记录为 1,024 passed、1 deselected。
- [代理路由测试日志](../../../../artifacts/methods/v23_4/campaign_integration_001/pytest_proxy.log)：历史记录为 48 passed。
- [测试收集日志](../../../../artifacts/methods/v23_4/campaign_integration_001/collection.log)：当时收集 349 项测试。
- 旧 Campaign 的 [config.json](../../../../artifacts/methods/v23_4/campaign_integration_001/superseded_official_route/campaign/config.json)、[initial_config.json](../../../../artifacts/methods/v23_4/campaign_integration_001/superseded_official_route/campaign/initial_config.json)。
- 旧 experiment 的 [campaign.json](../../../../artifacts/methods/v23_4/campaign_integration_001/superseded_official_route/experiment/config/campaign.json)、[evaluation.json](../../../../artifacts/methods/v23_4/campaign_integration_001/superseded_official_route/experiment/config/evaluation.json)、[provenance.json](../../../../artifacts/methods/v23_4/campaign_integration_001/superseded_official_route/experiment/config/provenance.json)。

旧配置只供追溯；正式配置仍在正式实验目录。历史 JSON 中的日志路径保留原文，可通过 [公共读取工具](../archive_io.py) 定位归档。以上测试数字来自原日志，本次文件整理没有重跑测试或实验。完整原始数据被 Git 忽略，仅克隆 Git 不包含归档文件。

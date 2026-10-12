# v5 实验材料

本目录保存可版本化实验证据；[基准定义与原型入口](../../../benchmarks/standalone/editions/v5/README.md)与[研究文档](../../../docs/benchmarks/v5/README.md)分别维护。

| 材料 | 配置 / 冻结 | 精选结果 |
|---|---|---|
| 四原型工程验证 | 原型定义见基准目录 | [46 条预期路径摘要](prototype-engineering/results.json) |
| 真实模型校准 | [协议](calibration/protocol.json)、[冻结清单](calibration/freeze.json) | [主实验与预算诊断汇总](calibration/results.json) |
| D1/D2 决策探测 | [复现说明](decision_probe/README.md)、[协议](decision_probe/protocol.json) | [结果](decision_probe/results.json)、[去留](decision_probe/decisions.json) |
| LS1/LG1 学习实验 | [复现说明](learning/README.md)、[协议](learning/protocol.json)、[等待补充](learning/latency_protocol.json) | [结果与结论](learning/results.json) |

完整运行产物位于本机 [artifacts/benchmarks/v5](../../../artifacts/benchmarks/v5)。结果 JSON、配置和冻结清单在此次迁移中保持原始字节，包括历史路径和哈希；没有重评分或改写实验结论。

旧结果内的路径应通过 [迁移映射](../../../benchmarks/path-map.json)定位。历史严格运行器需要匹配其冻结源码；当前目录下直接执行旧实验校验可能拒绝运行，详见 [历史核验与复现边界](../../../docs/repository/BENCHMARK_LAYOUT.md)。不要通过修改冻结哈希继续旧实验。

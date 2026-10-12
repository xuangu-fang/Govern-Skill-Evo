# 决策困难最小试跑：D1 / D2

> 目录已迁移，见[历史冻结与复现说明](../../../../docs/repository/BENCHMARK_LAYOUT.md)。下文历史分析/运行入口保留严格哈希检查，须在匹配冻结源码的工作副本中执行；单元测试可在当前目录运行。

独立Dev诊断，15次真实deepseek-v4-flash执行，5个条件各3次；不加入原四个v5原型注册表，不改v4，不接Skill/Memory。D3/D4没有在本轮实现或运行。

- [冻结协议](../../../../docs/benchmarks/v5/DECISION_PROBE.md#benchmark-v5-minimal-probe-protocol)
- [配置](protocol.json)
- [结果与去留报告](../../../../docs/benchmarks/v5/DECISION_PROBE.md#benchmark-v5-minimal-probe-report)
- [聚合结果](results.json)
- [原始执行目录](../../../../artifacts/benchmarks/v5/decision-probe-20261010-001)
- [环境](../../../../src/benchmark_v5/probe/environment.py)、[私有评价](../../../../src/benchmark_v5/probe/evaluation.py)、[运行器](../../../../src/benchmark_v5/probe/runner.py)、[本地重放分析](../../../../src/benchmark_v5/probe/analyze.py)

模型只见用户目标、公开工具和返回信息，不见私有评价或轨迹文件。确定性ask_user可提供必需事实；没有自由文本用户Simulator。支付和改签均为本地合成沙盒，非生产业务服务。

以下只运行本地测试或分析，不产生模型调用：

```sh
PYTHONPATH=src python3 -m unittest discover -s tests/benchmarks/v5/probe -v
PYTHONPATH=src python3 -m benchmark_v5.probe.analyze
```

冻结前执行`python3 -m benchmark_v5.probe.runner freeze`，实际模型运行入口为`python3 -m benchmark_v5.probe.runner run`（均需`PYTHONPATH=src`）。固定目录禁止重复冻结；已完成episode跳过，遗留未完成episode须审计，不自动重跑。新研究应另建协议和目录，不能改变本次冻结文件后继续拼接结果。只需查看既有结果时不要调用run。

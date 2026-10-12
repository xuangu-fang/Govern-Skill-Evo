# Benchmark V4 源码

`environment/` 提供 V4 的环境注册和新增 JRA-01 联合任务环境；其余任务直接复用 [V3 实现](../benchmark_v3/README.md)。V4 共 81 个任务，任务定义和划分保留在 [V4 数据目录](../../benchmarks/tau2_governed_evolution/editions/phase_v4_day36)。

[构建与校验脚本](../../scripts/benchmarks/v4)负责生成任务清单、联合任务准入和离线环境检查；[测试](../../tests/benchmarks/v4)检查版本结构与准入约束。

```sh
python -m scripts.benchmarks.validate_editions phase_v4_day36
PYTHONPATH=.:src:external/tau2-bench/src python -m pytest tests/benchmarks/v4 -q
```

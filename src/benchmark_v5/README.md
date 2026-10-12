# Benchmark V5 源码

V5 的实现统一放在此包中。包根目录保留基础环境、会话、评测及原型命令入口，各实验功能按子包区分。

| 位置 | 内容 |
| --- | --- |
| 包根目录 | 确定性环境、工具会话、原型评测与校验 |
| `calibration/` | 模型校准、传输与预算探测 |
| `probe/` | 最小决策探测 |
| `learning/` | 学习实验、经验构建、接口修订与恢复 |
| `sa/` | SA 环境、规则及离线校验 |
| `sc/` | S/C 评测、试运行与重评分 |

从项目根目录使用新模块路径，例如：

```sh
PYTHONPATH=src python -m benchmark_v5 --help
PYTHONPATH=src python -m benchmark_v5.calibration.runner --help
PYTHONPATH=src python -m benchmark_v5.learning.runner --help
PYTHONPATH=.:src python -m pytest tests/benchmarks/v5 -q
```

配置与结果见 [V5 实验](../../experiments/benchmarks/v5)，定义与数据见 [V5 benchmark](../../benchmarks/standalone/editions/v5)，协议与报告见 [V5 文档](../../docs/benchmarks/v5)。

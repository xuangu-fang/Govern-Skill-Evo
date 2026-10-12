# Benchmark V3 源码

这里集中保存 Phase Benchmark V3 的环境、工具、评测与运行适配实现。`development/` 是 Day 34 的开发版，`final/` 是 Day 35 的 73 任务版；二者属于同一 V3 发展过程。它们与方法 V03、Governed 谱系的 V3 是不同版本序列。

| 子目录 | 归属 |
| --- | --- |
| `development/` | 早期环境、统一领域工具、候选机制及其评测 |
| `final/` | 73 任务版的环境入口、数据构造函数与历史运行适配 |
| `construction/` | 正式版及 V4 复用的机制实现、评测器和保留的候选原型 |

V4 直接导入这里的共用实现，不复制源码。[跨版本基础模块](../benchmark_shared/README.md)单独归类。

任务、策略文本和研究数据仍在 [Day 34 数据](../../benchmarks/tau2_governed_evolution/editions/phase_v3_day34)、[Day 35 数据](../../benchmarks/tau2_governed_evolution/editions/phase_final_candidate_day35)及[构造材料](../../benchmarks/tau2_governed_evolution/final_candidate)中。代码中的数据路径明确指向这些位置，不依赖源码与数据相邻。

执行入口见 [V3 脚本](../../scripts/benchmarks/v3)。离线结构检查：

```sh
python -m scripts.benchmarks.validate_editions phase_v3_day34 phase_final_candidate_day35
```

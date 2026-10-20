# Benchmark 系列与版本

按“研究系列 → edition”组织基准。方法 v18/v19/v20/v21 的版本号不属于此处的 benchmark 版本序列。

| 系列 | 版本入口 | 状态 |
|---|---|---|
| [τ² Governed Evolution](tau2_governed_evolution/README.md) | [8 个命名 editions](tau2_governed_evolution/editions) | Governed 与 Phase 两条谱系，分别保留历史身份 |
| [Standalone](standalone/README.md) | [v5](standalone/editions/v5/README.md) | 独立合成原型，尚未冻结为正式任务集 |
| [ALFWorld](alfworld/README.md) | [SkillOpt 39/18/134](alfworld/editions/skillopt_39_18_134/README.md) | 已保存固定划分并检查本机文件，已接入单任务和 NoSkill Test 评测入口 |

## 内容归属

- `benchmarks/<系列>/editions/<版本>/`：基准定义、任务、划分、版本证据和原型入口。
- [experiments/benchmarks/v5](../experiments/benchmarks/v5/README.md)：v5 校准/探测/学习实验的协议、冻结清单、精选结果。
- [artifacts/benchmarks/v5](../artifacts/benchmarks/v5)：本机完整运行产物，Git 忽略；克隆仓库后不一定存在。
- [docs/benchmarks/v5](../docs/benchmarks/v5/README.md)：设计、业务契约和研究报告。
- 源码统一导航：[V3](../src/benchmark_v3/README.md)、[V4](../src/benchmark_v4/README.md)、[V5](../src/benchmark_v5/README.md)、[跨版本共享实现](../src/benchmark_shared/README.md)。测试位于 `tests/benchmarks/`，执行脚本位于 `scripts/benchmarks/`。

τ² 的任务、划分、模板和业务定义保留在本目录；Python 实现已全部迁入 `src/`、`scripts/` 和 `tests/`。配置与精选报告见 [benchmark 实验材料](../experiments/benchmarks/README.md)，完整运行材料位于 `artifacts/benchmarks/`。Governed V1–V3 与 Phase V1–V4 是不同谱系，不能按相同数字混并。

## 路径迁移与核验

[第 2 步整理记录](../docs/repository/BENCHMARK_LAYOUT.md) · [旧路径映射与摘要](path-map.json)

旧冻结清单中的路径和摘要保留原文；使用映射查阅当前文件，使用快照核对历史源码。快照匹配不等于当前源码仍与旧冻结版本相同。

```sh
python3 scripts/maintenance/verify_benchmark_layout.py
python3 -m scripts.benchmarks.validate_editions
```

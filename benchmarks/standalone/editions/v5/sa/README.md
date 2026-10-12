# S-A isolated engineering prototype

> 目录已迁移，见[历史冻结与复现说明](../../../../../docs/repository/BENCHMARK_LAYOUT.md)。旧归档的 `--verify` 检查冻结源码，须使用匹配的历史工作副本；当前单元测试和纯内存 `offline.validate()` 可直接运行。

本包是2026-10-12的合成工程验证，不是正式Benchmark任务集。没有模型调用或Skill更新；C/SC为N/A。

- [业务契约](../../../../../docs/benchmarks/v5/SA.md#benchmark-v5-sa-contract)
- [离线核验报告](../../../../../docs/benchmarks/v5/SA.md#benchmark-v5-sa-offline-report)
- [源码](../../../../../src/benchmark_v5/sa)
- [运行结果](../../../../../artifacts/benchmarks/v5/sa-offline-20261012-001/results.json)

```sh
PYTHONPATH=src python3 -m unittest discover -s tests/benchmarks/v5/sa -v
PYTHONPATH=src python3 -m benchmark_v5.sa.validate --output artifacts/benchmarks/v5/sa-offline-20261012-001 --verify
```

`Environment.request()/catalog()/call()`是公开适配面，`audit()`及`World`只供维护侧使用。`learning_observation()`仅导出受控Train请求、实际工具结果与统一反馈，Dev拒绝。没有实现LLM运行器，后续不得直接把环境对象或源码交给模型。

开发样例在`fixtures.py`手工定义。`offline.py`中的可行性求解器使用真规则；公开启发式仅获得工具回调，两类结果分开。历史作业由受控计划采集，不伪称真实Agent探索。

当前状态：25项测试通过、57条归档轨迹可重放；有限64项候选族可由8批记录识别，但一个无历史经验的组合启发式7/7。**本版本仅保留工程锚点，暂不进入Flash校准。** 不增设限制堵住该策略。

归档目录禁止覆盖。新离线运行需新目录及运行前`protected_before.json`保护摘要，再调用`python -m benchmark_v5.sa.validate --output <新目录>`。如只需重做逻辑核验而不写归档，可调用`benchmark_v5.sa.offline.validate()`；不访问网络。验证器检查源码、原始轨迹、评分和历史文件摘要，`--verify`不会修改旧结果。

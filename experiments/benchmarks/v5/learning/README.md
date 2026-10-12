# Benchmark v5 学习型环境与校准

> 目录已迁移，见[历史冻结与复现说明](../../../../docs/repository/BENCHMARK_LAYOUT.md)。下文涉及历史冻结校验的命令须在匹配源码的工作副本中执行，不应改写旧哈希；当前接口与单元测试可直接使用。

LS1售后结算与LG1资料替代的隔离合成诊断，独立于v21。当前可复用入口是 `benchmark_v5.learning.current`：导出接口0.2的build和评价器0.2的evaluate。历史执行入口继续使用各自冻结版本，不应覆盖。

- [最终报告与去留](../../../../docs/benchmarks/v5/LEARNING.md#benchmark-v5-learning-report)
- [设计规格](../../../../docs/benchmarks/v5/LEARNING_SPEC.md#benchmark-v5-learning-spec)
- [原冻结协议](../../../../docs/benchmarks/v5/LEARNING.md#benchmark-v5-learning-protocol)
- [等待补充](../../../../docs/benchmarks/v5/LEARNING.md#benchmark-v5-learning-latency-protocol)与[独立条件续行](../../../../docs/benchmarks/v5/LEARNING.md#benchmark-v5-learning-partial-protocol)
- [接口修订复核](../../../../docs/benchmarks/v5/LEARNING.md#benchmark-v5-learning-interface-protocol)与[依据记录评分修正](../../../../docs/benchmarks/v5/LEARNING.md#benchmark-v5-learning-grader-correction)

固定共同经验，文本学习状态接口不要求Skill或Memory。仅调用deepseek-v4-flash。主计划44格中实际执行40格，4格因LS1无有效归纳产物而缺测；另有4格独立接口复核，不与主比较混算。10个开发留出实例不是最终盲测Test，外部业务代表性和跨世界泛化待验证。

## 当前接口

```python
from benchmark_v5.learning.current import build, evaluate
# case/world由维护侧提供；不能将其私有字段传给实验Agent。
env = build(case, world)
public_request = env.request()
public_tools = env.catalog()
# Agent仅能调用env.call(name, arguments)；evaluate和audit只在维护侧运行。
private_score = evaluate(env.audit())
```

## 验证与复现

```bash
PYTHONPATH=src python -m unittest discover -s tests/benchmarks/v5/learning -v
PYTHONPATH=src python -m benchmark_v5.learning.recover validate
PYTHONPATH=src python -m benchmark_v5.learning.recover analyze
PYTHONPATH=src python -m benchmark_v5.learning.interface_probe validate
PYTHONPATH=src python -m benchmark_v5.learning.rescore artifacts/benchmarks/v5/learning-20261011-002
PYTHONPATH=src python -m benchmark_v5.learning.rescore artifacts/benchmarks/v5/learning-interface-20261011-003
```

已有run不重跑或覆盖；freeze命令仅用于首次封存，遇到半成品必须先审计。新实验应另立ID/协议。恢复执行入口为recover，接口复核为interface_probe；参数、预算与适用范围见各自冻结协议。连接凭据只在传输层使用，不进入轨迹。

## 证据目录

- `artifacts/benchmarks/v5/learning-20261010-001`：原等待预算下的2次超时及接口健康诊断，没有留出执行。
- `artifacts/benchmarks/v5/learning-20261011-002`：主freeze、21条训练观察、学习产物、44格状态、40条真实trace/audit/result、重放、原分析、独立修正评分与格式敏感性审计。
- `artifacts/benchmarks/v5/learning-interface-20261011-003`：4条独立接口复核与审计。
- 本目录`results.json`：便于版本管理的汇总与决定；私有逐题记录仍在artifact目录，不向Agent公开。

冻结训练/测试载荷和规则含维护侧答案，不能直接让被测Agent读取仓库。主结果的10个预算异常episode、4个未执行格及1个评分误扣修正单列，不能当作正常业务难度或人工补成功。

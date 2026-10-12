# Benchmark v5 隔离工程原型

> 材料导航：[实验配置与精选结果](../../../../experiments/benchmarks/v5/README.md) · [目录迁移与历史冻结说明](../../../../docs/repository/BENCHMARK_LAYOUT.md)。下文旧实验的严格复核命令须在匹配冻结源码的历史工作副本中执行；当前源码契约测试可直接运行。

后续独立决策困难筛选见[最小试跑目录](../../../../experiments/benchmarks/v5/decision_probe/README.md)和[去留报告](../../../../docs/benchmarks/v5/DECISION_PROBE.md#benchmark-v5-minimal-probe-report)：D1/D2共15次Flash执行均成功，保留基础锚点，停止复杂候选扩展。该实现位于独立`benchmark_v5.probe`，不改变下述四原型注册表和历史结果。

版本 `v5-prototype-0.1`。仅 Dev：S2、G2、I1、K2 四个标准原型及少量确定性边界检查；第6步已完成真实模型首轮校准；没有隐藏 Test、Skill 优化或 v21 Memory 接口。完整设计见[Draft 0.3](../../../../docs/benchmarks/v5/DESIGN.md#benchmark-v5-design-draft)，本次证据见[第5步工程验证报告](../../../../docs/benchmarks/v5/PROTOTYPES.md#benchmark-v5-engineering-validation)。

## 运行

在仓库根目录，使用 Python 3.10+；只依赖标准库，不安装或修改 tau2。

```sh
PYTHONPATH=src python -m unittest discover -s tests/benchmarks/v5/prototypes -v
PYTHONPATH=src python -m benchmark_v5 validate --output artifacts/benchmarks/v5/my-new-run
PYTHONPATH=src python -m benchmark_v5 serve S2 --audit-out artifacts/benchmarks/v5/my-private-session.json
PYTHONPATH=src python -m benchmark_v5 evaluate artifacts/benchmarks/v5/my-private-session.json
```

输出目录/文件须不存在，防止覆盖历史证据。`validate` 会保存46份私有审计轨迹和`summary.json`；返回码非零表示工程期望不匹配或基础设施异常。没有网络或模型调用。

`serve` 首行输出用户请求、JSON工具schema与调用预算。随后每个输入行形如：

```json
{"tool":"read_order","arguments":{}}
```

每行只返回工具结果；`finish`或调用预算/输入结束关闭本次服务。Agent看不到评分、私有初态、审计快照或反例期望。运行宿主在结束后保存`--audit-out`，可用独立`evaluate`重评分。未来接模型时，不要把证据目录、Python宿主或私有评分接口授予Agent。

## 文件与边界

- [scenarios.json](prototypes/scenarios.json)：四个小型合成初态；仅宿主载入。金额一律整数分，美元；G2时刻含明确时区。
- [engineering_results.json](../../../../experiments/benchmarks/v5/prototype-engineering/results.json)：本轮46条工程期望核对摘要、来源摘要和既有文件隔离结果。成功/失败象限是预设诊断行为的结果，不是模型能力统计。
- [运行实现](../../../../src/benchmark_v5)：状态转换、工具目录、结构化用户/批准响应、私有评分器、参考行为和CLI。
- [契约测试](../../../../tests/benchmarks/v5/prototypes/test_prototypes.py)：合法等价顺序、事件时点、范围边界、重放、原子性、信息边界和评分反例。

隔离注册表只有S2/G2/I1/K2；不导入`skill_evolution`、tau2或v4工具。所有付款、退款和授权均为本地沙盒状态。

本阶段以结构化回执测准确反馈，不使用自然语言判分器；未实现开放式用户对话、进程崩溃恢复或物流后台。状态在单次episode中跨调用保留，超时不会抹掉提交，审计在运行结束后写文件；这不是生产数据库的持久性保证。公共`AgentSession`供可信参考脚本使用，进程内Python对象本身不是针对恶意代码的安全沙盒。

K2从已知交接与目标v2开始，不测试从零办理中的在线需求变更。G2的不可行边界检查声明独立成功类型，不混入标准退款完成率。S1/G1/I2/G3仍是规格，本轮未实现。

## 第6步真实校准

[报告](../../../../docs/benchmarks/v5/CALIBRATION.md#benchmark-v5-calibration-report)、[协议](../../../../docs/benchmarks/v5/CALIBRATION.md#benchmark-v5-calibration-protocol)、[配置](../../../../experiments/benchmarks/v5/calibration/protocol.json)、[冻结摘要](../../../../experiments/benchmarks/v5/calibration/freeze.json)、[结果](../../../../experiments/benchmarks/v5/calibration/results.json)。独立适配器在`src/benchmark_v5/calibration`，原型环境和评分保持第5步摘要不变。

本地`.env`或环境变量提供`OPENAI_BASE_URL`/`OPENAI_API_KEY`；请求体归档不含鉴权头。运行真实模型会产生调用成本。下面的run命令仅用于明确需要的新实验目录；重复执行不是无成本分析。已有完成结果会跳过，遗留未完成目录须审计，不自动从头重跑。新协议不要覆盖现有冻结清单。

```sh
PYTHONPATH=src python -m unittest discover -s tests/benchmarks/v5/calibration -v
PYTHONPATH=src python -m benchmark_v5.calibration.runner run --output artifacts/benchmarks/v5/a-new-calibration
PYTHONPATH=src python -m benchmark_v5.calibration.analyze artifacts/benchmarks/v5/step6-20261010-001
PYTHONPATH=src python -m benchmark_v5.calibration.analyze artifacts/benchmarks/v5/step6-budget-20261010-001
```

最后两条仅本地重放/分析，不调用模型。原72次主实验和独立18次预算诊断各自保留，不能混合作为正式Test分数。主实验2次代理usage超请求上限，原结果与预算一致性过滤结果并列记录。`budget_probe`是一次性补充driver，目录和协议已冻结，不能反复覆盖调用择优。

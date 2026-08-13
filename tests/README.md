# 测试目录

本目录保存项目自己实现代码的自动化测试。目录结构尽量与`src/`保持对应，便于从实现文件找到相关测试。

表格中保留了测试文件和程序字段的英文名称。几个常用概念是：Schema 表示数据格式规则，Verifier 表示校验程序，Human Gold 表示人工审核的标准答案，Campaign 表示一次完整的正式实验。

## 目录说明

| 目录 | 当前测试内容 |
|---|---|
| `adapters/tau2/` | τ³原始结果到正式`TrajectoryDataset`的转换。 |
| `trajectory/` | 检查统一任务记录能否正确保存、读取、验证事件顺序，以及从 v0.1 迁移到 v0.2。 |
| `verifiers/` | 检查任务成功判断、固定规则校验、AI 语义校验以及与人工标准答案的比较。 |
| `skill_evolution/` | 检查 Autonomous GSE 的协议、任务分批、步骤流转、候选生成、预算限制、正式运行边界和冻结规则。 |

## 主要测试文件

| 测试文件 | 对应实现 |
|---|---|
| `adapters/tau2/test_tau2_to_common.py` | `src/adapters/tau2/tau2_to_common.py` |
| `trajectory/test_schema.py` | `src/trajectory/schema.py` |
| `trajectory/test_migration_v01_to_v02.py` | `src/trajectory/migrations/v01_to_v02.py` |
| `verifiers/test_task_verifier.py` | `src/verifiers/task_verifier.py` |
| `verifiers/test_process_verifier.py` | 规则处理程序注册、中间判断参数、结果汇总逻辑及多规则完整运行。 |
| `verifiers/handlers/deterministic/test_transfer_protocol.py` | 转人工工具调用和通知顺序。 |
| `verifiers/handlers/deterministic/test_tool_response_exclusivity.py` | 工具调用和用户回复互斥，包括多tool calls顺序执行口径。 |
| `verifiers/handlers/deterministic/test_payment_method_ownership.py` | 付款方式归属的合规、违规、证据不足和未触发场景。 |
| `verifiers/handlers/semantic/test_transfer_scope.py` | 检查“是否应该转人工”的提示词隔离、AI 中间判断和最终规则结果。 |
| `verifiers/handlers/semantic/test_write_confirmation.py` | 检查写操作详情、明确确认、打包确认、执行顺序和 AI 中间判断。 |
| `verifiers/evaluators/test_transfer_scope.py` | 检查转人工判断与人工标准答案的比较指标和数据覆盖。 |
| `verifiers/evaluators/test_write_confirmation.py` | 检查写操作确认与人工标准答案的字段指标、证据步骤和数据覆盖。 |
| `skill_evolution/test_autonomous_gse_protocol.py` | 检查正式实验和步骤的数据格式、演化门槛代表性案例，以及冻结文件绑定。 |
| `skill_evolution/test_batch_planner.py` | 检查51个任务能否稳定分成三批、各模板分布均衡、任务不重叠且结果可复现。 |
| `skill_evolution/test_autonomous_gse_controller.py` | 检查步骤进度、最终结果、当前版本与评测基准的继承关系，以及非法状态转换。 |
| `skill_evolution/test_autonomous_gse_proposal.py` | 检查候选提议格式，以及初始生成和增量修改两种方式。 |
| `skill_evolution/test_autonomous_gse_runtime.py` | 在不调用外部 API 的情况下检查三步流程、预算和 Test 隔离。 |
| `skill_evolution/test_autonomous_gse_benchmark_runtime.py` | 检查提示词和 Learner 绑定、最多123条任务记录的预算路径、内部任务入口、四个日常命令及正式文件状态保护。 |
| `skill_evolution/test_autonomous_gse_freeze.py` | 检查最终运行前校验、冻结记录只能写入一次，以及检查失败时必须停止。 |

## 运行测试

从项目根目录运行本项目的全部测试：

```bash
python -m pytest -q tests
```

不要在项目根目录直接运行不带路径的`pytest -q`。仓库中的`external/`包含第三方项目及其测试，裸命令会同时收集这些测试，并可能因为第三方可选依赖未安装而在收集阶段报错。

只运行某一部分：

```bash
pytest -q tests/trajectory
pytest -q tests/verifiers
pytest -q tests/adapters/tau2
```

只运行单个测试文件：

```bash
pytest -q tests/verifiers/handlers/semantic/test_transfer_scope.py
```

单元测试不得调用真实外部模型。AI 语义校验测试使用假的模型调用函数，检查提示词是否泄漏答案、JSON 能否解析、证据步骤是否正确，以及中间判断能否得到预期的最终合规结果。

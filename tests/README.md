# 测试目录

本目录保存项目自己实现代码的自动化测试。目录结构尽量与`src/`保持对应，便于从实现文件找到相关测试。

## 目录说明

| 目录 | 当前测试内容 |
|---|---|
| `adapters/tau2/` | τ³原始结果到正式`TrajectoryDataset`的转换。 |
| `trajectory/` | Schema序列化、反序列化、事件顺序校验，以及v0.1到v0.2迁移。 |
| `verifiers/` | Task Verifier、Deterministic Process Verifier、Semantic Process Verifier及Human Gold评估。 |

## 主要测试文件

| 测试文件 | 对应实现 |
|---|---|
| `adapters/tau2/test_tau2_to_common.py` | `src/adapters/tau2/tau2_to_common.py` |
| `trajectory/test_schema.py` | `src/trajectory/schema.py` |
| `trajectory/test_migration_v01_to_v02.py` | `src/trajectory/migrations/v01_to_v02.py` |
| `verifiers/test_task_verifier.py` | `src/verifiers/task_verifier.py` |
| `verifiers/test_process_verifier.py` | 通用handler注册、rule_id judgments参数、汇总真值表及多规则端到端运行。 |
| `verifiers/handlers/deterministic/test_transfer_protocol.py` | 转人工工具调用和通知顺序。 |
| `verifiers/handlers/deterministic/test_tool_response_exclusivity.py` | 工具调用和用户回复互斥，包括多tool calls顺序执行口径。 |
| `verifiers/handlers/deterministic/test_payment_method_ownership.py` | 付款方式归属的合规、违规、证据不足和未触发场景。 |
| `verifiers/handlers/semantic/test_transfer_scope.py` | 是否应该转人工的Prompt、judgments和规则结果。 |
| `verifiers/handlers/semantic/test_write_confirmation.py` | 写操作详情、明确确认、打包确认、顺序校验及中间判断。 |
| `verifiers/evaluators/test_transfer_scope.py` | transfer-scope Human Gold指标和覆盖检查。 |
| `verifiers/evaluators/test_write_confirmation.py` | write-confirmation Human Gold字段指标、证据step和覆盖检查。 |

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

单元测试不得调用真实外部模型。Semantic Process Verifier测试通过注入假的模型调用函数，验证Prompt隔离、JSON解析、证据step、中间判断和最终ComplianceVerdict。

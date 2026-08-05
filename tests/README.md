# 测试目录

本目录保存项目自己实现代码的自动化测试。目录结构尽量与`src/`保持对应，便于从实现文件找到相关测试。

## 目录说明

| 目录 | 当前测试内容 |
|---|---|
| `adapters/tau2/` | τ³原始结果到正式`TrajectoryDataset`的转换。 |
| `trajectory/` | Schema序列化、反序列化、事件顺序校验，以及v0.1到v0.2迁移。 |
| `verifiers/` | Semantic Judge输出校验、Human Gold评估和Process Verifier合并逻辑。 |

## 主要测试文件

| 测试文件 | 对应实现 |
|---|---|
| `adapters/tau2/test_tau2_to_common.py` | `src/adapters/tau2/tau2_to_common.py` |
| `trajectory/test_schema.py` | `src/trajectory/schema.py` |
| `trajectory/test_migration_v01_to_v02.py` | `src/trajectory/migrations/v01_to_v02.py` |
| `verifiers/test_transfer_scope_judge.py` | `src/verifiers/transfer_scope_judge.py` |
| `verifiers/test_transfer_scope_verifier.py` | `src/verifiers/transfer_scope_verifier.py` |
| `verifiers/test_evaluate_transfer_scope_judge.py` | `src/verifiers/evaluate_transfer_scope_judge.py` |

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
pytest -q tests/verifiers/test_transfer_scope_judge.py
```

单元测试不得调用真实外部模型。Semantic Judge测试通过注入假的模型调用函数，验证Prompt隔离、JSON解析、证据step和输出Schema。

`__pycache__/`是Python生成的本地缓存，不属于测试数据。
